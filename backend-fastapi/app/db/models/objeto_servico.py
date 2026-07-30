# ---------------------------------------------------------------------------
# ARQUIVO: db/models/objeto_servico.py
# DESCRICAO: Modelo SQLAlchemy para a tabela 'objetos_servico'.
# ---------------------------------------------------------------------------

from datetime import datetime, date
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .cliente import Cliente
    from .ordem_servico import OrdemServico


class ObjetoServico(Base):
    """Objeto/Ativo cadastrado para um cliente e reutilizavel em OS."""

    __tablename__ = "objetos_servico"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, doc="ID unico do objeto (PK)")

    cliente_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clientes.id"),
        nullable=False,
        index=True,
        doc="ID do cliente proprietario do objeto (FK)"
    )

    # --- Campos Universais ---
    marca: Mapped[str] = mapped_column(String(100), nullable=False, doc="Marca do objeto (ex: Fiat, Samsung)")
    modelo: Mapped[str] = mapped_column(String(100), nullable=False, doc="Modelo do objeto (ex: Uno, Galaxy S20)")
    cor: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, doc="Cor do objeto")
    numero_serie: Mapped[str] = mapped_column(
        String(100), 
        nullable=False, 
        index=True, 
        doc="Identificador principal (ex: Placa do carro, IMEI do celular, Serial do motor)"
    )

    # --- Esquema Dinâmico ---
    dados_adicionais: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, 
        nullable=True, 
        default=dict,
        doc="Metadados específicos do segmento (ex: ano, chassi, etc.)"
    )
    
    # --- Lembrete de revisão (pós-venda / oficina) ---
    # Nulos para segmentos que não usam (ex: informática). A próxima revisão pode
    # ser agendada por data e/ou por quilometragem — o que vier primeiro.
    proxima_revisao_data: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, doc="Data agendada da próxima revisão (opcional)"
    )
    proxima_revisao_km: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="KM alvo para a próxima revisão (opcional)"
    )

    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, doc="Status ativo (soft delete)")
    data_criacao: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False, doc="Data de criacao")
    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Data da ultima atualizacao"
    )

    cliente: Mapped["Cliente"] = relationship("Cliente", back_populates="objetos", doc="Cliente dono do objeto")
    ordens_servico: Mapped[List["OrdemServico"]] = relationship(
        "OrdemServico",
        back_populates="objeto",
        doc="Ordens de servico associadas a este objeto"
    )

    def _set_dado_adicional(self, chave: str, valor: Optional[str]) -> None:
        """Grava um campo legado de forma transparente na coluna JSON dados_adicionais."""
        # Cria um novo dict para garantir que o SQLAlchemy detecte a mutacao (JSON nao e rastreado in-place).
        dados = dict(self.dados_adicionais or {})
        # Vazio ("") significa "sem valor": remove a chave em vez de gravar string vazia,
        # senao um form que devolve "" apaga o dado real do cliente.
        if not valor:
            dados.pop(chave, None)
        else:
            dados[chave] = valor
        self.dados_adicionais = dados

    @property
    def imei(self) -> Optional[str]:
        # `imei` nao e coluna: vive em dados_adicionais desde a refatoracao
        # Equipamento->ObjetoServico. Sem esta property o Pydantic nao acha o
        # atributo no ORM e devolve null calado — o valor fica gravado mas
        # invisivel, e o proximo save do form o sobrescreve.
        return (self.dados_adicionais or {}).get("imei")

    @imei.setter
    def imei(self, value: Optional[str]) -> None:
        self._set_dado_adicional("imei", value)

    @property
    def tipo_equipamento(self):
        class TipoEquipamentoShim:
            def __init__(self, val):
                self.value = val
            def __eq__(self, other):
                if hasattr(other, 'value'):
                    return self.value == other.value
                return self.value == other
            def __hash__(self):
                return hash(self.value)
            def __str__(self):
                return str(self.value)

        # Retorna tipo configurado ou deduz baseado nos metadados
        val = (self.dados_adicionais or {}).get("tipo_equipamento")
        if val:
            return TipoEquipamentoShim(str(val))
        
        if (self.dados_adicionais or {}).get("placa") or (self.dados_adicionais or {}).get("chassi"):
            return TipoEquipamentoShim("Veículo")
            
        return TipoEquipamentoShim("Equipamento")
