# ---------------------------------------------------------------------------
# ARQUIVO: schemas/empresa.py
# DESCRICAO: Schemas Pydantic para validacao de dados de Empresa.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import List, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.endereco import Endereco, EnderecoRead, EnderecoUpdate

# =========================
# Fiscal Settings Schemas
# =========================

class FiscalSettingsBase(BaseModel):
    """
    Campos comuns para configurações fiscais.
    Usados para leitura e atualização.
    """
    ambiente_emissao: int = Field(
        default=2,
        ge=1,
        le=2,
        description="Ambiente: 1=Produção, 2=Homologação"
    )
    serie_nfe: int = Field(default=1, ge=0, description="Série da NFe")
    ultimo_numero_nfe: int = Field(default=0, ge=0, description="Último número NFe")
    serie_nfce: int = Field(default=1, ge=0, description="Série da NFCe")
    ultimo_numero_nfce: int = Field(default=0, ge=0, description="Último número NFCe")
    csc_token: Optional[str] = Field(None, max_length=100, description="Token CSC para NFCe")
    csc_id: Optional[str] = Field(None, max_length=10, description="ID do Token CSC")
    rps_serie: Optional[str] = Field(None, max_length=10, description="Série do RPS")
    rps_ultimo_numero: int = Field(default=0, ge=0, description="Último número RPS")
    prefeitura_login: Optional[str] = Field(None, max_length=50, description="Login prefeitura")
    prefeitura_senha: Optional[str] = Field(None, max_length=100, description="Senha prefeitura")
    prefeitura_token_api: Optional[str] = Field(None, max_length=200, description="Token API prefeitura")
    regime_tributacao_iss: Optional[int] = Field(None, ge=1, le=6, description="Regime ISS (1-6)")
    tipo_certificado: str = Field(default="ARQUIVO", description="Tipo: ARQUIVO, WINDOWS, NENHUM")

    model_config = ConfigDict(from_attributes=True)


class FiscalSettingsUpdate(BaseModel):
    """
    Schema para atualização parcial de configurações fiscais.
    Todos os campos são opcionais.
    """
    ambiente_emissao: Optional[int] = Field(None, ge=1, le=2)
    serie_nfe: Optional[int] = Field(None, ge=0)
    ultimo_numero_nfe: Optional[int] = Field(None, ge=0)
    serie_nfce: Optional[int] = Field(None, ge=0)
    ultimo_numero_nfce: Optional[int] = Field(None, ge=0)
    csc_token: Optional[str] = Field(None, max_length=100)
    csc_id: Optional[str] = Field(None, max_length=10)
    rps_serie: Optional[str] = Field(None, max_length=10)
    rps_ultimo_numero: Optional[int] = Field(None, ge=0)
    prefeitura_login: Optional[str] = Field(None, max_length=50)
    prefeitura_senha: Optional[str] = Field(None, max_length=100)
    prefeitura_token_api: Optional[str] = Field(None, max_length=200)
    regime_tributacao_iss: Optional[int] = Field(None, ge=1, le=6)
    tipo_certificado: Optional[str] = Field(None)

    model_config = ConfigDict(from_attributes=True)


class FiscalSettingsRead(FiscalSettingsBase):
    """
    Schema de leitura completo das configurações fiscais.
    Inclui metadados read-only do certificado.
    """
    id: int = Field(..., description="ID único das configurações")
    empresa_id: int = Field(..., description="ID da empresa")
    certificado_digital_path: Optional[str] = Field(None, description="Caminho do certificado A1")
    certificado_validade: Optional[datetime] = Field(None, description="Validade do certificado")
    certificado_subject: Optional[str] = Field(None, description="Subject/CN do certificado")
    certificado_thumbprint: Optional[str] = Field(None, description="Thumbprint (Windows)")

    model_config = ConfigDict(from_attributes=True)


class WindowsCertificateRead(BaseModel):
    """
    DTO para listagem de certificados do Windows Certificate Store.
    Read-only - não persiste no banco.
    """
    thumbprint: str = Field(..., description="Identificador único do certificado")
    subject: str = Field(..., description="Subject/CN do certificado")
    friendly_name: str = Field(..., description="Nome amigável")
    issuer: str = Field(..., description="Autoridade certificadora emissora")
    valid_until: Optional[str] = Field(None, description="Data de validade (ISO format)")
    serial_number: str = Field(..., description="Número de série")

    model_config = ConfigDict(from_attributes=True)


