# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/espelho_nota.py
# DESCRIÇÃO: Espelha o DocumentoFiscal na nota da venda (venda.nota_fiscal).
#
# O livro fiscal é `documento_fiscal`; a tela da venda lê `venda_nota_fiscal`.
# Até 11/09/2026 só a NFC-e espelhava, e só na emissão: a NF-e emitida pelo
# modal da venda deixava a nota em PENDENTE (o botão "Emitir NF-e" continuava
# na tela com a nota já autorizada), e um PROCESSANDO que virava AUTORIZADA no
# polling nunca chegava à venda. Um lugar só, chamado por quem muda o status.
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session

from app.db.crud import fiscal as crud
from app.db.models.documento_fiscal import DocumentoFiscal
from app.db.models.venda_nota_fiscal import VendaNotaFiscal


def espelhar_na_nota_da_venda(db: Session, doc: DocumentoFiscal) -> None:
    """Copia o estado do documento para a nota da venda de origem, se houver.

    Só documentos de VENDA têm espelho; a OS guarda o seu do lado dela.
    Nunca levanta: espelho é conveniência da tela, não parte da emissão.
    """
    if doc.origem_tipo != "VENDA" or doc.origem_id is None:
        return

    venda_id = crud.get_venda_id_por_numero(db, doc.origem_id)
    if venda_id is None:
        return

    nota = db.query(VendaNotaFiscal).filter(VendaNotaFiscal.venda_id == venda_id).first()
    if nota is None:
        return

    nota.status_nota = doc.status
    nota.chave_acesso = doc.chave_acesso
    nota.numero_nota = doc.numero_documento
    nota.serie = doc.serie
    nota.protocolo_autorizacao = doc.protocolo_autorizacao
    nota.data_autorizacao = doc.data_autorizacao
    nota.url_danfe = doc.url_pdf
    nota.qrcode = doc.qrcode
    nota.mensagem_sefaz = (doc.mensagem_sefaz or "")[:500] or None
