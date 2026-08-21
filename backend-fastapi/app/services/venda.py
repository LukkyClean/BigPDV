from datetime import datetime

from sqlalchemy.orm import Session
from typing import Sequence

from app.db.models.venda import Venda
from app.db.models.venda_produto import ProdutoVenda
from app.db.models.venda_pagamento import PagamentoVenda
from app.db.models.contador_venda import ContadorVenda
from app.schemas.vendas import VendaCreate, VendaSearchFilters, VendaStatusSummary, VendaUpdate, ProdutoVendaCreate, ProdutoVendaUpdate, PagamentoVendaCreate, VendaRead

from app.services.cliente import cliente_exists
from app.services.funcionario import funcionario_exists
from app.services import produto as produto_service
from app.services import sessao_caixa as caixa_service

from app.db.crud import venda as venda_crud
from app.db.crud import forma_pagamento as forma_pagamento_crud
from app.db.crud import configuracao_produtos as config_produtos_crud
from app.db.crud import configuracao_vendas as config_vendas_crud
from app.db.crud import configuracao_seguranca as config_seg_crud

from app.core.enum import VendaStatus, TipoProdutoVenda

from app.helpers.set_pagination import _set_pagination
from app.core.security import verify_password
from app.helpers.exceptions import BadRequestException, InternalServerException, NotFoundException

def _recalc_total_sale(db: Session, sale_in_db: Venda, *, sai_da_fila: bool = True) -> Venda:

    if sale_in_db.total_bruto < sale_in_db.descontos:
        raise BadRequestException(detail="O desconto não pode ser maior que o total da venda")

    total_sale = sale_in_db.total_bruto - sale_in_db.descontos + (sale_in_db.acrescimo or 0)

    sale_in_db.subtotal = sale_in_db.total_bruto
    sale_in_db.total = total_sale

    # MUDOU O VALOR DO CARRINHO, A VENDA SAI DA FILA DO CAIXA.
    #
    # Se o atendente acrescentar um item depois de entregar, o caixa fica
    # olhando um total que mudou embaixo dele. Custa um reenvio ao atendente e
    # evita cobrar valor errado.
    #
    # A regra mora AQUI porque este e o ponto de estrangulamento: acrescentar,
    # alterar e remover item, e aplicar desconto, todos passam por esta funcao.
    # Repeti-la nos quatro chamadores seria quatro chances de esquecer uma.
    #
    # `finish_sale` passa `sai_da_fila=False`, e e a unica excecao: la quem esta
    # mexendo e o proprio caixa, a venda esta saindo da fila pela porta certa, e
    # apagar o carimbo perderia o registro de que ela chegou a esperar.
    if sai_da_fila:
        sale_in_db.enviada_ao_caixa_em = None

    return venda_crud.update_sale(db, sale_in_db)


def enviar_ao_caixa(db: Session, sale_id: int) -> Venda:
    """O atendente entrega a venda ao caixa.

    Nao muda o status: a venda continua ATIVA. O que muda e o carimbo que a
    lista usa para separar "pronta, esperando o caixa" de "ainda sendo montada".

    IDEMPOTENTE de proposito. Reenviar mantem o carimbo original -- senao um
    clique repetido mandaria o atendente para o fim da fila sem que ninguem
    tivesse feito nada de errado.
    """
    sale_in_db = get_sale_by_id(db, sale_id=sale_id)

    # A fila e opcional. A tela ja esconde o botao quando a chave esta desligada,
    # mas quem garante que nao entra venda na fila de uma loja que nao usa fila e
    # esta checagem -- o frontend pode estar mais novo que a configuracao, e foi
    # exatamente assim que a chave do PIN pareceu quebrada num teste na loja.
    empresa_id = sale_in_db.funcionario.empresa_id
    config = config_vendas_crud.get_configuracao_vendas(db, empresa_id=empresa_id)
    if not (config and config.usar_fila_do_caixa):
        raise BadRequestException(
            detail="A fila do caixa não está ligada em Configurações > Regras de Vendas"
        )

    if sale_in_db.status != VendaStatus.ATIVA:
        raise BadRequestException(detail="Só uma venda em aberto pode ir para o caixa")

    # Carrinho vazio na fila e ruido: o caixa abre e nao ha o que cobrar.
    if not sale_in_db.itens:
        raise BadRequestException(detail="Adicione ao menos um item antes de enviar ao caixa")

    if sale_in_db.enviada_ao_caixa_em is None:
        sale_in_db.enviada_ao_caixa_em = datetime.utcnow()

    return venda_crud.update_sale(db, sale_in_db)


