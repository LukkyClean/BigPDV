# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/fiscal.py
# DESCRIÇÃO: Endpoints do Centro Fiscal — documentos emitidos, pendências
#            e emissão de NF-e (real e teste/homologação).
#
# Tres camadas de acesso (ver app/core/depends.py):
#   leitura/regularizacao -> get_current_active_user
#   configuracao          -> requer_configuracao_fiscal (master, sem plano)
#   emissao               -> requer_modulo_fiscal (exige plano contratado)
# ---------------------------------------------------------------------------

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.depends import (
    get_current_active_user,
    get_db,
    requer_configuracao_fiscal,
    requer_modulo_fiscal,
    _handle_db_transaction,
)
from app.db.crud import fiscal as fiscal_crud
from app.schemas.documento_fiscal import (
    DocumentoFiscalHistorico,
    DocumentoFiscalListRead,
    DocumentoFiscalRead,
    DocumentoFiscalResumo,
    PendenciasGlobais,
)
from app.schemas.emissao_fiscal import (
    DiagnosticoPlataforma,
    GapNumeracao,
    InutilizacaoRead,
    InutilizacaoRequest,
    CancelamentoRequest,
    EmissaoBatchResponse,
    EmissaoNFeBatchRequest,
    EmissaoNFCeRequest,
    EmissaoNFeRequest,
    EmissaoResponse,
    FiscalConfiguracao,
)
from app.schemas.produto_fiscal import ProdutoFiscalUpdate
from app.schemas.tributacao import (
    RegraNcmRead,
    RegraNcmUpsert,
    TributacaoPadraoRead,
    TributacaoPadraoUpdate,
)
from app.services import documento_fiscal as documento_fiscal_service
from app.services import pendencias_globais as pendencias_globais_service
from app.services.fiscal.helpers import dias_para_vencer_certificado, mascarar_csc, obter_csc_token
from app.services.fiscal.payload_builder import _so_digitos
from app.core.modulos import requer_modulo

# A LOJA contratou a NF-e? Trava de licenca, no router inteiro, como no
# /financeiro. NFE NEGA por padrao: licenca sem resposta nao libera (ver
# app/core/modulos.py).
#
# Ela fica ACIMA das tres camadas descritas no topo. A camada de configuracao
# e deliberadamente frouxa quanto a plano -- a ideia sendo deixar preparar
# certificado antes de contratar --, mas no nosso fluxo isso nao se aplica: o
# menu inteiro do Centro Fiscal fica escondido ate a licenca conceder o NFE,
# entao nao existe "configurar antes de ter". Manter a trava aqui e o que
# sustenta a promessa do nega-por-padrao: nenhuma rota fiscal responde sem a
# concessao.
router = APIRouter(dependencies=[Depends(requer_modulo("NFE"))])


# ===========================================================================
# RESUMO (contadores por status)
# ===========================================================================

@router.get(
    "/resumo",
    response_model=DocumentoFiscalResumo,
    summary="Resumo de Documentos Fiscais",
    description="Retorna contadores operacionais agrupados por status.",
)
def obter_resumo(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
    tipo: Optional[str] = Query(
        None, description="Restringe os contadores a um tipo (NFE, NFCE, NFSE)",
    ),
):
    return documento_fiscal_service.obter_resumo(db, tipo=tipo)


# ===========================================================================
# PENDÊNCIAS GLOBAIS
# ===========================================================================

