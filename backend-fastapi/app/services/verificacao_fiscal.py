# ---------------------------------------------------------------------------
# ARQUIVO: app/services/verificacao_fiscal.py
# DESCRIÇÃO: Lógica central de verificação de completude fiscal.
#            Função reutilizada pelo gate de emissão e pelo futuro painel
#            de pendências. Camada 2 + Camada 3 do design de validação.
# ---------------------------------------------------------------------------

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload, subqueryload

from app.core.validators import validar_cpf, validar_cnpj
from app.db.models.empresa import Empresa
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.db.models.endereco import Endereco
from app.db.models.venda import Venda
from app.db.models.venda_pagamento import PagamentoVenda
from app.db.models.venda_produto import ProdutoVenda
from app.db.models.ordem_servico import OrdemServico
from app.db.models.ordem_servico_pagamento import OrdemServicoPagamento
from app.db.models.ordem_servico_item import OrdemServicoItem
from app.db.models.produto_fiscal import ProdutoFiscal
from app.db.models.servico_fiscal import ServicoFiscal
from app.db.models.cliente import Cliente, ClientePF, ClientePJ
from app.core.enum import EntityType, TipoProdutoVenda, OrdemServicoItemTipo, OrdemServicoItemAprovacao
from app.schemas.verificacao_fiscal import (
    PendenciaFiscal,
    ResultadoVerificacaoFiscal,
    DocumentoAtivoResumo,
    VerificacaoBatchItem,
    ResultadoVerificacaoBatch,
)
from app.db.crud import fiscal as fiscal_crud


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _p(categoria: str, campo: str, mensagem: str,
       referencia_id: int = None, referencia_nome: str = None) -> PendenciaFiscal:
    return PendenciaFiscal(
        categoria=categoria,
        campo=campo,
        mensagem=mensagem,
        referencia_id=referencia_id,
        referencia_nome=referencia_nome,
    )


# Cópia local removida: a regra de CRT vive em services/fiscal/helpers.py.
from app.services.fiscal.helpers import obter_crt, usa_csosn


# ---------------------------------------------------------------------------
# 1. Verificação do Emitente (Empresa)
# ---------------------------------------------------------------------------

def _verificar_emitente(db: Session, empresa_id: int) -> list[PendenciaFiscal]:
    pendencias: list[PendenciaFiscal] = []

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        pendencias.append(_p("emitente", "empresa", "Empresa não encontrada no sistema."))
        return pendencias

    # CNPJ
    if not empresa.documento:
        pendencias.append(_p("emitente", "documento", "CNPJ da empresa não está preenchido."))
    elif empresa.is_cnpj:
        try:
            resultado = validar_cnpj(empresa.documento)
            if resultado is None:
                pendencias.append(_p("emitente", "documento", "CNPJ da empresa é inválido."))
        except Exception:
            pendencias.append(_p("emitente", "documento", "CNPJ da empresa é inválido."))

    # Regime tributário
    if not empresa.regime_tributario:
        pendencias.append(_p("emitente", "regime_tributario", "Regime tributário da empresa não está definido."))

    # Indicador de IE (obrigatório para emissão)
    if not empresa.indicador_ie:
        pendencias.append(_p(
            "emitente", "indicador_ie",
            "Indicador de IE não definido em Dados da Empresa (1 = contribuinte de ICMS, 2 = isento, 9 = não contribuinte)."
        ))

    # Inscrição Estadual (obrigatória se contribuinte ICMS)
    if empresa.indicador_ie == "1" and not empresa.inscricao_estadual:
        pendencias.append(_p(
            "emitente", "inscricao_estadual",
            "Inscrição Estadual é obrigatória para contribuinte ICMS (indicador IE = 1)."
        ))

    # Endereço
    endereco = (
        db.query(Endereco)
        .filter(
            Endereco.id_entidade == empresa_id,
            Endereco.tipo_entidade == EntityType.EMPRESA,
        )
        .first()
    )
    if not endereco:
        pendencias.append(_p("emitente", "endereco", "Empresa não possui endereço cadastrado."))
    else:
        for campo in ["logradouro", "numero", "bairro", "cidade", "cep"]:
            if not getattr(endereco, campo, None):
                pendencias.append(_p(
                    "emitente", campo,
                    f"Campo '{campo}' do endereço da empresa está vazio.",
                ))
        if not endereco.estado:
            pendencias.append(_p("emitente", "estado", "UF do endereço da empresa está vazia."))

    # Fiscal Settings
    fiscal_settings = (
        db.query(EmpresaFiscalSettings)
        .filter(EmpresaFiscalSettings.empresa_id == empresa_id)
        .first()
    )
    if not fiscal_settings:
        pendencias.append(_p(
            "emitente", "fiscal_settings",
            "Configurações fiscais da empresa não estão cadastradas."
        ))
    else:
        # Certificado digital — desabilitado temporariamente.
        # A API Online usa Bearer token (licença), não certificado local.
        # Reativar quando integração direta com SEFAZ for implementada.
        pass

    return pendencias


