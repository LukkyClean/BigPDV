# ---------------------------------------------------------------------------
# ARQUIVO: db/models/ordem_servico.py
# DESCRICAO: Modelo SQLAlchemy para a tabela 'ordens_servico'.
# ---------------------------------------------------------------------------

from datetime import datetime
from sqlalchemy import Integer, String, Boolean, DateTime, Text, Enum as SqlAlchemyEnum, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from app.db.base import Base
from app.core.enum import OrdemServicoStatus, OrdemServicoPrioridade, SituacaoEquipamento

if TYPE_CHECKING:
    from .cliente import Cliente
    from .funcionario import Funcionario
    from .objeto_servico import ObjetoServico
    from .ordem_servico_item import OrdemServicoItem
    from .ordem_servico_pagamento import OrdemServicoPagamento
    from .ordem_servico_foto import OrdemServicoFoto


class OrdemServico(Base):
    """Modelo ORM que representa uma Ordem de Servico na tabela 'ordens_servico'."""

    __tablename__ = "ordens_servico"

    # --- Identificacao ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, doc="ID unico da OS (PK)")
    numero_os: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False, doc="Numero sequencial da OS (ex: OS-2026-000001)")

    # --- Vinculos ---
    funcionario_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("funcionarios.id"), nullable=True, doc="ID do funcionario responsavel (FK)")
    objeto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("objetos_servico.id"),
        nullable=False,
        doc="ID do objeto usado na OS (FK)"
    )

    # --- Status e Prioridade ---
    status: Mapped[OrdemServicoStatus] = mapped_column(
        SqlAlchemyEnum(OrdemServicoStatus),
        default=OrdemServicoStatus.ABERTA,
        nullable=False,
        doc="Status atual da OS"
    )
    prioridade: Mapped[OrdemServicoPrioridade] = mapped_column(
        SqlAlchemyEnum(OrdemServicoPrioridade),
        default=OrdemServicoPrioridade.NORMAL,
        nullable=False,
        doc="Prioridade da OS"
    )

    # --- Descricao do Servico ---
    defeito_relatado: Mapped[str] = mapped_column(Text, nullable=False, doc="Defeito relatado pelo cliente")
    diagnostico: Mapped[Optional[str]] = mapped_column(Text, nullable=True, doc="Diagnostico tecnico")
    solucao: Mapped[Optional[str]] = mapped_column(Text, nullable=True, doc="Solucao aplicada")
    situacao_equipamento: Mapped[Optional[SituacaoEquipamento]] = mapped_column(
        SqlAlchemyEnum(SituacaoEquipamento),
        nullable=True,
        doc="Situação final do equipamento: REPARADO, SEM_REPARO ou CONDENADO"
    )
   
    # --- Observações do Servico ---
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, doc="Observacoes gerais")
    dados_adicionais: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        doc="Dados adicionais específicos do segmento (ex: quilometragem, combustível, etc.)"
    )

    # --- Financeiro (valores em centavos) ---
    valor_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="Valor total da OS (centavos)")
    valor_bruto: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="Valor bruto antes de desconto (centavos)")
    desconto: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="Desconto aplicado (centavos)")
    valor_entrada: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="Valor de entrada/adiantamento (centavos)")
    taxa_entrega: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="Taxa de entrega/frete (centavos)")
    acrescimo: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="Acréscimo de juros/cartão (centavos)")
    credito_anterior: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None, doc="Crédito efetivo da finalização anterior ao reabrir (centavos)")

    # --- Datas ---
    garantia: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, doc="Garantia em dias")
    data_previsao: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, doc="Data prevista para conclusao")
    data_finalizacao: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, doc="Data de finalizacao efetiva")
    data_criacao: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False, doc="Data de criacao da OS")
    data_atualizacao: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, doc="Data da ultima atualizacao")

    # --- Status ---
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, doc="Status ativo (soft delete)")

    # --- Relacionamentos ---
    funcionario: Mapped[Optional["Funcionario"]] = relationship(
        "Funcionario",
        back_populates="ordens_servico",
        doc="Funcionario responsavel"
    )
    objeto: Mapped["ObjetoServico"] = relationship(
        "ObjetoServico",
        back_populates="ordens_servico",
        doc="Objeto utilizado nesta OS"
    )
    itens: Mapped[List["OrdemServicoItem"]] = relationship(
        "OrdemServicoItem",
        back_populates="ordem_servico",
        cascade="all, delete-orphan",
        doc="Itens/servicos da OS"
    )
    pagamentos: Mapped[List["OrdemServicoPagamento"]] = relationship(
        "OrdemServicoPagamento",
        back_populates="ordem_servico",
        cascade="all, delete-orphan",
        doc="Pagamentos da OS"
    )
    fotos: Mapped[List["OrdemServicoFoto"]] = relationship(
        "OrdemServicoFoto",
        back_populates="ordem_servico",
        cascade="all, delete-orphan",
        doc="Fotos da OS"
    )

    @property
    def cliente(self) -> Optional["Cliente"]:
        return self.objeto.cliente if self.objeto else None

    @property
    def equipamento(self) -> Optional["ObjetoServico"]:
        return self.objeto

    def _set_dado_adicional(self, chave: str, valor: Optional[str]) -> None:
        """Grava um campo legado de forma transparente na coluna JSON dados_adicionais."""
        # Cria um novo dict para garantir que o SQLAlchemy detecte a mutação (JSON não é rastreado in-place).
        dados = dict(self.dados_adicionais or {})
        if valor is None:
            dados.pop(chave, None)
        else:
            dados[chave] = valor
        self.dados_adicionais = dados

    @property
    def senha_aparelho(self) -> Optional[str]:
        return (self.dados_adicionais or {}).get("senha_aparelho")

    @senha_aparelho.setter
    def senha_aparelho(self, value: Optional[str]) -> None:
        self._set_dado_adicional("senha_aparelho", value)

    @property
    def acessorios(self) -> Optional[str]:
        # Compat multi-segmento: em TI é string ("carregador, capa..."); na oficina a
        # chave "acessorios" guarda o checklist da vistoria (dict). Só expõe como string
        # quando for string — evita quebrar a leitura da OS quando for o dict da vistoria.
        val = (self.dados_adicionais or {}).get("acessorios")
        return val if isinstance(val, str) else None

    @acessorios.setter
    def acessorios(self, value: Optional[str]) -> None:
        self._set_dado_adicional("acessorios", value)

    @property
    def condicoes_aparelho(self) -> Optional[str]:
        return (self.dados_adicionais or {}).get("condicoes_aparelho")

    @condicoes_aparelho.setter
    def condicoes_aparelho(self, value: Optional[str]) -> None:
        self._set_dado_adicional("condicoes_aparelho", value)
