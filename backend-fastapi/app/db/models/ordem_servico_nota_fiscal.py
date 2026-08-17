# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/ordem_servico_nota_fiscal.py
# DESCRIÇÃO: Tabela satélite de nota fiscal por OS (1:1 opcional com OrdemServico).
#
# A OS pode gerar dois documentos distintos:
# - NFe/NFCe para itens de produto (peças)
# - NFSe para itens de serviço (mão de obra)
#
# Por isso existem dois blocos de resultado independentes. Os campos de
# entrada (natureza_operacao, finalidade_emissao…) são compartilhados.
#
# Todos os campos fiscais são nullable — a obrigatoriedade é verificada
# apenas na service layer, no momento de emissão (fase futura).
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from .ordem_servico import OrdemServico


class OrdemServicoNotaFiscal(Base):
    __tablename__ = "ordem_servico_nota_fiscal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    os_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ordens_servico.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # --- Parâmetros de entrada para emissão (compartilhados entre NFe e NFSe) ---
    natureza_operacao: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    # 1=Normal, 2=Complementar, 3=Ajuste, 4=Devolução/Retorno
    finalidade_emissao: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Indica se é para consumidor final
    consumidor_final: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    # 1=Presencial, 2=Internet, 3=Teleatendimento, 4=Entrega domiciliar, 9=Outros
    indicador_presenca: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Controle de quais documentos emitir
    emitir_nfe: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=True)
    emitir_nfse: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=True)

    # --- Resultado NFe/NFCe (peças — preenchidos pelo Focus NFe, fase futura) ---
    # PENDENTE, EMITIDA, CANCELADA, DENEGADA, ERRO
    status_nfe: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="PENDENTE")
    chave_acesso_nfe: Mapped[Optional[str]] = mapped_column(String(44), nullable=True)
    numero_nfe: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    serie_nfe: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    protocolo_nfe: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    data_autorizacao_nfe: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    url_danfe: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    mensagem_nfe: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    qrcode_nfe: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Resultado NFSe (mão de obra — preenchidos pelo Focus NFe, fase futura) ---
    # PENDENTE, EMITIDA, CANCELADA, ERRO
    status_nfse: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="PENDENTE")
    numero_nfse: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    codigo_verificacao_nfse: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    data_emissao_nfse: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    url_nfse: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    mensagem_nfse: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    data_atualizacao: Mapped[datetime] = mapped_column(
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    ordem_servico: Mapped["OrdemServico"] = relationship(
        "OrdemServico",
        back_populates="nota_fiscal",
    )
