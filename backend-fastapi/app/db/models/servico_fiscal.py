# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/servico_fiscal.py
# DESCRIÇÃO: Tabela satélite de dados fiscais de serviço (1:1 opcional com Servico).
#
# Todos os campos fiscais são nullable — a obrigatoriedade é verificada apenas
# no momento de emissão (service layer). Ausência do registro = módulo inativo
# para aquele serviço, não é erro.
#
# Campos voltados a NFSe (Nota Fiscal de Serviços Eletrônica) via Focus NFe.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from .servico import Servico


class ServicoFiscal(Base):
    __tablename__ = "servico_fiscal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    servico_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("servicos.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # --- Campos NFSe ---
    # Item da Lista de Serviços da LC 116/2003 (ex: "1401" ou "14.01")
    codigo_servico_lc116: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    # Código CNAE (7 dígitos numéricos, ex: "9512600")
    cnae: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    # Alíquota ISS em centésimos de ponto percentual (500 = 5,00%)
    aliquota_iss: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Código de tributação no município (opcional, varia por prefeitura)
    codigo_tributacao_municipio: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # --- Campos compartilhados com NF-e (quando serviço consta em nota mista) ---
    cfop_padrao: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    cst_icms: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    csosn: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    unidade_tributavel: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)

    # --- Reforma Tributária (IBS/CBS) ---
    c_class_trib: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        doc="Código de Classificação Tributária IBS/CBS"
    )
    cst_ibs_cbs: Mapped[Optional[str]] = mapped_column(
        String(3), nullable=True,
        doc="CST IBS/CBS — situação tributária do item na reforma"
    )
    aliquota_ibs: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        doc="Alíquota IBS em centésimos de ponto percentual (500 = 5,00%)"
    )
    aliquota_cbs: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        doc="Alíquota CBS em centésimos de ponto percentual (500 = 5,00%)"
    )
    c_benef: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True,
        doc="Código de Benefício Fiscal IBS/CBS"
    )

    data_atualizacao: Mapped[datetime] = mapped_column(
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    servico: Mapped["Servico"] = relationship("Servico", back_populates="fiscal")
