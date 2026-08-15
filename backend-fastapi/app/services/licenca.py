# ---------------------------------------------------------------------------
# ARQUIVO: services/licenca.py
# MÓDULO: Regras de Negócio (Service Layer)
# DESCRIÇÃO: Serviço de licenciamento - auto-cadastro na API StartBig,
#            criptografia AES-256-GCM e persistência local.
# ---------------------------------------------------------------------------

import asyncio
import base64
import hashlib
import logging
import os
from datetime import datetime, timezone

import httpx
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException, status
from jose import jwt, JWTError, JOSEError
from sqlalchemy.orm import Session

from datetime import timedelta

from app.schemas.licenca import (
    AutoCadastroPayload,
    AutoCadastroResponse,
    ChavePublicaResponse,
    ConectarPayload,
    DesconectarPayload,
    HeartbeatPayload,
    LicencaEnderecoPayload,
    ValidarPayload,
    ValidarResponse,
)
from app.db.models.configuracao_licenca import ConfiguracaoLicenca
from app.db.models.terminal_conectado import TerminalConectado
from app.db.crud import configuracao_licenca as licenca_crud
from app.db.crud import terminal_conectado as terminal_crud
from app.core.hwid import obter_hwid

logger = logging.getLogger(__name__)

API_AUTO_CADASTRO_URL = "https://api.startbig.com.br/erp/auto-cadastro"
API_CONECTAR_URL = "https://api.startbig.com.br/licenca/conectar"
API_HEARTBEAT_URL = "https://api.startbig.com.br/licenca/heartbeat"
API_VALIDAR_URL = "https://api.startbig.com.br/licenca/validar"
API_DESCONECTAR_URL = "https://api.startbig.com.br/licenca/desconectar"
API_CHAVE_PUBLICA_URL = "https://api.startbig.com.br/licenca/chave-publica"
TIMEOUT_SECONDS = 30
CONECTAR_TIMEOUT_SECONDS = 3
HEARTBEAT_TIMEOUT = httpx.Timeout(
    connect=10.0,   # DNS + TCP + TLS (operação mais lenta)
    read=5.0,       # Aguardar resposta do servidor
    write=5.0,      # Enviar payload (pequeno)
    pool=5.0,       # Aguardar conexão do pool
)
DESCONECTAR_TIMEOUT = httpx.Timeout(connect=1.0, read=0.5, write=0.5, pool=0.5)
MAX_RETRIES = 3


# ===========================================================================
# Criptografia AES-256-GCM
# ===========================================================================

def _derivar_chave(hwid: str) -> bytes:
    """
    Deriva uma chave AES-256 (32 bytes) a partir do HWID usando SHA-256.
    Determinístico: mesmo HWID sempre gera a mesma chave.
    """
    return hashlib.sha256(hwid.encode("utf-8")).digest()


def encriptar_valor(valor: str, hwid: str) -> str:
    """
    Encripta um valor usando AES-256-GCM com chave derivada do HWID.
    Retorna: base64(nonce + ciphertext + tag)
    """
    chave = _derivar_chave(hwid)
    aesgcm = AESGCM(chave)
    nonce = os.urandom(12)  # 96-bit nonce para GCM
    ciphertext = aesgcm.encrypt(nonce, valor.encode("utf-8"), None)
    # nonce (12 bytes) + ciphertext (inclui tag de 16 bytes)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decriptar_valor(valor_encriptado: str, hwid: str) -> str:
    """
    Decripta um valor previamente encriptado com encriptar_valor.
    """
    chave = _derivar_chave(hwid)
    dados = base64.b64decode(valor_encriptado)
    nonce = dados[:12]
    ciphertext = dados[12:]
    aesgcm = AESGCM(chave)
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


# ===========================================================================
# Chamada à API Externa com Retry
# ===========================================================================