@router.get(
    "/pendencias",
    response_model=PendenciasGlobais,
    summary="Pendências Fiscais Globais",
    description=(
        "Retorna pendências cadastrais que impedem emissão fiscal: "
        "produtos sem NCM, serviços sem código LC 116, pagamentos sem código SEFAZ "
        "e dados do emitente incompletos."
    ),
)
def obter_pendencias(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    empresa_id = user_token["empresa_id"]
    return pendencias_globais_service.obter_pendencias_globais(db, empresa_id)


# ===========================================================================
# LISTAGEM DE DOCUMENTOS
# ===========================================================================

@router.get(
    "/documentos",
    response_model=DocumentoFiscalListRead,
    summary="Listar Documentos Fiscais",
    description="Retorna lista paginada de documentos fiscais com filtros.",
)
def listar_documentos(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
    status_filtro: Optional[str] = Query(None, alias="status", description="Filtrar por status"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo (NFE, NFCE, NFSE)"),
    origem: Optional[str] = Query(None, description="Filtrar por origem (VENDA, ORDEM_SERVICO)"),
    busca: Optional[str] = Query(None, description="Busca por chave de acesso ou número OS"),
    data_inicio: Optional[date] = Query(None, description="Data início (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data fim (YYYY-MM-DD)"),
    pagina: int = Query(1, ge=1, description="Número da página"),
    por_pagina: int = Query(20, ge=1, le=100, description="Itens por página"),
):
    return documento_fiscal_service.listar_documentos(
        db,
        status_filtro=status_filtro,
        tipo=tipo,
        origem=origem,
        busca=busca,
        data_inicio=data_inicio,
        data_fim=data_fim,
        pagina=pagina,
        por_pagina=por_pagina,
    )


# ===========================================================================
# DETALHE DO DOCUMENTO
# ===========================================================================

# Declarado ANTES de /documentos/{documento_id}: o path param captura
# qualquer segmento, e 'exportar-xml' viraria um 422 de 'nao e inteiro'.
@router.get(
    "/documentos/exportar-xml",
    summary="XMLs do período (ZIP para o contador)",
    description=(
        "Baixa um ZIP com o XML de cada NF-e/NFC-e autorizada ou cancelada no "
        "período, as inutilizações homologadas e uma relação em CSV. O que a "
        "emissora não devolver vai listado em nao_baixados.txt, sem derrubar o pacote."
    ),
)
def exportar_xml_periodo(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    data_inicio: date = Query(..., description="Primeiro dia (YYYY-MM-DD, data local)"),
    data_fim: date = Query(..., description="Último dia (YYYY-MM-DD, data local)"),
    tipo: Optional[str] = Query(None, description="NFE ou NFCE; vazio = os dois"),
):
    from fastapi.responses import Response
    from app.services.fiscal.exportacao_xml import montar_pacote_xml

    if data_fim < data_inicio:
        raise HTTPException(status_code=422, detail="data_fim anterior a data_inicio.")
    if (data_fim - data_inicio).days > 366:
        raise HTTPException(status_code=422, detail="O período máximo é de um ano.")

    conteudo, resumo = montar_pacote_xml(
        db, user_token["empresa_id"], data_inicio, data_fim, tipo,
    )
    nome = f"xml-fiscal-{data_inicio:%Y-%m-%d}_{data_fim:%Y-%m-%d}.zip"
    return Response(
        content=conteudo,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{nome}"',
            "X-Fiscal-Documentos": str(resumo["documentos"]),
            "X-Fiscal-Baixados": str(resumo["baixados"]),
            "X-Fiscal-Nao-Baixados": str(resumo["nao_baixados"]),
        },
    )


@router.get(
    "/documentos/{documento_id}",
    response_model=DocumentoFiscalRead,
    summary="Detalhe do Documento Fiscal",
    description="Retorna os dados completos de um documento fiscal.",
)
def obter_documento(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
    documento_id: int = Path(..., ge=1, description="ID do documento fiscal"),
):
    return documento_fiscal_service.obter_documento(db, documento_id)


# ===========================================================================
# REEMISSÃO (cria nova tentativa — linked list)
# ===========================================================================

@router.post(
    "/documentos/{documento_id}/reemitir",
    response_model=DocumentoFiscalRead,
    summary="Reemitir Documento Fiscal",
    description=(
        "Emite de novo a origem (venda ou OS) de um documento REJEITADO e devolve o "
        "documento novo já com o desfecho da SEFAZ. O original mantém seu status; o "
        "novo aponta para ele por tentativa_anterior_id e recebe número novo."
    ),
)
def reemitir_documento(
    background_tasks: BackgroundTasks,
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    documento_id: int = Path(..., ge=1, description="ID do documento fiscal"),
):
    from app.services.fiscal.emissao import poll_nfe_status_async
    from app.services.fiscal.reemissao import reemitir_documento as _reemitir

    doc = _handle_db_transaction(db, _reemitir, documento_id, user_token["empresa_id"])

    # Mesmo acompanhamento do /emitir/nfe: a NF-e é assíncrona na SEFAZ.
    if doc.status == "PROCESSANDO":
        background_tasks.add_task(poll_nfe_status_async, doc.id, user_token["empresa_id"])

    return doc


# ===========================================================================
# EMISSÃO DE NF-e
# ===========================================================================

from app.schemas.emissao_fiscal import EmissaoPreviewResponse

@router.post(
    "/preview/nfe",
    response_model=EmissaoPreviewResponse,
    summary="Pré-visualizar NF-e",
    description="Gera um resumo da NF-e para visualização e verificação antes da emissão.",
)
def preview_nfe(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    payload: EmissaoNFeRequest = Body(...),
):
    from app.services.fiscal.emissao import preview_nfe_os, preview_nfe_venda

    empresa_id = user_token["empresa_id"]
    if payload.venda_id:
        return preview_nfe_venda(db, payload.venda_id, empresa_id)
    return preview_nfe_os(db, payload.numero_os, empresa_id)

@router.post(
    "/emitir/nfe",
    response_model=EmissaoResponse,
    summary="Emitir NF-e",
    description="Emite NF-e a partir de uma venda ou OS (apenas itens de produto).",
)
def emitir_nfe(
    background_tasks: BackgroundTasks,
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    payload: EmissaoNFeRequest = Body(...),
):
    from app.services.fiscal.emissao import (
        emitir_nfe_os, emitir_nfe_venda, poll_nfe_status_async,
    )

    empresa_id = user_token["empresa_id"]

    # A NF-e de uma OS cobre os itens de PRODUTO. A mao de obra e servico e
    # pede NFS-e municipal, que este sistema ainda nao emite.
    if payload.venda_id:
        doc = _handle_db_transaction(
            db, emitir_nfe_venda, payload.venda_id, empresa_id,
        )
    else:
        doc = _handle_db_transaction(
            db, emitir_nfe_os, payload.numero_os, empresa_id,
        )

    if doc.status == "PROCESSANDO":
        background_tasks.add_task(poll_nfe_status_async, doc.id, empresa_id)

    return EmissaoResponse(
        documento_id=doc.id,
        ref_api=doc.ref_api,
        status=doc.status,
        mensagem=doc.mensagem_sefaz or f"NF-e {doc.status.lower()}.",
        ambiente=doc.ambiente_emissao or 2,
    )


@router.post(
    "/preview/nfce",
    # NFC-e exige o modulo NFCE, SEPARADO do NFE: a plataforma tem familia,
    # cota e modulo proprios para o modelo 65 (/erp/fiscal/nfce/...). Uma loja
    # pode ter NF-e e nao ter cupom. Sem esta trava o lojista so descobriria no
    # 403 da plataforma, com a venda ja fechada.
    dependencies=[Depends(requer_modulo("NFCE"))],
    response_model=EmissaoPreviewResponse,
    summary="Pré-visualizar NFC-e",
    description="Gera um resumo da NFC-e para conferência antes da emissão.",
)
def preview_nfce(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    payload: EmissaoNFCeRequest = Body(...),
):
    from app.services.fiscal.emissao import preview_nfce_venda

    return preview_nfce_venda(db, payload.venda_id, user_token["empresa_id"])


@router.post(
    "/emitir/nfce",
    # NFC-e exige o modulo NFCE, SEPARADO do NFE: a plataforma tem familia,
    # cota e modulo proprios para o modelo 65 (/erp/fiscal/nfce/...). Uma loja
    # pode ter NF-e e nao ter cupom. Sem esta trava o lojista so descobriria no
    # 403 da plataforma, com a venda ja fechada.
    dependencies=[Depends(requer_modulo("NFCE"))],
    response_model=EmissaoResponse,
    summary="Emitir NFC-e",
    description=(
        "Emite NFC-e (modelo 65) a partir de uma venda do PDV. "
        "A autorização é síncrona: o resultado volta nesta resposta."
    ),
)
def emitir_nfce(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    payload: EmissaoNFCeRequest = Body(...),
):
    # Sem BackgroundTasks de propósito: a NFC-e é síncrona. Agendar polling
    # aqui atrasaria o cupom que o operador está esperando para entregar.
    from app.services.fiscal.emissao import emitir_nfce_venda

    doc = _handle_db_transaction(
        db, emitir_nfce_venda, payload.venda_id, user_token["empresa_id"],
    )
    return EmissaoResponse.de_documento(doc, "NFC-e")


@router.post(
    "/emitir/nfe/batch",
    response_model=EmissaoBatchResponse,
    summary="Emitir NF-e em Lote",
    description="Emite NF-e para múltiplas vendas sequencialmente. Máximo 20 vendas por lote.",
)
def emitir_nfe_batch(
    background_tasks: BackgroundTasks,
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    payload: EmissaoNFeBatchRequest = Body(...),
):
    from app.services.fiscal.emissao import emitir_nfe_batch as _emitir_batch, poll_nfe_status_async

    empresa_id = user_token["empresa_id"]
    resultados = _emitir_batch(db, payload.venda_ids, empresa_id)

    for r in resultados:
        if r["status"] == "PROCESSANDO" and r["documento_id"]:
            background_tasks.add_task(poll_nfe_status_async, r["documento_id"], empresa_id)

    # Sucesso é a SEFAZ ter aceitado — não é "tudo que não deu pau".
    # A regra anterior (`not in ("ERRO", "REJEITADA")`) contava DENEGADA como
    # sucesso, e o contador que o lojista lê na tela mentia sobre o resultado.
    sucesso = sum(1 for r in resultados if r["status"] in ("AUTORIZADA", "PROCESSANDO"))
    return EmissaoBatchResponse(
        resultados=resultados,
        total=len(resultados),
        sucesso=sucesso,
        falha=len(resultados) - sucesso,
    )


@router.post(
    "/emitir/teste/nfe",
    response_model=EmissaoResponse,
    summary="Emitir NF-e de Teste",
    description=(
        "Emite NF-e com dados fictícios no ambiente de homologação. "
        "Apenas disponível quando ambiente_emissao = 2 (Homologação)."
    ),
)
def emitir_teste_nfe(
    background_tasks: BackgroundTasks,
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
):
    from app.services.fiscal.emissao import emitir_teste_nfe as _emitir_teste, poll_nfe_status_async

    empresa_id = user_token["empresa_id"]
    doc = _handle_db_transaction(db, _emitir_teste, empresa_id)

    if doc.status == "PROCESSANDO":
        background_tasks.add_task(poll_nfe_status_async, doc.id, empresa_id)

    return EmissaoResponse(
        documento_id=doc.id,
        ref_api=doc.ref_api,
        status=doc.status,
        mensagem=doc.mensagem_sefaz or f"NF-e de teste {doc.status.lower()}.",
        ambiente=2,
    )


# ===========================================================================
# CONSULTA (polling de status na API)
# ===========================================================================

@router.get(
    "/documentos/{documento_id}/consultar",
    response_model=DocumentoFiscalRead,
    summary="Consultar Status do Documento",
    description="Consulta o status atualizado do documento na API de emissão.",
)
def consultar_documento(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
    documento_id: int = Path(..., ge=1, description="ID do documento fiscal"),
):
    from app.services.fiscal.emissao import consultar_documento as _consultar

    empresa_id = user_token["empresa_id"]
    return _handle_db_transaction(
        db, _consultar, documento_id, empresa_id,
    )


# ===========================================================================
# CANCELAMENTO
# ===========================================================================

@router.post(
    "/documentos/{documento_id}/cancelar",
    response_model=DocumentoFiscalRead,
    summary="Cancelar Documento Fiscal",
    description="Solicita cancelamento de documento autorizado (justificativa mínima: 15 caracteres).",
)
def cancelar_documento(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
    documento_id: int = Path(..., ge=1, description="ID do documento fiscal"),
    payload: CancelamentoRequest = Body(...),
):
    from app.services.fiscal.emissao import cancelar_documento as _cancelar

    empresa_id = user_token["empresa_id"]
    return _handle_db_transaction(
        db,
        _cancelar,
        documento_id,
        empresa_id,
        payload.justificativa,
    )


# ===========================================================================
# HISTÓRICO DE TENTATIVAS
# ===========================================================================

@router.get(
    "/documentos/{documento_id}/historico",
    response_model=DocumentoFiscalHistorico,
    summary="Histórico de Tentativas",
    description="Retorna a cadeia completa de tentativas de emissão (do mais recente ao mais antigo).",
)
def obter_historico(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
    documento_id: int = Path(..., ge=1, description="ID do documento fiscal"),
):
    return documento_fiscal_service.obter_historico_tentativas(db, documento_id)


# ===========================================================================
# CONFIGURAÇÃO DO AMBIENTE FISCAL
# ===========================================================================

@router.get(
    "/configuracao",
    response_model=FiscalConfiguracao,
    summary="Configuração Fiscal",
    description="Retorna o ambiente atual (homologação/produção) e status do módulo.",
)
def obter_configuracao(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    empresa_id = user_token["empresa_id"]
    fs = fiscal_crud.get_fiscal_settings(db, empresa_id)

    ambiente = fs.ambiente_emissao if fs else 2
    # "Configurado" passou a significar CHEGOU NA EMISSORA.
    #
    # `tipo_certificado == "NUVEM"` saiu desta conta: ele e gravado no upload
    # mesmo quando a plataforma nao recebeu o arquivo, e era o que fazia o card
    # exibir "Conectado" com o certificado parado nesta maquina. VALIDADO_LOCAL
    # e um estado proprio, e a tela o mostra como tal.
    cert_configurado = bool(
        fs and (
            fs.certificado_digital_path
            or fs.certificado_thumbprint
            or fs.certificado_status == "CONECTADO_NUVEM"
        )
    )
    cert_valido = bool(
        cert_configurado and fs.certificado_validade and fs.certificado_validade.replace(tzinfo=None) > datetime.now()
    )

    return FiscalConfiguracao(
        ambiente=ambiente,
        ambiente_label="Homologação" if ambiente == 2 else "Produção",
        # `or ambiente == 2` saiu: quem escolhe o client e a factory, e ela
        # olha SO o FISCAL_MOCK_ENABLED. Em homologacao a tela mostrava
        # "(mock)" enquanto a emissao batia de verdade na plataforma --
        # exatamente o tipo de mentira que atrapalha um diagnostico.
        mock_ativo=settings.FISCAL_MOCK_ENABLED,
        certificado_configurado=cert_configurado,
        certificado_valido=cert_valido,
        certificado_status=fs.certificado_status if fs else None,
        certificado_cnpj=fs.certificado_cnpj if fs else None,
        certificado_validade=fs.certificado_validade if fs else None,
        certificado_dias_restantes=dias_para_vencer_certificado(fs.certificado_validade) if fs else None,
        serie_nfe=fs.serie_nfe if fs else 1,
        ultimo_numero_nfe=fs.ultimo_numero_nfe if fs else 0,
        serie_nfce=fs.serie_nfce if fs else 1,
        ultimo_numero_nfce=fs.ultimo_numero_nfce if fs else 0,
        csc_token=mascarar_csc(obter_csc_token(fs)) if fs else None,
        csc_configurado=bool(fs and obter_csc_token(fs)),
        csc_id=fs.csc_id if fs else None,
        limite_consumidor_anonimo=(
            fs.limite_consumidor_anonimo if fs else 1000000
        ),
    )

from app.schemas.empresa import FiscalSettingsUpdate
from app.services.empresa import update_fiscal_settings, upload_certificado_focus
from fastapi import UploadFile, File, Form

# ===========================================================================
# SUGESTÃO DE CAMPOS FISCAIS
# ===========================================================================

@router.get(
    "/sugestao/produto",
    summary="Sugerir Campos Fiscais de Produto",
    description=(
        "Devolve os campos fiscais que o sistema consegue deduzir para um "
        "produto novo, com procedência e fundamentação. NÃO persiste nada: "
        "quem decide o que aplicar é o formulário."
    ),
)
def sugerir_campos_fiscais_produto(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    """
    Sugestões para o cadastro de produto.

    Camada de leitura: sugerir não emite nada.

    ATENÇÃO: o router inteiro de `/fiscal` exige o módulo NFE
    (`APIRouter(dependencies=[requer_modulo("NFE")])`), então esta rota TAMBÉM
    exige — ao contrário do que esta docstring afirmava. Deixar o catálogo
    pronto antes de contratar depende de mover a rota para fora deste router,
    o que não foi feito.

    Cada campo vem com `fundamentacao` (o "por quê?" que a tela mostra ao lado)
    e `exige_confirmacao`, ligado onde errar produz nota aceita e errada.
    """
    from app.services.fiscal.derivacao import derivar_produto
    from app.services.fiscal.derivacao.resolver_db import contexto_do_cadastro

    contexto = contexto_do_cadastro(db, user_token["empresa_id"])
    return {"sugestoes": [s.model_dump() for s in derivar_produto(contexto)]}


@router.get(
    "/campos/produto",
    summary="Campos Fiscais Aplicáveis ao Produto",
    description=(
        "Diz quais campos fiscais o cadastro de produto deve mostrar e exigir, "
        "conforme o regime tributário da empresa. Empresa do Simples não vê "
        "CST nem alíquota de ICMS; empresa do regime normal não vê CSOSN."
    ),
)
def campos_fiscais_produto(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    """
    O mapa de campos da tela de produto.

    Quem responde é o mesmo `obter_crt` que decide na hora de emitir — é essa
    a razão de a pergunta vir ao servidor em vez de virar `v-if` na tela.

    Exige o módulo NFE, como todo este router. A tela trata a recusa mostrando
    TODOS os campos: esconder campo obrigatório por falha de consulta produz
    cadastro incompleto que ninguém consegue explicar.
    """
    from app.db.crud import fiscal as crud
    from app.services.fiscal.campos_produto import mapa_campos_da_empresa

    empresa = crud.get_empresa(db, user_token["empresa_id"])
    return mapa_campos_da_empresa(empresa)


# ===========================================================================
# TABELA NCM (achar o código pela descrição)
# ===========================================================================


@router.get(
    "/ncm",
    summary="Buscar NCM por Código ou Descrição",
    description=(
        "Procura na tabela NCM embarcada. Aceita o código (com ou sem pontos) "
        "e a descrição — 'mouse', 'caneta esferográfica'. Funciona sem internet."
    ),
)
def buscar_ncm(
    user_token: dict = Depends(get_current_active_user),
    *,
    buscar: str = Query("", max_length=120),
    limite: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    A busca de NCM.

    Reusa `core/busca.py`, o mesmo motor de produto, cliente e serviço — quatro
    camadas: contém, palavras soltas, acentos com relevância e erro de
    digitação. Filtrar CSV em Python seria um segundo mecanismo de busca, com
    outro comportamento, na mesma tela.

    Varre a `descricao_completa` porque a descrição própria costuma ser um
    fragmento: a do 9608.10.00 é só "Canetas esferográficas", e quem digita
    "caneta para escrever" não a encontraria.
    """
    from app.core import busca as motor_busca
    from app.db.models.ncm import Ncm

    termo = (buscar or "").strip()
    if not termo:
        return {"resultados": [], "total_na_base": db.query(Ncm).count()}

    # Código digitado com pontos ("9608.10.00") casa com o gravado sem eles.
    so_digitos = "".join(c for c in termo if c.isdigit())
    if so_digitos and so_digitos == termo.replace(".", "").replace(" ", "") and len(so_digitos) >= 2:
        resultados = (
            db.query(Ncm)
            .filter(Ncm.codigo.startswith(so_digitos))
            .order_by(Ncm.codigo)
            .limit(limite)
            .all()
        )
        return {
            "resultados": [
                {"codigo": n.codigo, "descricao": n.descricao,
                 "descricao_completa": n.descricao_completa}
                for n in resultados
            ],
            "total_na_base": db.query(Ncm).count(),
        }

    # BUSCA EM DUAS PASSADAS, e as duas razões são igualmente importantes.
    #
    # RELEVÂNCIA: "caneta" tem de trazer 9608.10.00, não um fichário cujo
    # CAPÍTULO menciona canetas. Quem casa na descrição própria vem primeiro.
    #
    # VELOCIDADE: `descricao_completa` guarda a hierarquia inteira (até 2000
    # caracteres) e `LIKE %termo%` não usa índice — varrer as 10.437 linhas
    # custava ~600 ms no pior caso, lento demais para busca enquanto se digita.
    # A primeira passada olha só campos curtos e resolve a maioria das buscas.
    def _consultar(campos):
        consulta = db.query(Ncm)
        filtro = motor_busca.filtro_busca(termo, campos)
        if filtro is None:
            return []
        consulta = consulta.filter(filtro)
        ordem = motor_busca.ordenacao_relevancia(termo, Ncm.descricao, (Ncm.codigo,))
        if ordem is not None:
            consulta = consulta.order_by(ordem)
        return consulta.limit(limite).all()

    resultados = _consultar((Ncm.codigo, Ncm.descricao))

    # Segunda passada só quando a primeira NÃO ACHOU NADA — e não quando ela
    # achou menos que o limite.
    #
    # A diferença é de meio segundo: completar 12 achados bons com 8 fracos
    # obrigava a varrer a hierarquia em TODA busca. Doze resultados relevantes
    # valem mais que vinte com enchimento.
    #
    # A passada existe para o caso do pneu: a descrição própria do 4011.10.00 é
    # "Dos tipos utilizados em automóveis de passageiros", e "pneumáticos" só
    # aparece no ancestral.
    if not resultados:
        vistos = {n.codigo for n in resultados}
        complemento = [
            n for n in _consultar((Ncm.descricao_completa,)) if n.codigo not in vistos
        ]
        resultados = (resultados + complemento)[:limite]

    return {
        "resultados": [
            {
                "codigo": n.codigo,
                "descricao": n.descricao,
                "descricao_completa": n.descricao_completa,
            }
            for n in resultados
        ],
        "total_na_base": db.query(Ncm).count(),
    }



# ===========================================================================
# PRÉ-VALIDAÇÃO DO CADASTRO DE PRODUTO
# ===========================================================================


@router.post(
    "/validar/produto",
    summary="Conferir os Dados Fiscais Antes de Salvar",
    description=(
        "Diz o que a SEFAZ recusaria neste produto, campo a campo, SEM emitir "
        "nada. Aplica a mesma cascata da emissão (produto → regra por NCM → "
        "padrão da loja) e roda a MESMA regra do gate."
    ),
)
def validar_produto_fiscal(
    user_token: dict = Depends(get_current_active_user),
    *,
    dados: ProdutoFiscalUpdate,
    nome_produto: str = Query("Este produto", max_length=120),
    db: Session = Depends(get_db),
):
    """
    A pré-validação do cadastro.

    POR QUE PASSA PELO SERVIDOR, E NÃO É UM ZOD NA TELA
    ---------------------------------------------------
    Porque a regra já existe no `validators.py`, e ela é mais esperta do que
    "campo obrigatório": CEST só é exigido sob substituição tributária, a
    redução de base só com CST 20, e há códigos que o motor ainda não calcula.
    Reescrever isso em Zod criaria um segundo lugar para desatualizar — e
    quando os dois discordam, o cadastro aprova o que a emissão recusa.

    E POR QUE APLICA A CASCATA
    --------------------------
    Sem ela, um produto cadastrado só com NCM apareceria cheio de pendências,
    quando na verdade a loja já respondeu tudo na tributação padrão. A tela
    mostraria erro onde não há.
    """
    from types import SimpleNamespace

    from app.db.crud import tributacao as tributacao_crud
    from app.services.fiscal.helpers import obter_crt, usa_csosn
    from app.services.fiscal.tributacao import mesclar
    from app.services.fiscal.validators import conferir_fiscal_do_produto

    empresa_id = user_token["empresa_id"]
    empresa = fiscal_crud.get_empresa(db, empresa_id)

    rascunho = SimpleNamespace(**dados.model_dump())

    padrao = tributacao_crud.get_tributacao_padrao(db, empresa_id)
    regra = (
        tributacao_crud.get_regra_ncm(db, empresa_id, dados.ncm)
        if dados.ncm else None
    )
    efetivo = mesclar(produto_fiscal=rascunho, regra_ncm=regra, padrao=padrao)

    pendencias = conferir_fiscal_do_produto(
        efetivo,
        nome=nome_produto,
        simples_nacional=usa_csosn(obter_crt(empresa)),
    )

    return {
        "pode_emitir": not pendencias,
        "pendencias": [
            {"campo": p.campo, "mensagem": p.mensagem} for p in pendencias
        ],
        # De onde veio cada valor conferido — a tela diz "CSOSN 102, da
        # tributação padrão da loja" em vez de mostrar campo preenchido sem
        # explicação.
        "procedencia": getattr(efetivo, "procedencia", {}) or {},
    }




def _cliente_fiscal(db: Session, empresa_id: int):
    """
    O client da emissora, montado como a emissão monta.

    Vive aqui porque os endpoints de arquivo precisam dele para o plano B
    (buscar na emissora o que não está no disco) — e a assinatura pede
    ambiente e token, não a sessão.
    """
    from app.db.crud import fiscal as crud
    from app.services.fiscal.http.client_factory import get_fiscal_client

    settings_fiscais = crud.get_fiscal_settings(db, empresa_id)
    ambiente = settings_fiscais.ambiente_emissao if settings_fiscais else 2
    return get_fiscal_client(ambiente, crud.get_licenca_token(db))



# ===========================================================================
# ARQUIVOS DA NOTA (XML guardado no computador da loja)
# ===========================================================================


@router.get(
    "/documentos/{documento_id}/xml",
    summary="Baixar o XML da Nota",
    description=(
        "Entrega o XML autorizado. Lê do disco da loja quando existe — e aí "
        "funciona sem internet; cai na emissora só para documentos anteriores "
        "ao arquivamento local, guardando o que baixar."
    ),
)
def baixar_xml_documento(
    user_token: dict = Depends(get_current_active_user),
    documento_id: int = Path(..., ge=1),
    *,
    db: Session = Depends(get_db),
):
    from fastapi.responses import Response
    from app.services.fiscal.arquivos import obter_xml

    doc = fiscal_crud.get_documento_fiscal(db, documento_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    conteudo = obter_xml(db, _cliente_fiscal(db, user_token["empresa_id"]), doc)
    if not conteudo:
        raise HTTPException(
            status_code=404,
            detail=(
                "XML indisponível: não está guardado nesta máquina e a emissora "
                "não respondeu."
            ),
        )
    db.commit()  # o `obter_xml` pode ter gravado o caminho recém-arquivado

    nome = f"{doc.chave_acesso or f'documento-{doc.id}'}.xml"
    return Response(
        content=conteudo,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get(
    "/documentos/{documento_id}/pdf",
    summary="Baixar o DANFE da Nota",
    description=(
        "Entrega o DANFE em PDF. Lê do disco da loja quando existe — e aí "
        "reimprime sem internet; cai na emissora como plano B."
    ),
)
def baixar_pdf_documento(
    user_token: dict = Depends(get_current_active_user),
    documento_id: int = Path(..., ge=1),
    *,
    db: Session = Depends(get_db),
):
    from fastapi.responses import Response
    from app.services.fiscal.arquivos import guardar_pdf, ler_pdf

    doc = fiscal_crud.get_documento_fiscal(db, documento_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    conteudo = ler_pdf(doc.caminho_pdf_local)
    if not conteudo and doc.url_pdf:
        conteudo = _cliente_fiscal(db, user_token["empresa_id"]).baixar_pdf(doc.url_pdf)
        caminho = guardar_pdf(
            conteudo, chave=doc.chave_acesso,
            fallback=f"doc-{doc.id}", quando=doc.data_autorizacao,
        )
        if caminho:
            doc.caminho_pdf_local = caminho
            db.commit()

    if not conteudo:
        raise HTTPException(
            status_code=404,
            detail="DANFE indisponível: não está nesta máquina e a emissora não respondeu.",
        )

    nome = f"{doc.chave_acesso or f'documento-{doc.id}'}.pdf"
    return Response(
        content=conteudo,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.post(
    "/documentos/arquivos/sincronizar",
    summary="Guardar os XMLs que faltam",
    description=(
        "Baixa da emissora o XML das notas autorizadas que ainda não têm "
        "arquivo nesta máquina. É o caminho das notas emitidas antes do "
        "arquivamento local existir. Processa em lotes — rode de novo enquanto "
        "sobrar."
    ),
)
def sincronizar_arquivos_fiscais(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    limite: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    from app.services.fiscal.arquivos import sincronizar_pendentes

    def _sincronizar(db_: Session):
        cliente = _cliente_fiscal(db_, user_token["empresa_id"])
        return sincronizar_pendentes(db_, cliente, limite=limite)

    return _handle_db_transaction(db, _sincronizar)



# ===========================================================================
# TRIBUTAÇÃO DA LOJA (padrão + regras por NCM)
# ===========================================================================
#
# A cascata é: produto (exceção) → regra por NCM → padrão da loja.
# Ver `app/services/fiscal/tributacao.py` e `docs/cadastro-produto-plano.md`.
#
# LER é para qualquer usuário ativo; ESCREVER exige master
# (`requer_configuracao_fiscal`), porque muda o imposto de TODA nota futura —
# é decisão do dono, de preferência com o contador.


@router.get(
    "/tributacao-padrao",
    response_model=Optional[TributacaoPadraoRead],
    summary="Tributação Padrão da Loja",
    description=(
        "A resposta padrão da loja para CFOP, origem, CST/CSOSN e PIS/COFINS. "
        "Devolve null enquanto ninguém configurou — e nesse estado a cascata é "
        "inerte: cada produto vale pelo que tem gravado nele."
    ),
)
def obter_tributacao_padrao(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    from app.db.crud import tributacao as tributacao_crud

    return tributacao_crud.get_tributacao_padrao(db, user_token["empresa_id"])


@router.put(
    "/tributacao-padrao",
    response_model=TributacaoPadraoRead,
    summary="Salvar a Tributação Padrão da Loja",
    description=(
        "Cria ou atualiza a tributação padrão. Campo omitido não é apagado: "
        "vazio significa 'não decido isto' e deixa o produto responder."
    ),
)
def salvar_tributacao_padrao(
    user_token: dict = Depends(requer_configuracao_fiscal),
    *,
    dados: TributacaoPadraoUpdate,
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone
    from app.db.crud import tributacao as tributacao_crud

    def _salvar(db_: Session):
        registro = tributacao_crud.upsert_tributacao_padrao(
            db_, user_token["empresa_id"], dados,
        )
        # Quem confirmou importa: o padrão nasce SUGERIDO pelo motor de
        # derivação, e emitir com valor que ninguém olhou é o risco da nota
        # aceita e errada.
        registro.confirmado_em = datetime.now(timezone.utc)
        registro.confirmado_por = user_token.get("nome") or "Master"
        db_.flush()
        return registro

    return _handle_db_transaction(db, _salvar)


@router.get(
    "/regras-ncm",
    response_model=list[RegraNcmRead],
    summary="Regras Tributárias por NCM",
    description="As exceções ao padrão da loja. Quem tem dez pneus cadastra uma regra, e os dez obedecem.",
)
def listar_regras_ncm(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    from app.db.crud import tributacao as tributacao_crud

    return tributacao_crud.listar_regras_ncm(db, user_token["empresa_id"])


@router.put(
    "/regras-ncm/{ncm}",
    response_model=RegraNcmRead,
    summary="Salvar Regra Tributária de um NCM",
)
def salvar_regra_ncm(
    user_token: dict = Depends(requer_configuracao_fiscal),
    ncm: str = Path(..., min_length=8, max_length=8, description="NCM de 8 dígitos"),
    *,
    dados: RegraNcmUpsert,
    db: Session = Depends(get_db),
):
    from app.db.crud import tributacao as tributacao_crud

    if not ncm.isdigit():
        raise HTTPException(status_code=422, detail="NCM deve conter 8 dígitos numéricos.")

    return _handle_db_transaction(
        db, tributacao_crud.upsert_regra_ncm, user_token["empresa_id"], ncm, dados,
    )


@router.delete(
    "/regras-ncm/{ncm}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover Regra Tributária de um NCM",
    description=(
        "Os produtos daquele NCM voltam a seguir o padrão da loja. Nenhum "
        "produto é alterado — a cascata é resolvida na leitura."
    ),
)
def remover_regra_ncm(
    user_token: dict = Depends(requer_configuracao_fiscal),
    ncm: str = Path(..., min_length=8, max_length=8),
    *,
    db: Session = Depends(get_db),
):
    from app.db.crud import tributacao as tributacao_crud

    removeu = _handle_db_transaction(
        db, tributacao_crud.deletar_regra_ncm, user_token["empresa_id"], ncm,
    )
    if not removeu:
        raise HTTPException(status_code=404, detail=f"Nenhuma regra cadastrada para o NCM {ncm}.")



# ===========================================================================
# ATIVACAO LOCAL DO MODULO -- REMOVIDA DE PROPOSITO
# ===========================================================================
#
# A feat/fiscal-module tinha aqui um POST /ativar que ligava uma flag local
# (empresa_fiscal_settings.modulo_fiscal_ativo) para liberar as telas. A
# propria docstring dizia que existia so ate o servidor de licencas mandar o
# claim de recursos no JWT.
#
# Aqui esse claim JA existe: e o `modulos`, o mesmo que o FINANCEIRO usa, e a
# concessao do NFE e feita pela plataforma, por plano ou por cliente. Manter a
# rota daria a um master a chance de destravar as telas na propria maquina --
# contra a regra de NEGAR por padrao que sustenta o modulo fiscal aqui.
#
# Se um dia o onboarding precisar de um empurrao, ele vem da plataforma, nao
# de uma coluna no SQLite do cliente.



@router.put(
    "/configuracao",
    response_model=FiscalConfiguracao,
    summary="Atualizar Configuração Fiscal",
    description="Atualiza configurações fiscais da empresa.",
)
def atualizar_configuracao(
    user_token: dict = Depends(requer_configuracao_fiscal),
    *,
    db: Session = Depends(get_db),
    payload: FiscalSettingsUpdate = Body(...)
):
    empresa_id = user_token["empresa_id"]
    # `update_fiscal_settings` termina em `flush`, nunca em `commit`, e o
    # `get_db` so fecha a sessao -- fechar com transacao pendente DESCARTA a
    # escrita. A tela dizia "salvo", devolvia os valores novos (que estao na
    # sessao) e no proximo GET tudo voltava ao que era: serie, numero, CSC e
    # limite nunca chegaram ao disco. Quem comita nesta base e o
    # `_handle_db_transaction`, como nos outros oito endpoints deste arquivo.
    fs = _handle_db_transaction(db, update_fiscal_settings, empresa_id, payload)
    
    ambiente = fs.ambiente_emissao if fs else 2
    cert_configurado = bool(
        fs and (
            fs.certificado_digital_path
            or fs.certificado_thumbprint
            or fs.certificado_status == "CONECTADO_NUVEM"
        )
    )
    cert_valido = bool(
        cert_configurado and fs.certificado_validade and fs.certificado_validade.replace(tzinfo=None) > datetime.now()
    )

    return FiscalConfiguracao(
        ambiente=ambiente,
        ambiente_label="Homologação" if ambiente == 2 else "Produção",
        mock_ativo=settings.FISCAL_MOCK_ENABLED,
        certificado_configurado=cert_configurado,
        certificado_valido=cert_valido,
        certificado_status=fs.certificado_status if fs else None,
        certificado_cnpj=fs.certificado_cnpj if fs else None,
        certificado_validade=fs.certificado_validade if fs else None,
        certificado_dias_restantes=dias_para_vencer_certificado(fs.certificado_validade) if fs else None,
        serie_nfe=fs.serie_nfe if fs else 1,
        ultimo_numero_nfe=fs.ultimo_numero_nfe if fs else 0,
        serie_nfce=fs.serie_nfce if fs else 1,
        ultimo_numero_nfce=fs.ultimo_numero_nfce if fs else 0,
        csc_token=mascarar_csc(obter_csc_token(fs)) if fs else None,
        csc_configurado=bool(fs and obter_csc_token(fs)),
        csc_id=fs.csc_id if fs else None,
        limite_consumidor_anonimo=(
            fs.limite_consumidor_anonimo if fs else 1000000
        ),
    )

@router.get(
    "/plataforma",
    response_model=DiagnosticoPlataforma,
    summary="Diagnóstico da Plataforma",
    description=(
        "O que a plataforma de emissão enxerga desta licença — ambiente, token, "
        "CSC e certificado — ao lado do CNPJ que este ERP envia como emitente."
    ),
)
def obter_diagnostico_plataforma(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    """
    Responde "de quem é o problema" sem abrir chamado.

    Quando a emissão é recusada, hoje o lojista só vê a mensagem que a
    plataforma devolveu — e ela costuma parecer da SEFAZ, porque o corpo do 4xx
    vira `mensagem_sefaz`. Não havia como olhar o outro lado.

    "Não sei" NUNCA vira "não configurado": se a consulta falhar,
    `consultar_config` devolve {} e esta rota responde `consultou=False`. Um
    diagnóstico indisponível não pode virar acusação.
    """
    from app.services.fiscal.http import get_fiscal_client

    empresa_id = user_token["empresa_id"]
    fs = fiscal_crud.get_fiscal_settings(db, empresa_id)
    ambiente = fs.ambiente_emissao if fs else 2

    empresa = fiscal_crud.get_empresa(db, empresa_id)
    cnpj_erp = _so_digitos(empresa.documento) if empresa else None

    config = get_fiscal_client(ambiente, fiscal_crud.get_licenca_token(db)).consultar_config()
    if not config:
        return DiagnosticoPlataforma(consultou=False, cnpj_erp=cnpj_erp)

    # A plataforma ainda não devolve o CNPJ da ficha dela. Aceitamos as duas
    # grafias prováveis para o dia em que devolver — até lá, `cnpj_confere` fica
    # None, que a tela mostra como "a plataforma não informa", e não como
    # divergência.
    cnpj_plataforma = _so_digitos(config.get("cnpj") or config.get("cnpjEmitente"))

    return DiagnosticoPlataforma(
        consultou=True,
        ambiente=config.get("ambiente"),
        ambiente_nome=config.get("ambienteNome"),
        configurado=config.get("configurado"),
        token_configurado=config.get("tokenConfigurado"),
        csc_configurado=config.get("cscConfigurado"),
        certificado_status=config.get("certificadoStatus"),
        pendencias=[str(p) for p in (config.get("pendencias") or [])],
        cnpj_erp=cnpj_erp,
        cnpj_plataforma=cnpj_plataforma,
        cnpj_confere=(
            None if not (cnpj_erp and cnpj_plataforma) else cnpj_erp == cnpj_plataforma
        ),
    )


@router.post(
    "/certificado/upload-focus",
    summary="Upload de Certificado para a Nuvem",
    description="Envia o certificado para a API da Focus NFe (simulado) e atualiza o status."
)
def upload_certificado_focus_endpoint(
    user_token: dict = Depends(requer_configuracao_fiscal),
    *,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    senha: str = Form(...)
):
    empresa_id = user_token["empresa_id"]
    # Mesmo defeito do PUT /configuracao acima: o servico so dava `flush`, e a
    # sessao morria sem `commit`. O lojista via "Certificado enviado com
    # sucesso!", reabria o Centro Fiscal e lia "Nao configurado" -- porque de
    # fato nada tinha sido gravado.
    _handle_db_transaction(db, upload_certificado_focus, empresa_id, file, senha)
    return {"message": "Certificado enviado e configurado com sucesso."}


# ===========================================================================
# INUTILIZAÇÃO DE NUMERAÇÃO
# ===========================================================================

@router.get(
    "/numeracao/gaps",
    response_model=list[GapNumeracao],
    summary="Buracos na Numeração",
    description=(
        "Lista faixas de numeração que foram reservadas mas nunca viraram nota "
        "autorizada. Esses números precisam ser inutilizados junto à SEFAZ."
    ),
)
def listar_gaps_numeracao(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    from app.services.fiscal.inutilizacao import listar_gaps_numeracao as _gaps

    return _gaps(db, user_token["empresa_id"])


@router.get(
    "/numeracao/inutilizacoes",
    response_model=list[InutilizacaoRead],
    summary="Inutilizações Solicitadas",
    description="Histórico de pedidos de inutilização de faixa de numeração.",
)
def listar_inutilizacoes(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    from app.services.fiscal.inutilizacao import listar_inutilizacoes as _listar

    return _listar(db, user_token["empresa_id"])


@router.post(
    "/numeracao/inutilizar",
    response_model=InutilizacaoRead,
    summary="Inutilizar Faixa de Numeração",
    description=(
        "Declara à SEFAZ que uma faixa de numeração não foi utilizada. "
        "A justificativa precisa de no mínimo 15 caracteres."
    ),
)
def inutilizar_numeracao(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
    payload: InutilizacaoRequest = Body(...),
):
    from app.services.fiscal.inutilizacao import solicitar_inutilizacao

    return _handle_db_transaction(
        db,
        solicitar_inutilizacao,
        user_token["empresa_id"],
        payload.serie,
        payload.numero_inicial,
        payload.numero_final,
        payload.justificativa,
    )