class CertificadoWindowsVincular(BaseModel):
    """
    Schema para vincular certificado Windows por thumbprint.
    """
    thumbprint: str = Field(..., min_length=40, max_length=64, description="Thumbprint do certificado")

# NOTA ARQUITETURA:
# Para evitar referencias circulares em schemas aninhados, usamos o nome
# da classe como string literal ("NomeDaClasse").
# E necessario importar os schemas abaixo para que o Pydantic os encontre
# e use no tempo de execucao.

# =========================
# Schema Base
# =========================
class EmpresaBase(BaseModel):
    """
    Campos comuns para criar, ler ou atualizar uma empresa.

    Attributes:
        razao_social (str): Razao Social da empresa (obrigatorio).
        nome_fantasia (Optional[str]): Nome Fantasia (comercial).
        is_cnpj (bool): Indica se o documento e CPF ou CNPJ.
        documento (str): Documento CPF/CNPJ (apenas numeros, 11 a 14 digitos).
        inscricao_estadual (Optional[str]): Inscricao Estadual.
        inscricao_municipal (Optional[str]): Inscricao Municipal.
        regime_tributario (Optional[str]): Regime Tributario (ex: Simples Nacional).
        cnae_principal (Optional[str]): CNAE Principal.
        telefone (Optional[str]): Telefone fixo.
        celular (Optional[str]): Celular / WhatsApp.
        email (Optional[str]): Email principal para contato.
        url_logo (Optional[str]): URL ou caminho relativo da logo da empresa.
    """

    # Identificacao
    razao_social: Optional[str] = Field(
        None,
        max_length=255,
        description="Razao Social da empresa",
    )
    nome_fantasia: Optional[str] = Field(
        None,
        max_length=255,
        description="Nome Fantasia (comercial)",
    )
    is_cnpj: bool = Field(
        ...,
        description="Define se o documento e um CPF ou CNPJ",
    )
    documento: Optional[str] = Field(
        None,
        pattern=r"^\d{11,14}$",
        description="Documento CPF/CNPJ (apenas numeros, 11 a 14 digitos)",
    )
    inscricao_estadual: Optional[str] = Field(
        None,
        max_length=50,
        description="Inscricao Estadual",
    )
    inscricao_municipal: Optional[str] = Field(
        None,
        max_length=50,
        description="Inscricao Municipal",
    )
    regime_tributario: Optional[str] = Field(
        None,
        max_length=50,
        description="Regime Tributario (ex: Simples Nacional)",
    )
    cnae_principal: Optional[str] = Field(
        None,
        max_length=50,
        description="CNAE Principal",
    )
    segmento: Optional[str] = Field(
        None,
        max_length=50,
        description="Segmento de negócio da empresa",
    )
    indicador_ie: Optional[str] = Field(
        None,
        max_length=1,
        description="Indicador de IE: 1=Contribuinte ICMS, 2=Isento, 9=Não contribuinte",
    )
    natureza_juridica: Optional[str] = Field(
        None,
        max_length=50,
        description="Natureza jurídica (MEI, ME, EPP, LTDA, SA, EI, SLU)",
    )
    tipo_atividade: Optional[str] = Field(
        None,
        max_length=20,
        description="Tipo de atividade: COMERCIO, INDUSTRIA, SERVICO, MISTO",
    )
    cnaes_secundarios: Optional[str] = Field(
        None,
        max_length=500,
        description="CNAEs secundários separados por vírgula",
    )
    data_abertura: Optional[str] = Field(
        None,
        max_length=10,
        description="Data de abertura/fundação (YYYY-MM-DD)",
    )
    website: Optional[str] = Field(
        None,
        max_length=255,
        description="Site da empresa",
    )

    # Contato
    telefone: Optional[str] = Field(
        None,
        max_length=20,
        description="Telefone fixo",
    )
    celular: Optional[str] = Field(
        None,
        max_length=20,
        description="Celular / WhatsApp",
    )
    email: Optional[str] = Field(
        None,
        max_length=255,
        description="Endereco de email principal para contato",
    )

    # Outros
    url_logo: Optional[str] = Field(
        None,
        max_length=255,
        description="URL ou caminho da logo da empresa",
    )
    cor_tema: Optional[str] = Field(
        None,
        max_length=7,
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="Cor da marca em hex (#RRGGBB). NULL usa a paleta de fabrica.",
    )

    model_config = ConfigDict(from_attributes=True)