def devolver_para_montagem(db: Session, sale_id: int) -> Venda:
    """Tira a venda da fila do caixa, sem mexer em mais nada.

    Qualquer operador pode: o atendente que se arrependeu e o caixa que viu
    problema. Como a coluna e so sinal de lista, nao ha nada a desfazer alem
    dela -- nenhum dinheiro foi movido para entrar na fila.

    NAO checa `usar_fila_do_caixa`, ao contrario do enviar. Se o dono desligar a
    chave com vendas ainda na fila, elas precisam poder sair -- recusar aqui as
    deixaria carimbadas para sempre, sem tela nenhuma para desfazer.
    """
    sale_in_db = get_sale_by_id(db, sale_id=sale_id)

    if sale_in_db.status != VendaStatus.ATIVA:
        raise BadRequestException(detail="Só uma venda em aberto pode voltar para montagem")

    sale_in_db.enviada_ao_caixa_em = None
    return venda_crud.update_sale(db, sale_in_db)

def _aplly_discount(sale_in_db: Venda, discount: int) -> Venda:
    items_subtotal = sum(item.subtotal for item in sale_in_db.itens)
    discount_remaining = discount
    for index, item in enumerate(sale_in_db.itens):
        if index == len(sale_in_db.itens) - 1:
            item.desconto = discount_remaining
        else:
            item_discount = (item.subtotal * discount) // (items_subtotal or 1)
            item.desconto = item_discount
            discount_remaining -= item_discount
    return sale_in_db

def _payments_valid(db: Session, payments: Sequence[PagamentoVendaCreate]) -> Sequence[PagamentoVenda]:
    sale_payments: Sequence[PagamentoVenda] = []
    for payment in payments:
        payment_type = forma_pagamento_crud.get_forma_pagamento_by_id(db, payment.forma_pagamento_id)
        if not payment_type:
            raise BadRequestException(detail="Pagamentos devem ser uma forma válida")
        if payment.parcelado and payment.qtd_parcelas is None:
            raise BadRequestException(detail="Pagamentos parcelados devem ter no mínimo 1 parcela")
        if not payment.parcelado and payment.qtd_parcelas is not None:
            raise BadRequestException(detail="Pagamentos a vista não deve ter parcelas")
        dados = payment.model_dump()
        # O enum é str-subclass, mas gravamos o `.value` explicitamente para que a
        # coluna String nunca dependa da representação do Enum.
        dados["juros_responsavel"] = payment.juros_responsavel.value
        sale_payments.append(PagamentoVenda(**dados))
    return sale_payments

def create_sale(db: Session, sale: VendaCreate) -> VendaRead:
    # Valida existência de cliente (se informado) e funcionário.
    # `funcionario_exists` existe pelo efeito -- levanta se nao achar.
    if sale.cliente_id is not None:
        cliente_exists(db, sale.cliente_id)
    funcionario_exists(db, sale.funcionario_id)

    # AQUI NAO HA TRAVA DE CAIXA -- e a ausencia e deliberada.
    #
    # Ate 21/08/2026 esta funcao chamava `exigir_caixa_aberto_para_vender`, e o
    # comentario de entao ja admitia que aquilo era CORTESIA: "a trava existe
    # tambem na finalizacao, e la e a garantia de verdade -- e o momento do
    # dinheiro". Montar carrinho nao move dinheiro nenhum; so `finish_sale` move.
    #
    # Tirar a cortesia e o que permite o atendente montar a venda e o CAIXA
    # receber, sem que os dois precisem de turno aberto no proprio nome. O
    # dinheiro continua caindo no turno de quem recebe -- isso e `finish_sale` e
    # `registrar_pagamentos_de_venda`, e nenhum dos dois mudou.
    #
    # E de graca fecha o beco da maquina RETAGUARDA, que escondia a barra do
    # caixa mas continuava sendo cobrada por `exigir_caixa_aberto`: ficava sem o
    # botao de abrir E sem poder vender.
    #
    # O QUE VEIO NO LUGAR, no frontend: a barra do caixa avisa que a venda pode
    # ser montada mas nao finalizada. Sem esse aviso, quem trabalha sozinho na
    # loja montaria o carrinho inteiro para descobrir no checkout -- que era
    # exatamente o atrito que a linha removida evitava.

    sale_data = Venda(
        **sale.model_dump(exclude_unset=True),
        status=VendaStatus.ATIVA
    )

    return venda_crud.create_sale(db, sale_data=sale_data)

