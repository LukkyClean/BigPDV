# app/services/verificacao_fiscal/validators.py
import re
from sqlalchemy.orm import Session
from app.core.validators import validar_cpf, validar_cnpj
from app.core.enum import TipoProdutoVenda, OrdemServicoItemTipo, OrdemServicoItemAprovacao
from app.schemas.verificacao_fiscal import PendenciaFiscal
from app.db.models.cliente import Cliente, ClientePF, ClientePJ
from app.db.models.venda import Venda
from app.db.models.ordem_servico import OrdemServico

from .helpers import criar_pendencia as _p, dias_para_vencer_certificado, get_nome_cliente
from app.db.crud import fiscal as crud

from app.services.fiscal.tax_engine.constants import (
    CSOSN_SUPORTADOS,
    CST_ICMS_SUPORTADOS,
)

_RE_NCM = re.compile(r"^\d{8}$")
_RE_CFOP = re.compile(r"^\d{4}$")
_RE_CEST = re.compile(r"^\d{7}$")

# Códigos que caracterizam substituição tributária e, por isso, exigem CEST.
_CST_COM_ST = frozenset({"10", "30", "60", "70", "90"})
_CSOSN_COM_ST = frozenset({"201", "202", "203", "500", "900"})


def _exige_cest(fiscal, simples_nacional: bool) -> bool:
    """CEST é obrigatório para item em regime de ICMS-ST."""
    codigo = fiscal.csosn if simples_nacional else fiscal.cst_icms
    if not codigo:
        return False
    conjunto = _CSOSN_COM_ST if simples_nacional else _CST_COM_ST
    return codigo in conjunto

def verificar_emitente(db: Session, empresa_id: int) -> list[PendenciaFiscal]:
    pendencias = []
    empresa = crud.get_empresa(db, empresa_id)
    
    if not empresa:
        return [_p("emitente", "empresa", "Empresa não encontrada no sistema.")]

    if not empresa.documento:
        pendencias.append(_p(
            "emitente", "documento",
            "CNPJ da empresa não está preenchido em Dados da Empresa.",
        ))
    elif empresa.is_cnpj:
        try:
            if validar_cnpj(empresa.documento) is None:
                pendencias.append(_p("emitente", "documento", "CNPJ da empresa é inválido."))
        except Exception:
            pendencias.append(_p("emitente", "documento", "CNPJ da empresa é inválido."))
    else:
        # Cadastro com CPF no lugar do CNPJ.
        #
        # Não havia trava: o payload manda `empresa.documento` no campo `cnpj`,
        # então um CPF de 11 dígitos saía como se fosse CNPJ. A recusa vinha lá
        # da frente -- da plataforma ou da SEFAZ -- com uma mensagem que não
        # aponta para o cadastro, e foi exatamente esse o rastro que custou caro
        # de seguir ("CNPJ do emitente não autorizado").
        #
        # Emitente pessoa física existe na NF-e (produtor rural usa `cpf_emitente`
        # na Focus), mas o nosso payload não tem esse campo e o resto do fluxo
        # pressupõe CNPJ. Enquanto não houver suporte de verdade, barrar aqui é
        # honesto: a alternativa é uma nota que não sai e ninguém sabe por quê.
        pendencias.append(_p(
            "emitente", "documento",
            "A NF-e exige CNPJ, e esta empresa está cadastrada com CPF. "
            "Corrija o documento em Dados da Empresa.",
        ))

    if not empresa.regime_tributario:
        pendencias.append(_p("emitente", "regime_tributario", "Regime tributário não definido em Dados da Empresa."))

    if not empresa.indicador_ie:
        pendencias.append(_p("emitente", "indicador_ie", "Indicador de IE não definido em Dados da Empresa (1 = contribuinte de ICMS, 2 = isento, 9 = não contribuinte)."))

    if empresa.indicador_ie == "1" and not empresa.inscricao_estadual:
        pendencias.append(_p("emitente", "inscricao_estadual", "Inscrição Estadual é obrigatória para contribuinte de ICMS (Indicador de IE = 1)."))

    endereco = crud.get_endereco_empresa(db, empresa_id)
    if not endereco:
        pendencias.append(_p("emitente", "endereco", "Empresa não possui endereço cadastrado."))
    else:
        for campo in ["logradouro", "numero", "bairro", "cidade", "cep"]:
            if not getattr(endereco, campo, None):
                pendencias.append(_p("emitente", campo, f"Campo '{campo}' do endereço vazio."))
        if not endereco.estado:
            pendencias.append(_p("emitente", "estado", "UF do endereço está vazia."))

    fiscal_settings = crud.get_fiscal_settings(db, empresa_id)
    if not fiscal_settings:
        pendencias.append(_p("emitente", "fiscal_settings", "Configurações fiscais não cadastradas."))
    else:
        # Só o VENCIDO barra. "Vence em 20 dias" é aviso do painel, não recusa:
        # a nota ainda sai. E a ausência de certificado não barra porque ele
        # vive na plataforma -- o ERP só sabe a validade do que passou por aqui.
        dias = dias_para_vencer_certificado(fiscal_settings.certificado_validade)
        if dias is not None and dias < 0:
            pendencias.append(_p(
                "emitente", "certificado",
                f"Certificado digital vencido em "
                f"{fiscal_settings.certificado_validade.strftime('%d/%m/%Y')}. "
                f"Envie o certificado novo em Centro Fiscal > Configurações.",
            ))

    return pendencias