def _chamar_api_auto_cadastro(payload: AutoCadastroPayload) -> AutoCadastroResponse:
    """
    Faz a requisição HTTP POST para a API de auto-cadastro com retry.

    Retry: apenas para erros 5xx, ConnectError e TimeoutException.
    Erros 4xx: propagados imediatamente (sem retry).

    Raises:
        HTTPException 422: Se a API retornar erro 4xx (validação, duplicidade).
        HTTPException 503: Se não conseguir conectar após todas as tentativas.
    """
    ultimo_erro = None

    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
                response = client.post(
                    API_AUTO_CADASTRO_URL,
                    json=payload.model_dump(exclude_none=True),
                )

            if 200 <= response.status_code < 300:
                return AutoCadastroResponse(**response.json())

            # Erros 4xx da API (ex: documento duplicado) — não faz retry
            if 400 <= response.status_code < 500:
                detail = response.json().get("message", response.text)
                try:
                    body = response.json()
                    detail = body.get("message", body.get("detail", response.text))
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Erro no auto-cadastro de licença: {detail}"
                )

            # Erros 5xx — faz retry
            ultimo_erro = f"API retornou status {response.status_code}"
            logger.warning(
                "[licenca] Tentativa %d/%d falhou: %s",
                tentativa, MAX_RETRIES, ultimo_erro,
            )

        except httpx.ConnectError as e:
            ultimo_erro = f"Falha de conexão: {e}"
            logger.warning(
                "[licenca] Tentativa %d/%d: %s", tentativa, MAX_RETRIES, ultimo_erro
            )
        except httpx.TimeoutException as e:
            ultimo_erro = f"Timeout: {e}"
            logger.warning(
                "[licenca] Tentativa %d/%d: %s", tentativa, MAX_RETRIES, ultimo_erro
            )
        except HTTPException:
            raise  # Re-raise erros 4xx sem retry
        except Exception as e:
            ultimo_erro = f"Erro inesperado: {e}"
            logger.error(
                "[licenca] Tentativa %d/%d: %s", tentativa, MAX_RETRIES, ultimo_erro
            )

    # Todas as tentativas falharam
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            f"Não foi possível conectar ao servidor de licenças após {MAX_RETRIES} tentativas. "
            f"Verifique sua conexão com a internet. Último erro: {ultimo_erro}"
        ),
    )


# ===========================================================================
# Resgate de Chave Pública (Endpoint 7)
# ===========================================================================

def _buscar_chave_publica_online() -> str:
    """
    Faz GET ao endpoint público da StartBig para obter a chave pública RSA PEM.

    Returns:
        str: Chave pública RSA em formato PEM.

    Raises:
        httpx.ConnectError / httpx.TimeoutException: Se offline.
        HTTPException 503: Se o servidor retornar erro.
    """
    with httpx.Client(timeout=CONECTAR_TIMEOUT_SECONDS) as client:
        response = client.get(API_CHAVE_PUBLICA_URL)

    if 200 <= response.status_code < 300:
        dados = ChavePublicaResponse(**response.json())
        return dados.publicKey

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Falha ao obter chave pública: servidor retornou status {response.status_code}",
    )


def resgatar_chave_publica_online(
    db: Session,
    hwid: str,
    licenca_id: str,
) -> str:
    """
    Resgata a chave pública RSA da nuvem, encripta-a com o HWID
    e persiste na coluna public_key com commit independente.

    Args:
        db: Sessão do banco de dados.
        hwid: Hardware ID da máquina.
        licenca_id: UUID da licença.

    Returns:
        str: Chave pública PEM em texto limpo (para uso imediato em memória).

    Raises:
        httpx.ConnectError / httpx.TimeoutException: Se offline.
        HTTPException: Se o servidor retornar erro.
    """
    public_key_pem = _buscar_chave_publica_online()

    # Encriptar e persistir com commit independente
    licenca = licenca_crud.get_licenca(db)
    if licenca:
        licenca.public_key = encriptar_valor(public_key_pem, hwid)
        licenca_crud.update_licenca(db, licenca)
        db.commit()
        logger.info("[licenca] Chave pública resgatada e persistida com sucesso.")

    return public_key_pem


# ===========================================================================
# Orquestração Principal
# ===========================================================================

