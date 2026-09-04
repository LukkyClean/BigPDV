# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/venda_nota_fiscal.py
# DESCRIÇÃO: Tabela satélite de nota fiscal por venda (1:1 opcional com Venda).
#
# Armazena dois tipos de dados:
# - Parâmetros de entrada para emissão (natureza_operação, finalidade…)
# - Resultados da emissão Focus NFe (chave_acesso, protocolo, status…)
#
# Todos os campos são nullable — a obrigatoriedade é verificada apenas
# na service layer, no momento de emissão (fase futura).
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from .venda import Venda


class VendaNotaFiscal(Base):
    __tablename__ = "venda_nota_fiscal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    venda_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vendas.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # --- Parâmetros de entrada para emissão ---
    # Descrição da natureza da operação (ex: "Venda de Mercadoria")
    natureza_operacao: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    # 1=Normal, 2=Complementar, 3=Ajuste, 4=Devolução/Retorno
    finalidade_emissao: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Indica se é venda para consumidor final
    consumidor_final: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    # 1=Presencial, 2=Internet, 3=Teleatendimento, 4=Entrega domiciliar, 9=Outros
    indicador_presenca: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # --- Resultados da emissão (preenchidos pelo Focus NFe — fase futura) ---
    # PENDENTE, EMITIDA, CANCELADA, DENEGADA, ERRO
    status_nota: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="PENDENTE")
    chave_acesso: Mapped[Optional[str]] = mapped_column(String(44), nullable=True)
    numero_nota: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    serie: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    protocolo_autorizacao: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    data_autorizacao: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    url_danfe: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    mensagem_sefaz: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    qrcode: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    data_atualizacao: Mapped[datetime] = mapped_column(
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    venda: Mapped["Venda"] = relationship("Venda", back_populates="nota_fiscal")
