# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/http/client_startbig.py
# DESCRIÇÃO: Client real que chama a API Online StartBig para emissão fiscal.
# ---------------------------------------------------------------------------

import logging
import httpx
from typing import Optional

from .client import EmissaoResultado

logger = logging.getLogger(__name__)


class EmissaoIncertaError(Exception):
    """A emissao pode ter acontecido, e nao sabemos.

    Existe para separar dois desfechos que o codigo antigo confundia:

      - A SEFAZ respondeu NAO  -> rejeicao. Vira REJEITADA, e reemitir e seguro.
      - Nao houve resposta     -> INCERTEZA. A nota pode estar autorizada.

    O client ANTIGO capturava `Exception` e devolvia {"status": "erro"} para os
    dois casos. Como `erro` vira REJEITADA em `_aplicar_resultado`, e REJEITADA
    e reemitivel, um timeout produzia esta sequencia:

        timeout (a SEFAZ demora) -> "erro" -> REJEITADA -> operador reemite
        -> reemissao usa ref NOVA -> a idempotencia da plataforma e POR REF
        -> nota DUPLICADA, as duas autorizadas, no mesmo CNPJ

    A protecao contra isso ja existia em emissao.py (status INDETERMINADA), mas
    era codigo morto: nunca chegava excecao ate la. Levantar esta e o que a
    religa.
    """


# Chaves cujo valor nunca pode ir para o log em disco do cliente.
_CHAVES_SENSIVEIS = (
    "password", "senha", "token", "secret", "certificado", "csc",
    "authorization", "cpf", "cnpj", "chave_pix",
)


def _ofuscar(valor, _nivel: int = 0):
    """
    Remove valores sensíveis antes de registrar em disco.

    O log fica na máquina do cliente, sem proteção. Um corpo de resposta da
    API costuma ecoar o documento inteiro — CPF, endereço e valores do
    destinatário — e às vezes credenciais.
    """
    if _nivel > 6:
        return "..."
    if isinstance(valor, dict):
        return {
            chave: (
                "***"
                if any(s in str(chave).lower() for s in _CHAVES_SENSIVEIS)
                else _ofuscar(item, _nivel + 1)
            )
            for chave, item in valor.items()
        }
    if isinstance(valor, (list, tuple)):
        return [_ofuscar(item, _nivel + 1) for item in valor[:20]]
    if isinstance(valor, str) and len(valor) > 200:
        return valor[:200] + "…"
    return valor


def _resposta_para_log(response) -> str:
    """Corpo da resposta pronto para log — ofuscado quando for JSON."""
    try:
        return str(_ofuscar(response.json()))[:600]
    except Exception:
        return f"<corpo nao-JSON, {len(response.content or b'')} bytes>"