# ---------------------------------------------------------------------------
# 2. Verificação do Destinatário (Cliente)
# ---------------------------------------------------------------------------

def _verificar_destinatario_venda(venda: Venda) -> list[PendenciaFiscal]:
    pendencias: list[PendenciaFiscal] = []

    if not venda.cliente_id or not venda.cliente:
        pendencias.append(_p(
            "destinatario", "cliente",
            "Venda não possui cliente identificado. NF-e requer destinatário."
        ))
        return pendencias

    return _verificar_documento_cliente(venda.cliente)


def _verificar_destinatario_os(os_obj: OrdemServico) -> list[PendenciaFiscal]:
    cliente = getattr(os_obj.objeto, "cliente", None) if os_obj.objeto else None
    if not cliente:
        return [_p(
            "destinatario", "cliente",
            "OS não possui cliente vinculado ao objeto de serviço."
        )]

    return _verificar_documento_cliente(cliente)


def _verificar_documento_cliente(cliente: Cliente) -> list[PendenciaFiscal]:
    pendencias: list[PendenciaFiscal] = []
    nome_cliente = _get_nome_cliente(cliente)

    if isinstance(cliente, ClientePF):
        if not cliente.cpf:
            pendencias.append(_p(
                "destinatario", "cpf",
                f"Cliente '{nome_cliente}' não possui CPF cadastrado.",
                referencia_id=cliente.id, referencia_nome=nome_cliente,
            ))
        else:
            try:
                resultado = validar_cpf(cliente.cpf)
                if resultado is None:
                    pendencias.append(_p(
                        "destinatario", "cpf",
                        f"CPF do cliente '{nome_cliente}' é inválido.",
                        referencia_id=cliente.id, referencia_nome=nome_cliente,
                    ))
            except Exception:
                pendencias.append(_p(
                    "destinatario", "cpf",
                    f"CPF do cliente '{nome_cliente}' é inválido.",
                    referencia_id=cliente.id, referencia_nome=nome_cliente,
                ))
    elif isinstance(cliente, ClientePJ):
        if not cliente.cnpj:
            pendencias.append(_p(
                "destinatario", "cnpj",
                f"Cliente '{nome_cliente}' não possui CNPJ cadastrado.",
                referencia_id=cliente.id, referencia_nome=nome_cliente,
            ))
        else:
            try:
                resultado = validar_cnpj(cliente.cnpj)
                if resultado is None:
                    pendencias.append(_p(
                        "destinatario", "cnpj",
                        f"CNPJ do cliente '{nome_cliente}' é inválido.",
                        referencia_id=cliente.id, referencia_nome=nome_cliente,
                    ))
            except Exception:
                pendencias.append(_p(
                    "destinatario", "cnpj",
                    f"CNPJ do cliente '{nome_cliente}' é inválido.",
                    referencia_id=cliente.id, referencia_nome=nome_cliente,
                ))

    return pendencias


def _get_nome_cliente(cliente: Cliente) -> str:
    if isinstance(cliente, ClientePF):
        return cliente.nome
    elif isinstance(cliente, ClientePJ):
        return cliente.nome_fantasia or cliente.razao_social
    return f"Cliente #{cliente.id}"


# ---------------------------------------------------------------------------
# 3. Verificação de Itens — Venda
# ---------------------------------------------------------------------------