def verificar_documento_cliente(cliente: Cliente) -> list[PendenciaFiscal]:
    pendencias = []
    nome = get_nome_cliente(cliente)

    if isinstance(cliente, ClientePF):
        if not cliente.cpf:
            pendencias.append(_p("destinatario", "cpf", f"Cliente '{nome}' sem CPF.", cliente.id, nome))
        else:
            try:
                if validar_cpf(cliente.cpf) is None:
                    pendencias.append(_p("destinatario", "cpf", f"CPF inválido.", cliente.id, nome))
            except Exception:
                pendencias.append(_p("destinatario", "cpf", f"CPF inválido.", cliente.id, nome))
    elif isinstance(cliente, ClientePJ):
        if not cliente.cnpj:
            pendencias.append(_p("destinatario", "cnpj", f"Cliente '{nome}' sem CNPJ.", cliente.id, nome))
        else:
            try:
                if validar_cnpj(cliente.cnpj) is None:
                    pendencias.append(_p("destinatario", "cnpj", f"CNPJ inválido.", cliente.id, nome))
            except Exception:
                pendencias.append(_p("destinatario", "cnpj", f"CNPJ inválido.", cliente.id, nome))
    return pendencias

# Campos do enderDest, e como o lojista os ve no cadastro do cliente.
#
# O rotulo importa: a mensagem que o operador le tem que apontar para o campo da
# tela dele, nao para o nome do campo da SEFAZ. "logradouro_destinatario nao pode
# ser vazio" -- que foi o que a Focus devolveu -- nao diz a ninguem que a rua do
# cliente esta em branco no cadastro.
_CAMPOS_ENDERECO_DESTINATARIO = (
    ("logradouro", "Logradouro (rua)"),
    ("numero", "Numero"),
    ("bairro", "Bairro"),
    ("cidade", "Cidade"),
    ("cep", "CEP"),
)


def verificar_endereco_destinatario(cliente: Cliente) -> list[PendenciaFiscal]:
    """Endereco do destinatario -- obrigatorio na NF-e, PROIBIDO na NFC-e.

    So chame isto para o modelo 55. Na NFC-e (modelo 65) o grupo `dest` e
    opcional e o endereco deve ser OMITIDO -- a venda de balcao nao tem endereco
    de comprador para informar. A unica excecao e indPres 4 (entrega a
    domicilio), tratada em `_montar_destinatario_nfce`. Unificar as duas regras
    quebraria um dos dois modelos, e o que quebraria e o cupom do caixa.

    Por que existe: `_montar_endereco_destinatario` devolve None quando o
    endereco esta incompleto, e o payload entao OMITE o grupo -- com o
    comentario de que "grupo incompleto e rejeitado pela SEFAZ; melhor omitir do
    que enviar com campos vazios". Omitir tambem e rejeitado, e a nota de teste
    provou isso: 422 nomeando logradouro, numero, bairro e municipio do
    destinatario.

    Sem esta conferencia, uma venda para cliente com cadastro incompleto so
    falharia depois da viagem ate a emissora, com uma mensagem em vocabulario de
    SEFAZ que o operador nao sabe resolver -- e, pior, depois de a numeracao ter
    sido reservada.
    """
    nome = get_nome_cliente(cliente)

    enderecos = getattr(cliente, "endereco", None)
    if not enderecos or len(enderecos) == 0:
        return [_p(
            "destinatario", "endereco",
            f"Cliente '{nome}' nao possui endereco cadastrado. A NF-e exige o "
            f"endereco completo do destinatario.",
            cliente.id, nome,
        )]

    end = enderecos[0]
    pendencias = []

    for campo, rotulo in _CAMPOS_ENDERECO_DESTINATARIO:
        if not getattr(end, campo, None):
            pendencias.append(_p(
                "destinatario", f"endereco_{campo}",
                f"Endereco do cliente '{nome}' sem {rotulo}.",
                cliente.id, nome,
            ))

    # A UF sai de um enum e por isso e conferida a parte: `not end.estado` nao
    # basta quando o valor existe mas e vazio.
    uf = end.estado.value if hasattr(end.estado, "value") else str(end.estado or "")
    if not uf:
        pendencias.append(_p(
            "destinatario", "endereco_uf",
            f"Endereco do cliente '{nome}' sem UF.",
            cliente.id, nome,
        ))

    return pendencias