def update_sale(db: Session, sale_id: int, update_data: VendaUpdate) -> Venda:
    sale_in_db = get_sale_by_id(db, sale_id=sale_id)
    if sale_in_db.status != VendaStatus.ATIVA:
        raise BadRequestException(detail="Venda não pode ser editada")

    update_fields = update_data.model_dump(exclude_unset=True)

    if 'cliente_id' in update_fields:
        if update_data.cliente_id is not None:
            customer_in_db = cliente_exists(db, update_data.cliente_id)
            sale_in_db.cliente_id = customer_in_db.id
        else:
            sale_in_db.cliente_id = None

    if update_data.funcionario_id:
        funcionario_in_db = funcionario_exists(db, update_data.funcionario_id)
        sale_in_db.funcionario_id = funcionario_in_db.id

    if update_data.entrega is not None:
        sale_in_db.entrega = update_data.entrega

    if update_data.desconto is not None:
        if update_data.desconto > sale_in_db.subtotal:
            raise BadRequestException(detail="O desconto não pode ser maior que o total da venda")
        empresa_id = sale_in_db.funcionario.empresa_id
        config_vendas = config_vendas_crud.get_configuracao_vendas(db, empresa_id=empresa_id)
        config_seg = config_seg_crud.get_configuracao_seguranca(db, empresa_id=empresa_id)
        if config_vendas and config_vendas.permitir_desconto and sale_in_db.subtotal > 0 and update_data.desconto > 0:
            percentual = (update_data.desconto * 100) // sale_in_db.subtotal
            if percentual > config_vendas.desconto_maximo_percent:
                if config_seg and config_seg.requer_pin_desconto_venda and config_seg.pin_gerente:
                    codigo = update_data.codigo_gerente
                    if not codigo:
                        raise BadRequestException(detail="REQUER_APROVACAO_GERENTE")
                    if not verify_password(codigo, config_seg.pin_gerente):
                        raise BadRequestException(detail="PIN_GERENTE_INVALIDO")
                else:
                    raise BadRequestException(
                        detail=f"Desconto máximo permitido é de {config_vendas.desconto_maximo_percent}%"
                    )
        sale_in_db = _aplly_discount(sale_in_db=sale_in_db, discount=update_data.desconto)

    if update_data.observacao is not None:
        sale_in_db.observacao = update_data.observacao

    return _recalc_total_sale(db, sale_in_db=sale_in_db)

def add_item_to_sale(db: Session, sale_id: int, item_data: ProdutoVendaCreate) -> tuple[Venda, ProdutoVenda]:
    sale_in_db = get_sale_by_id(db, sale_id=sale_id)
    if sale_in_db.status != VendaStatus.ATIVA:
        raise BadRequestException(detail="Venda não pode ser editada")
    
    quantidade = item_data.quantidade
    valor_unitario = item_data.valor_unitario
    desconto = item_data.desconto

    if item_data.produto_id:
        if item_data.tipo_produto == TipoProdutoVenda.AVULSO:
            raise BadRequestException(detail="Um produto avulso não pode estar cadastrado")

        product_in_db = produto_service.get_produto_by_id(db, produto_id=item_data.produto_id)

        estoque_disponivel = product_in_db.estoque.quantidade
        if quantidade > estoque_disponivel:
            empresa_id = sale_in_db.funcionario.empresa_id
            config = config_produtos_crud.get_configuracao_produtos(db, empresa_id=empresa_id)
            permitir = config.permitir_venda_estoque_zerado if config else False
            if not permitir:
                raise BadRequestException(detail=f"Quantidade em estoque insuficiente para o produto {product_in_db.nome}")

        valor_unitario = product_in_db.estoque.valor_varejo
    if item_data.tipo_produto == TipoProdutoVenda.AVULSO and item_data.descricao_avulsa is None:
        raise BadRequestException(detail="Um produto avulso deve ter descrição")

    if desconto > quantidade * valor_unitario:
        raise BadRequestException(detail="O desconto não pode ser maior que o total do produto")
    
    subtotal = quantidade * valor_unitario

    product_data = ProdutoVenda(
        **item_data.model_dump(exclude={"valor_unitario"}),
        venda_id=sale_id,
        valor_unitario=valor_unitario,
        subtotal=subtotal
    )

    product_in_db = venda_crud.add_product_to_sale(db, product_data)

    sale_in_db = _recalc_total_sale(db, sale_in_db)

    return sale_in_db, product_in_db