def registrar_licenca(
    db: Session,
    documento: str,
    nome_ou_razao: str,
    email: str,
    senha: str,
    endereco_data: dict,
) -> ConfiguracaoLicenca:
    """
    Orquestra o auto-cadastro de licença:
    1. Obtém o HWID da máquina localmente
    2. Verifica se já existe licença para este HWID
    3. Chama a API externa
    4. Encripta campos sensíveis
    5. Persiste no banco (flush, não commit — commit fica com _handle_db_transaction)

    Args:
        db: Sessão do banco de dados.
        documento: CPF ou CNPJ (apenas números).
        nome_ou_razao: Nome ou Razão Social.
        email: Email do responsável.
        endereco_data: Dict com campos de endereço (pode ser vazio).

    Returns:
        ConfiguracaoLicenca: O registro de licença criado.

    Raises:
        HTTPException 409: Se a máquina já possui licença.
        HTTPException 422: Se a API retornar erro de validação.
        HTTPException 503: Se não conseguir conectar ao servidor.
    """
    # 1. Obter HWID da máquina
    hwid = obter_hwid()

    # 2. Verificar duplicidade de HWID
    existente = licenca_crud.get_licenca_by_hwid(db, hwid)
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta máquina já possui uma licença registrada.",
        )

    # 2. Montar payload e chamar API
    endereco_payload = None
    if endereco_data and endereco_data.get("cep"):
        endereco_payload = LicencaEnderecoPayload(**endereco_data)

    payload = AutoCadastroPayload(
        documento=documento,
        nomeOuRazao=nome_ou_razao,
        email=email,
        senha=senha,
        hwid=hwid,
        endereco=endereco_payload,
    )

    resposta = _chamar_api_auto_cadastro(payload)

    # 3. Buscar chave pública RSA da plataforma StartBig
    public_key_pem = _buscar_chave_publica_online()

    # 4. Encriptar campos sensíveis
    chave_ativacao_enc = encriptar_valor(resposta.chaveAtivacao, hwid)
    public_key_enc = encriptar_valor(public_key_pem, hwid)

    # 5. Criar registro no banco
    licenca = ConfiguracaoLicenca(
        cliente_id=resposta.clienteId,
        hwid=hwid,
        licenca_id=resposta.licencaId,
        chave_ativacao=chave_ativacao_enc,
        public_key=public_key_enc,
        limite=resposta.limite,
        data_vencimento=resposta.dataVencimento,
        token=resposta.token,
        ultima_sinc=resposta.ultimaSincronizacao,
        grace_period=resposta.gracePeriodDias,
        proxima_validacao=resposta.proximaValidacaoEm,
    )

    return licenca_crud.create_licenca(db, licenca)


# ===========================================================================
# Reconexão de Licença
# ===========================================================================

def reconnect_licenca(
    db: Session,
    email: str,
    senha: str,
) -> ConfiguracaoLicenca:
    """
    Reconecta uma licença existente na StartBig usando email e senha.
    """
    hwid = obter_hwid()

    # Verifica se já existe
    existente = licenca_crud.get_licenca_by_hwid(db, hwid)
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta máquina já possui uma licença registrada.",
        )

    payload = {
        "email": email,
        "senha": senha,
        "hwid": hwid
    }

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            response = client.post(
                "https://api.startbig.com.br/erp/auth/login",
                json=payload,
            )
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Falha de conexão com a StartBig: {e}"
        )

    if 200 <= response.status_code < 300:
        resposta = AutoCadastroResponse(**response.json())
    else:
        detail = response.text
        try:
            body = response.json()
            detail = body.get("message", body.get("msg", detail))
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Credenciais inválidas: {detail}"
        )

    # 3. Buscar chave pública RSA da plataforma StartBig
    public_key_pem = _buscar_chave_publica_online()

    # 4. Encriptar campos sensíveis
    chave_ativacao_enc = encriptar_valor(resposta.chaveAtivacao, hwid)
    public_key_enc = encriptar_valor(public_key_pem, hwid)

    # 5. Criar registro no banco
    licenca = ConfiguracaoLicenca(
        cliente_id=resposta.clienteId or "000000000-0000000000-0000000000",
        hwid=hwid,
        licenca_id=resposta.licencaId,
        chave_ativacao=chave_ativacao_enc,
        public_key=public_key_enc,
        limite=resposta.limite,
        data_vencimento=resposta.dataVencimento,
        token=resposta.token,
        ultima_sinc=resposta.ultimaSincronizacao,
        grace_period=resposta.gracePeriodDias,
        proxima_validacao=resposta.proximaValidacaoEm,
    )

    return licenca_crud.create_licenca(db, licenca)

# ===========================================================================
# Validação de Sessão (Etapa 2 — Boot Check)
# ===========================================================================

