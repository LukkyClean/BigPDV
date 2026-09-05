# ---------------------------------------------------------------------------
# ARQUIVO: services/financeiro.py
# DESCRIÇÃO: Regras do módulo de gestão financeira — plano de contas, contas
#            bancárias, contas a pagar, baixa, estorno e o resumo do mês.
# ---------------------------------------------------------------------------
"""
A REGRA QUE ATRAVESSA TUDO AQUI: documento muda, lançamento não.

`contas_pagar` é DOCUMENTO. Prorrogar vencimento e corrigir valor digitado
errado são operações legítimas, e cada uma deixa rastro em
`historico_financeiro`.

`movimentacoes_financeiras` é LANÇAMENTO. Só insere. Um pagamento lançado por
engano não se apaga: estorna-se, com um movimento contrário na data de HOJE.

Confundir as duas camadas é o que faz ERP virar planilha com senha.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from app.core.enum import (
    ContaBancariaTipo,
    ContaPagarStatus,
    ContaReceberStatus,
    MovimentacaoFinanceiraOrigem,
    MovimentacaoFinanceiraTipo,
    PlanoContaTipo,
)
from app.core.tempo import agora_utc, fim_do_dia_utc, hoje_local, inicio_do_dia_utc
from app.db.crud import dashboard as dashboard_crud
from app.db.crud import financeiro as financeiro_crud
from app.db.crud import sessao_caixa as caixa_crud
from app.db.models.conta_bancaria import ContaBancaria
from app.db.models.conta_pagar import ContaPagar
from app.db.models.conta_receber import ContaReceber
from app.db.models.plano_conta import PlanoConta
from app.helpers.exceptions import BadRequestException, NotFoundException
from app.schemas.conta_bancaria import ContaBancariaCreate, ContaBancariaUpdate
from app.schemas.conta_pagar import (
    ContaPagarBaixa,
    ContaPagarCreate,
    ContaPagarEstorno,
    ContaPagarUpdate,
)
# `ContaReceberBaixa` é construído AQUI, no lote: cada cobrança do depósito é
# baixada pelo mesmo caminho da baixa manual, com o mesmo schema de entrada.
from app.schemas.conta_receber import ContaReceberBaixa
from app.schemas.financeiro import (
    AlertaFinanceiro,
    Conciliacao,
    ConciliacaoDia,
    ConciliacaoItem,
    ConciliacaoResultado,
    DespesaPorCategoria,
    Extrato,
    ExtratoLinha,
    FluxoCaixa,
    FluxoDia,
    FluxoLancamento,
    ResumoFinanceiro,
)
from app.schemas.plano_conta import PlanoContaCreate, PlanoContaUpdate

ENTIDADE_CONTA_PAGAR = "CONTA_PAGAR"


# ===========================================================================
# PLANO DE CONTAS
# ===========================================================================

# Semeadas no primeiro acesso. Não é adivinhação de negócio: são as despesas que
# TODA loja tem, independente do segmento -- a oficina, a assistência e a
# serigrafia pagam aluguel, luz e fornecedor igual.
#
# Existem porque um plano de contas vazio trava o módulo no primeiro uso: o
# lojista abre Contas a Pagar, vê que precisa de categoria, vai criar categoria,
# e desiste no meio. Ele pode apagar as que não usa; ver a lista e cortar é
# muito mais fácil do que encarar o branco.
# A PRIMEIRA É CUSTO, e não despesa: comprar mercadoria não empobrece a loja,
# converte dinheiro em estoque. Ela sai do caixa no dia da compra e só sai do
# LUCRO no dia em que a peça é vendida, pelo CMV -- classificá-la como despesa
# descontava a mesma peça duas vezes. Ver PlanoContaTipo e a migration
# f4a5b6c7d8e9, que reclassificou as lojas que já existiam.
PLANO_CONTAS_PADRAO: List[tuple[str, PlanoContaTipo]] = [
    ("Fornecedores / Mercadoria", PlanoContaTipo.CUSTO),
    ("Aluguel", PlanoContaTipo.DESPESA),
    ("Água, luz e internet", PlanoContaTipo.DESPESA),
    ("Salários e encargos", PlanoContaTipo.DESPESA),
    ("Impostos e taxas", PlanoContaTipo.DESPESA),
    ("Manutenção e equipamentos", PlanoContaTipo.DESPESA),
    ("Marketing", PlanoContaTipo.DESPESA),
    ("Outras despesas", PlanoContaTipo.DESPESA),
]


def _semear_plano_padrao(db: Session, empresa_id: int) -> None:
    """Cria as categorias padrão, uma única vez na vida da empresa.

    Roda na LISTAGEM, e não na criação da empresa, para alcançar também as lojas
    que já existem -- nenhuma delas passou por um `setup` que soubesse do módulo
    financeiro.

    A condição é "nunca semeou", e não "a lista está vazia": semear pela lista
    vazia faria as categorias ressuscitarem toda vez que o lojista apagasse
    todas, e ele nunca conseguiria dizer "não quero nenhuma dessas".
    """
    ja_semeou = (
        db.query(PlanoConta)
        .filter(PlanoConta.empresa_id == empresa_id, PlanoConta.padrao.is_(True))
        .first()
    )
    if ja_semeou:
        return

    # Se a loja já criou categoria à mão, ela não é uma instalação virgem —
    # semear por cima só empurraria itens que ela não pediu.
    tem_alguma = (
        db.query(PlanoConta).filter(PlanoConta.empresa_id == empresa_id).first()
    )
    if tem_alguma:
        return

    for nome, tipo in PLANO_CONTAS_PADRAO:
        financeiro_crud.criar_plano_conta(
            db,
            PlanoConta(
                empresa_id=empresa_id, nome=nome, tipo=tipo.value, padrao=True, ativo=True
            ),
        )


def listar_planos_conta(
    db: Session, empresa_id: int, apenas_ativos: bool = False
) -> List[Dict[str, Any]]:
    _semear_plano_padrao(db, empresa_id)

    planos = financeiro_crud.listar_planos_conta(db, empresa_id, apenas_ativos)
    em_uso = financeiro_crud.ids_de_planos_em_uso(db, empresa_id)

    return [
        {
            "id": p.id,
            "nome": p.nome,
            "tipo": p.tipo,
            "padrao": p.padrao,
            "ativo": p.ativo,
            "criado_em": p.criado_em,
            "em_uso": p.id in em_uso,
        }
        for p in planos
    ]


def criar_plano_conta(
    db: Session, empresa_id: int, dados: PlanoContaCreate
) -> Dict[str, Any]:
    nome = dados.nome.strip()
    if financeiro_crud.get_plano_conta_por_nome(db, empresa_id, nome):
        raise BadRequestException(detail=f"Já existe uma categoria chamada '{nome}'.")

    plano = financeiro_crud.criar_plano_conta(
        db, PlanoConta(empresa_id=empresa_id, nome=nome, tipo=dados.tipo.value)
    )
    return {
        "id": plano.id, "nome": plano.nome, "tipo": plano.tipo, "padrao": plano.padrao,
        "ativo": plano.ativo, "criado_em": plano.criado_em, "em_uso": False,
    }


def atualizar_plano_conta(
    db: Session, empresa_id: int, plano_id: int, dados: PlanoContaUpdate
) -> Dict[str, Any]:
    plano = financeiro_crud.get_plano_conta(db, empresa_id, plano_id)
    if not plano:
        raise NotFoundException(detail="Categoria não encontrada")

    if dados.nome is not None:
        nome = dados.nome.strip()
        existente = financeiro_crud.get_plano_conta_por_nome(db, empresa_id, nome)
        if existente and existente.id != plano.id:
            raise BadRequestException(detail=f"Já existe uma categoria chamada '{nome}'.")
        plano.nome = nome

    if dados.tipo is not None and dados.tipo.value != plano.tipo:
        # DESPESA <-> CUSTO é correção de classificação: as duas são saída, e o
        # que muda é QUANDO o gasto sai do lucro (no dia da compra ou no dia da
        # venda, pelo CMV). Recalcular meses passados com a regra certa é o
        # ponto, não um efeito colateral.
        #
        # Envolver RECEITA numa categoria já lançada é outra coisa: inverte o
        # sinal do dinheiro e transformaria despesa em receita no relatório sem
        # ninguém ter tocado numa conta.
        vira_receita = PlanoContaTipo.RECEITA.value in (dados.tipo.value, plano.tipo)
        if vira_receita and plano.id in financeiro_crud.ids_de_planos_em_uso(
            db, empresa_id
        ):
            raise BadRequestException(
                detail=(
                    "Esta categoria já tem contas lançadas e não pode virar (ou "
                    "deixar de ser) receita. Crie uma categoria nova."
                )
            )
        plano.tipo = dados.tipo.value

    if dados.ativo is not None:
        plano.ativo = dados.ativo

    db.flush()
    em_uso = plano.id in financeiro_crud.ids_de_planos_em_uso(db, empresa_id)
    return {
        "id": plano.id, "nome": plano.nome, "tipo": plano.tipo, "padrao": plano.padrao,
        "ativo": plano.ativo, "criado_em": plano.criado_em, "em_uso": em_uso,
    }


# ===========================================================================
# CONTAS BANCÁRIAS
# ===========================================================================

def _semear_conta_padrao(db: Session, empresa_id: int) -> None:
    """Garante ao menos 'Caixa da loja'.

    Sem nenhuma conta cadastrada, dar baixa exigiria criar uma antes -- e o
    lojista que só usa dinheiro nunca vai querer cadastrar banco nenhum. A
    gaveta é o mínimo que toda loja tem.
    """
    if db.query(ContaBancaria).filter(ContaBancaria.empresa_id == empresa_id).first():
        return
    financeiro_crud.criar_conta_bancaria(
        db,
        ContaBancaria(
            empresa_id=empresa_id,
            nome="Caixa da loja",
            tipo=ContaBancariaTipo.CAIXA.value,
            principal=True,
        ),
    )


def _conta_padrao_id(db: Session, empresa_id: int) -> Optional[int]:
    """A conta que recebe o dinheiro quando o lançamento não escolheu uma.

    Existe porque o saldo deixou de ser declarado e passou a ser derivado do
    livro: linha sem conta é dinheiro que entrou ou saiu e não aparece em saldo
    nenhum. Antes disso o campo era só um detalhe de auditoria e ficar nulo não
    custava nada.

    Semeia 'Caixa da loja' se não houver nenhuma, pela mesma razão de sempre --
    o lojista que só trabalha com dinheiro nunca vai cadastrar banco.
    """
    _semear_conta_padrao(db, empresa_id)
    conta = financeiro_crud.get_conta_principal(db, empresa_id)
    return conta.id if conta else None


def listar_contas_bancarias(
    db: Session, empresa_id: int, apenas_ativas: bool = False
) -> Sequence[ContaBancaria]:
    _semear_conta_padrao(db, empresa_id)
    return financeiro_crud.listar_contas_bancarias(db, empresa_id, apenas_ativas)


def criar_conta_bancaria(
    db: Session, empresa_id: int, dados: ContaBancariaCreate
) -> ContaBancaria:
    nome = dados.nome.strip()
    ja_existe = any(
        c.nome.lower() == nome.lower()
        for c in financeiro_crud.listar_contas_bancarias(db, empresa_id)
    )
    if ja_existe:
        raise BadRequestException(detail=f"Já existe uma conta chamada '{nome}'.")

    if dados.principal:
        financeiro_crud.limpar_principal(db, empresa_id)

    return financeiro_crud.criar_conta_bancaria(
        db,
        ContaBancaria(
            empresa_id=empresa_id, nome=nome, tipo=dados.tipo.value,
            principal=dados.principal,
        ),
    )


def atualizar_conta_bancaria(
    db: Session, empresa_id: int, conta_id: int, dados: ContaBancariaUpdate
) -> ContaBancaria:
    conta = financeiro_crud.get_conta_bancaria(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")

    if dados.nome is not None:
        conta.nome = dados.nome.strip()
    if dados.tipo is not None:
        conta.tipo = dados.tipo.value
    if dados.ativo is not None:
        conta.ativo = dados.ativo
    if dados.principal is not None:
        if dados.principal:
            financeiro_crud.limpar_principal(db, empresa_id, exceto_id=conta.id)
        conta.principal = dados.principal

    if dados.saldo_informado is not None:
        # A data é carimbada AQUI, e não recebida do cliente: ela é a prova de
        # quando o retrato foi tirado, e o Fluxo de Caixa avisa quando envelhece.
        # Deixar o cliente mandar a data permitiria declarar hoje um saldo
        # "de ontem" e o aviso nunca aparecer.
        conta.saldo_informado = dados.saldo_informado
        conta.saldo_informado_em = hoje_local()
        # E o INSTANTE, que é o corte de verdade do saldo derivado: só entra no
        # saldo o movimento posterior a ele. Sem isto, quem declara o saldo às
        # 15h veria a venda das 10h somada de novo -- ela já estava dentro do
        # número que ele contou na gaveta.
        conta.saldo_informado_instante = agora_utc()

    db.flush()
    return conta


# ===========================================================================
# CONTAS A PAGAR — leitura
# ===========================================================================

def _serializar_conta(conta: ContaPagar, hoje: date) -> Dict[str, Any]:
    """Monta o dicionário da tela, com os campos derivados de hoje.

    `vencida` e `dias_para_vencer` são calculados na leitura, nunca guardados:
    uma coluna "está vencida" precisaria de alguém rodando à meia-noite para
    acertá-la, e ficaria errada em toda máquina que passou a noite desligada --
    que é o caso de praticamente toda loja.
    """
    pendente = conta.status == ContaPagarStatus.PENDENTE.value
    dias = (conta.vencimento - hoje).days if pendente else None

    return {
        "id": conta.id,
        "descricao": conta.descricao,
        "valor": conta.valor,
        "vencimento": conta.vencimento,
        "status": conta.status,
        "plano_conta_id": conta.plano_conta_id,
        "plano_conta_nome": conta.plano_conta.nome if conta.plano_conta else None,
        "fornecedor_id": conta.fornecedor_id,
        "fornecedor_nome": getattr(conta.fornecedor, "nome", None),
        "valor_pago": conta.valor_pago,
        "pago_em": conta.pago_em,
        "conta_bancaria_id": conta.conta_bancaria_id,
        "conta_bancaria_nome": conta.conta_bancaria.nome if conta.conta_bancaria else None,
        "forma_pagamento_id": conta.forma_pagamento_id,
        "recorrente": conta.recorrente,
        "parcelamento_id": conta.parcelamento_id,
        "parcela_numero": conta.parcela_numero,
        "parcela_total": conta.parcela_total,
        "observacao": conta.observacao,
        "criado_em": conta.criado_em,
        "vencida": bool(pendente and conta.vencimento < hoje),
        "dias_para_vencer": dias,
    }


def listar_contas_pagar(
    db: Session,
    empresa_id: int,
    *,
    status: Optional[str] = None,
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    plano_conta_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    busca: Optional[str] = None,
    vencidas: bool = False,
    sem_categoria: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> Dict[str, Any]:
    hoje = hoje_local()

    # OS RECORTES DO PAINEL IGNORAM O MÊS, e essa é a parte que importa.
    #
    # `vencidas`: dívida vencida costuma ser de um mês que já passou.
    #
    # `sem_categoria`: a listagem filtra por VENCIMENTO, e o alerta nasce do que
    # foi PAGO no mês -- eixos diferentes. A Energia Solar paga em agosto vence
    # em setembro; com o recorte do mês, o atalho "Classificar" abriria uma
    # lista VAZIA. Um alerta que leva a lugar nenhum é pior que alerta nenhum.
    if vencidas or sem_categoria:
        inicio = fim = None

    itens, total_itens = financeiro_crud.listar_contas_pagar(
        db, empresa_id, status=status, inicio=inicio, fim=fim,
        plano_conta_id=plano_conta_id, fornecedor_id=fornecedor_id, busca=busca,
        vencidas=vencidas, sem_categoria=sem_categoria,
        limit=limit, offset=offset,
    )
    pendente, pago, vencido = financeiro_crud.totais_contas_pagar(
        db, empresa_id, hoje=hoje, inicio=inicio, fim=fim,
        plano_conta_id=plano_conta_id, fornecedor_id=fornecedor_id, busca=busca,
        vencidas=vencidas, sem_categoria=sem_categoria,
    )

    return {
        "itens": [_serializar_conta(c, hoje) for c in itens],
        "total_itens": total_itens,
        "total_pendente": pendente,
        "total_pago": pago,
        "total_vencido": vencido,
    }


def get_conta_pagar(db: Session, empresa_id: int, conta_id: int) -> Dict[str, Any]:
    conta = financeiro_crud.get_conta_pagar(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    return _serializar_conta(conta, hoje_local())


def listar_historico_da_conta(db: Session, empresa_id: int, conta_id: int):
    conta = financeiro_crud.get_conta_pagar(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    return financeiro_crud.listar_historico(
        db, empresa_id, ENTIDADE_CONTA_PAGAR, conta_id
    )


# ===========================================================================
# CONTAS A PAGAR — escrita
# ===========================================================================

def _funcionario_do_token(usuario_token: Dict[str, Any]) -> tuple[Optional[int], Optional[str]]:
    """(id, nome) de quem está operando, para o rastro.

    Tolerante a ausência: o Master pode não ter funcionário vinculado, e recusar
    o lançamento por isso deixaria o dono sem conseguir usar o próprio módulo.
    """
    return usuario_token.get("funcionario_id"), usuario_token.get("nome")


def _validar_referencias(
    db: Session, empresa_id: int, plano_conta_id: Optional[int]
) -> None:
    """Impede pendurar a conta numa categoria de OUTRA empresa.

    A FK do banco garante que o ID existe, não que ele é desta loja. Sem esta
    checagem, um ID chutado vazaria o nome da categoria alheia na listagem.
    """
    if plano_conta_id is not None:
        if not financeiro_crud.get_plano_conta(db, empresa_id, plano_conta_id):
            raise BadRequestException(detail="Categoria não encontrada")


def criar_conta_pagar(
    db: Session, empresa_id: int, dados: ContaPagarCreate, usuario_token: Dict[str, Any]
) -> Dict[str, Any]:
    """Cria a conta — ou TODAS as parcelas, quando `parcelas > 1`.

    Parcelamento gera tudo de uma vez, e não uma parcela por baixa como faz a
    recorrência. O motivo é que as dez parcelas JÁ SÃO dívida hoje: se nascessem
    conforme o pagamento, o fluxo de caixa de dezembro ficaria cego para a
    parcela de dezembro e diria que sobra dinheiro já comprometido.

    É também o que os ERPs fazem — o Odoo gera "um item contábil para cada data
    de vencimento" no momento em que a fatura é lançada.

    Devolve a PRIMEIRA parcela: é ela que a tela acabou de criar do ponto de
    vista do usuário, e é o começo do grupo.
    """
    _validar_referencias(db, empresa_id, dados.plano_conta_id)
    func_id, func_nome = _funcionario_do_token(usuario_token)

    descricao = dados.descricao.strip()
    total = dados.parcelas
    parcelado = total > 1

    primeira: Optional[ContaPagar] = None

    for numero in range(1, total + 1):
        # Sempre a partir do vencimento ORIGINAL, nunca da parcela anterior:
        # ancorar é o que impede o dia encolhido de ficar encolhido.
        vencimento = _somar_meses(dados.vencimento, numero - 1)

        conta = financeiro_crud.criar_conta_pagar(
            db,
            ContaPagar(
                empresa_id=empresa_id,
                descricao=descricao,
                valor=dados.valor,
                vencimento=vencimento,
                plano_conta_id=dados.plano_conta_id,
                fornecedor_id=dados.fornecedor_id,
                recorrente=dados.recorrente,
                observacao=dados.observacao,
                status=ContaPagarStatus.PENDENTE.value,
                parcela_numero=numero if parcelado else None,
                parcela_total=total if parcelado else None,
                # A primeira parcela aponta para si mesma; as demais para ela.
                # É o que dispensa tabela-pai e sequência — o grupo é o id da
                # primeira linha, que o flush do CRUD já devolveu.
                parcelamento_id=(primeira.id if primeira else None) if parcelado else None,
            ),
        )

        if primeira is None:
            primeira = conta
            if parcelado:
                conta.parcelamento_id = conta.id
                db.flush()

        # Só a primeira entra na auditoria: dez linhas de "criação" para uma
        # única compra afogariam a trilha, e o grupo já diz que são a mesma.
        if numero == 1:
            financeiro_crud.registrar_historico(
                db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_PAGAR,
                entidade_id=conta.id, campo="criacao", valor_antigo=None,
                valor_novo=f"{descricao} ({total}x)" if parcelado else descricao,
                funcionario_id=func_id, funcionario_nome=func_nome,
            )


    db.refresh(primeira)
    return _serializar_conta(primeira, hoje_local())


# Campos cuja alteração o histórico registra. Descrição e observação ficam de
# fora: corrigir uma vírgula na descrição não é fato financeiro, e encher a
# trilha de ruído faz ninguém ler a trilha.
CAMPOS_AUDITADOS = ("valor", "vencimento", "plano_conta_id", "fornecedor_id")


# O ÚNICO campo que ainda muda depois do pagamento: a categoria.
#
# Ela nunca entrou no livro do dinheiro, então corrigi-la não faz documento e
# lançamento discordarem -- e classificar despesa depois de paga é rotina em
# qualquer escritório de contabilidade.
#
# A lista é curta de propósito. Fornecedor e observação também não estão no
# livro e poderiam entrar aqui, mas nenhuma tela os edita hoje: backend que
# aceita mais do que a interface oferece é surpresa esperando para acontecer.
CAMPOS_LIVRES_APOS_PAGAMENTO = ("plano_conta_id",)


def atualizar_conta_pagar(
    db: Session,
    empresa_id: int,
    conta_id: int,
    dados: ContaPagarUpdate,
    usuario_token: Dict[str, Any],
) -> Dict[str, Any]:
    conta = financeiro_crud.get_conta_pagar(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")

    # CONTA PAGA: o dinheiro está congelado, a CLASSIFICAÇÃO não.
    #
    # Valor e vencimento já viraram lançamento no livro, e mexer neles faria a
    # despesa do relatório discordar do movimento -- para isso, estorna-se
    # primeiro. Mas categoria, fornecedor e observação nunca entraram no livro:
    # são a leitura contábil do documento, e corrigi-las depois do pagamento é
    # rotina em qualquer escritório.
    #
    # A regra larga de antes criava um laço fechado com o painel de atenção: o
    # alerta "gastos sem categoria" conta despesa PAGA, e conta paga não podia
    # ser classificada. O aviso não teria como sair da tela nunca.
    if conta.status == ContaPagarStatus.PAGA.value:
        mexidos = set(dados.model_dump(exclude_unset=True))
        congelados = mexidos - set(CAMPOS_LIVRES_APOS_PAGAMENTO)
        if congelados:
            raise BadRequestException(
                detail=(
                    "Esta conta já foi paga: só a categoria ainda pode ser corrigida. "
                    "Para mudar valor ou vencimento, estorne o pagamento antes."
                )
            )

    _validar_referencias(db, empresa_id, dados.plano_conta_id)
    func_id, func_nome = _funcionario_do_token(usuario_token)

    alteracoes = dados.model_dump(exclude_unset=True)
    propagar = bool(alteracoes.pop("aplicar_nas_proximas", False))

    for campo, novo in alteracoes.items():
        antigo = getattr(conta, campo)
        if antigo == novo:
            continue

        if campo in CAMPOS_AUDITADOS:
            financeiro_crud.registrar_historico(
                db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_PAGAR,
                entidade_id=conta.id, campo=campo,
                valor_antigo=str(antigo) if antigo is not None else None,
                valor_novo=str(novo) if novo is not None else None,
                funcionario_id=func_id, funcionario_nome=func_nome,
            )

        setattr(conta, campo, novo.strip() if isinstance(novo, str) else novo)

    if propagar:
        _propagar_nas_proximas_parcelas(
            db, empresa_id, conta, alteracoes, func_id, func_nome
        )

    db.flush()
    db.refresh(conta)
    return _serializar_conta(conta, hoje_local())


# Só estes se repetem. `descricao` fica de fora porque ela carrega o "9/72" da
# parcela; `recorrente` porque parcelado e recorrente se excluem (ver o modelo).
CAMPOS_PROPAGAVEIS = ("valor", "vencimento", "plano_conta_id", "fornecedor_id", "observacao")


def _propagar_nas_proximas_parcelas(
    db: Session,
    empresa_id: int,
    conta,
    alteracoes: Dict[str, Any],
    func_id: Optional[int],
    func_nome: Optional[str],
) -> int:
    """Repete a correção nas parcelas seguintes que ainda estão em aberto.

    Nasceu de um empréstimo em 30x cadastrado com a data errada: corrigir mês a
    mês são 30 telas, e em 72x ninguém corrige -- desiste do módulo.

    TRÊS RECORTES, e cada um evita um estrago:
      - só o MESMO parcelamento (nunca outra dívida do mesmo fornecedor);
      - só as parcelas DEPOIS desta (o passado não se reescreve);
      - só as PENDENTES -- parcela paga já virou lançamento no livro, e mexer
        nela faria o relatório do mês discordar do movimento.

    O VENCIMENTO RE-ANCORA em vez de copiar. Copiar a data faria as 63 parcelas
    restantes vencerem todas no mesmo dia; aqui cada uma recebe o mesmo DIA do
    novo vencimento, mês a mês, pela mesma `_somar_meses` que criou o
    parcelamento -- e por isso dia 30 continua encolhendo só em fevereiro e
    voltando para 30 em março.
    """
    if not conta.parcelamento_id or not conta.parcela_numero:
        return 0

    campos = {c: v for c, v in alteracoes.items() if c in CAMPOS_PROPAGAVEIS}
    if not campos:
        return 0

    seguintes = financeiro_crud.listar_parcelas_seguintes(
        db, empresa_id, conta.parcelamento_id, conta.parcela_numero
    )

    for parcela in seguintes:
        for campo, novo in campos.items():
            if campo == "vencimento":
                novo = _somar_meses(
                    conta.vencimento, (parcela.parcela_numero or 0) - conta.parcela_numero
                )
            antigo = getattr(parcela, campo)
            if antigo == novo:
                continue
            if campo in CAMPOS_AUDITADOS:
                financeiro_crud.registrar_historico(
                    db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_PAGAR,
                    entidade_id=parcela.id, campo=campo,
                    valor_antigo=str(antigo) if antigo is not None else None,
                    valor_novo=str(novo) if novo is not None else None,
                    funcionario_id=func_id, funcionario_nome=func_nome,
                )
            setattr(parcela, campo, novo.strip() if isinstance(novo, str) else novo)

    db.flush()
    return len(seguintes)


def reativar_conta_pagar(
    db: Session, empresa_id: int, conta_id: int, usuario_token: Dict[str, Any]
) -> Dict[str, Any]:
    """Desfaz um cancelamento -- CANCELADA volta para PENDENTE.

    Faltava, e o buraco aparecia na primeira vez que alguém errava o clique: o
    cancelamento era porta de mão única, e a conta ficava para sempre fora da
    lista de "em aberto" sem forma de voltar. Numa parcela de um empréstimo em
    72x isso significava perder a linha 9/72 do controle inteiro.

    NÃO cancela recorrência nem recria nada: a conta é a mesma linha, com o
    mesmo id, vencimento e valor. Só o status volta.

    O rastro fica: cancelar gravou uma linha no histórico e reativar grava
    outra. "Cancelaram e voltaram atrás" continua sendo uma pergunta que o
    módulo responde.
    """
    conta = financeiro_crud.get_conta_pagar(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    if conta.status != ContaPagarStatus.CANCELADA.value:
        raise BadRequestException(
            detail="Só uma conta cancelada pode ser reativada."
        )

    func_id, func_nome = _funcionario_do_token(usuario_token)
    financeiro_crud.registrar_historico(
        db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_PAGAR, entidade_id=conta.id,
        campo="status", valor_antigo=ContaPagarStatus.CANCELADA.value,
        valor_novo=ContaPagarStatus.PENDENTE.value,
        funcionario_id=func_id, funcionario_nome=func_nome,
    )
    conta.status = ContaPagarStatus.PENDENTE.value
    db.flush()
    db.refresh(conta)
    return _serializar_conta(conta, hoje_local())


def cancelar_conta_pagar(
    db: Session, empresa_id: int, conta_id: int, usuario_token: Dict[str, Any]
) -> Dict[str, Any]:
    """Cancela em vez de excluir.

    Excluir apagaria o rastro de que a conta existiu, e "sumiu uma conta de
    R$ 3.000" é exatamente o tipo de pergunta que o módulo tem que responder.
    """
    conta = financeiro_crud.get_conta_pagar(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    if conta.status == ContaPagarStatus.PAGA.value:
        raise BadRequestException(
            detail="Esta conta já foi paga. Estorne o pagamento antes de cancelá-la."
        )

    func_id, func_nome = _funcionario_do_token(usuario_token)
    financeiro_crud.registrar_historico(
        db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_PAGAR, entidade_id=conta.id,
        campo="status", valor_antigo=conta.status,
        valor_novo=ContaPagarStatus.CANCELADA.value,
        funcionario_id=func_id, funcionario_nome=func_nome,
    )
    conta.status = ContaPagarStatus.CANCELADA.value
    db.flush()
    db.refresh(conta)
    return _serializar_conta(conta, hoje_local())


# ===========================================================================
# BAIXA E ESTORNO — onde o documento vira lançamento
# ===========================================================================

def _somar_meses(base: date, meses: int) -> date:
    """`base` mais N meses, ANCORADO no dia de `base`.

    Encolhe quando o dia não existe no mês de destino (31 em fevereiro vira 28),
    e nunca vaza para o dia 1º do mês seguinte -- vazar atrasaria o alerta em um
    mês inteiro justamente na conta que vence no fim do mês.

    ANCORAR IMPORTA. Calcular cada parcela a partir da ANTERIOR faz o dia
    encolhido ficar encolhido: 31/jan viraria 28/fev e depois 28/mar, quando o
    correto é 31/mar. O erro cresce em silêncio ao longo do parcelamento.
    """
    total = base.month - 1 + meses
    ano = base.year + total // 12
    mes = total % 12 + 1

    dia = base.day
    while dia > 1:
        try:
            return date(ano, mes, dia)
        except ValueError:
            dia -= 1
    return date(ano, mes, 1)


def _proximo_vencimento(vencimento: date) -> date:
    """O mês seguinte, para a RECORRÊNCIA.

    Aqui a âncora é mesmo a conta anterior, e não há outra: a recorrência não
    tem começo guardado -- cada ocorrência nasce da baixa da anterior. A
    consequência é que uma conta de dia 31 encolhe para 28 em fevereiro e assim
    permanece. É uma imprecisão conhecida e aceita: acertá-la exigiria guardar o
    dia original numa coluna, e ninguém contratou aluguel para o dia 31.

    No PARCELAMENTO isso não acontece -- lá existe a primeira parcela como
    âncora, e `_somar_meses` a usa.
    """
    return _somar_meses(vencimento, 1)


def pagar_conta(
    db: Session,
    empresa_id: int,
    conta_id: int,
    dados: ContaPagarBaixa,
    usuario_token: Dict[str, Any],
) -> Dict[str, Any]:
    """Dá baixa: marca a conta como PAGA e escreve no livro do dinheiro.

    As duas coisas na MESMA transação. Uma conta marcada como paga sem o
    lançamento correspondente deixaria o resultado do mês mentindo, e um
    lançamento sem a conta deixaria a despesa órfã no livro.
    """
    conta = financeiro_crud.get_conta_pagar(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    if conta.status == ContaPagarStatus.PAGA.value:
        raise BadRequestException(detail="Esta conta já está paga.")
    if conta.status == ContaPagarStatus.CANCELADA.value:
        raise BadRequestException(detail="Esta conta foi cancelada e não pode ser paga.")

    valor_pago = dados.valor_pago if dados.valor_pago is not None else conta.valor
    dia_pagamento = dados.pago_em or hoje_local()

    if dados.conta_bancaria_id is not None:
        if not financeiro_crud.get_conta_bancaria(db, empresa_id, dados.conta_bancaria_id):
            raise BadRequestException(detail="Conta bancária não encontrada")

    func_id, func_nome = _funcionario_do_token(usuario_token)

    # O LANÇAMENTO. Passa pelo mesmo `registrar_movimento` que a venda e a
    # sangria usam: é o único lugar que escreve no livro, e concentrar a escrita
    # é o que impede uma linha de dinheiro nascer sem origem.
    #
    # `sessao_caixa_id` fica NULO de propósito, mesmo quando há caixa aberto:
    # pagar fornecedor não é sangria. Se o dinheiro saiu fisicamente da gaveta, a
    # sangria é lançada à parte pelo operador, e contar as duas coisas faria a
    # gaveta fechar com falta.
    conta_origem_id = dados.conta_bancaria_id or _conta_padrao_id(db, empresa_id)

    movimento = caixa_crud.registrar_movimento(
        db,
        tipo=MovimentacaoFinanceiraTipo.SAIDA,
        origem=MovimentacaoFinanceiraOrigem.DESPESA,
        valor=valor_pago,
        conta_bancaria_id=conta_origem_id,
        forma_pagamento_id=dados.forma_pagamento_id,
        funcionario_id=func_id,
        funcionario_nome=func_nome,
        motivo=f"Pagamento: {conta.descricao}",
    )

    conta.status = ContaPagarStatus.PAGA.value
    conta.valor_pago = valor_pago
    # Guardado como início do dia em UTC: é timestamp de evento e converte
    # (ver core/tempo.py), diferente de `vencimento`, que é data pura.
    conta.pago_em = inicio_do_dia_utc(dia_pagamento)
    # A conta RESOLVIDA, e nao a escolha crua do usuario: o movimento caiu
    # nela, e deixar aqui um NULL faria o estorno procurar de onde o dinheiro
    # saiu e nao achar.
    conta.conta_bancaria_id = conta_origem_id
    conta.forma_pagamento_id = dados.forma_pagamento_id
    conta.movimentacao_financeira_id = movimento.id
    if dados.observacao:
        conta.observacao = dados.observacao

    financeiro_crud.registrar_historico(
        db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_PAGAR, entidade_id=conta.id,
        campo="baixa", valor_antigo=ContaPagarStatus.PENDENTE.value,
        valor_novo=f"PAGA {valor_pago}",
        funcionario_id=func_id, funcionario_nome=func_nome,
    )

    # Recorrência: a próxima nasce agora, com o valor ORIGINAL da conta e não o
    # pago. A luz veio R$ 80 mais cara este mês por causa do calor; repetir esse
    # valor viraria previsão errada todo mês seguinte.
    #
    # IDEMPOTENTE. Sem a checagem, estornar e pagar de novo criava uma SEGUNDA
    # ocorrência do mês seguinte, e a dívida se multiplicava a cada repetição do
    # ciclo. `gerada_por_id` é o que permite perguntar "já gerei a partir desta?".
    if conta.recorrente and not financeiro_crud.get_ocorrencia_gerada(
        db, empresa_id, conta.id
    ):
        financeiro_crud.criar_conta_pagar(
            db,
            ContaPagar(
                empresa_id=empresa_id,
                descricao=conta.descricao,
                valor=conta.valor,
                vencimento=_proximo_vencimento(conta.vencimento),
                plano_conta_id=conta.plano_conta_id,
                fornecedor_id=conta.fornecedor_id,
                recorrente=True,
                status=ContaPagarStatus.PENDENTE.value,
                gerada_por_id=conta.id,
            ),
        )

    db.flush()
    db.refresh(conta)
    return _serializar_conta(conta, hoje_local())


def estornar_pagamento(
    db: Session,
    empresa_id: int,
    conta_id: int,
    dados: ContaPagarEstorno,
    usuario_token: Dict[str, Any],
) -> Dict[str, Any]:
    """Desfaz a baixa sem apagar nada do livro.

    O movimento de estorno é lançado com a data de HOJE, jamais na data original.
    `sessao_caixa` PERSISTE `saldo_final_esperado` e `saldo_final_informado`: um
    lançamento retroativo faria a quebra de caixa gravada discordar da
    recalculada, e aí nenhum dos dois números serve para nada.
    """
    conta = financeiro_crud.get_conta_pagar(db, empresa_id, conta_id)
    if not conta:
        raise NotFoundException(detail="Conta não encontrada")
    if conta.status != ContaPagarStatus.PAGA.value:
        raise BadRequestException(detail="Só é possível estornar uma conta paga.")

    func_id, func_nome = _funcionario_do_token(usuario_token)
    valor_estornado = conta.valor_pago or conta.valor

    # ENTRADA, o espelho da SAIDA original. Origem segue DESPESA: o par
    # saída + entrada com o mesmo motivo é o que a auditoria lê como estorno,
    # e uma origem própria faria o total de despesas do período ignorá-lo.
    caixa_crud.registrar_movimento(
        db,
        tipo=MovimentacaoFinanceiraTipo.ENTRADA,
        origem=MovimentacaoFinanceiraOrigem.DESPESA,
        valor=valor_estornado,
        # A MESMA conta de onde o dinheiro saiu -- lido ANTES de a baixa ser
        # limpa, mais abaixo. Devolver noutra conta deixaria uma com sobra e a
        # outra com falta, e a soma esconderia o erro.
        conta_bancaria_id=conta.conta_bancaria_id or _conta_padrao_id(db, empresa_id),
        forma_pagamento_id=conta.forma_pagamento_id,
        funcionario_id=func_id,
        funcionario_nome=func_nome,
        motivo=f"Estorno de pagamento: {conta.descricao} — {dados.motivo}",
    )

    financeiro_crud.registrar_historico(
        db, empresa_id=empresa_id, entidade=ENTIDADE_CONTA_PAGAR, entidade_id=conta.id,
        campo="estorno", valor_antigo=f"PAGA {valor_estornado}",
        valor_novo=f"PENDENTE — {dados.motivo}",
        funcionario_id=func_id, funcionario_nome=func_nome,
    )

    # Desfaz também a CONSEQUÊNCIA do pagamento: a ocorrência do mês seguinte
    # que a recorrência criou ao dar a baixa.
    #
    # Sem isto, estornar deixava a loja aparentando dever duas contas de
    # internet -- a de setembro, de volta a pendente, e a de outubro, que só
    # existia por causa do pagamento que acabou de ser desfeito.
    #
    # Apaga em vez de cancelar, e é a única exceção à regra da casa: a linha foi
    # criada pelo SISTEMA, nunca teve dinheiro andando, e some ao desfazer
    # exatamente o que a criou. Um fantasma "Cancelada" por estorno seria ruído
    # de uma conta que ninguém lançou.
    #
    # Se a ocorrência JÁ FOI PAGA ou cancelada, fica onde está: aí houve decisão
    # de gente no meio, e apagá-la levaria junto um pagamento de verdade.
    gerada = financeiro_crud.get_ocorrencia_gerada(db, empresa_id, conta.id)
    if gerada is not None and gerada.status == ContaPagarStatus.PENDENTE.value:
        financeiro_crud.apagar_conta(db, gerada)

    # Volta a PENDENTE e limpa a baixa. A CHECK do banco exige coerência: conta
    # não-PAGA não pode carregar `pago_em` nem `valor_pago`.
    conta.status = ContaPagarStatus.PENDENTE.value
    conta.valor_pago = None
    conta.pago_em = None
    conta.conta_bancaria_id = None
    conta.forma_pagamento_id = None
    conta.movimentacao_financeira_id = None

    db.flush()
    db.refresh(conta)
    return _serializar_conta(conta, hoje_local())


