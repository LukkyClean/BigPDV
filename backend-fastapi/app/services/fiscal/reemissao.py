# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/reemissao.py
# DESCRIÇÃO: Reemissão de um documento fiscal rejeitado.
#
# Reemitir NÃO é uma emissão diferente: é a emissão da mesma origem, de novo,
# com o elo para a tentativa anterior. Por isso este módulo não monta payload,
# não reserva número e não fala com a plataforma -- ele valida o que só a
# reemissão sabe (status do anterior, tamanho da cadeia) e DESPACHA para o
# `emitir_*` da origem, que já faz tudo isso com os testes e as cicatrizes.
#
# Antes disto existiam duas cópias de `reemitir_documento`, e nenhuma
# transmitia: criavam uma linha PENDENTE e paravam. A que estava ligada ao
# endpoint ainda herdava o `numero_documento` da rejeitada -- ligar a
# transmissão nela produziria Rejeição 204 na primeira tentativa.
#
# Fica em módulo próprio de propósito: `emissao.py` está na beira do teto de
# bytecode do PyArmor, e novidade lá quebra o sidecar.
# ---------------------------------------------------------------------------

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.crud import fiscal as crud
from app.db.models.documento_fiscal import DocumentoFiscal

from .emissao import emitir_nfce_venda, emitir_nfe_os, emitir_nfe_venda

logger = logging.getLogger(__name__)

# Contando a original, quantas vezes a mesma origem pode ir à SEFAZ. Depois
# disso o problema não é a nota -- é o cadastro, e repetir só queima número.
MAX_TENTATIVAS = 5


def _tamanho_da_cadeia(db: Session, doc: DocumentoFiscal) -> int:
    """Quantas tentativas existem desta origem até `doc`, inclusive."""
    tamanho = 1
    atual = doc
    while atual is not None and atual.tentativa_anterior_id:
        tamanho += 1
        atual = crud.get_documento_fiscal(db, atual.tentativa_anterior_id)
    return tamanho


def reemitir_documento(db: Session, documento_id: int, empresa_id: int) -> DocumentoFiscal:
    """
    Emite de novo a origem de um documento REJEITADO e devolve o documento
    NOVO, já com o desfecho da SEFAZ (AUTORIZADA, PROCESSANDO, REJEITADA ou
    INDETERMINADA) e `tentativa_anterior_id` apontando para o rejeitado.

    Só REJEITADA é reemitível. DENEGADA é decisão da SEFAZ sobre o
    contribuinte -- reenviar volta denegada e queima outro número. Os demais
    status ou estão vivos (bloqueiam a origem) ou nunca saíram do prédio
    (NAO_TRANSMITIDA se emite pelo caminho normal, não por aqui).

    O número é sempre NOVO: o da tentativa anterior pode ter sido consumido na
    SEFAZ, e reusar dá Rejeição 204. O buraco se resolve com inutilização.
    """
    doc_anterior = crud.get_documento_fiscal(db, documento_id)
    if not doc_anterior:
        raise HTTPException(status_code=404, detail="Documento fiscal não encontrado.")

    if doc_anterior.status == "DENEGADA":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Documento denegado pela SEFAZ: a decisão é sobre a situação cadastral "
                "do contribuinte, e reenviar a mesma nota volta denegada. Regularize a "
                "situação junto à SEFAZ antes de emitir novamente."
            ),
        )
    if doc_anterior.status != "REJEITADA":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Apenas documentos rejeitados podem ser reemitidos.",
        )

    tentativas = _tamanho_da_cadeia(db, doc_anterior)
    if tentativas >= MAX_TENTATIVAS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Esta origem já foi enviada {tentativas} vezes. Corrija o cadastro "
                f"apontado na última rejeição e emita pela venda ou OS."
            ),
        )

    logger.info(
        "[FISCAL] Reemitindo %s de %s %s (tentativa %d, anterior=%s)",
        doc_anterior.tipo_documento, doc_anterior.origem_tipo,
        doc_anterior.origem_numero_os or doc_anterior.origem_id,
        tentativas + 1, doc_anterior.id,
    )

    if doc_anterior.origem_tipo == "OS":
        return emitir_nfe_os(
            db, doc_anterior.origem_numero_os, empresa_id,
            tentativa_anterior_id=doc_anterior.id,
        )

    if doc_anterior.origem_tipo == "VENDA":
        # `origem_id` guarda o NÚMERO da venda, não a PK -- ver `emitir_nfe_venda`.
        venda_id = crud.get_venda_id_por_numero(db, doc_anterior.origem_id)
        if venda_id is None:
            raise HTTPException(
                status_code=404,
                detail=f"Venda nº {doc_anterior.origem_id} não encontrada.",
            )
        emitir = emitir_nfce_venda if doc_anterior.tipo_documento == "NFCE" else emitir_nfe_venda
        return emitir(db, venda_id, empresa_id, tentativa_anterior_id=doc_anterior.id)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Origem '{doc_anterior.origem_tipo}' não pode ser reemitida por aqui.",
    )