def _verificar_itens_venda(
    db: Session, venda: Venda, simples_nacional: bool
) -> list[PendenciaFiscal]:
    pendencias: list[PendenciaFiscal] = []

    if not venda.itens:
        pendencias.append(_p("item", "itens", "Venda não possui itens."))
        return pendencias

    for item in venda.itens:
        if item.tipo_produto == TipoProdutoVenda.AVULSO:
            pendencias.append(_p(
                "item", "avulso",
                f"Item avulso '{item.descricao_avulsa}' não permite emissão fiscal — cadastre o produto primeiro.",
                referencia_id=item.id, referencia_nome=item.descricao_avulsa,
            ))
            continue

        # CADASTRADO — verificar dados fiscais do produto
        if not item.produto_id or not item.produto:
            pendencias.append(_p(
                "item", "produto",
                f"Item '{item.nome}' não possui produto vinculado.",
                referencia_id=item.id, referencia_nome=item.nome,
            ))
            continue

        _verificar_produto_fiscal(
            db, item.produto, pendencias, simples_nacional
        )

    return pendencias


def _verificar_produto_fiscal(
    db: Session, produto, pendencias: list[PendenciaFiscal],
    simples_nacional: bool
) -> None:
    nome = produto.nome
    produto_id = produto.id

    fiscal = (
        db.query(ProdutoFiscal)
        .filter(ProdutoFiscal.produto_id == produto_id)
        .first()
    )

    if not fiscal:
        pendencias.append(_p(
            "item", "dados_fiscais",
            f"Produto '{nome}' não possui dados fiscais cadastrados.",
            referencia_id=produto_id, referencia_nome=nome,
        ))
        return

    campos_obrigatorios = {
        "ncm": "NCM",
        "cfop_padrao": "CFOP padrão",
        "unidade_tributavel": "Unidade tributável",
    }
    for campo, label in campos_obrigatorios.items():
        if not getattr(fiscal, campo, None):
            pendencias.append(_p(
                "item", campo,
                f"Produto '{nome}' — {label} não preenchido.",
                referencia_id=produto_id, referencia_nome=nome,
            ))

    if fiscal.origem_mercadoria is None:
        pendencias.append(_p(
            "item", "origem_mercadoria",
            f"Produto '{nome}' — Origem da mercadoria não preenchida.",
            referencia_id=produto_id, referencia_nome=nome,
        ))

    # CST ou CSOSN conforme regime
    if simples_nacional:
        if not fiscal.csosn:
            pendencias.append(_p(
                "item", "csosn",
                f"Produto '{nome}' — CSOSN não preenchido (obrigatório para Simples Nacional).",
                referencia_id=produto_id, referencia_nome=nome,
            ))
    else:
        if not fiscal.cst_icms:
            pendencias.append(_p(
                "item", "cst_icms",
                f"Produto '{nome}' — CST ICMS não preenchido (obrigatório para Lucro Presumido/Real).",
                referencia_id=produto_id, referencia_nome=nome,
            ))


# ---------------------------------------------------------------------------
# 4. Verificação de Itens — OS (NFe: produtos)
# ---------------------------------------------------------------------------

def _verificar_itens_os_nfe(
    db: Session, os_obj: OrdemServico, simples_nacional: bool
) -> list[PendenciaFiscal]:
    pendencias: list[PendenciaFiscal] = []

    itens_produto = [
        item for item in os_obj.itens
        if item.tipo == OrdemServicoItemTipo.PRODUTO
        and item.status_aprovacao != OrdemServicoItemAprovacao.REPROVADO
    ]

    if not itens_produto:
        pendencias.append(_p(
            "item", "itens_produto",
            "OS não possui itens de produto aprovados para emissão de NFe."
        ))
        return pendencias

    for item in itens_produto:
        if not item.produto_id:
            pendencias.append(_p(
                "item", "avulso",
                f"Item de produto '{item.nome}' é avulso — cadastre o produto para emitir NFe.",
                referencia_id=item.id, referencia_nome=item.nome,
            ))
            continue

        produto = item.produtos  # relationship name in OrdemServicoItem
        if not produto:
            pendencias.append(_p(
                "item", "produto",
                f"Item '{item.nome}' — produto vinculado não encontrado.",
                referencia_id=item.id, referencia_nome=item.nome,
            ))
            continue

        _verificar_produto_fiscal(db, produto, pendencias, simples_nacional)

    return pendencias


# ---------------------------------------------------------------------------
# 5. Verificação de Itens — OS (NFSe: serviços)
# ---------------------------------------------------------------------------