def update_item_in_sale(db: Session, sale_id: int, item_id: int, item_update: ProdutoVendaUpdate) -> tuple[Venda, ProdutoVenda]:

    sale_in_db = get_sale_by_id(db, sale_id=sale_id)
    if sale_in_db.status != VendaStatus.ATIVA:
        raise BadRequestException(detail="Venda não pode ser editada")
    
    item_in_db = venda_crud.get_product_by_id(db, item_id=item_id)
    if not item_in_db or item_in_db.venda_id != sale_id:
        raise NotFoundException(detail="Produto não encontrado")
    
    if item_in_db.tipo_produto == TipoProdutoVenda.CADASTRADO:
        if item_update.descricao_avulsa:
            raise BadRequestException(detail="Um produto cadastrado não pode ter descrição avulsa")
        if item_update.valor_unitario:
            empresa_id = sale_in_db.funcionario.empresa_id
            config_seg = config_seg_crud.get_configuracao_seguranca(db, empresa_id=empresa_id)
            pin_configurado = bool(config_seg and config_seg.pin_gerente)
            permite_com_pin = config_seg and config_seg.requer_pin_alterar_preco_venda and pin_configurado
            if not permite_com_pin:
                raise BadRequestException(detail="Um produto cadastrado não pode ter valor unitário definido manualmente")
            codigo = item_update.codigo_gerente
            if not codigo:
                raise BadRequestException(detail="REQUER_APROVACAO_GERENTE")
            if not verify_password(codigo, config_seg.pin_gerente):
                raise BadRequestException(detail="PIN_GERENTE_INVALIDO")

    quantidade = item_update.quantidade or (item_in_db.quantidade or 0)

    if item_in_db.produto.estoque.quantidade < quantidade:
        empresa_id = sale_in_db.funcionario.empresa_id
        config = config_produtos_crud.get_configuracao_produtos(db, empresa_id=empresa_id)
        permitir = config.permitir_venda_estoque_zerado if config else False
        if not permitir:
            raise BadRequestException(detail=f"Quantidade em estoque insuficiente para o produto {item_in_db.nome}")
    
    preco_unitario = item_update.valor_unitario or (item_in_db.valor_unitario or 0)
    
    desconto = item_in_db.desconto or 0
    if item_update.desconto is not None:
        desconto = item_update.desconto
    
    subtotal = quantidade * preco_unitario
    
    if subtotal < desconto:
        raise BadRequestException(detail="O desconto não pode ser maior que o valor total do produto")
        
    item_in_db.descricao_avulsa = item_update.descricao_avulsa or item_in_db.descricao_avulsa
    item_in_db.quantidade = quantidade
    item_in_db.valor_unitario = preco_unitario
    # Custo interno só existe no avulso. No cadastrado o custo vem do livro de
    # estoque, e aceitar um valor aqui criaria dois números divergentes para a
    # mesma peça — com o relatório somando os dois.
    if item_update.custo_unitario is not None:
        if item_in_db.tipo_produto == TipoProdutoVenda.CADASTRADO:
            raise BadRequestException(
                detail="Produto cadastrado tem o custo vindo do estoque; não informe custo manual"
            )
        item_in_db.custo_unitario = item_update.custo_unitario
    item_in_db.desconto = desconto
    item_in_db.subtotal = subtotal

    item_in_db = venda_crud.update_product_in_sale(db, item_in_db)
    
    sale_in_db = _recalc_total_sale(db, sale_in_db)

    return sale_in_db, item_in_db
    
def remove_item_from_sale(db: Session, sale_id: int, item_id: int) -> None:
    sale_in_db = get_sale_by_id(db, sale_id=sale_id)
    if sale_in_db.status != VendaStatus.ATIVA:
        raise BadRequestException(detail="Venda não pode ser editada")
    
    item_in_db = venda_crud.get_product_by_id(db, item_id=item_id)
    if not item_in_db or item_in_db.venda_id != sale_id:
        raise NotFoundException(detail="Produto não encontrado")

    venda_crud.remove_product_from_sale(db, item_in_db)
    
    return _recalc_total_sale(db, sale_in_db)

