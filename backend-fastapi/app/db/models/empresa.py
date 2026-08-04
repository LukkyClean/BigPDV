# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/empresa.py
# DESCRIÇÃO: Modelo SQLAlchemy para a tabela 'empresas'.
#            Representa a entidade principal do sistema (Tenant).
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, and_, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign
from app.db.base import Base

# Importa modelos relacionados para type hints e relacionamentos
from app.db.models.usuario import Usuario
from app.db.models.funcionario import Funcionario
from app.db.models.endereco import Endereco

if TYPE_CHECKING:
    from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
    from app.db.models.configuracao_clientes import ConfiguracaoClientes
    from app.db.models.configuracao_produtos import ConfiguracaoProdutos
    from app.db.models.configuracao_os import ConfiguracaoOS
    from app.db.models.configuracao_vendas import ConfiguracaoVendas
    from app.db.models.configuracao_seguranca import ConfiguracaoSeguranca

class Empresa(Base):
    """
    Representa a entidade principal do sistema (Multi-tenancy).
    Todos os dados (usuários, funcionários, etc.) pertencem a uma instância de Empresa.
    """
    __tablename__ = "empresas"

    # --- Identificação Principal ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, doc="ID único da empresa (Chave primária)")
    razao_social: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, doc="Razão social registrada")
    nome_fantasia: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, doc="Nome comercial da empresa")
    is_cnpj: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, doc="Indica se o documento é CPF ou CNPJ")
    documento: Mapped[Optional[str]] = mapped_column(String(14), unique=True, nullable=True, index=True, doc="CPF ou CNPJ (apenas números)")
    
    # --- Dados Fiscais ---
    inscricao_estadual: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, doc="Inscrição Estadual (IE)")
    inscricao_municipal: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, doc="Inscrição Municipal (IM)")
    regime_tributario: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, doc="Regime fiscal (Simples Nacional, Lucro Presumido, etc.)")
    cnae_principal: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, doc="CNAE (Classificação Nacional de Atividades Econômicas) principal")
    segmento: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, doc="Segmento de negócio da empresa (ex: assistencia_tecnica, oficina_mecanica)")
    indicador_ie: Mapped[Optional[str]] = mapped_column(String(1), nullable=True, doc="Indicador de IE para NF-e: 1=Contribuinte ICMS, 2=Isento, 9=Não contribuinte")
    natureza_juridica: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, doc="Natureza jurídica (MEI, ME, EPP, LTDA, SA, EI, SLU)")
    tipo_atividade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, doc="Tipo de atividade: COMERCIO, INDUSTRIA, SERVICO, MISTO")
    cnaes_secundarios: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, doc="CNAEs secundários separados por vírgula")
    data_abertura: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, doc="Data de abertura no formato YYYY-MM-DD")
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, doc="Site da empresa")

    # --- Contato e Visual ---
    telefone: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, doc="Telefone principal de contato")
    celular: Mapped[Optional[str]] = mapped_column(String(11), nullable=True, doc="Celular de contato")
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, doc="Email de contato principal")
    url_logo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, doc="Caminho/URL da imagem da logo para uso no PDV/Relatórios")
    chave_pix: Mapped[Optional[str]] = mapped_column(
        String(77),
        nullable=True,
        doc=(
            "Chave PIX do recebedor. 77 e o teto do BR Code para e-mail, a mais longa "
            "das cinco formas (CPF, CNPJ, telefone, e-mail, aleatoria). Guardada como "
            "texto porque o QR embute a chave literalmente -- o formato nao muda a "
            "montagem do payload."
        ),
    )
    pix_ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc=(
            "Se o QR PIX aparece na finalizacao. Separado da chave de proposito: "
            "permite desligar temporariamente sem apagar a chave cadastrada."
        ),
    )
    cor_tema: Mapped[Optional[str]] = mapped_column(
        String(7),
        nullable=True,
        doc=(
            "Cor da marca escolhida pelo dono, em hex (#RRGGBB). Fica ao lado do logo "
            "porque e da mesma natureza: identidade visual, nao regra de negocio. "
            "NULL = paleta de fabrica. A paleta completa e derivada dela no frontend "
            "(shared/theme/paleta.ts); aqui guarda-se so a semente."
        ),
    )
    
    # --- Status ---
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, doc="Status de ativo/inativo no sistema")
    
    # --- Metadados ----
    data_criacao: Mapped[datetime] = mapped_column(DateTime, default=func.now(), doc="Data de criação da empresa no banco de dados")

    # =========================
    # RELACIONAMENTOS (Um-para-Muitos)
    # =========================

    # 1 Empresa tem VÁRIOS Usuários (Multi-tenancy)
    usuarios: Mapped[list[Usuario]] = relationship(
        "Usuario", 
        back_populates="empresa",
        cascade="all, delete-orphan", # Deleta usuários se a empresa for deletada
        doc="Lista de usuários (contas de acesso) vinculados à empresa"
    )
    
    # 1 Empresa tem VÁRIOS Funcionários
    funcionarios: Mapped[list[Funcionario]] = relationship(
        "Funcionario", 
        back_populates="empresa",
        cascade="all, delete-orphan", # Deleta funcionários se a empresa for deletada
        doc="Lista de registros de funcionários (dados pessoais/documentos) da empresa"
    )

    # Relacionamento Polimórfico com Endereço
    enderecos: Mapped[list[Endereco]] = relationship(
        "Endereco",
        # Define a condição de junção: Endereco.id_entidade == Empresa.id E Endereco.tipo_entidade == 'EMPRESA'
        primaryjoin=lambda: and_(foreign(Endereco.id_entidade) == Empresa.id, foreign(Endereco.tipo_entidade) == 'EMPRESA'),
        cascade="all, delete-orphan",
        overlaps="endereco",
        doc="Lista de endereços da empresa (pode ser sede, filiais, etc.)"
    )

    # Relacionamento 1:1 com Configurações Fiscais
    fiscal_settings: Mapped[Optional["EmpresaFiscalSettings"]] = relationship(
        "EmpresaFiscalSettings",
        back_populates="empresa",
        uselist=False,  # 1:1 - Uma empresa tem apenas uma configuração fiscal
        cascade="all, delete-orphan",
        doc="Configurações fiscais da empresa (NFe, NFCe, NFSe, certificados)"
    )

    # Relacionamento 1:1 com Configurações de Clientes
    config_clientes: Mapped[Optional["ConfiguracaoClientes"]] = relationship(
        "ConfiguracaoClientes",
        back_populates="empresa",
        uselist=False,
        cascade="all, delete-orphan",
        doc="Configurações do módulo de clientes"
    )

    # Relacionamento 1:1 com Configurações de Produtos
    config_produtos: Mapped[Optional["ConfiguracaoProdutos"]] = relationship(
        "ConfiguracaoProdutos",
        back_populates="empresa",
        uselist=False,
        cascade="all, delete-orphan",
        doc="Configurações do módulo de produtos e estoque"
    )

    # Relacionamento 1:1 com Configurações de OS
    config_os: Mapped[Optional["ConfiguracaoOS"]] = relationship(
        "ConfiguracaoOS",
        back_populates="empresa",
        uselist=False,
        cascade="all, delete-orphan",
        doc="Configurações do módulo de ordens de serviço"
    )

    # Relacionamento 1:1 com Configurações de Vendas
    config_vendas: Mapped[Optional["ConfiguracaoVendas"]] = relationship(
        "ConfiguracaoVendas",
        back_populates="empresa",
        uselist=False,
        cascade="all, delete-orphan",
        doc="Configurações de regras de vendas"
    )

    # Relacionamento 1:1 com Configurações de Segurança
    config_seguranca: Mapped[Optional["ConfiguracaoSeguranca"]] = relationship(
        "ConfiguracaoSeguranca",
        back_populates="empresa",
        uselist=False,
        cascade="all, delete-orphan",
        doc="Configurações de segurança e aprovações por PIN"
    )