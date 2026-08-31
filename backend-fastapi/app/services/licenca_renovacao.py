# ---------------------------------------------------------------------------
# ARQUIVO: app/services/licenca_renovacao.py
# DESCRICAO: Renovacao de assinatura pela loja (PIX e cartao).
#
# POR QUE E UM MODULO A PARTE, e nao mais funcoes em services/licenca.py:
#
#   `licenca.py` e o que mantem as lojas em producao licenciadas, e nao tem
#   teste automatizado nenhum hoje. Toda linha nova aqui e ADITIVA: nada do
#   caminho que ja roda (status, conectar, heartbeat, renovacao em background)
#   passa por este arquivo. Se a renovacao inteira quebrar, o sistema das lojas
#   continua exatamente como estava.
#
#   O preco disso e a duplicacao consciente em `revalidar_agora`, que repete o
#   corpo de `renovar_licenca_background` sem o limiar de 24h. Preferi duplicar
#   trinta linhas a mexer, sem rede, na funcao que renova o token de quem ja
#   paga. Quando houver teste cobrindo aquele caminho, as duas viram uma.
#
# A TRADUCAO DE VOCABULARIO mora aqui e so aqui: a API StartBig fala camelCase,
# a API local fala snake_case. Campo que a nuvem renomear se conserta nas
# funcoes `_para_periodo` / `_para_cobranca` -- em nenhum outro lugar.
# ---------------------------------------------------------------------------

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.hwid import obter_hwid
from app.db.crud import configuracao_licenca as licenca_crud
from app.schemas.licenca import (
    CobrancaRead,
    CobrancaStatusRead,
    RenovacaoPeriodoRead,
    RenovacaoPlanosRead,
    ValidarPayload,
    ValidarResponse,
)
from app.services.licenca import _limpar_bloqueio, decriptar_valor

logger = logging.getLogger(__name__)

# ===========================================================================
# Endpoints da API StartBig
# ===========================================================================

API_BASE = "https://api.startbig.com.br"
API_PLANOS_URL = f"{API_BASE}/licenca/renovacao/planos"
API_COBRANCA_URL = f"{API_BASE}/licenca/renovacao/cobranca"
API_VALIDAR_URL = f"{API_BASE}/licenca/validar"

# Curto de proposito: quem esta olhando a tela de pagamento nao pode ficar
# esperando trinta segundos por um spinner. O contrato pede resposta em menos
# de cinco segundos.
TIMEOUT = httpx.Timeout(connect=5.0, read=8.0, write=5.0, pool=5.0)

METODOS_VALIDOS = frozenset({"PIX", "CARTAO"})


# ===========================================================================
# Modo simulado (desenvolvimento)
# ===========================================================================
# Existe porque a API de cobranca sobe DEPOIS desta tela. Sem isto, a tela de
# pagamento so poderia ser vista pela primeira vez em producao -- e tela que
# estreia em producao e exatamente a divida que este projeto ja pagou caro.
#
# Ligado por variavel de ambiente, nunca por configuracao de loja: e ferramenta
# de desenvolvimento, nao recurso do produto.

def _modo_simulado() -> bool:
    return os.getenv("STARTBIG_RENOVACAO_SIMULADA", "").strip().lower() in {"1", "true", "sim"}


# BR Code de exemplo. Nao e uma chave real e nao paga ninguem: serve para o app
# desenhar um QR de verdade na tela durante o desenvolvimento.
_PIX_SIMULADO = (
    "00020126360014BR.GOV.BCB.PIX0114+5588996971128520400005303986"
    "5406599.995802BR5906STARTBIG6008FORTALEZA62070503***6304ABCD"
)

_COBRANCAS_SIMULADAS: dict[str, dict[str, Any]] = {}
_SEGUNDOS_ATE_PAGAR_SIMULADO = 20


# ===========================================================================
# Erros
# ===========================================================================

def _erro(codigo: str, mensagem: str, http_status: int = status.HTTP_503_SERVICE_UNAVAILABLE) -> HTTPException:
    return HTTPException(status_code=http_status, detail={"codigo": codigo, "mensagem": mensagem})


