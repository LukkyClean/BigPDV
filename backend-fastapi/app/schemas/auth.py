# ---------------------------------------------------------------------------
# ARQUIVO: auth.py
# DESCRIÇÃO: Schemas Pydantic para requisição e resposta de Login/Autenticação.
# ---------------------------------------------------------------------------

from datetime import date
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.endereco import Endereco

# Tipos válidos para enums do setup
SEGMENTOS_VALIDOS = Literal[
    'assistencia_tecnica', 'oficina_mecanica',
    'mercado', 'marcenaria', 'eletricista', 'outros'
]
GENEROS_VALIDOS = Literal['MASCULINO', 'FEMININO', 'OUTRO']

class UsuarioLogin(BaseModel):
    """
    Schema de entrada para a requisição de login.

    Attributes:
        email (str): E-mail do usuário.
        senha (str): Senha em texto plano do usuário.
    """
    email: str = Field(
        ...,
        max_length=255,
        description="Email do usuário"
    )
    senha: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Senha do usuário"
    )
    hwid: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Hardware ID do terminal que está fazendo login"
    )

    @field_validator('email', mode='before')
    @classmethod
    def normalizar_email_login(cls, v: str) -> str:
        return v.strip().lower()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "test@test.com",
                "senha": "test1234"
            }
        }
    )

# =========================
# Setup Inicial (Sign-In)
# =========================

class ReconnectRequest(BaseModel):
    """Schema de entrada para a requisição de reconexão de licença."""
    email: str = Field(..., max_length=255, description="Email do usuário cadastrado na StartBig")
    senha: str = Field(..., min_length=8, max_length=72, description="Senha do usuário cadastrado na StartBig")

    @field_validator('email', mode='before')
    @classmethod
    def normalizar_email_reconnect(cls, v: str) -> str:
        return v.strip().lower()

class LogoutRequest(BaseModel):
    """Schema de entrada para a requisição de logout com HWID do terminal."""
    hwid: str = Field(
        ...,
        max_length=255,
        description="Hardware ID do terminal que está fazendo logout"
    )


class StatusResponse(BaseModel):
    """Resposta do endpoint de verificação de inicialização do sistema."""
    inicializado: bool = Field(
        ...,
        description="Indica se o sistema já possui um usuário Master cadastrado"
    )

class SetupCreate(BaseModel):
    """
    Schema de entrada para o setup inicial do sistema.
    Cria atomicamente: Empresa + Endereco + Usuario Master + Cargo Master + Funcionario.
    """
    # Loja (→ Empresa)
    nome_loja: str = Field(..., max_length=255, description="Nome da loja (→ Empresa.nome_fantasia)")
    segmento: Optional[SEGMENTOS_VALIDOS] = Field(None, description="Segmento de negócio")
    celular: Optional[str] = Field(None, max_length=20, description="Celular da loja")
    email_loja: Optional[str] = Field(None, max_length=255, description="Email da loja")
    telefone: Optional[str] = Field(None, max_length=20, description="Telefone fixo da loja")

    # Endereco
    endereco: Optional[List[Endereco]] = Field(None, description="Endereços da loja")

    # Responsável
    tipo_pessoa: str = Field(..., pattern=r"^(PF|PJ)$", description="Tipo de pessoa: PF ou PJ")
    nome_responsavel: str = Field(..., max_length=255, description="Nome completo (PF) ou nome do responsável (PJ)")

    # Campos PF (→ Funcionario)
    cpf: Optional[str] = Field(None, pattern=r"^\d{11}$", description="CPF do responsável (apenas PF)")
    rg: Optional[str] = Field(None, max_length=20, description="RG do responsável (apenas PF)")
    genero: Optional[GENEROS_VALIDOS] = Field(None, description="Gênero do responsável (apenas PF)")
    data_nascimento: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Data de nascimento (apenas PF, formato YYYY-MM-DD)")

    # Campos PJ (→ Empresa)
    razao_social: Optional[str] = Field(None, max_length=255, description="Razão Social (apenas PJ)")
    cnpj: Optional[str] = Field(None, pattern=r"^\d{14}$", description="CNPJ (apenas PJ)")
    nome_fantasia_pj: Optional[str] = Field(None, max_length=255, description="Nome fantasia PJ")
    inscricao_estadual: Optional[str] = Field(None, max_length=50, description="Inscrição Estadual (apenas PJ)")
    inscricao_municipal: Optional[str] = Field(None, max_length=50, description="Inscrição Municipal (apenas PJ)")
    regime_tributario: Optional[str] = Field(None, max_length=50, description="Regime Tributário (apenas PJ)")

    # Contato do responsável (→ Funcionario)
    celular_responsavel: Optional[str] = Field(None, max_length=20, description="Celular do responsável")
    email_responsavel: Optional[str] = Field(None, max_length=255, description="Email do responsável")

    # Acesso (→ Usuario)
    nome_usuario: str = Field(..., max_length=255, description="Nome de exibição no sistema")
    email: str = Field(..., max_length=255, description="Email de login do usuário")
    senha: str = Field(..., min_length=8, max_length=72, description="Senha do usuário")

    @field_validator('email', 'email_loja', 'email_responsavel', mode='before')
    @classmethod
    def normalizar_email(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.strip().lower()

    @field_validator('data_nascimento', mode='before')
    @classmethod
    def validar_data_nascimento(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError('Data de nascimento inválida (esperado YYYY-MM-DD)')
        return v

    @model_validator(mode='after')
    def validar_campos_por_tipo_pessoa(self):
        if self.tipo_pessoa == 'PJ':
            if not self.razao_social:
                raise ValueError("Razão Social é obrigatória para Pessoa Jurídica")
            if not self.cnpj:
                raise ValueError("CNPJ é obrigatório para Pessoa Jurídica")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nome_loja": "Exemplo Tech",
                "segmento": "assistencia_tecnica",
                "celular": "11999887766",
                "email_loja": "contato@exemplo.com",
                "endereco": [
                    {
                        "logradouro": "Rua Exemplo",
                        "numero": "100",
                        "bairro": "Centro",
                        "cidade": "São Paulo",
                        "estado": "SP",
                        "cep": "01000-000"
                    }
                ],
                "tipo_pessoa": "PF",
                "nome_responsavel": "João Silva",
                "cpf": "12345678900",
                "celular_responsavel": "11999887766",
                "email_responsavel": "joao@exemplo.com",
                "nome_usuario": "João",
                "email": "joao@exemplo.com",
                "senha": "senha1234"
            }
        }
    )
