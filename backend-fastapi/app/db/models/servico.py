# ---------------------------------------------------------------------------
# ARQUIVO: db/models/servico.py
# DESCRIÇÃO: Define o modelo da tabela 'servicos' (SQLAlchemy ORM).
# ---------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .servico_fiscal import ServicoFiscal


class Servico(Base):
    """
    Modelo ORM que representa um Serviço na tabela 'servicos'.
    """

    # Nome exato da tabela no banco de dados
    __tablename__ = "servicos"

    # =========================
    # COLUNAS DA TABELA
    # =========================

    # Chave primária (PK) - [Estilo de linha única]
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, doc="ID único do serviço (Chave primária)")

    # Descrição do serviço - [Estilo de linha única]
    descricao: Mapped[String] = mapped_column(String(255), index=True, nullable=False, doc="Descrição do servico (Discriminador de pesquisa)")
    
    # Valor do serviço (em centavos) - [Estilo de linha única]
    valor: Mapped[int] = mapped_column(Integer, nullable=False, doc="Valor do serviço cobrado")

    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, doc="Status do serviço (Soft Delete)")

    # Relação 1:1 opcional com os dados fiscais (NBS/LC116, ISS).
    # Ausência é o normal: só empresas com o módulo fiscal ativo preenchem.
    fiscal: Mapped[Optional["ServicoFiscal"]] = relationship(
        "ServicoFiscal",
        back_populates="servico",
        cascade="all, delete-orphan",
        uselist=False,
    )