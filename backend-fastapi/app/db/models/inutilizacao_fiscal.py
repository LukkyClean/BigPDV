# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/inutilizacao_fiscal.py
# DESCRIÇÃO: Registro de inutilização de faixa de numeração de NF-e.
#
# Quando um número é reservado mas a nota nunca é autorizada, ele fica como
# buraco na sequência fiscal. A SEFAZ exige que esses números sejam
# formalmente inutilizados — declarados como não usados — senão a empresa
# fica com a sequência irregular perante o fisco.
#
# Não é DocumentoFiscal: inutilização cobre uma FAIXA (inicial..final) e não
# tem itens, destinatário nem valor.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class InutilizacaoFiscal(Base):
    __tablename__ = "inutilizacao_fiscal"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id", "serie", "ano", "numero_inicial", "numero_final",
            name="uq_inutilizacao_faixa",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    empresa_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # --- Faixa inutilizada ---
    modelo: Mapped[int] = mapped_column(
        Integer, nullable=False, default=55,
        doc="Modelo do documento: 55=NF-e, 65=NFC-e"
    )
    serie: Mapped[int] = mapped_column(Integer, nullable=False)
    ano: Mapped[int] = mapped_column(
        Integer, nullable=False,
        doc="Ano da inutilização (a SEFAZ segrega a numeração por ano)"
    )
    numero_inicial: Mapped[int] = mapped_column(Integer, nullable=False)
    numero_final: Mapped[int] = mapped_column(Integer, nullable=False)

    justificativa: Mapped[str] = mapped_column(
        String(255), nullable=False,
        doc="Motivo declarado à SEFAZ (mínimo 15 caracteres)"
    )

    # --- Status do pedido ---
    # PENDENTE, PROCESSANDO, HOMOLOGADA, REJEITADA, INDETERMINADA
    status: Mapped[str] = mapped_column(
        String(15), nullable=False, default="PENDENTE", index=True
    )
    protocolo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    mensagem_sefaz: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    codigo_status_sefaz: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url_xml: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # --- Comunicação com a API ---
    ref_api: Mapped[Optional[str]] = mapped_column(
        String(50), unique=True, index=True, nullable=True
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(36), unique=True, index=True, nullable=True
    )
    ambiente_emissao: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Timestamps ---
    data_solicitacao: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    data_homologacao: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<InutilizacaoFiscal(serie={self.serie}, "
            f"faixa={self.numero_inicial}-{self.numero_final}, status={self.status})>"
        )