INDISPONIVEL = "RENOVACAO_INDISPONIVEL"


# ===========================================================================
# Credenciais
# ===========================================================================

def _credenciais(db: Session) -> tuple[str, str]:
    """Par `chave` + `hwid` que autentica esta loja na API StartBig.

    Mesma credencial dos endpoints ja existentes -- nao ha sessao a parte para
    renovacao. Funciona com a licenca VENCIDA de proposito: quem precisa pagar
    e justamente quem venceu.
    """
    licenca = licenca_crud.get_licenca(db)
    if not licenca:
        raise _erro(
            "LICENCA_NAO_ENCONTRADA",
            "Nenhuma licenca registrada nesta maquina.",
            status.HTTP_404_NOT_FOUND,
        )

    hwid = obter_hwid()
    try:
        chave = decriptar_valor(licenca.chave_ativacao, hwid)
    except Exception as erro:  # noqa: BLE001 - qualquer falha aqui e chave corrompida
        logger.warning("[renovacao] Falha ao decriptar a chave de ativacao: %s", erro)
        raise _erro(
            "CHAVE_CORROMPIDA",
            "A chave de ativacao desta maquina nao pode ser lida.",
            status.HTTP_403_FORBIDDEN,
        ) from erro

    return chave, hwid


# ===========================================================================
# Chamada HTTP
# ===========================================================================

def _chamar(metodo: str, url: str, **kwargs) -> dict[str, Any]:
    """Chama a API StartBig traduzindo as falhas em erro de negocio.

    A distincao que importa: 404 e 501 significam "a API de cobranca ainda nao
    subiu" -- estado NORMAL enquanto a VPS nao recebeu o deploy, e a tela mostra
    "indisponivel" em vez de erro. Falha de rede e outra coisa: a loja esta sem
    internet, e ai a mensagem tem que dizer isso.
    """
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resposta = client.request(metodo, url, **kwargs)
    except (httpx.ConnectError, httpx.TimeoutException) as erro:
        logger.warning("[renovacao] Sem conexao com a API StartBig: %s", erro)
        raise _erro(
            "SEM_CONEXAO",
            "Sem conexao com a internet. A renovacao precisa de internet para ser feita.",
        ) from erro
    except httpx.RequestError as erro:
        logger.warning("[renovacao] Falha de rede: %s", erro)
        raise _erro("SEM_CONEXAO", "Nao foi possivel falar com o servidor da StartBig.") from erro

    if resposta.status_code in (404, 501):
        logger.info("[renovacao] API de cobranca ainda nao disponivel (%d).", resposta.status_code)
        raise _erro(INDISPONIVEL, "A renovacao pelo sistema ainda nao esta disponivel.")

    if resposta.status_code >= 400:
        corpo: dict[str, Any] = {}
        try:
            corpo = resposta.json()
        except ValueError:
            pass
        codigo = corpo.get("codigo") or corpo.get("code") or "ERRO_RENOVACAO"
        mensagem = (
            corpo.get("mensagem")
            or corpo.get("message")
            or "Nao foi possivel concluir a renovacao."
        )
        logger.warning("[renovacao] %s respondeu %d: %s", url, resposta.status_code, resposta.text[:300])
        raise _erro(codigo, mensagem, status.HTTP_400_BAD_REQUEST)

    try:
        return resposta.json()
    except ValueError as erro:
        raise _erro("ERRO_RENOVACAO", "Resposta invalida do servidor da StartBig.") from erro


# ===========================================================================
# Traducao camelCase -> snake_case
# ===========================================================================
# Os nomes abaixo seguem o contrato escrito em
# docs/renovacao-assinatura-contrato-web.md. Cada campo tem um segundo nome
# aceito porque o relatorio da API descreve os mesmos dados com outra palavra
# em dois pontos ("planos"/"periodos"). Aceitar os dois evita que a tela morra
# por causa de um sinonimo -- e o dia que a nuvem se decidir, some o alias.

def _primeiro(dados: dict[str, Any], *nomes: str, padrao: Any = None) -> Any:
    for nome in nomes:
        if dados.get(nome) is not None:
            return dados[nome]
    return padrao