def _verificar_itens_os_nfse(
    db: Session, os_obj: OrdemServico
) -> list[PendenciaFiscal]:
    pendencias: list[PendenciaFiscal] = []

    itens_servico = [
        item for item in os_obj.itens
        if item.tipo == OrdemServicoItemTipo.SERVICO
        and item.status_aprovacao != OrdemServicoItemAprovacao.REPROVADO
    ]

    if not itens_servico:
        pendencias.append(_p(
            "item", "itens_servico",
            "OS não possui itens de serviço aprovados para emissão de NFSe."
        ))
        return pendencias

    for item in itens_servico:
        if not item.servico_id:
            pendencias.append(_p(
                "item", "avulso",
                f"Item de serviço '{item.nome}' é avulso — cadastre o serviço para emitir NFSe.",
                referencia_id=item.id, referencia_nome=item.nome,
            ))
            continue

        servico = item.servico
        if not servico:
            pendencias.append(_p(
                "item", "servico",
                f"Item '{item.nome}' — serviço vinculado não encontrado.",
                referencia_id=item.id, referencia_nome=item.nome,
            ))
            continue

        fiscal = (
            db.query(ServicoFiscal)
            .filter(ServicoFiscal.servico_id == servico.id)
            .first()
        )

        if not fiscal:
            pendencias.append(_p(
                "item", "dados_fiscais",
                f"Serviço '{servico.descricao}' não possui dados fiscais cadastrados.",
                referencia_id=servico.id, referencia_nome=servico.descricao,
            ))
            continue

        if not fiscal.codigo_servico_lc116:
            pendencias.append(_p(
                "item", "codigo_servico_lc116",
                f"Serviço '{servico.descricao}' — código de serviço (LC 116) não preenchido.",
                referencia_id=servico.id, referencia_nome=servico.descricao,
            ))

    return pendencias


# ---------------------------------------------------------------------------
# 6. Verificação de Pagamentos
# ---------------------------------------------------------------------------

def _verificar_pagamentos(pagamentos: list) -> list[PendenciaFiscal]:
    pendencias: list[PendenciaFiscal] = []

    if not pagamentos:
        pendencias.append(_p(
            "pagamento", "pagamentos",
            "Nenhum pagamento registrado."
        ))
        return pendencias

    formas_verificadas: set[int] = set()

    for pag in pagamentos:
        forma = getattr(pag, "forma_pagamento", None)
        if not forma:
            continue
        if forma.id in formas_verificadas:
            continue
        formas_verificadas.add(forma.id)

        if not forma.codigo_sefaz:
            pendencias.append(_p(
                "pagamento", "codigo_sefaz",
                f"Forma de pagamento '{forma.nome}' não possui código SEFAZ configurado.",
                referencia_id=forma.id, referencia_nome=forma.nome,
            ))

    return pendencias


# ---------------------------------------------------------------------------
# API Pública: Verificação por Venda
# ---------------------------------------------------------------------------

def verificar_completude_venda(
    db: Session, venda_id: int, empresa_id: int
) -> ResultadoVerificacaoFiscal:
    venda = (
        db.query(Venda)
        .options(
            joinedload(Venda.cliente),
            subqueryload(Venda.itens).joinedload(ProdutoVenda.produto),
            subqueryload(Venda.pagamentos).joinedload(PagamentoVenda.forma_pagamento),
        )
        .filter(Venda.id == venda_id)
        .first()
    )
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada.")

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    simples_nacional = usa_csosn(obter_crt(empresa))

    pendencias: list[PendenciaFiscal] = []
    pendencias.extend(_verificar_emitente(db, empresa_id))
    pendencias.extend(_verificar_destinatario_venda(venda))
    pendencias.extend(_verificar_itens_venda(db, venda, simples_nacional))
    pendencias.extend(_verificar_pagamentos(venda.pagamentos))

    return ResultadoVerificacaoFiscal(
        completo=len(pendencias) == 0,
        pendencias=pendencias,
    )


# ---------------------------------------------------------------------------
# API Pública: Verificação por OS
# ---------------------------------------------------------------------------