def delete_draft_sale(db: Session, sale_id: int) -> None:
    sale_in_db = get_sale_by_id(db, sale_id=sale_id)
    if sale_in_db.status != VendaStatus.ATIVA:
        raise BadRequestException(detail="Apenas vendas ativas podem ser descartadas")
    db.delete(sale_in_db)
    db.commit()


def finish_sale(
    db: Session,
    sale_id: int,
    payments: Sequence[PagamentoVendaCreate],
    acrescimo: int = 0,
    operador_funcionario_id: int | None = None,
):
    sale_in_db = get_sale_by_id(db, sale_id=sale_id)

    if sale_in_db.status != VendaStatus.ATIVA:
        raise BadRequestException(detail="Esta venda não pode ser finalizada")

    empresa_id = sale_in_db.funcionario.empresa_id
    config_vendas = config_vendas_crud.get_configuracao_vendas(db, empresa_id=empresa_id)
    if config_vendas and config_vendas.exigir_cliente_identificado and not sale_in_db.cliente_id:
        raise BadRequestException(detail="Esta venda exige um cliente identificado para ser finalizada")

    # Trava do caixa: so morde quando a loja ligou AS DUAS chaves
    # (`controlar_caixa` e `exigir_caixa_aberto`). Loja que nao ligou nada passa
    # reto -- e o que mantem as tres lojas em producao vendendo como sempre.
    caixa_service.exigir_caixa_aberto_para_vender(
        db, sale_in_db.funcionario, operador_funcionario_id
    )

    valid_payments_to_db = _payments_valid(db, payments)

    # Valida parcelamento
    if config_vendas:
        for p in valid_payments_to_db:
            if p.parcelado and not config_vendas.permitir_parcelamento:
                raise BadRequestException(detail="Parcelamento não é permitido nas configurações de vendas")
            if p.parcelado and p.qtd_parcelas and p.qtd_parcelas > config_vendas.parcelas_maximas:
                raise BadRequestException(detail=f"Máximo de {config_vendas.parcelas_maximas} parcelas permitido")

    # Aplica o acréscimo (juros de cartão informado no checkout) e recalcula o total.
    # O valor de cada pagamento já vem com o juros embutido; o acréscimo entra no
    # total para que o excedente não seja tratado como troco.
    sale_in_db.acrescimo = acrescimo or 0
    # `sai_da_fila=False`: quem esta mexendo aqui e o proprio caixa, e a venda
    # esta saindo da fila pela porta certa. Ver `_recalc_total_sale`.
    sale_in_db = _recalc_total_sale(db, sale_in_db, sai_da_fila=False)

    total_payments = sum(payment.valor for payment in valid_payments_to_db)
    total_sale = sale_in_db.total or 0

    if total_payments < total_sale:
        raise BadRequestException(detail="Os pagamentos não conferem ao total da venda")

    # Valida valor mínimo de venda
    if config_vendas and config_vendas.valor_minimo_venda > 0 and total_sale < config_vendas.valor_minimo_venda:
        raise BadRequestException(detail=f"Valor mínimo de venda não atingido")

    # Zera desconto se exceder o limite configurado no momento da finalização
    empresa_id = sale_in_db.funcionario.empresa_id
    config_vendas = config_vendas_crud.get_configuracao_vendas(db, empresa_id=empresa_id)
    if config_vendas and config_vendas.permitir_desconto and sale_in_db.total_bruto > 0 and sale_in_db.descontos > 0:
        percentual = (sale_in_db.descontos * 100) // sale_in_db.total_bruto
        if percentual > config_vendas.desconto_maximo_percent:
            sale_in_db = _aplly_discount(sale_in_db=sale_in_db, discount=0)
            sale_in_db = _recalc_total_sale(db, sale_in_db, sai_da_fila=False)

    # Atribui número sequencial oficial
    contador = db.query(ContadorVenda).filter(ContadorVenda.id == 1).with_for_update().first()
    if not contador:
        raise InternalServerException(detail="Contador de vendas não inicializado. Contate o suporte.")
    sale_in_db.numero_venda = contador.proximo_numero
    contador.proximo_numero += 1

    products_in_db = sale_in_db.itens

    for product in products_in_db:
        if product.tipo_produto == TipoProdutoVenda.CADASTRADO:
            produto_service.decrease_product_in_stock(db, produto_id=product.produto_id, quantidade=product.quantidade, funcionario_id=sale_in_db.funcionario_id, venda_id=sale_in_db.id)

    sale_in_db.status = VendaStatus.FINALIZADA
    sale_in_db.pagamentos = valid_payments_to_db

    # Lanca os pagamentos no livro do dinheiro. Sai na primeira linha quando o
    # controle de caixa esta desligado, entao para quem nao usa esta chamada
    # custa uma consulta a configuracao e nada mais: nenhuma linha nova gravada.
    # Precisa vir DEPOIS do flush dos pagamentos, senao eles ainda nao teriam id
    # para o movimento apontar.
    db.flush()
    caixa_service.registrar_pagamentos_de_venda(db, sale_in_db, operador_funcionario_id)

    return venda_crud.update_sale(db, sale_in_db)

