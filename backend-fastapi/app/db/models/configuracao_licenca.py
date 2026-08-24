# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/configuracao_licenca.py
# DESCRIÇÃO: Modelo SQLAlchemy para a tabela 'configuracoes_licenca'.
#            Armazena dados de licenciamento do sistema obtidos via auto-cadastro.
# ---------------------------------------------------------------------------

from datetime import datetime, timezone
from sqlalchemy import Boolean, Integer, String, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ConfiguracaoLicenca(Base):
    """
    Armazena dados da licença do sistema obtidos via auto-cadastro na API StartBig.
    Tabela standalone (sem FK para empresas) pois é criada durante o setup,
    antes da empresa existir na transação.
    """
    __tablename__ = "configuracoes_licenca"

    # --- Identificação ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # --- Dados do cliente/licença (da API externa) ---
    cliente_id: Mapped[str] = mapped_column(
        String(36), nullable=False,
        doc="UUID do cliente na plataforma StartBig"
    )
    hwid: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True,
        doc="Hardware ID da máquina"
    )
    licenca_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False,
        doc="UUID da licença"
    )

    # --- Campos sensíveis (AES-256-GCM encrypted com HWID como chave) ---
    chave_ativacao: Mapped[str] = mapped_column(
        Text, nullable=False,
        doc="Chave de ativação (AES-256-GCM encrypted)"
    )
    public_key: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        doc="Chave pública RSA PEM (AES-256-GCM encrypted com HWID)"
    )

    # --- Limites e validade ---
    limite: Mapped[int] = mapped_column(
        Integer, nullable=False,
        doc="Limite de terminais/licenças"
    )
    data_vencimento: Mapped[datetime] = mapped_column(
        DateTime, nullable=False,
        doc="Data de vencimento da licença"
    )
    token: Mapped[str] = mapped_column(
        Text, nullable=False,
        doc="JWT token da plataforma de licenças"
    )

    # --- Sincronização e validação ---
    ultima_sinc: Mapped[datetime] = mapped_column(
        DateTime, nullable=False,
        doc="Última sincronização com servidor de licenças"
    )
    grace_period: Mapped[int] = mapped_column(
        Integer, default=7, nullable=False,
        doc="Período de graça em dias"
    )
    proxima_validacao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False,
        doc="Data da próxima validação obrigatória"
    )

    # --- Carencia de pagamento (cartao) ---
    #
    # NAO confundir com `grace_period`, logo acima: aquele e validade OFFLINE
    # (quanto tempo a loja roda sem falar com o servidor). Este e outro assunto
    # -- a janela em que o gateway ainda esta re-tentando um cartao que falhou.
    #
    # Quem paga no cartao pode ficar inadimplente sem saber (limite, cartao
    # trocado, banco recusando), e travar a loja no primeiro dia puniria
    # justamente quem contratou para nao ter que lembrar de pagar. Quem paga no
    # PIX nao entra aqui: nao pagar foi uma escolha.
    #
    # Nulos numa instalacao que ainda nao sincronizou depois da atualizacao --
    # e nesse estado o comportamento tem que ser exatamente o de antes.
    em_carencia: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True,
        doc="True enquanto o gateway ainda re-tenta a cobranca (assinatura no cartao)"
    )
    data_limite_carencia: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True,
        doc="Ate quando a carencia vale. Sem esta data a carencia NAO e honrada."
    )

    # --- Controle de bloqueio remoto ---
    bloqueada: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        doc="Flag de bloqueio remoto via heartbeat"
    )

    # --- Metadados ---
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ConfiguracaoLicenca(id={self.id}, hwid={self.hwid}, licenca_id={self.licenca_id})>"
