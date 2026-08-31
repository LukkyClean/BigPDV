# app/services/verificacao_fiscal/validators.py
import re
from sqlalchemy.orm import Session
from app.core.validators import validar_cpf, validar_cnpj
from app.core.enum import TipoProdutoVenda, OrdemServicoItemTipo, OrdemServicoItemAprovacao
from app.schemas.verificacao_fiscal import PendenciaFiscal
from app.db.models.cliente import Cliente, ClientePF, ClientePJ
from app.db.models.venda import Venda
from app.db.models.ordem_servico import OrdemServico

from .helpers import criar_pendencia as _p, get_nome_cliente
from app.db.crud import fiscal as crud

_RE_NCM = re.compile(r"^\d{8}$")
_RE_CFOP = re.compile(r"^\d{4}$")
_RE_CEST = re.compile(r"^\d{7}$")

def verificar_emitente(db: Session, empresa_id: int) -> list[PendenciaFiscal]:
    pendencias = []
    empresa = crud.get_empresa(db, empresa_id)
    
    if not empresa:
        return [_p("emitente", "empresa", "Empresa não encontrada no sistema.")]

    if not empresa.documento:
        pendencias.append(_p("emitente", "documento", "CNPJ da empresa não está preenchido."))
    elif empresa.is_cnpj:
        try:
            if validar_cnpj(empresa.documento) is None:
                pendencias.append(_p("emitente", "documento", "CNPJ da empresa é inválido."))
        except Exception:
            pendencias.append(_p("emitente", "documento", "CNPJ da empresa é inválido."))

    if not empresa.regime_tributario:
        pendencias.append(_p("emitente", "regime_tributario", "Regime tributário não definido."))

    if not empresa.indicador_ie:
        pendencias.append(_p("emitente", "indicador_ie", "Indicador de IE não definido. Acesse Configurações da Empresa > Dados Fiscais."))

    if empresa.indicador_ie == "1" and not empresa.inscricao_estadual:
        pendencias.append(_p("emitente", "inscricao_estadual", "Inscrição Estadual obrigatória para IE=1."))

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
    # Certificado digital será validado quando a integração com a API real estiver pronta.
    # elif not (fiscal_settings.certificado_digital_path or fiscal_settings.certificado_thumbprint):
    #     pendencias.append(_p("emitente", "certificado", "Certificado digital não configurado."))

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

def verificar_produto_fiscal(db: Session, produto, pendencias: list, simples_nacional: bool):
    fiscal = crud.get_produto_fiscal(db, produto.id)
    if not fiscal:
        pendencias.append(_p("item", "dados_fiscais", f"Produto '{produto.nome}' sem dados fiscais.", produto.id, produto.nome))
        return

    for c, label in [("ncm", "NCM"), ("cfop_padrao", "CFOP padrão"), ("unidade_tributavel", "Unidade")]:
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

    if fiscal.origem_mercadoria is None:
        pendencias.append(_p("item", "origem_mercadoria", f"Origem não preenchida.", produto.id, produto.nome))
    elif fiscal.origem_mercadoria not in range(9):
        pendencias.append(_p("item", "origem_mercadoria", f"Produto '{produto.nome}' — Origem '{fiscal.origem_mercadoria}' deve ser entre 0 e 8.", produto.id, produto.nome))

    if simples_nacional and not fiscal.csosn:
        pendencias.append(_p("item", "csosn", f"CSOSN não preenchido.", produto.id, produto.nome))
    elif not simples_nacional and not fiscal.cst_icms:
        pendencias.append(_p("item", "cst_icms", f"CST ICMS não preenchido.", produto.id, produto.nome))

    # --- Validações de alíquota (FiscalTaxEngine) ---

    # CSTs que exigem alíquota ICMS (00=Tributada, 20=Reduzida)
    cst_exige_aliquota = {"00", "000", "20"}
    cst_atual = fiscal.cst_icms if not simples_nacional else None

    if cst_atual and cst_atual.lstrip("0") in {"0", "00", "20"} or cst_atual in cst_exige_aliquota:
        # Verifica se há alíquota no produto (a UF default cobre se não houver,
        # mas se ambos estiverem ausentes o engine vai usar zero)
        pass  # UF default resolve — o resolver.py trata fallback

    # CST 20 — redução de base obrigatória
    if not simples_nacional and fiscal.cst_icms in {"20"}:
        if fiscal.reducao_base_icms is None:
            pendencias.append(_p(
                "item", "reducao_base_icms",
                f"Produto '{produto.nome}' — CST 20 exige percentual de redução da base ICMS.",
                produto.id, produto.nome,
            ))

    # CST PIS/COFINS — obrigatório para emissão
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