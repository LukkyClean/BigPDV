# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/empresa_fiscal_settings.py
# DESCRIÇÃO: Modelo SQLAlchemy para a tabela 'empresa_fiscal_settings'.
#            Armazena configurações fiscais da empresa (NFe, NFCe, NFSe, certificados).
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.empresa import Empresa


class EmpresaFiscalSettings(Base):
    """
    Configurações fiscais da empresa para emissão de documentos eletrônicos.
    Relacionamento 1:1 com Empresa.

    A senha do certificado A1 (`certificado_senha`) É persistida, criptografada
    com Fernet — a emissão precisa dela a cada chamada. A docstring anterior
    afirmava o contrário e contradizia o próprio modelo.
    """
    __tablename__ = "empresa_fiscal_settings"

    # --- Identificação ---
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        doc="ID único das configurações fiscais"
    )
    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        doc="ID da empresa (FK única - relacionamento 1:1)"
    )

    # --- Ambiente de Emissão ---
    ambiente_emissao: Mapped[int] = mapped_column(
        Integer,
        default=2,
        nullable=False,
        doc="Ambiente: 1=Produção, 2=Homologação (Testes)"
    )

    # --- NFe (Modelo 55) ---
    serie_nfe: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Série da NFe"
    )
    ultimo_numero_nfe: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Último número de NFe emitida"
    )

    # --- NFCe (Modelo 65) ---
    serie_nfce: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Série da NFCe"
    )
    ultimo_numero_nfce: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Último número de NFCe emitida"
    )

    # --- CSC (Código de Segurança do Contribuinte - NFCe) ---
    csc_token: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Token CSC para NFCe (código alfanumérico)"
    )
    csc_id: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        doc="ID do Token CSC (ex: 000001)"
    )

    # --- NFSe (Serviços / RPS) ---
    rps_serie: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        doc="Série do RPS para NFSe"
    )
    rps_ultimo_numero: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Último número de RPS emitido"
    )

    # --- Integração Municipal (Prefeitura) ---
    prefeitura_login: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Login de acesso ao portal da prefeitura"
    )
    prefeitura_senha: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Senha do portal da prefeitura (criptografada)"
    )
    prefeitura_token_api: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        doc="Token/Chave de API da prefeitura (webservice)"
    )
    regime_tributacao_iss: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Regime de tributação ISS: 1-Microempresa Municipal, 2-Estimativa, 3-Sociedade de Profissionais, 4-Cooperativa, 5-MEI, 6-ME/EPP Simples Nacional"
    )

    # --- Certificado Digital ---
    tipo_certificado: Mapped[str] = mapped_column(
        String(10),
        default="ARQUIVO",
        nullable=False,
        doc="Tipo: ARQUIVO (A1), WINDOWS (Store do SO), NENHUM"
    )
    certificado_digital_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Caminho do arquivo .pfx/.p12 (certificado A1)"
    )
    certificado_validade: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Data de validade do certificado digital"
    )
    certificado_subject: Mapped[Optional[str]] = mapped_column(
        String(300),
        nullable=True,
        doc="Subject/CN do certificado (nome da empresa no certificado)"
    )
    certificado_thumbprint: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Thumbprint do certificado Windows (identificador único)"
    )
    certificado_senha: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        doc="Senha do certificado digital A1 (Criptografada com Fernet)"
    )
    certificado_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Status da conexão do certificado. Ex: CONECTADO_NUVEM, ERRO, etc."
    )
    certificado_cnpj: Mapped[Optional[str]] = mapped_column(
        String(14),
        nullable=True,
        doc="CNPJ extraído do certificado (somente números)"
    )

    # --- Metadados ---
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        doc="Data de criação do registro"
    )
    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Data da última atualização"
    )

    # --- Relacionamento ---
    empresa: Mapped["Empresa"] = relationship(
        "Empresa",
        back_populates="fiscal_settings",
        doc="Empresa proprietária destas configurações"
    )

    def __repr__(self) -> str:
        return f"<EmpresaFiscalSettings(id={self.id}, empresa_id={self.empresa_id}, ambiente={self.ambiente_emissao})>"