class FiscalClientStartBig:
    """
    Client que se comunica com a API Online StartBig para emissão fiscal.
    """

    def __init__(self, ambiente: int = 1, token: str = ""):
        self.ambiente = ambiente
        self.token = token
        self.base_url = "https://api.startbig.com.br"

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }


    @staticmethod
    def _segmento(tipo_documento: str) -> str:
        """Caminho da API para o modelo do documento.

        A plataforma tem famílias SEPARADAS -- /erp/fiscal/nfe/... e
        /erp/fiscal/nfce/... --, com módulo e cota próprios cada uma. Consultar
        um cupom no caminho da NF-e não acha a referência.
        """
        return "nfce" if (tipo_documento or "").upper() == "NFCE" else "nfe"

    @staticmethod
    def _primeiro(dados: dict, *chaves: str):
        """Primeiro valor presente entre as chaves, na ordem dada.

        A API StartBig é uma INTERMEDIÁRIA da Focus NFe, e as duas nem sempre
        usam o mesmo nome: a Focus devolve `qrcode_url`, `numero_protocolo` e
        `caminho_xml_nota_fiscal`, enquanto a intermediária pode normalizar
        para `qrcode`, `protocolo` e `url_xml`. Aceitar as duas grafias evita
        que uma diferença de vocabulário faça o cupom sair sem QR Code — e o
        cupom sem QR Code não vale.
        """
        for chave in chaves:
            valor = dados.get(chave)
            if valor not in (None, ""):
                return valor
        return None

    def _parse_response(self, response_data: dict) -> EmissaoResultado:
        """Converte a resposta padrão da API para EmissaoResultado."""
        mensagem = response_data.get("mensagem_sefaz")
        if not mensagem:
            msg_api = response_data.get("message")
            if isinstance(msg_api, list):
                mensagem = " | ".join(str(m) for m in msg_api)
            elif msg_api:
                mensagem = str(msg_api)
            else:
                mensagem = "Erro desconhecido"

        return {
            "status": response_data.get("status", "erro"),
            "chave_acesso": self._primeiro(response_data, "chave_acesso", "chave_nfe"),
            "protocolo": self._primeiro(response_data, "protocolo", "numero_protocolo"),
            "numero": response_data.get("numero"),
            "serie": response_data.get("serie"),
            "url_pdf": self._primeiro(response_data, "url_pdf", "caminho_danfe"),
            "url_xml": self._primeiro(
                response_data, "url_xml", "caminho_xml_nota_fiscal",
            ),
            "codigo_sefaz": self._primeiro(response_data, "codigo_sefaz", "status_sefaz"),
            "mensagem_sefaz": mensagem,
            # Campos de NFC-e. Vêm None na NF-e, que não os devolve.
            "qrcode": self._primeiro(response_data, "qrcode", "qrcode_url"),
            "url_consulta": self._primeiro(
                response_data, "url_consulta", "url_consulta_nf",
            ),
            # A Focus CALCULA o vTotTrib (tabela IBPT por NCM) mas não o
            # devolve no JSON — só no XML. Por isso quase sempre vem None aqui
            # e quem o busca é `obter_valor_tributos_do_xml`.
            "valor_tributos": self._primeiro(
                response_data, "valor_tributos", "valor_total_tributos",
            ),
        }

    def emitir_nfe(
        self, ref: str, payload: dict, idempotency_key: Optional[str] = None
    ) -> EmissaoResultado:
        url = f"{self.base_url}/erp/fiscal/nfe/emitir"
        body = {
            "ref": ref,
            "payload": payload
        }
        headers = dict(self.headers)
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=body, headers=headers)
                response.raise_for_status()
                return self._parse_response(response.json())
        except httpx.HTTPStatusError as exc:
            logger.error("[FISCAL] Erro HTTP ao emitir NF-e: %s - %s",
                         exc.response.status_code, _resposta_para_log(exc.response))
            # 5xx: o servidor pode ter processado antes de falhar. Incerto.
            if exc.response.status_code >= 500:
                raise EmissaoIncertaError(
                    f"Servidor respondeu {exc.response.status_code} ao emitir."
                ) from exc
            # 4xx: recusa ANTES de transmitir (CNPJ divergente, sem config,
            # rota inexistente). Nada foi para a SEFAZ.
            try:
                return self._parse_response(exc.response.json())
            except Exception:
                return {
                    "status": "erro",
                    "mensagem_sefaz": (
                        f"A API recusou a emissão (HTTP {exc.response.status_code}) "
                        f"antes de enviar à SEFAZ."
                    ),
                }
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            # Sem resposta: a nota PODE estar autorizada. Ver EmissaoIncertaError.
            logger.error("[FISCAL] Sem resposta ao emitir NF-e: %s", exc)
            raise EmissaoIncertaError(str(exc)) from exc
        except Exception as exc:
            logger.error("[FISCAL] Falha na requisição de emissão: %s", exc)
            raise EmissaoIncertaError(str(exc)) from exc

    def emitir_nfce(
        self, ref: str, payload: dict, idempotency_key: Optional[str] = None
    ) -> EmissaoResultado:
        """Emite NFC-e. Mesmo contrato da NF-e, outro endpoint e sem polling."""
        url = f"{self.base_url}/erp/fiscal/nfce/emitir"
        body = {
            "ref": ref,
            "payload": payload
        }
        headers = dict(self.headers)
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=body, headers=headers)
                response.raise_for_status()
                return self._parse_response(response.json())
        except httpx.HTTPStatusError as exc:
            logger.error("[FISCAL] Erro HTTP ao emitir NFC-e: %s - %s",
                         exc.response.status_code, _resposta_para_log(exc.response))
            if exc.response.status_code >= 500:
                raise EmissaoIncertaError(
                    f"Servidor respondeu {exc.response.status_code} ao emitir NFC-e."
                ) from exc
            try:
                return self._parse_response(exc.response.json())
            except Exception:
                return {
                    "status": "erro",
                    "mensagem_sefaz": (
                        f"A API recusou a emissão (HTTP {exc.response.status_code}) "
                        f"antes de enviar à SEFAZ."
                    ),
                }
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            logger.error("[FISCAL] Sem resposta ao emitir NFC-e: %s", exc)
            raise EmissaoIncertaError(str(exc)) from exc
        except Exception as exc:
            logger.error("[FISCAL] Falha na requisição de emissão de NFC-e: %s", exc)
            raise EmissaoIncertaError(str(exc)) from exc

    def baixar_xml(self, caminho: str) -> Optional[str]:
        """Baixa o XML autorizado. Devolve None em qualquer falha."""
        if not caminho:
            return None

        # A Focus devolve caminho RELATIVO em `caminho_xml_nota_fiscal`
        # (ex.: "/arquivos/.../123-nfe.xml"); a intermediária pode devolver a
        # URL completa. Aceitar os dois evita montar uma URL malformada.
        url = caminho if caminho.startswith("http") else f"{self.base_url}{caminho}"

        try:
            with httpx.Client(timeout=15.0) as client:
                resposta = client.get(url, headers=self.headers)
                resposta.raise_for_status()
                return resposta.text
        except Exception as exc:
            # Só o valor dos tributos depende disto. A nota já está autorizada
            # — derrubar o fluxo aqui seria perder o cupom por um detalhe de
            # impressão.
            logger.warning("[FISCAL] Falha ao baixar XML em %s: %s", url, exc)
            return None

    def consultar_nfe(
        self, ref: str, tipo_documento: str = "NFE"
    ) -> EmissaoResultado:
        url = f"{self.base_url}/erp/fiscal/{self._segmento(tipo_documento)}/consultar"
        params = {"ref": ref}
        
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                return self._parse_response(response.json())
        except httpx.HTTPStatusError as exc:
            logger.error("[FISCAL] Erro HTTP ao consultar NF-e: %s", exc.response.status_code)
            try:
                return self._parse_response(exc.response.json())
            except Exception:
                return {"status": "erro", "mensagem_sefaz": f"Erro {exc.response.status_code} da API"}
        except Exception as exc:
            logger.error("[FISCAL] Falha na requisição de consulta: %s", exc)
            return {"status": "erro", "mensagem_sefaz": str(exc)}

    def cancelar_nfe(
        self, ref: str, justificativa: str, tipo_documento: str = "NFE"
    ) -> EmissaoResultado:
        url = f"{self.base_url}/erp/fiscal/{self._segmento(tipo_documento)}/cancelar"
        body = {
            "ref": ref,
            "justificativa": justificativa
        }
        
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(url, json=body, headers=self.headers)
                response.raise_for_status()
                return self._parse_response(response.json())
        except httpx.HTTPStatusError as exc:
            logger.error("[FISCAL] Erro HTTP ao cancelar NF-e: %s", exc.response.status_code)
            try:
                return self._parse_response(exc.response.json())
            except Exception:
                return {"status": "erro", "mensagem_sefaz": f"Erro {exc.response.status_code} da API"}
        except Exception as exc:
            logger.error("[FISCAL] Falha na requisição de cancelamento: %s", exc)
            return {"status": "erro", "mensagem_sefaz": str(exc)}

    def inutilizar_numeracao(
        self,
        ref: str,
        payload: dict,
        idempotency_key: Optional[str] = None,
        tipo_documento: str = "NFE",
    ) -> EmissaoResultado:
        """
        Inutiliza uma faixa de numeração.

        A plataforma NÃO recebe `ref` aqui -- a Focus identifica a operação pela
        própria faixa --, nem o modelo, que vem da rota. O corpo é PLANO, e não
        {ref, payload} como na emissão.

        `ref` continua na assinatura porque é a nossa chave local de rastreio
        (fica em InutilizacaoFiscal.ref_api) e entra no log.

        Aqui o `X-Idempotency-Key` é a PROTEÇÃO PRINCIPAL: sem ref, é ele que
        impede uma retentativa de queimar uma segunda faixa.
        """
        url = f"{self.base_url}/erp/fiscal/{self._segmento(tipo_documento)}/inutilizar"
        body = {
            "serie": payload.get("serie"),
            "numero_inicial": payload.get("numero_inicial"),
            "numero_final": payload.get("numero_final"),
            "justificativa": payload.get("justificativa"),
        }
        headers = dict(self.headers)
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=body, headers=headers)
                response.raise_for_status()
                return self._parse_response(response.json())
        except httpx.HTTPStatusError as exc:
            logger.error("[FISCAL] Erro HTTP ao inutilizar numeracao: %s", exc.response.status_code)
            if exc.response.status_code >= 500:
                raise EmissaoIncertaError(
                    f"Servidor respondeu {exc.response.status_code} ao inutilizar."
                ) from exc
            try:
                return self._parse_response(exc.response.json())
            except Exception:
                return {
                    "status": "erro",
                    "mensagem_sefaz": (
                        f"A API recusou a inutilização (HTTP {exc.response.status_code})."
                    ),
                }