def verificar_produto_fiscal(db: Session, produto, pendencias: list, simples_nacional: bool):
    fiscal = crud.get_produto_fiscal(db, produto.id)
    if not fiscal:
        pendencias.append(_p("item", "dados_fiscais", f"Produto '{produto.nome}' sem dados fiscais.", produto.id, produto.nome))
        return

    # `unidade_tributavel` SAIU desta lista de propósito.
    #
    # O payload já resolve `fiscal.unidade_tributavel or produto.unidade_medida
    # or "UN"` (payload_builder), então exigir o preenchimento aqui obrigava o
    # lojista a digitar duas vezes a mesma unidade para depois o sistema usar o
    # fallback. Pela contabilidade, forçar uTrib = uCom é a prática aceita no
    # varejo fracionado — e é o correto aqui, já que o payload não envia
    # `qTrib`/`vUnTrib`, que a divergência exigiria.
    for c, label in [("ncm", "NCM"), ("cfop_padrao", "CFOP padrão")]:
        if not getattr(fiscal, c, None):
            pendencias.append(_p("item", c, f"Produto '{produto.nome}' — {label} vazio.", produto.id, produto.nome))

    # Validação de formato NCM (8 dígitos numéricos)
    if fiscal.ncm and not _RE_NCM.match(fiscal.ncm):
        pendencias.append(_p("item", "ncm", f"Produto '{produto.nome}' — NCM '{fiscal.ncm}' deve ter exatamente 8 dígitos numéricos.", produto.id, produto.nome))

    # Validação de formato CFOP (4 dígitos numéricos)
    if fiscal.cfop_padrao and not _RE_CFOP.match(fiscal.cfop_padrao):
        pendencias.append(_p("item", "cfop_padrao", f"Produto '{produto.nome}' — CFOP '{fiscal.cfop_padrao}' deve ter exatamente 4 dígitos numéricos.", produto.id, produto.nome))

    # Validação de formato CEST (7 dígitos numéricos, quando preenchido)
    if fiscal.cest and not _RE_CEST.match(fiscal.cest):
        pendencias.append(_p("item", "cest", f"Produto '{produto.nome}' — CEST '{fiscal.cest}' deve ter exatamente 7 dígitos numéricos.", produto.id, produto.nome))

    # CEST é obrigatório sob substituição tributária. Validar só o formato
    # deixava passar o produto sem CEST, que só era recusado pela SEFAZ.
    if _exige_cest(fiscal, simples_nacional) and not fiscal.cest:
        codigo = fiscal.csosn if simples_nacional else fiscal.cst_icms
        pendencias.append(_p(
            "item", "cest",
            f"Produto '{produto.nome}' — CEST obrigatório: o código {codigo} "
            f"indica substituição tributária.",
            produto.id, produto.nome,
        ))

    if fiscal.origem_mercadoria is None:
        pendencias.append(_p("item", "origem_mercadoria", f"Origem não preenchida.", produto.id, produto.nome))
    elif fiscal.origem_mercadoria not in range(9):
        pendencias.append(_p("item", "origem_mercadoria", f"Produto '{produto.nome}' — Origem '{fiscal.origem_mercadoria}' deve ser entre 0 e 8.", produto.id, produto.nome))

    if simples_nacional and not fiscal.csosn:
        pendencias.append(_p("item", "csosn", f"CSOSN não preenchido.", produto.id, produto.nome))
    elif not simples_nacional and not fiscal.cst_icms:
        pendencias.append(_p("item", "cst_icms", f"CST ICMS não preenchido.", produto.id, produto.nome))

    # --- Cobertura do FiscalTaxEngine ---
    # O gate existe para o usuário descobrir o problema no cadastro, não com um
    # 422 genérico ao clicar em Emitir. Se o código não está implementado no
    # motor, avisa aqui com o nome do produto e a lista do que é aceito.
    if simples_nacional and fiscal.csosn and fiscal.csosn not in CSOSN_SUPORTADOS:
        pendencias.append(_p(
            "item", "csosn",
            f"Produto '{produto.nome}' — CSOSN '{fiscal.csosn}' ainda não é "
            f"calculado pelo sistema. Suportados: "
            f"{', '.join(sorted(CSOSN_SUPORTADOS))}.",
            produto.id, produto.nome,
        ))
    elif not simples_nacional and fiscal.cst_icms and fiscal.cst_icms not in CST_ICMS_SUPORTADOS:
        pendencias.append(_p(
            "item", "cst_icms",
            f"Produto '{produto.nome}' — CST ICMS '{fiscal.cst_icms}' ainda não é "
            f"calculado pelo sistema. Suportados: "
            f"{', '.join(sorted(CST_ICMS_SUPORTADOS))}.",
            produto.id, produto.nome,
        ))

    # CST 20 — redução de base obrigatória
    if not simples_nacional and fiscal.cst_icms in {"20"}:
        if fiscal.reducao_base_icms is None:
            pendencias.append(_p(
                "item", "reducao_base_icms",
                f"Produto '{produto.nome}' — CST 20 exige percentual de redução da base ICMS.",
                produto.id, produto.nome,
            ))

    # CST PIS/COFINS — obrigatório só FORA do Simples Nacional.
    #
    # No Simples o resolver IGNORA o que estiver gravado e força CST 49 zerado,
    # porque os tributos vão na guia única. Exigir o preenchimento de um campo
    # que será descartado é pedir digitação para nada — e era o que acontecia
    # com todo lojista do Simples, que é a maioria.
    if not simples_nacional:
        if not fiscal.cst_pis:
            pendencias.append(_p(
                "item", "cst_pis",
                f"Produto '{produto.nome}' — CST PIS não preenchido.",
                produto.id, produto.nome,
            ))
        if not fiscal.cst_cofins:
            pendencias.append(_p(
                "item", "cst_cofins",
                f"Produto '{produto.nome}' — CST COFINS não preenchido.",
                produto.id, produto.nome,
            ))