# =========================
# Create (Entrada)
# =========================
class EmpresaCreate(EmpresaBase):
    """
    Dados necessarios para cadastrar uma nova empresa (Sign Up).
    Aninha a lista opcional de enderecos.

    Attributes:
        endereco (Optional[List[Endereco]]): Lista opcional de enderecos da empresa.
    """

    endereco: Optional[List["Endereco"]] = Field(
        None,
        description="Lista de enderecos da empresa (Principal, Entrega, etc)",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "razao_social": "Solucoes Tecnologicas Alpha S.A.",
                "nome_fantasia": "Alpha Tech",
                "is_cnpj": True,
                "documento": "68056674073060",
                "inscricao_estadual": "ISENTA",
                "inscricao_municipal": "001.234/2025-0",
                "regime_tributario": "Simples Nacional",
                "cnae_principal": "6201-5/01",
                "telefone": "6832104000",
                "celular": "68999887766",
                "email": "contato@alphatech.com",
                "endereco": [
                    {
                        "logradouro": "Avenida Cicero Pompeu",
                        "numero": "1500",
                        "bairro": "Centro",
                        "cidade": "Rio Branco",
                        "estado": "AC",
                        "cep": "69900-000",
                        "complemento": "Sala 101, Predio Comercial",
                    }
                ],
            }
        },
    )

# =========================
# Update (Entrada)
# =========================
class EmpresaUpdate(BaseModel):
    """
    Dados para atualizacao parcial de uma empresa (PATCH).
    Todos os campos sao opcionais.

    Attributes:
        endereco (Optional[List[EnderecoUpdate]]): Enderecos da empresa para atualizar.
    """

    # Identificacao
    razao_social: Optional[str] = Field(
        None,
        max_length=255,
        description="Razao Social da empresa",
    )
    nome_fantasia: Optional[str] = Field(
        None,
        max_length=255,
        description="Nome Fantasia (comercial)",
    )
    is_cnpj: Optional[bool] = Field(
        None,
        description="Define se o documento e um CPF ou CNPJ",
    )
    documento: Optional[str] = Field(
        None,
        pattern=r"^\d{11,14}$",
        description="Documento CPF/CNPJ (apenas numeros, 11 a 14 digitos)",
    )
    inscricao_estadual: Optional[str] = Field(
        None,
        max_length=50,
        description="Inscricao Estadual",
    )
    inscricao_municipal: Optional[str] = Field(
        None,
        max_length=50,
        description="Inscricao Municipal",
    )
    regime_tributario: Optional[str] = Field(
        None,
        max_length=50,
        description="Regime Tributario (ex: Simples Nacional)",
    )
    cnae_principal: Optional[str] = Field(
        None,
        max_length=50,
        description="CNAE Principal",
    )
    segmento: Optional[str] = Field(
        None,
        max_length=50,
        description="Segmento de negócio da empresa",
    )
    indicador_ie: Optional[str] = Field(
        None,
        max_length=1,
        description="Indicador de IE: 1=Contribuinte ICMS, 2=Isento, 9=Não contribuinte",
    )
    natureza_juridica: Optional[str] = Field(
        None,
        max_length=50,
        description="Natureza jurídica (MEI, ME, EPP, LTDA, SA, EI, SLU)",
    )
    tipo_atividade: Optional[str] = Field(
        None,
        max_length=20,
        description="Tipo de atividade: COMERCIO, INDUSTRIA, SERVICO, MISTO",
    )
    cnaes_secundarios: Optional[str] = Field(
        None,
        max_length=500,
        description="CNAEs secundários separados por vírgula",
    )
    data_abertura: Optional[str] = Field(
        None,
        max_length=10,
        description="Data de abertura/fundação (YYYY-MM-DD)",
    )
    website: Optional[str] = Field(
        None,
        max_length=255,
        description="Site da empresa",
    )

    # Contato
    telefone: Optional[str] = Field(
        None,
        max_length=20,
        description="Telefone fixo",
    )
    celular: Optional[str] = Field(
        None,
        max_length=20,
        description="Celular / WhatsApp",
    )
    email: Optional[str] = Field(
        None,
        max_length=255,
        description="Endereco de email principal para contato",
    )

    # Outros
    url_logo: Optional[str] = Field(
        None,
        max_length=255,
        description="URL ou caminho da logo da empresa",
    )
    cor_tema: Optional[str] = Field(
        None,
        max_length=7,
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="Cor da marca em hex (#RRGGBB). NULL usa a paleta de fabrica.",
    )

    endereco: Optional[List["EnderecoUpdate"]] = Field(
        None,
        description="Lista de enderecos da empresa para atualizacao",
    )

    fiscal_settings: Optional["FiscalSettingsUpdate"] = Field(
        None,
        description="Configurações fiscais para atualização",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "nome_fantasia": "Alpha Tech Brasil",
                "telefone": "1132104000",
                "endereco": [
                    {
                        "id": 10,
                        "logradouro": "Avenida Cicero Pompeu",
                        "numero": "1500",
                        "bairro": "Centro",
                        "cidade": "Rio Branco",
                        "estado": "AC",
                        "cep": "69900-000",
                        "complemento": "Sala 101",
                    }
                ],
                "fiscal_settings": {
                    "ambiente_emissao": 2,
                    "serie_nfe": 1,
                    "csc_token": "ABC123",
                    "csc_id": "000001"
                }
            }
        },
    )

