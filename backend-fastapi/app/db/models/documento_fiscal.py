# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/documento_fiscal.py
# DESCRIÇÃO: Tabela unificada de documentos fiscais emitidos.
#
# Registra cada emissão fiscal (NFe, NFCe, NFSe) independente da origem
# (Venda ou Ordem de Serviço). A referência à origem é polimórfica
# (origem_tipo + origem_id/origem_numero_os), sem FK rígida.
#
# Esta tabela é usada pelo Centro Fiscal para exibir todos os documentos
# emitidos, seus status e permitir ações como reemissão e download.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.documento_fiscal import DocumentoFiscal as _Self


class DocumentoFiscal(Base):
    __tablename__ = "documento_fiscal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # --- Tipo e origem polimórfica (sem FK) ---
    # NFE, NFCE, NFSE
    tipo_documento: Mapped[str] = mapped_column(String(5), nullable=False)
    # VENDA, ORDEM_SERVICO
    origem_tipo: Mapped[str] = mapped_column(String(15), nullable=False)
    # ID da venda (quando origem_tipo = VENDA)
    origem_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    # Número da OS (quando origem_tipo = ORDEM_SERVICO)
    origem_numero_os: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)

    # --- Status ---
    # PENDENTE, PROCESSANDO, AUTORIZADA, REJEITADA, CANCELADA, DENEGADA
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="PENDENTE", index=True)

    # --- Dados do documento emitido ---
    chave_acesso: Mapped[Optional[str]] = mapped_column(String(44), nullable=True)
    numero_documento: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    serie: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    protocolo_autorizacao: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    data_autorizacao: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # --- Arquivos ---
    url_pdf: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    url_xml: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # --- SEFAZ feedback ---
    mensagem_sefaz: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    codigo_status_sefaz: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    motivo_rejeicao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Valor total (centavos) ---
    valor_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # --- Específicos da NFC-e (modelo 65) ---
    # Ficam AQUI, e não só em venda_nota_fiscal, porque a reimpressão do cupom
    # parte do documento fiscal: sem estes três não há como reimprimir sem
    # consultar o provedor de novo — e o cliente está no balcão esperando.
    qrcode: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        doc="Texto do QR Code do DANFE NFC-e, montado pelo provedor com o CSC"
    )
    url_consulta: Mapped[Optional[str]] = mapped_column(
        String(300), nullable=True,
        doc="Endereço de consulta da SEFAZ impresso no cupom"
    )
    valor_tributos: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        doc="Tributos totais aproximados em CENTAVOS (Lei 12.741/2012 — IBPT)"
    )

    # --- Emissão via API ---
    ref_api: Mapped[Optional[str]] = mapped_column(
        String(50), unique=True, index=True, nullable=True,
        doc="Referência única enviada à API de emissão"
    )
    ambiente_emissao: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        doc="Ambiente em que foi emitido: 1=Produção, 2=Homologação"
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(36), unique=True, index=True, nullable=True,
        doc=(
            "UUID gerado e persistido ANTES do disparo HTTP. Reenviado em "
            "X-Idempotency-Key para que a retentativa de rede após timeout "
            "não vire uma segunda nota na API intermediária."
        )
    )

    # --- Cadeia de tentativas (linked list) ---
    tentativa_anterior_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("documento_fiscal.id"), nullable=True, index=True,
        doc="ID da tentativa anterior (reemissão cria nova linha)"
    )

    tentativa_anterior: Mapped[Optional["DocumentoFiscal"]] = relationship(
        "DocumentoFiscal",
        remote_side="DocumentoFiscal.id",
        foreign_keys=[tentativa_anterior_id],
        uselist=False,
        doc="Documento da tentativa anterior"
    )

    # --- Timestamps ---
    data_emissao: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )
