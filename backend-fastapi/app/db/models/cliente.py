# ---------------------------------------------------------------------------
# ARQUIVO: cliente.py
# DESCRICAO: Modelos SQLAlchemy para as tabelas 'clientes', 'clientes_pf'
#            e 'clientes_pj' com heranca polimorfica (joined-table).
# ---------------------------------------------------------------------------

from datetime import date, datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Boolean, Date, ForeignKey, Enum as SqlAlchemyEnum, and_, func
from sqlalchemy.orm import relationship, Mapped, mapped_column, foreign

from app.db.base import Base
from app.core.enum import Gender, ClientType
from app.db.models.endereco import Endereco

if TYPE_CHECKING:
    from .objeto_servico import ObjetoServico
    from .venda import Venda


class Cliente(Base):
    """
    Representa a tabela base 'clientes', contendo dados comuns
    a todos os tipos de clientes (PF, PJ, etc.).
    """

    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, doc="ID unico do cliente (PK)")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, doc="Define se o cliente esta ativo")

    tipo: Mapped[ClientType] = mapped_column(SqlAlchemyEnum(ClientType), nullable=False, doc="Tipo de cliente (PF ou PJ)")

    email: Mapped[Optional[str]] = mapped_column(String(255, collation="NOCASE"), nullable=True, doc="Email do cliente")
    telefone: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, doc="Telefone de contato do cliente")
    celular: Mapped[Optional[str]] = mapped_column(String(11), nullable=True, doc="Celular para contato")
    observacoes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, doc="Observacoes gerais sobre o cliente")
    saldo_credito: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="Saldo de credito disponivel do cliente em centavos")

    data_criacao: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False, doc="Data de criacao do cliente")

    endereco: Mapped[List[Endereco]] = relationship(
        "Endereco",
        primaryjoin="and_(foreign(Endereco.id_entidade) == Cliente.id, foreign(Endereco.tipo_entidade) == 'CLIENTE')",
        cascade="all, delete-orphan",
        overlaps="endereco",
        doc="Lista de enderecos associados a este cliente"
    )

    objetos: Mapped[List["ObjetoServico"]] = relationship(
        "ObjetoServico",
        back_populates="cliente",
        doc="Objetos de serviço cadastrados para este cliente"
    )

    vendas: Mapped[List["Venda"]] = relationship(
        "Venda",
        back_populates="cliente",
        doc="Vendas associadas a este cliente"
    )

    __mapper_args__ = {
        "polymorphic_on": tipo,
        "polymorphic_identity": "cliente",
    }


class ClientePF(Cliente):
    """
    Representa a tabela 'clientes_pf', com dados especificos de PF.
    """

    __tablename__ = "clientes_pf"

    id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), primary_key=True, index=True, doc="ID do cliente (FK de clientes)")

    nome: Mapped[str] = mapped_column(String(255, collation="NOCASE"), index=True, nullable=False, doc="Nome completo do cliente")
    cpf: Mapped[Optional[str]] = mapped_column(String(11), unique=True, index=True, nullable=True, doc="CPF do cliente (11 digitos)")
    rg: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True, doc="RG do cliente")
    genero: Mapped[Optional[Gender]] = mapped_column(SqlAlchemyEnum(Gender), nullable=True, doc="Genero do cliente")
    data_nascimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True, doc="Data de nascimento do cliente")

    __mapper_args__ = {
        "polymorphic_identity": ClientType.PF.value,
    }


class ClientePJ(Cliente):
    """
    Representa a tabela 'clientes_pj', com dados especificos de PJ.
    """

    __tablename__ = "clientes_pj"

    id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), primary_key=True, index=True, doc="ID do cliente (FK de clientes)")

    razao_social: Mapped[str] = mapped_column(String(255, collation="NOCASE"), index=True, nullable=False, doc="Razao social da empresa")
    cnpj: Mapped[Optional[str]] = mapped_column(String(14), unique=True, index=True, nullable=True, doc="CNPJ da empresa (14 digitos)")
    nome_fantasia: Mapped[Optional[str]] = mapped_column(String(255, collation="NOCASE"), index=True, nullable=True, doc="Nome fantasia da empresa")
    ie: Mapped[Optional[str]] = mapped_column(String(14), unique=True, nullable=True, doc="Inscricao Estadual (IE) da empresa")
    im: Mapped[Optional[str]] = mapped_column(String(14), unique=True, nullable=True, doc="Inscricao Municipal (IM) da empresa")
    regime_tributario: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, doc="Regime tributario do juridico")
    responsavel: Mapped[Optional[str]] = mapped_column(String(255, collation="NOCASE"), nullable=True, doc="Nome do responsavel ou contato principal")

    __mapper_args__ = {
        "polymorphic_identity": ClientType.PJ.value,
    }