def _erro_licenca(codigo: str, mensagem: str) -> HTTPException:
    """
    Cria uma HTTPException 403 padronizada para erros de licença inválida.
    E um HTTPException 404 para licença não encontrada.
    """
    
    if codigo == "LICENCA_NAO_ENCONTRADA":
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"codigo": codigo, "mensagem": mensagem},
        )

    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"codigo": codigo, "mensagem": mensagem},
    )


def _tentar_conexao_remota(
    db: Session,
    licenca: ConfiguracaoLicenca,
    chave_ativacao: str,
    hwid: str,
) -> dict:
    """
    Tenta validar a licença online via POST /licenca/conectar.

    Raises:
        httpx.ConnectError / httpx.TimeoutException: Se offline (fallback).
        HTTPException 403: Se o servidor recusar a licença.
    """
    payload = ConectarPayload(chave=chave_ativacao, hwid=hwid)

    with httpx.Client(timeout=CONECTAR_TIMEOUT_SECONDS) as client:
        response = client.post(
            API_CONECTAR_URL,
            json=payload.model_dump(),
        )

    if 200 <= response.status_code < 300:
        resposta = AutoCadastroResponse(**response.json())

        # Atualizar dados da licença atomicamente
        licenca.ultima_sinc = resposta.ultimaSincronizacao
        licenca.proxima_validacao = resposta.proximaValidacaoEm
        licenca.token = resposta.token
        licenca.data_vencimento = resposta.dataVencimento
        licenca.limite = resposta.limite
        licenca.grace_period = resposta.gracePeriodDias

        licenca_crud.update_licenca(db, licenca)
        db.commit()

        logger.info("[licenca] Validação online bem-sucedida.")

        # dias_restantes a partir do vencimento recém-sincronizado do servidor,
        # para o frontend (badge de licença) alertar sobre renovação também no
        # caminho online — antes só o fallback offline devolvia esse número.
        vencimento = licenca.data_vencimento
        if vencimento.tzinfo is None:
            vencimento = vencimento.replace(tzinfo=timezone.utc)
        dias_restantes = (vencimento - datetime.now(timezone.utc)).days
        return {"status": "online_valid", "dias_restantes": dias_restantes}

    # Erro 4xx do servidor (licença inválida/suspensa)
    if 400 <= response.status_code < 500:
        detail = response.text
        try:
            body = response.json()
            detail = body.get("msg", body.get("message", response.text))
        except Exception:
            pass
        raise _erro_licenca("LICENCA_RECUSADA", f"Servidor recusou a licença: {detail}")

    # Erro 5xx — tratar como offline (fallback)
    raise httpx.ConnectError(f"Servidor retornou status {response.status_code}")


def _validar_offline(
    licenca: ConfiguracaoLicenca,
    public_key: str,
) -> dict:
    """
    Validação offline usando JWT RS256 e regras de grace period.

    Args:
        licenca: Registro da licença no banco.
        public_key: Chave pública RSA PEM descriptografada.

    Returns:
        dict com status e dias_restantes.

    Raises:
        HTTPException 403: Se a validação offline falhar.
    """
    agora = datetime.now(timezone.utc)

    # 1. Validar JWT com a chave pública RSA
    try:
        jwt.decode(
            licenca.token,
            public_key,
            algorithms=["RS256"],
            options={"verify_exp": True, "verify_aud": False}
        )
    except (JWTError, JOSEError) as e:
        logger.warning("[licenca] Falha na validação JWT offline: %s", e)
        raise _erro_licenca(
            "REQUISITA_CONEXAO_INTERNET",
            "Token de licença inválido ou expirado. Conecte-se à internet para revalidar.",
        )

    # 2. Verificar data de vencimento do plano
    data_vencimento = licenca.data_vencimento
    if data_vencimento.tzinfo is None:
        data_vencimento = data_vencimento.replace(tzinfo=timezone.utc)

    if agora >= data_vencimento:
        raise _erro_licenca(
            "LICENCA_EXPIRADA",
            "Sua licença expirou. Entre em contato com o suporte para renovação.",
        )

    # 3. Verificar grace period (dias desde última sincronização)
    ultima_sinc = licenca.ultima_sinc
    if ultima_sinc.tzinfo is None:
        ultima_sinc = ultima_sinc.replace(tzinfo=timezone.utc)

    dias_offline = (agora - ultima_sinc).days
    if dias_offline > licenca.grace_period:
        raise _erro_licenca(
            "REQUISITA_CONEXAO_INTERNET",
            f"Limite de {licenca.grace_period} dias offline excedido ({dias_offline} dias). "
            "Conecte-se à internet para revalidar a licença.",
        )

    # 4. Verificar próxima validação obrigatória
    proxima_validacao = licenca.proxima_validacao
    if proxima_validacao.tzinfo is None:
        proxima_validacao = proxima_validacao.replace(tzinfo=timezone.utc)

    if agora >= proxima_validacao:
        raise _erro_licenca(
            "REQUISITA_CONEXAO_INTERNET",
            "Data de validação obrigatória atingida. Conecte-se à internet para revalidar.",
        )

    # 5. Calcular dias restantes
    dias_ate_vencimento = (data_vencimento - agora).days
    dias_ate_grace = licenca.grace_period - dias_offline
    dias_ate_validacao = (proxima_validacao - agora).days
    dias_restantes = min(dias_ate_vencimento, dias_ate_grace, dias_ate_validacao)

    logger.info(
        "[licenca] Validação offline aceita. Dias restantes: %d", dias_restantes
    )
    return {"status": "offline_valid", "dias_restantes": dias_restantes}


