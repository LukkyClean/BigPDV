# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/reconciliacao.py
# DESCRIÇÃO: Reconciliação de documentos fiscais em estado não-terminal.
#
# O polling de emissão vive num BackgroundTask: morre junto com o processo.
# Fechar o app, reiniciar a máquina ou estourar a janela de ~3 minutos deixa
# o documento preso em PROCESSANDO/PENDENTE/INDETERMINADA — e, como esses
# estados bloqueiam nova emissão, a venda fica travada sem saída pela interface.
#
# Esta rotina roda no startup e reconsulta cada pendência na API.
# ---------------------------------------------------------------------------

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.db.crud import fiscal as crud
from app.db.models.documento_fiscal import DocumentoFiscal

logger = logging.getLogger(__name__)


# Estados que ainda podem mudar de valor sozinhos — precisam ser reconsultados.
STATUS_NAO_TERMINAIS = ("PROCESSANDO", "PENDENTE", "INDETERMINADA")

# Teto por execução: o startup não pode ficar refém de uma fila gigante.
LIMITE_POR_EXECUCAO = 50


def listar_documentos_pendentes(
    db: Session, limite: int = LIMITE_POR_EXECUCAO
) -> list[DocumentoFiscal]:
    """Documentos que continuam sem resposta definitiva da SEFAZ."""
    return (
        db.query(DocumentoFiscal)
        .filter(
            DocumentoFiscal.status.in_(STATUS_NAO_TERMINAIS),
            DocumentoFiscal.ref_api.isnot(None),
        )
        .order_by(DocumentoFiscal.data_criacao.asc())
        .limit(limite)
        .all()
    )


def reconciliar_documento(
    db: Session, doc: DocumentoFiscal, empresa_id: int
) -> Optional[str]:
    """
    Reconsulta um documento e atualiza seu status.

    Retorna o novo status quando ele muda, ou None se continuar pendente.
    Nunca levanta: uma falha de rede aqui deve deixar o documento como está
    para a próxima execução, não derrubar o startup.
    """
    from .emissao import consultar_documento

    status_anterior = doc.status
    try:
        atualizado = consultar_documento(db, doc.id, empresa_id)
    except Exception as e:
        logger.warning(
            "[FISCAL] Reconciliação falhou para documento %s (ref=%s): %s",
            doc.id, doc.ref_api, e,
        )
        return None

    if atualizado.status != status_anterior:
        logger.info(
            "[FISCAL] Documento %s reconciliado: %s -> %s",
            doc.id, status_anterior, atualizado.status,
        )
        return atualizado.status

    return None


def reconciliar_pendentes(db: Session) -> dict:
    """
    Reconsulta todos os documentos sem resposta definitiva.

    Retorna um resumo {verificados, resolvidos, ainda_pendentes} para log.
    """
    pendentes = listar_documentos_pendentes(db)
    if not pendentes:
        return {"verificados": 0, "resolvidos": 0, "ainda_pendentes": 0}

    resolvidos = 0
    for doc in pendentes:
        empresa_id = _empresa_do_documento(db, doc)
        if empresa_id is None:
            logger.warning(
                "[FISCAL] Documento %s sem empresa identificável — ignorado.", doc.id
            )
            continue

        if reconciliar_documento(db, doc, empresa_id):
            resolvidos += 1

    db.commit()

    return {
        "verificados": len(pendentes),
        "resolvidos": resolvidos,
        "ainda_pendentes": len(pendentes) - resolvidos,
    }


def _empresa_do_documento(db: Session, doc: DocumentoFiscal) -> Optional[int]:
    """
    Descobre a empresa emissora do documento.

    DocumentoFiscal não guarda empresa_id (a origem é polimórfica). Como o
    StartBig é monoempresa por instalação, a empresa com configuração fiscal
    é a resposta correta.
    """
    from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings

    fs = db.query(EmpresaFiscalSettings).first()
    return fs.empresa_id if fs else None


def reconciliar_no_startup() -> None:
    """
    Ponto de entrada chamado pelo lifespan. Abre a própria sessão e nunca
    propaga exceção — falhar aqui não pode impedir o app de subir.
    """
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        resumo = reconciliar_pendentes(db)
        if resumo["verificados"]:
            logger.info(
                "[FISCAL] Reconciliação de boot: %d verificados, %d resolvidos, %d pendentes.",
                resumo["verificados"], resumo["resolvidos"], resumo["ainda_pendentes"],
            )
    except Exception as e:
        db.rollback()
        logger.error("[FISCAL] Reconciliação de boot falhou: %s", e)
    finally:
        db.close()