def cancel_sale(db: Session, sale_id: int, motivo: str, codigo_gerente: str | None = None) -> Venda:
    sale_in_db = get_sale_by_id(db, sale_id=sale_id)

    if sale_in_db.status != VendaStatus.FINALIZADA:
        raise BadRequestException("Apenas vendas finalizadas podem ser canceladas")

    empresa_id = sale_in_db.funcionario.empresa_id
    config_seg = config_seg_crud.get_configuracao_seguranca(db, empresa_id=empresa_id)
    if config_seg and config_seg.requer_pin_cancelar_venda and config_seg.pin_gerente:
        if not codigo_gerente:
            raise BadRequestException(detail="REQUER_APROVACAO_GERENTE")
        if not verify_password(codigo_gerente, config_seg.pin_gerente):
            raise BadRequestException(detail="PIN_GERENTE_INVALIDO")

    for product in sale_in_db.itens:
        if product.tipo_produto == TipoProdutoVenda.CADASTRADO:
            produto_service.restore_product_to_stock(
                db,
                produto_id=product.produto_id,
                quantidade=product.quantidade,
                funcionario_id=sale_in_db.funcionario_id,
                venda_id=sale_in_db.id,
            )

    sale_in_db.status = VendaStatus.CANCELADA
    sale_in_db.motivo_cancelamento = motivo
    return venda_crud.update_sale(db, sale_in_db)

def reopen_sale(db: Session, sale_id: int, codigo_gerente: str | None = None) -> Venda:
    sale_in_db = get_sale_by_id(db, sale_id=sale_id)

    if sale_in_db.status != VendaStatus.CANCELADA:
        raise BadRequestException(detail="Venda não pode ser reaberta")

    empresa_id = sale_in_db.funcionario.empresa_id
    config_seg = config_seg_crud.get_configuracao_seguranca(db, empresa_id=empresa_id)
    if config_seg and config_seg.requer_pin_reabrir_venda and config_seg.pin_gerente:
        if not codigo_gerente:
            raise BadRequestException(detail="REQUER_APROVACAO_GERENTE")
        if not verify_password(codigo_gerente, config_seg.pin_gerente):
            raise BadRequestException(detail="PIN_GERENTE_INVALIDO")

    sale_in_db.status = VendaStatus.ATIVA
    return venda_crud.update_sale(db, sale_in_db)

def get_sale_by_id(db: Session, sale_id: int) -> Venda:
    sale_in_db = venda_crud.get_sale_by_id(db, sale_id=sale_id)
    if not sale_in_db:
        raise NotFoundException(detail="Venda não encontrada")
    return sale_in_db

def get_sales(db: Session, filters: VendaSearchFilters, page: int, limit: int = 100) -> tuple[Sequence[Venda], int, int, dict]:
    skip = (page - 1) * limit

    filters_dict = filters.model_dump(exclude_unset=True)
    
    sales_in_db, total_sales = venda_crud.get_sales_by_search(
        db, filters=filters_dict, skip=skip, limit=limit
    )
    
    total_pages, links = _set_pagination(
        total_items=total_sales, filters=filters_dict, page=page, limit=limit
    )

    return sales_in_db, total_sales, total_pages, links

def get_sales_status(db: Session, funcionario_id: int | None = None) -> Sequence[VendaStatusSummary]:
    return venda_crud.get_sales_status(db, funcionario_id=funcionario_id)
    

    
        
        
    
    

    