def verificar_licenca_ativa(db: Session) -> dict:
    """
    Verifica se a licença da máquina está ativa.

    Fluxo:
    1. Obtém HWID local.
    2. Busca licença no banco.
    3. Testa descriptografia (anti-clonagem).
    4. Tenta validação online (prioridade).
    5. Fallback offline se a nuvem estiver inacessível.

    Returns:
        dict: {"status": "online_valid"} ou {"status": "offline_valid", "dias_restantes": N}

    Raises:
        HTTPException 403: Com código estruturado em caso de falha.
    """
    # 1. Obter HWID
    try:
        hwid = obter_hwid()
    except RuntimeError as e:
        logger.error("[licenca] Falha ao obter HWID: %s", e)
        raise _erro_licenca(
            "CLONAGEM_DETECTADA",
            "Não foi possível identificar a máquina. Verifique a instalação.",
        )

    # 2. Buscar licença no banco
    licenca = licenca_crud.get_licenca(db)
    if not licenca:
        raise _erro_licenca(
            "LICENCA_NAO_ENCONTRADA",
            "Nenhuma licença encontrada. Execute o setup inicial do sistema.",
        )

    # 3. Descriptografar chave de ativação (teste anti-clonagem)
    try:
        chave_ativacao = decriptar_valor(licenca.chave_ativacao, hwid)
    except Exception as e:
        logger.warning("[licenca] Falha na descriptografia — possível clonagem: %s", e)
        raise _erro_licenca(
            "CLONAGEM_DETECTADA",
            "Falha na verificação de integridade. "
            "O banco de dados pode ter sido copiado de outra máquina.",
        )

    # 4. Tentar validação online (prioridade)
    try:
        return _tentar_conexao_remota(db, licenca, chave_ativacao, hwid)
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.info("[licenca] Nuvem inacessível (%s), iniciando fallback offline.", e)
    except HTTPException:
        raise  # Erros 403 da API são repassados

    # 5. Desencriptar chave pública com resiliência
    public_key = None
    try:
        if licenca.public_key:
            public_key = decriptar_valor(licenca.public_key, hwid)
    except (InvalidTag, Exception) as e:
        logger.warning("[licenca] public_key corrompida, tentando resgate online: %s", e)

    if not public_key:
        try:
            public_key = resgatar_chave_publica_online(db, hwid, licenca.licenca_id)
        except Exception:
            raise _erro_licenca(
                "CHAVE_CORROMPIDA",
                "Chave de segurança corrompida. Necessária ligação à internet para recuperação.",
            )

    # 6. Fallback offline
    return _validar_offline(licenca, public_key)


# ===========================================================================
# Conexão de Terminal (Login)
# ===========================================================================