def verificar_completude_os(
    db: Session, numero_os: str, empresa_id: int,
    tipo_documento: str = "ambos"
) -> ResultadoVerificacaoFiscal:
    from app.db.models.objeto_servico import ObjetoServico

    os_obj = (
        db.query(OrdemServico)
        .options(
            joinedload(OrdemServico.objeto).joinedload(ObjetoServico.cliente),
            subqueryload(OrdemServico.itens).joinedload(OrdemServicoItem.produtos),
            subqueryload(OrdemServico.itens).joinedload(OrdemServicoItem.servico),
            subqueryload(OrdemServico.pagamentos).joinedload(OrdemServicoPagamento.forma_pagamento),
            joinedload(OrdemServico.nota_fiscal),
        )
        .filter(OrdemServico.numero_os == numero_os)
        .first()
    )
    if not os_obj:
        raise HTTPException(status_code=404, detail="Ordem de Serviço não encontrada.")

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    simples_nacional = usa_csosn(obter_crt(empresa))

    # Determinar quais documentos emitir
    nota_fiscal = os_obj.nota_fiscal
    emitir_nfe = True
    emitir_nfse = True
    if nota_fiscal:
        emitir_nfe = nota_fiscal.emitir_nfe if nota_fiscal.emitir_nfe is not None else True
        emitir_nfse = nota_fiscal.emitir_nfse if nota_fiscal.emitir_nfse is not None else True

    pendencias: list[PendenciaFiscal] = []
    pendencias.extend(_verificar_emitente(db, empresa_id))
    pendencias.extend(_verificar_destinatario_os(os_obj))

    if tipo_documento in ("nfe", "ambos") and emitir_nfe:
        pendencias.extend(_verificar_itens_os_nfe(db, os_obj, simples_nacional))
    if tipo_documento in ("nfse", "ambos") and emitir_nfse:
        pendencias.extend(_verificar_itens_os_nfse(db, os_obj))

    pendencias.extend(_verificar_pagamentos(os_obj.pagamentos))

    return ResultadoVerificacaoFiscal(
        completo=len(pendencias) == 0,
        pendencias=pendencias,
    )


# ---------------------------------------------------------------------------
# API Pública: Verificação em Lote (Batch)
# ---------------------------------------------------------------------------

def verificar_completude_vendas_batch(
    db: Session, venda_ids: list[int], empresa_id: int
) -> ResultadoVerificacaoBatch:
    """Verifica completude fiscal de múltiplas vendas em uma única chamada otimizada."""

    # 1. Emitente — verificado UMA vez para todo o lote
    pendencias_emitente = _verificar_emitente(db, empresa_id)

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    simples = usa_csosn(obter_crt(empresa))

    # 2. Carregar vendas com relacionamentos (query única)
    vendas = fiscal_crud.get_vendas_completas_batch(db, venda_ids)

    # 3. Carregar documentos ativos em lote (query única)
    numeros_venda = [v.numero_venda for v in vendas if v.numero_venda is not None]
    docs_map = fiscal_crud.get_documentos_relevantes_por_vendas(db, numeros_venda)

    # 4. Montar resultado por venda
    resultados: list[VerificacaoBatchItem] = []
    total_aptas = 0
    total_com_pendencias = 0
    total_com_documento = 0

    for venda in vendas:
        pendencias: list[PendenciaFiscal] = list(pendencias_emitente)  # cópia
        pendencias.extend(_verificar_destinatario_venda(venda))
        pendencias.extend(_verificar_itens_venda(db, venda, simples))
        pendencias.extend(_verificar_pagamentos(venda.pagamentos))

        completo = len(pendencias) == 0

        # Documento ativo existente?
        doc_ativo = docs_map.get(venda.numero_venda) if venda.numero_venda else None
        documento_ativo = None
        if doc_ativo:
            documento_ativo = DocumentoAtivoResumo(
                documento_id=doc_ativo.id,
                status=doc_ativo.status,
                numero_documento=doc_ativo.numero_documento,
                serie=doc_ativo.serie,
                chave_acesso=doc_ativo.chave_acesso,
            )
            total_com_documento += 1
        elif completo:
            total_aptas += 1
        else:
            total_com_pendencias += 1

        resultados.append(VerificacaoBatchItem(
            venda_id=venda.id,
            numero_venda=venda.numero_venda,
            completo=completo,
            pendencias=pendencias,
            documento_ativo=documento_ativo,
        ))

    return ResultadoVerificacaoBatch(
        resultados=resultados,
        total=len(resultados),
        total_aptas=total_aptas,
        total_com_pendencias=total_com_pendencias,
        total_com_documento=total_com_documento,
    )
