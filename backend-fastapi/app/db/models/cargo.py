# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/cargo.py
# DESCRIÇÃO: Modelo SQLAlchemy para a tabela 'cargos'.
#            Define os diferentes cargos ou funções, e armazena as permissões.
# ---------------------------------------------------------------------------

from sqlalchemy import Integer, String, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from typing import TYPE_CHECKING, Dict, Optional

# Previne circular import para type checking
if TYPE_CHECKING:
    from .funcionario import Funcionario

class Cargo(Base):
    """
    Exemplos: 'Gerente', 'Caixa', 'Estoquista'.
    Define o nível hierárquico e as permissões de acesso e operação para os Funcionários.
    """
    __tablename__ = "cargos"

    # --- Identificação ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, doc="ID único do cargo (Chave primária)")
    
    # --- Vínculo ---
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, doc="ID da empresa à qual o cargo pertence")
    
    # --- Dados ---
    nome: Mapped[str] = mapped_column(String(50), nullable=False, doc="Nome do cargo (Ex: 'Caixa', 'Gerente de Vendas')") 
    
    # Campo JSON para armazenar permissões dinâmicas
    permissoes: Mapped[Dict[str, bool]] = mapped_column(JSON, nullable=False, default={}, doc="Objeto JSON contendo as permissões de acesso e operação")

    # --- Comissão (padrão do cargo; o Funcionário pode sobrescrever) ---
    # Percentuais em BASIS POINTS (int): 500 = 5,00%. Meta mensal em centavos.
    # Nullable: cargo sem comissão configurada = herda o padrão da empresa/sem comissão.
    comissao_venda_percentual: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Comissão padrão sobre vendas (basis points: 500 = 5,00%)"
    )
    comissao_servico_percentual: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Comissão padrão sobre serviços/OS (basis points: 500 = 5,00%)"
    )
    meta_mensal: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Meta mensal de faturamento do cargo (centavos)"
    )
    # Modo de comissão: 'direto' paga a taxa sobre tudo (padrão); 'meta' só paga
    # ao bater a meta_mensal (gatilho). Nullable -> herda; sem nada = 'direto'.
    comissao_modo: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, doc="Modo de comissão: 'direto' | 'meta' (gatilho por meta)"
    )

    # =========================
    # RELACIONAMENTOS
    # =========================

    # Relacionamento 1:M com Funcionario
    funcionarios: Mapped[list["Funcionario"]] = relationship(
        back_populates="cargo",
        doc="Lista de funcionários que possuem este cargo"
    )