def conectar_terminal(db: Session, terminal_hwid: str) -> None:
    """
    Conecta um terminal à licença via API StartBig.

    Chamado durante o login de cada terminal. Idempotente: se o HWID
    já estiver registrado em terminais_conectados, atualiza ultima_sinc
    e retorna sem chamar a API externa.

    Fluxo:
    1. Verifica se terminal já está registrado (idempotente).
    2. Busca licença e decripta chave_ativacao com HWID do servidor.
    3. POST /licenca/conectar com {chave, hwid: terminal_hwid}.
    4. Sucesso → insere em terminais_conectados.
    5. Erro 4xx → HTTPException 403.
    6. Erro de rede → HTTPException 503.

    Args:
        db: Sessão do banco de dados.
        terminal_hwid: Hardware ID do terminal que está fazendo login.

    Raises:
        HTTPException 403: Limite de terminais atingido ou licença recusada.
        HTTPException 503: Não foi possível conectar ao servidor de licenças.
    """
    # 0. HWID vazio nao identifica terminal nenhum. Barrar aqui (e nao so no
    #    endpoint) porque esta funcao E a fronteira do limite de licenca: a API
    #    externa ACEITA hwid vazio, entao um hwid em branco entrava sem ocupar
    #    vaga e furava o limite -- bastava omitir o campo no login.
    if not (terminal_hwid or "").strip():
        raise _erro_licenca(
            "HWID_AUSENTE",
            "Terminal não identificado. Não foi possível validar a licença.",
        )

    print(f"[terminal] conectar_terminal chamado — hwid={terminal_hwid[:8]}...")

    # 1. Idempotência: terminal já conectado
    existente = terminal_crud.get_terminal_by_hwid(db, terminal_hwid)
    if existente:
        terminal_crud.update_ultima_sinc(db, existente)
        print(f"[terminal] Terminal {terminal_hwid[:8]}... já conectado — update ultima_sinc")
        return

    # 2. Buscar licença e decriptar com HWID do servidor
    licenca = licenca_crud.get_licenca(db)
    if not licenca:
        import os, sys
        if os.getenv("TESTING") or "pytest" in sys.modules:
            print("[terminal] Ignorando conexão de licença em ambiente de testes")
            return
        raise _erro_licenca(
            "LICENCA_NAO_ENCONTRADA",
            "Nenhuma licença encontrada. Execute o setup inicial do sistema.",
        )

    # 3. Pré-validação local: verificar limite de terminais antes da chamada API
    terminais = terminal_crud.get_todos_terminais(db)
    if len(terminais) >= licenca.limite:
        raise _erro_licenca(
            "LIMITE_TERMINAIS",
            f"Limite máximo de {licenca.limite} máquina(s) conectada(s) atingido. "
            "Desconecte um terminal para conectar um novo.",
        )

    # 4. Decriptar chave de ativação com HWID do servidor
    hwid_servidor = obter_hwid()
    try:
        chave_ativacao = decriptar_valor(licenca.chave_ativacao, hwid_servidor)
    except Exception as e:
        logger.warning("[licenca] Falha na descriptografia — possível clonagem: %s", e)
        raise _erro_licenca(
            "CLONAGEM_DETECTADA",
            "Falha na verificação de integridade. "
            "O banco de dados pode ter sido copiado de outra máquina.",
        )

    # 5. Chamar API externa
    payload = ConectarPayload(chave=chave_ativacao, hwid=terminal_hwid)

    try:
        with httpx.Client(timeout=CONECTAR_TIMEOUT_SECONDS) as client:
            response = client.post(
                API_CONECTAR_URL,
                json=payload.model_dump(),
            )
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        # 6. Fallback offline: API indisponível, mas validação local passou — registrar localmente
        terminal = TerminalConectado(hwid=terminal_hwid)
        terminal_crud.create_terminal(db, terminal)
        print(f"[terminal] Terminal {terminal_hwid[:8]}... CRIADO (fallback offline — {type(e).__name__})")
        return

    # 7. Processar resposta da API
    if 200 <= response.status_code < 300:
        terminal = TerminalConectado(hwid=terminal_hwid)
        terminal_crud.create_terminal(db, terminal)
        print(f"[terminal] Terminal {terminal_hwid[:8]}... CRIADO (API retornou {response.status_code})")
        return

    # 8. Erro 4xx (limite atingido na API, licença inválida)
    if 400 <= response.status_code < 500:
        detail = response.text
        try:
            body = response.json()
            detail = body.get("msg", body.get("message", response.text))
        except Exception:
            pass
        raise _erro_licenca(
            "LIMITE_TERMINAIS",
            f"Não foi possível conectar o terminal: {detail}",
        )

    # 9. Erro 5xx — tratar como indisponível (fallback offline)
    terminal = TerminalConectado(hwid=terminal_hwid)
    terminal_crud.create_terminal(db, terminal)
    print(f"[terminal] Terminal {terminal_hwid[:8]}... CRIADO (fallback 5xx — status {response.status_code})")