def _para_periodo(dados: dict[str, Any]) -> RenovacaoPeriodoRead:
    return RenovacaoPeriodoRead(
        codigo=str(_primeiro(dados, "codigo", "code", padrao="")),
        nome=str(_primeiro(dados, "nome", "name", padrao="")),
        valor_centavos=int(_primeiro(dados, "valorCentavos", "valor_centavos", padrao=0)),
        dias=_primeiro(dados, "dias", "days"),
        # A API manda `meses`; `dias` nunca vem. Sem ler os dois, a tela mostrava
        # o preco sem dizer o que se compra com ele.
        meses=_primeiro(dados, "meses", "months"),
        desconto=_primeiro(dados, "desconto", "discount"),
        metodos=[str(m).upper() for m in (_primeiro(dados, "metodos", "methods", padrao=[]) or [])],
    )


def _para_cobranca(dados: dict[str, Any]) -> CobrancaRead:
    return CobrancaRead(
        cobranca_id=str(_primeiro(dados, "cobrancaId", "cobranca_id", "id", padrao="")),
        metodo=str(_primeiro(dados, "metodo", "method", padrao="PIX")).upper(),
        valor_centavos=int(_primeiro(dados, "valorCentavos", "valor_centavos", padrao=0)),
        descricao=_primeiro(dados, "descricao", "description"),
        expira_em=_primeiro(dados, "expiraEm", "expira_em"),
        pix_copia_e_cola=_primeiro(dados, "pixCopiaECola", "pix_copia_e_cola", "payload"),
        qr_code_base64=_primeiro(dados, "qrCodeBase64", "qr_code_base64", "encodedImage"),
        url_checkout=_primeiro(dados, "url", "urlCheckout", "checkoutUrl"),
    )


# ===========================================================================
# Periodos disponiveis
# ===========================================================================

def listar_periodos(db: Session) -> RenovacaoPlanosRead:
    """Periodos que esta licenca pode comprar, com preco vindo do servidor.

    Preco NUNCA e decidido aqui. O ERP nao manda valor em requisicao nenhuma --
    ele pergunta e mostra.

    Indisponibilidade nao levanta erro: devolve `disponivel=False` com o motivo,
    porque "a cobranca ainda nao subiu" e um estado esperado, nao uma falha.
    """
    if _modo_simulado():
        return RenovacaoPlanosRead(
            disponivel=True,
            periodos=[
                RenovacaoPeriodoRead(
                    codigo="MENSAL", nome="Mensal (simulado)",
                    valor_centavos=8990, dias=30, metodos=["PIX", "CARTAO"],
                ),
                RenovacaoPeriodoRead(
                    codigo="ANUAL", nome="Anual (simulado)",
                    valor_centavos=89900, dias=365, metodos=["PIX", "CARTAO"],
                ),
            ],
        )

    chave, hwid = _credenciais(db)

    try:
        dados = _chamar("POST", API_PLANOS_URL, json={"chave": chave, "hwid": hwid})
    except HTTPException as erro:
        detalhe = erro.detail if isinstance(erro.detail, dict) else {}
        codigo = detalhe.get("codigo", "ERRO_RENOVACAO")
        # Só a indisponibilidade e a falta de internet viram "tela calma". Erro
        # de licenca (bloqueada, chave corrompida) precisa subir e ser dito.
        if codigo in (INDISPONIVEL, "SEM_CONEXAO"):
            return RenovacaoPlanosRead(
                disponivel=False,
                periodos=[],
                motivo=detalhe.get("mensagem"),
            )
        raise

    # ARMADILHA DE NOME: a API chama de "planos" a lista de PERIODOS
    # (mensal/trimestral/anual), e guarda o plano de verdade -- "Plano Start" --
    # num campo `plano`, no singular. Sao coisas diferentes: o plano diz quantos
    # computadores a loja pode usar; o periodo diz por quanto tempo se paga.
    crus = _primeiro(dados, "periodos", "planos", "periods", padrao=[]) or []
    periodos = [_para_periodo(item) for item in crus]

    # Quantos PCs o plano permite vem da licenca LOCAL, nao da API: o numero ja
    # esta gravado aqui desde o cadastro, e pedi-lo de novo seria uma ida a rede
    # para buscar o que a maquina ja sabe.
    licenca = licenca_crud.get_licenca(db)

    return RenovacaoPlanosRead(
        disponivel=bool(periodos),
        periodos=periodos,
        plano=_primeiro(dados, "plano", "planoNome"),
        limite_terminais=getattr(licenca, "limite", None),
    )


