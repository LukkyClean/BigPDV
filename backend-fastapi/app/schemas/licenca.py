# ---------------------------------------------------------------------------
# ARQUIVO: app/schemas/licenca.py
# DESCRIÇÃO: Schemas Pydantic para dados de licenciamento.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import List, Optional
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
    gracePeriodDias: int = Field(
        ...,
        description=(
            "Dias de validade OFFLINE. Apesar do nome, NAO e tolerancia de "
            "inadimplencia -- essa vem em `emCarencia`/`dataLimiteCarencia`."
        ),
    )
    proximaValidacaoEm: datetime = Field(..., description="Data da próxima validação obrigatória da licença")

    # --- Carencia de pagamento (opcionais) ---
    # Opcionais porque a API so passou a mandar depois; servidor que nao mandar
    # deixa a licenca sem carencia, que e o comportamento de sempre.
    emCarencia: Optional[bool] = Field(
        None, description="True enquanto o gateway ainda re-tenta a cobranca do cartao"
    )
    diasRestantesCarencia: Optional[int] = Field(
        None, description="Dias que ainda faltam da carencia"
    )
    dataLimiteCarencia: Optional[datetime] = Field(
        None, description="Ate quando a carencia vale"
    )


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
    em_carencia: bool = Field(
        False,
        description=(
            "True quando o plano venceu mas o gateway ainda re-tenta o cartao. "
            "A tela usa isto para avisar sem travar."
        ),
    )
    dias_restantes_carencia: Optional[int] = Field(
        None, description="Dias que ainda faltam da carencia, quando estiver em carencia"
    )
    modulos: Optional[List[str]] = Field(
        None,
        description=(
            "Modulos liberados para esta licenca, lidos do JWT assinado. "
            "AUSENTE/None = token sem a claim (emitido antes dos modulos existirem) "
            "e o frontend libera tudo. Lista VAZIA = nenhum modulo liberado."
        ),
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

    # --- Carencia de pagamento (opcionais) ---
    # Opcionais porque a API so passou a mandar depois; servidor que nao mandar
    # deixa a licenca sem carencia, que e o comportamento de sempre.
    emCarencia: Optional[bool] = Field(
        None, description="True enquanto o gateway ainda re-tenta a cobranca do cartao"
    )
    diasRestantesCarencia: Optional[int] = Field(
        None, description="Dias que ainda faltam da carencia"
    )
    dataLimiteCarencia: Optional[datetime] = Field(
        None, description="Ate quando a carencia vale"
    )


class ValidarErroResponse(BaseModel):
    """Resposta de erro da API StartBig ao validar/renovar o token."""
    valida: bool = Field(False, description="Sempre False para erros")
    motivo: str = Field(..., description="Motivo da recusa (ex: Licença vencida)")
    status: str = Field(..., description="Status da licença (VENCIDA, BLOQUEADA, SUSPENSA, REVOGADA)")


# ===========================================================================
# Renovação de Assinatura (Etapa 6) — PIX e cartão
# ===========================================================================
#
# Dois vocabulários convivem aqui, de propósito:
#
#   - o que vai e volta da API StartBig usa camelCase (`valorCentavos`), como
#     todos os payloads das etapas anteriores;
#   - o que este backend devolve ao frontend da loja usa snake_case
#     (`valor_centavos`), como o resto da API local.
#
# A tradução mora num lugar só: `services/licenca_renovacao.py`. Se a nuvem
# renomear um campo, é lá que se conserta -- e em nenhum outro lugar.


class RenovacaoCredenciaisPayload(BaseModel):
    """Par que autentica a loja nos endpoints de renovação da API StartBig.

    O mesmo de `ValidarPayload`: não há token novo nem sessão à parte."""
    chave: str = Field(..., description="Chave de ativação (descriptografada)")
    hwid: str = Field(..., description="Hardware ID da máquina")


class RenovacaoPeriodoRead(BaseModel):
    """Um período comprável do plano da licença — resposta ao frontend."""
    codigo: str = Field(..., description="Código do período (ex: MENSAL)")
    nome: str = Field(..., description="Nome exibível (ex: Mensal)")
    valor_centavos: int = Field(..., description="Preço em centavos, decidido pelo servidor")
    dias: Optional[int] = Field(None, description="Dias somados ao vencimento, quando informado")
    meses: Optional[int] = Field(
        None,
        description=(
            "Meses do período. É o que a API manda hoje — `dias` fica nulo, e a "
            "tela usa o que vier."
        ),
    )
    desconto: Optional[float] = Field(
        None,
        description=(
            "Fração de desconto do período longo (0.05 = 5%). Vem da API; a tela "
            "só mostra, nunca calcula preço."
        ),
    )
    metodos: list[str] = Field(
        default_factory=list,
        description="Métodos aceitos neste período: PIX, CARTAO",
    )


class RenovacaoPlanosRead(BaseModel):
    """Períodos disponíveis, ou o aviso de que a renovação ainda não está no ar.

    `disponivel=False` NÃO é erro: é o estado normal enquanto a API de cobrança
    não subiu. O frontend usa isso para mostrar o botão como indisponível em vez
    de uma tela quebrada.
    """
    disponivel: bool = Field(..., description="False quando a API de cobrança ainda não responde")
    periodos: list[RenovacaoPeriodoRead] = Field(default_factory=list)
    motivo: Optional[str] = Field(None, description="Por que está indisponível, quando estiver")
    plano: Optional[str] = Field(
        None, description="Nome do plano contratado (ex: 'Plano Start')"
    )
    limite_terminais: Optional[int] = Field(
        None,
        description=(
            "Quantos computadores o plano permite ao mesmo tempo. Vem da licença "
            "LOCAL, não da API — o número já está aqui desde o cadastro."
        ),
    )


class CobrancaCreate(BaseModel):
    """Pedido de cobrança vindo da tela da loja."""
    metodo: str = Field(..., description="PIX ou CARTAO")
    periodo: str = Field(..., description="Código do período escolhido")


class CobrancaRead(BaseModel):
    """Cobrança criada.

    PIX e cartão devolvem o mesmo schema com metades diferentes preenchidas:
    PIX traz `pix_copia_e_cola` (e talvez o QR pronto), cartão traz
    `url_checkout` para o app abrir no navegador. Um schema só porque a tela é
    uma só -- quem decide o que mostrar é o `metodo`.
    """
    cobranca_id: str
    metodo: str
    valor_centavos: int
    descricao: Optional[str] = None
    expira_em: Optional[datetime] = None

    # PIX
    pix_copia_e_cola: Optional[str] = Field(
        None,
        description="BR Code. É o único campo obrigatório do PIX — o app desenha o QR a partir dele.",
    )
    qr_code_base64: Optional[str] = Field(
        None, description="Imagem pronta do QR, quando o servidor mandar"
    )

    # Cartão
    url_checkout: Optional[str] = Field(
        None, description="URL do checkout para abrir no navegador"
    )


class CobrancaStatusRead(BaseModel):
    """Status da cobrança, consultado enquanto a tela de pagamento está aberta."""
    cobranca_id: str
    status: str = Field(..., description="PENDENTE | PAGA | EXPIRADA | CANCELADA")
    pago_em: Optional[datetime] = None
    data_vencimento: Optional[datetime] = Field(
        None, description="Vencimento novo, quando a cobrança já foi paga"
    )
    licenca_renovada: bool = Field(
        False,
        description=(
            "True quando este backend JÁ revalidou a licença e gravou o vencimento "
            "novo. É o sinal de que a loja destravou — não basta `status=PAGA`."
        ),
    )


# ===========================================================================
# Desconexão de Sessão (Etapa 5)
# ===========================================================================

class DesconectarPayload(BaseModel):
    """Payload enviado à API StartBig para desconectar a sessão da licença."""
    chave: str = Field(..., description="Chave de ativação (descriptografada)")
    hwid: str = Field(..., description="Hardware ID da máquina")