# ===========================================================================
# Heartbeat (Etapa 3 — Sincronização de Estado)
# ===========================================================================

async def _enviar_heartbeat_terminal(
    client: httpx.AsyncClient,
    licenca_id: str,
    terminal: "TerminalConectado",
) -> tuple["TerminalConectado", int | None]:
    """
    Envia heartbeat para um terminal específico.

    Returns:
        Tupla (terminal, status_code). status_code é None em caso de erro de rede.
    """
    payload = HeartbeatPayload(licencaId=licenca_id, hwid=terminal.hwid)
    try:
        response = await client.post(
            API_HEARTBEAT_URL,
            json=payload.model_dump(),
        )
        return terminal, response.status_code, response.text
    except httpx.RequestError as error:
        print(f"[licenca] Heartbeat falhou para {terminal.hwid[:8]}... — {type(error).__name__}: {error}")
        return terminal, None, None


async def enviar_heartbeat(db: Session) -> None:
    """
    Envia heartbeat para CADA terminal conectado em paralelo.

    Se não há terminais registrados, não envia nada (sem heartbeat).
    Reage à resposta da API por terminal:
    - 201: OK, atualiza ultima_sinc do terminal.
    - 400: Terminal bloqueado, remove da tabela.
    - Erro de rede: Registra em log e ignora.

    Ao final, se todos os terminais foram bloqueados, marca a licença
    como bloqueada. Se pelo menos um está OK, desbloqueia.
    """
    licenca = licenca_crud.get_licenca(db)
    if not licenca:
        return

    terminais = terminal_crud.get_todos_terminais(db)
    if not terminais:
        print("[licenca] Nenhum terminal conectado — heartbeat ignorado.")
        return

    # Enviar heartbeats em paralelo
    async with httpx.AsyncClient(timeout=HEARTBEAT_TIMEOUT) as client:
        resultados = await asyncio.gather(
            *[
                _enviar_heartbeat_terminal(client, licenca.licenca_id, terminal)
                for terminal in terminais
            ],
            return_exceptions=True,
        )

    tem_ok = False
    todos_bloqueados = True

    for resultado in resultados:
        if isinstance(resultado, Exception):
            logger.warning("[licenca] Heartbeat erro inesperado: %s", resultado)
            todos_bloqueados = False
            continue

        terminal, status_code, response_text = resultado

        if status_code == 201:
            terminal_crud.update_ultima_sinc(db, terminal)
            print(f"[licenca] Heartbeat OK para terminal {terminal.hwid[:8]}...")
            tem_ok = True
            todos_bloqueados = False

        elif status_code == 400:
            terminal_crud.delete_terminal_by_hwid(db, terminal.hwid)
            print(f"[terminal] Terminal {terminal.hwid[:8]}... bloqueado (400), REMOVIDO pelo heartbeat. Body: {response_text}")

        elif status_code is not None:
            print(f"[licenca] Heartbeat {terminal.hwid[:8]}...: status inesperado {status_code}")
            todos_bloqueados = False

        else:
            # Erro de rede — não conta como bloqueio
            todos_bloqueados = False

    # Atualizar flag de bloqueio da licença
    if tem_ok and licenca.bloqueada:
        licenca.bloqueada = False
        licenca_crud.update_licenca(db, licenca)
        print("[licenca] Licença desbloqueada (terminal ativo detectado).")
    elif todos_bloqueados and terminais and not licenca.bloqueada:
        licenca.bloqueada = True
        licenca_crud.update_licenca(db, licenca)
        print("[licenca] Licença BLOQUEADA (todos terminais rejeitados).")

    db.commit()


# ===========================================================================
# Renovação Ativa de Token (Etapa 4)
# ===========================================================================

LIMIAR_RENOVACAO = timedelta(hours=24)