def verificar_itens_venda(db: Session, venda: Venda, simples_nacional: bool) -> list[PendenciaFiscal]:
    pendencias = []
    if not venda.itens:
        return [_p("item", "itens", "Venda não possui itens.")]

    for item in venda.itens:
        if item.tipo_produto == TipoProdutoVenda.AVULSO:
            pendencias.append(_p("item", "avulso", "Item avulso não permite emissão.", item.id, item.descricao_avulsa))
            continue
        if not item.produto_id or not item.produto:
            pendencias.append(_p("item", "produto", "Item sem produto vinculado.", item.id, item.nome))
            continue
        verificar_produto_fiscal(db, item.produto, pendencias, simples_nacional)
    return pendencias

def verificar_itens_os_nfe(db: Session, os_obj: OrdemServico, simples_nacional: bool) -> list[PendenciaFiscal]:
    pendencias = []
    itens = [i for i in os_obj.itens if i.tipo == OrdemServicoItemTipo.PRODUTO and i.status_aprovacao != OrdemServicoItemAprovacao.REPROVADO]
    
    if not itens:
        return [_p("item", "itens_produto", "OS não possui itens de produto aprovados.")]

    for item in itens:
        if not item.produto_id:
            pendencias.append(_p("item", "avulso", "Item avulso.", item.id, item.nome))
            continue
        if not item.produtos:
            pendencias.append(_p("item", "produto", "Produto não encontrado.", item.id, item.nome))
            continue
        verificar_produto_fiscal(db, item.produtos, pendencias, simples_nacional)
    return pendencias

def verificar_itens_os_nfse(db: Session, os_obj: OrdemServico) -> list[PendenciaFiscal]:
    pendencias = []
    itens = [i for i in os_obj.itens if i.tipo == OrdemServicoItemTipo.SERVICO and i.status_aprovacao != OrdemServicoItemAprovacao.REPROVADO]
    
    if not itens:
        return [_p("item", "itens_servico", "OS sem itens de serviço aprovados.")]

    for item in itens:
        if not item.servico_id or not item.servico:
            pendencias.append(_p("item", "avulso_servico", "Serviço avulso ou não encontrado.", item.id, item.nome))
            continue
        
        fiscal = crud.get_servico_fiscal(db, item.servico.id)
        if not fiscal:
            pendencias.append(_p("item", "dados_fiscais", "Sem dados fiscais.", item.servico.id, item.servico.descricao))
        elif not fiscal.codigo_servico_lc116:
            pendencias.append(_p("item", "codigo", "Sem código LC116.", item.servico.id, item.servico.descricao))
    return pendencias

def verificar_pagamentos(pagamentos: list) -> list[PendenciaFiscal]:
    pendencias = []
    if not pagamentos:
        return [_p("pagamento", "pagamentos", "Nenhum pagamento registrado.")]

    vistos = set()
    for pag in pagamentos:
        forma = getattr(pag, "forma_pagamento", None)
        if not forma or forma.id in vistos:
            continue
        vistos.add(forma.id)
        if not forma.codigo_sefaz:
            pendencias.append(_p("pagamento", "codigo_sefaz", f"Sem código SEFAZ.", forma.id, forma.nome))
    return pendencias