# ===========================================================================
# Cobranca
# ===========================================================================

def criar_cobranca(db: Session, metodo: str, periodo: str) -> CobrancaRead:
    """Pede a cobranca ao servidor. PIX devolve BR Code; cartao devolve URL.

    Idempotencia e responsabilidade do servidor (dois cliques = uma cobranca),
    entao aqui nao ha cache nem trava local: reenviar e seguro por contrato.
    """
    metodo = (metodo or "").strip().upper()
    if metodo not in METODOS_VALIDOS:
        raise _erro(
            "METODO_INVALIDO",
            f"Metodo de pagamento invalido: {metodo!r}.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    if _modo_simulado():
        return _criar_cobranca_simulada(metodo, periodo)

    chave, hwid = _credenciais(db)
    dados = _chamar(
        "POST",
        API_COBRANCA_URL,
        json={"chave": chave, "hwid": hwid, "metodo": metodo, "periodo": periodo},
    )
    return _para_cobranca(dados)


def _criar_cobranca_simulada(metodo: str, periodo: str) -> CobrancaRead:
    cobranca_id = f"sim-{metodo.lower()}-{periodo.lower()}-{int(datetime.now().timestamp())}"
    _COBRANCAS_SIMULADAS[cobranca_id] = {
        "criada_em": datetime.now(timezone.utc),
        "metodo": metodo,
    }
    return CobrancaRead(
        cobranca_id=cobranca_id,
        metodo=metodo,
        valor_centavos=8990,
        descricao="StartBig — renovacao (simulada)",
        expira_em=datetime.now(timezone.utc) + timedelta(minutes=30),
        pix_copia_e_cola=_PIX_SIMULADO if metodo == "PIX" else None,
        url_checkout="https://startbig.com.br/#planos" if metodo == "CARTAO" else None,
    )


def consultar_cobranca(db: Session, cobranca_id: str) -> CobrancaStatusRead:
    """Status da cobranca. Chamado a cada poucos segundos com a tela aberta.

    Quando o servidor diz PAGA, este backend JA revalida a licenca antes de
    responder -- e so entao `licenca_renovada` vira True. Assim a tela nunca
    canta vitoria antes de o vencimento novo estar gravado no banco da loja.
    """
    if _modo_simulado():
        return _consultar_cobranca_simulada(db, cobranca_id)

    chave, hwid = _credenciais(db)
    dados = _chamar(
        "GET",
        f"{API_COBRANCA_URL}/{cobranca_id}",
        params={"chave": chave, "hwid": hwid},
    )

    situacao = str(_primeiro(dados, "status", padrao="PENDENTE")).upper()
    renovada = revalidar_agora(db) if situacao == "PAGA" else False

    return CobrancaStatusRead(
        cobranca_id=str(_primeiro(dados, "cobrancaId", "cobranca_id", "id", padrao=cobranca_id)),
        status=situacao,
        pago_em=_primeiro(dados, "pagoEm", "pago_em"),
        data_vencimento=_primeiro(dados, "dataVencimento", "data_vencimento"),
        licenca_renovada=renovada,
    )


def _consultar_cobranca_simulada(db: Session, cobranca_id: str) -> CobrancaStatusRead:
    registro = _COBRANCAS_SIMULADAS.get(cobranca_id)
    if not registro:
        return CobrancaStatusRead(cobranca_id=cobranca_id, status="EXPIRADA")

    idade = (datetime.now(timezone.utc) - registro["criada_em"]).total_seconds()
    if idade < _SEGUNDOS_ATE_PAGAR_SIMULADO:
        return CobrancaStatusRead(cobranca_id=cobranca_id, status="PENDENTE")

    # No simulado a licenca NAO e estendida: quem estende e o servidor, e forjar
    # isso aqui seria ensinar o codigo a fazer o que a invariante proibe.
    return CobrancaStatusRead(
        cobranca_id=cobranca_id,
        status="PAGA",
        pago_em=registro["criada_em"] + timedelta(seconds=_SEGUNDOS_ATE_PAGAR_SIMULADO),
        licenca_renovada=False,
    )


# ===========================================================================
# Revalidacao forcada
# ===========================================================================

def revalidar_agora(db: Session) -> bool:
    """Pede a validacao ao servidor AGORA, sem esperar o loop de uma hora.

    Chamada logo depois de o pagamento ser confirmado: e ela que traz a
    `dataVencimento` nova e destrava a loja. O ERP nao calcula data nenhuma --
    grava o que o servidor assinou.

    Returns:
        True se o vencimento gravado mudou (ou seja: renovou de fato).

    Nunca levanta: se a rede falhar, o loop de background tenta de novo mais
    tarde e o pior caso e a tela demorar a dizer que renovou.
    """
    licenca = licenca_crud.get_licenca(db)
    if not licenca:
        return False

    vencimento_anterior = licenca.data_vencimento
    hwid = obter_hwid()

    try:
        chave = decriptar_valor(licenca.chave_ativacao, hwid)
    except Exception:  # noqa: BLE001
        logger.warning("[renovacao] Revalidacao abortada: chave de ativacao ilegivel.")
        return False

    payload = ValidarPayload(chave=chave, hwid=hwid)

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resposta = client.post(API_VALIDAR_URL, json=payload.model_dump())
    except httpx.RequestError as erro:
        logger.warning("[renovacao] Revalidacao falhou (%s): %s", type(erro).__name__, erro)
        return False

    if resposta.status_code not in (200, 201):
        logger.warning("[renovacao] Revalidacao: servidor respondeu %d", resposta.status_code)
        return False

    dados = resposta.json()
    if not dados.get("valida", False):
        logger.info("[renovacao] Licenca ainda nao valida — status=%s", dados.get("status"))
        return False

    try:
        validada = ValidarResponse(**dados)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[renovacao] Resposta de validacao fora do contrato: %s", erro)
        return False

    licenca.token = validada.token
    licenca.proxima_validacao = validada.proximaValidacaoEm
    licenca.ultima_sinc = validada.ultimaSincronizacao
    licenca.data_vencimento = validada.dataVencimento
    licenca.grace_period = validada.gracePeriodDias
    # Mesmo cuidado do caminho online: a carencia so vale offline se estiver
    # guardada. Pagar no cartao e a internet cair no dia seguinte nao pode
    # travar a loja dentro dos dias de folga que o servidor concedeu.
    licenca.em_carencia = validada.emCarencia
    licenca.data_limite_carencia = validada.dataLimiteCarencia
    # Quem acabou de pagar nao pode continuar preso no bloqueio que a
    # inadimplencia deixou ligado -- e ele nao se apaga sozinho.
    _limpar_bloqueio(licenca)

    licenca_crud.update_licenca(db, licenca)
    db.commit()

    renovou = _mudou_o_vencimento(vencimento_anterior, validada.dataVencimento)
    logger.info(
        "[renovacao] Licenca revalidada. Vencimento: %s (mudou=%s)",
        validada.dataVencimento, renovou,
    )
    return renovou


def _mudou_o_vencimento(antes: Optional[datetime], depois: Optional[datetime]) -> bool:
    """Compara os dois vencimentos com o mesmo fuso.

    O banco guarda datas ingenuas (sem tzinfo) e o servidor manda com fuso;
    comparar cru levanta TypeError e derrubaria a consulta de status bem no
    momento em que o cliente acabou de pagar.
    """
    if antes is None or depois is None:
        return depois is not None

    if antes.tzinfo is None:
        antes = antes.replace(tzinfo=timezone.utc)
    if depois.tzinfo is None:
        depois = depois.replace(tzinfo=timezone.utc)

    return depois > antes