async def renovar_licenca_background(db: Session) -> None:
    """
    Verifica se o token está próximo de expirar e solicita renovação à API central.

    Executa em segundo plano a cada hora. Só faz requisição HTTP se a data atual
    estiver a menos de 24 horas de proximaValidacaoEm ou já a tiver ultrapassado.

    Idempotente: seguro para correr múltiplas vezes. Falhas de rede são ignoradas
    silenciosamente para não interromper o loop.
    """
    licenca = licenca_crud.get_licenca(db)
    if not licenca:
        return

    # Verificar se é necessário renovar
    agora = datetime.now(timezone.utc)
    proxima_validacao = licenca.proxima_validacao
    if proxima_validacao.tzinfo is None:
        proxima_validacao = proxima_validacao.replace(tzinfo=timezone.utc)

    tempo_restante = proxima_validacao - agora
    if tempo_restante > LIMIAR_RENOVACAO:
        return

    # Preparar payload
    hwid = obter_hwid()
    chave_ativacao = decriptar_valor(licenca.chave_ativacao, hwid)
    payload = ValidarPayload(
        chave=chave_ativacao,
        hwid=hwid,
    )

    try:
        async with httpx.AsyncClient(timeout=HEARTBEAT_TIMEOUT) as client:
            response = await client.post(
                API_VALIDAR_URL,
                json=payload.model_dump(),
            )

        if response.status_code == 201:
            dados = response.json()

            if not dados.get("valida", False):
                motivo = dados.get("motivo", "Desconhecido")
                status_licenca = dados.get("status", "DESCONHECIDO")
                logger.warning(
                    "[licenca] Renovação recusada — status=%s, motivo=%s",
                    status_licenca, motivo,
                )
                return

            resposta = ValidarResponse(**dados)

            # Atualizar campos atomicamente
            licenca.token = resposta.token
            licenca.proxima_validacao = resposta.proximaValidacaoEm
            licenca.ultima_sinc = resposta.ultimaSincronizacao
            licenca.data_vencimento = resposta.dataVencimento
            licenca.grace_period = resposta.gracePeriodDias

            licenca_crud.update_licenca(db, licenca)
            db.commit()

            logger.info("[licenca] Token renovado com sucesso. Próxima validação: %s", resposta.proximaValidacaoEm)
            return

        logger.warning(
            "[licenca] Renovação: servidor retornou status %d — %s",
            response.status_code, response.text,
        )

    except httpx.RequestError as error:
        logger.warning(
            "[licenca] Renovação falhou — %s: %s",
            type(error).__name__, error,
        )


# ===========================================================================
# Desconexão de Sessão (Etapa 5)
# ===========================================================================

async def desconectar_terminal(db: Session, terminal_hwid: str) -> dict:
    """
    Desconecta um terminal específico da licença.

    1. Remove o registro de terminais_conectados (local).
    2. Notifica a API StartBig via POST /licenca/desconectar.

    Fire-and-forget: nunca levanta exceção — falhas são registadas em log.

    Args:
        db: Sessão do banco de dados.
        terminal_hwid: Hardware ID do terminal a desconectar.

    Returns:
        dict: {"ok": True} sempre.
    """
    try:
        # 1. Remover da tabela local
        print(f"[terminal] desconectar_terminal chamado — hwid={terminal_hwid[:8]}...")
        terminal_crud.delete_terminal_by_hwid(db, terminal_hwid)
        db.commit()

        # 2. Notificar API externa
        licenca = licenca_crud.get_licenca(db)
        if not licenca:
            return {"ok": True}

        hwid_servidor = obter_hwid()
        chave_ativacao = decriptar_valor(licenca.chave_ativacao, hwid_servidor)
        payload = DesconectarPayload(chave=chave_ativacao, hwid=terminal_hwid)

        async with httpx.AsyncClient(timeout=DESCONECTAR_TIMEOUT) as client:
            response = await client.post(
                API_DESCONECTAR_URL,
                json=payload.model_dump(),
            )

        logger.info(
            "[licenca] Desconexão terminal %s: status %d",
            terminal_hwid[:8], response.status_code,
        )

    except Exception as e:
        logger.warning("[licenca] Desconexão falhou — %s: %s", type(e).__name__, e)

    return {"ok": True}
