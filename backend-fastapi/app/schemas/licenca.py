# ---------------------------------------------------------------------------
# ARQUIVO: app/schemas/licenca.py
# DESCRIÇÃO: Schemas Pydantic para dados de licenciamento.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ===========================================================================
# Auto-Cadastro (Etapa 1)
# ===========================================================================

class LicencaEnderecoPayload(BaseModel):
    """Sub-schema para o endereço no payload de auto-cadastro."""
    cep: str = Field(..., max_length=10)
    logradouro: str = Field(..., max_length=255)
    numero: str = Field(..., max_length=20)
    bairro: str = Field(..., max_length=100)
    cidade: str = Field(..., max_length=100)
    estado: str = Field(..., max_length=2)


class AutoCadastroPayload(BaseModel):
    """Payload enviado à API StartBig para auto-cadastro de licença."""
    documento: str = Field(..., description="CPF ou CNPJ")
    nomeOuRazao: str = Field(..., description="Nome ou Razão Social")
    email: str = Field(..., description="Email do responsável")
    senha: str = Field(..., description="Senha para autenticação futura")
    hwid: str = Field(..., description="Hardware ID da máquina (obtido internamente)")
    endereco: Optional[LicencaEnderecoPayload] = Field(
        None, description="Endereço (opcional)"
    )


class AutoCadastroResponse(BaseModel):
    """Resposta da API StartBig após auto-cadastro e conexão."""
    msg: str = Field(..., description="Mensagem de sucesso ou erro")
    clienteId: Optional[str] = Field(None, description="ID do cliente (se sucesso)")
    licencaId: str = Field(..., description="ID da licença gerada")
    chaveAtivacao: Optional[str] = Field(None, description="Chave de ativação (se sucesso)")
    sessionKey: Optional[str] = Field(None, description="Chave de sessão (deprecada, mantida por retrocompatibilidade)")
    limite: int = Field(..., description="Limite de uso da licença")
    dataVencimento: datetime = Field(..., description="Data de vencimento da licença")
    token: str = Field(..., description="Token de autenticação para futuras requisições")
    ultimaSincronizacao: datetime = Field(..., description="Data da última sincronização com a API")
    gracePeriodDias: int = Field(..., description="Dias de período de carência após vencimento")
    proximaValidacaoEm: datetime = Field(..., description="Data da próxima validação obrigatória da licença")


class ChavePublicaResponse(BaseModel):
    """Resposta do GET /licenca/chave-publica da API StartBig."""
    publicKey: str = Field(..., description="Chave pública RSA em formato PEM")


class LicencaRead(BaseModel):
    """Schema de leitura da licença armazenada localmente."""
    id: int
    cliente_id: str
    hwid: str
    licenca_id: str
    limite: int
    data_vencimento: datetime
    proxima_validacao: datetime
    grace_period: int


# ===========================================================================
# Validação de Sessão (Etapa 2)
# ===========================================================================

class ConectarPayload(BaseModel):
    """Payload enviado à API StartBig para validação de sessão."""
    chave: str = Field(..., description="Chave de ativação (descriptografada)")
    hwid: str = Field(..., description="Hardware ID da máquina")


class LicencaStatusResponse(BaseModel):
    """Resposta do GET /licenca/status para o frontend."""
    status: str = Field(..., description="online_valid | offline_valid")
    dias_restantes: Optional[int] = Field(
        None, description="Dias restantes até o vencimento (online) ou de validade offline"
    )
    trial: Optional[bool] = Field(
        None,
        description="True quando a licença é um trial. Reservado: depende de a "
        "API StartBig repassar essa informação; hoje não é preenchido.",
    )


class HeartbeatPayload(BaseModel):
    """Payload enviado à API StartBig para heartbeat de licença."""
    licencaId: str = Field(..., description="ID da licença")
    hwid: str = Field(..., description="Hardware ID da máquina")


class LicencaErroResponse(BaseModel):
    """Corpo do erro HTTP 403 para problemas de licença."""
    codigo: str = Field(
        ...,
        description=(
            "CLONAGEM_DETECTADA | REQUISITA_CONEXAO_INTERNET | "
            "LICENCA_EXPIRADA | LICENCA_NAO_ENCONTRADA | CHAVE_CORROMPIDA"
        ),
    )
    mensagem: str = Field(..., description="Mensagem descritiva do erro")


# ===========================================================================
# Renovação Ativa de Token (Etapa 4)
# ===========================================================================

class ValidarPayload(BaseModel):
    """Payload enviado à API StartBig para renovação ativa do token."""
    chave: str = Field(..., description="UUID da licença")
    hwid: str = Field(..., description="Hardware ID da máquina")


class ValidarResponse(BaseModel):
    """Resposta de sucesso da API StartBig ao validar/renovar o token."""
    valida: bool = Field(..., description="True se a licença é válida")
    licencaId: str = Field(..., description="UUID da licença")
    status: str = Field(..., description="Status da licença (ex: ATIVA)")
    dataVencimento: datetime = Field(..., description="Data de vencimento da licença")
    token: str = Field(..., description="Novo token JWT renovado")
    ultimaSincronizacao: datetime = Field(..., description="Timestamp da sincronização")
    gracePeriodDias: int = Field(..., description="Dias de período de carência offline")
    proximaValidacaoEm: datetime = Field(..., description="Data da próxima validação obrigatória")


class ValidarErroResponse(BaseModel):
    """Resposta de erro da API StartBig ao validar/renovar o token."""
    valida: bool = Field(False, description="Sempre False para erros")
    motivo: str = Field(..., description="Motivo da recusa (ex: Licença vencida)")
    status: str = Field(..., description="Status da licença (VENCIDA, BLOQUEADA, SUSPENSA, REVOGADA)")


# ===========================================================================
# Desconexão de Sessão (Etapa 5)
# ===========================================================================

class DesconectarPayload(BaseModel):
    """Payload enviado à API StartBig para desconectar a sessão da licença."""
    chave: str = Field(..., description="Chave de ativação (descriptografada)")
    hwid: str = Field(..., description="Hardware ID da máquina")