# =========================
# Admin Read (Saida)
# =========================
class EmpresaAdminRead(EmpresaBase):
    """
    Formato de resposta da API para Empresa. Inclui dados internos (id, ativo),
    lista aninhada de enderecos e configurações fiscais.

    Attributes:
        id (int): ID unico da empresa.
        ativo (bool): Status de ativo/inativo da empresa.
        enderecos (Optional[List[EnderecoRead]]): Enderecos cadastrados (com IDs).
        fiscal_settings (Optional[FiscalSettingsRead]): Configurações fiscais da empresa.
    """

    id: int = Field(..., description="ID unico da empresa")
    ativo: bool = Field(..., description="Status da empresa")
    enderecos: Optional[List["EnderecoRead"]] = Field(
        None,
        description="Enderecos cadastrados",
    )
    fiscal_settings: Optional["FiscalSettingsRead"] = Field(
        None,
        description="Configurações fiscais (NFe, NFCe, NFSe, certificados)",
    )

# =========================
# User Read (Saida)
# =========================
class EmpresaUserRead(BaseModel):
    """Resposta de Empresa para usuarios. Inclui dados de contato e endereco principal."""

    id: int = Field(..., description="ID unico da empresa")
    ativo: bool = Field(..., description="Status da empresa")
    razao_social: Optional[str] = Field(
        None,
        max_length=255,
        description="Razao Social da empresa",
    )
    nome_fantasia: Optional[str] = Field(
        None,
        max_length=255,
        description="Nome Fantasia (comercial)",
    )
    url_logo: Optional[str] = Field(
        None,
        max_length=255,
        description="URL ou caminho da logo da empresa",
    )
    cor_tema: Optional[str] = Field(
        None,
        max_length=7,
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="Cor da marca em hex (#RRGGBB). NULL usa a paleta de fabrica.",
    )
    documento: Optional[str] = Field(
        None,
        max_length=20,
        description="CNPJ ou CPF da empresa",
    )
    telefone: Optional[str] = Field(
        None,
        max_length=20,
        description="Telefone fixo da empresa",
    )
    celular: Optional[str] = Field(
        None,
        max_length=20,
        description="Celular / WhatsApp da empresa",
    )
    email: Optional[str] = Field(
        None,
        max_length=255,
        description="Email principal da empresa",
    )
    segmento: Optional[str] = Field(
        None,
        max_length=50,
        description="Segmento de negócio da empresa",
    )
    enderecos: Optional[Sequence["EnderecoRead"]] = Field(
        None,
        description="Enderecos cadastrados",
    )

    model_config = ConfigDict(from_attributes=True)


EmpresaCreate.model_rebuild()
EmpresaUpdate.model_rebuild()
EmpresaAdminRead.model_rebuild()
FiscalSettingsRead.model_rebuild()
