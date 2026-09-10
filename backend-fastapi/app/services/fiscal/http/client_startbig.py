# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/http/client_startbig.py
# DESCRIÇÃO: Client real que chama a API Online StartBig para emissão fiscal.
# ---------------------------------------------------------------------------

import logging
import httpx
from typing import Optional

from .client import (
    CODIGO_NOTA_INEXISTENTE,
    EmissaoResultado,
    EnvioCertificadoResultado,
    RESULTADO_NAO_ENCONTRADO,
    RESULTADO_NAO_TRANSMITIDO,
)

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
            # O status CRU da emissora, ao lado do normalizado.
            #
            # `denegado` e `erro_autorizacao` viram os dois "erro" no campo
            # acima, e sao coisas diferentes: denegada e decisao da SEFAZ sobre
            # o contribuinte, e reenviar nao adianta. Sem isto o ERP nao tem
            # como separar as duas.
            "status_focus": response_data.get("status_focus"),
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

    def _recusa_local(self, resposta) -> EmissaoResultado:
        """Recusa que aconteceu ANTES de a nota chegar na SEFAZ.

        Um 4xx da plataforma -- Zod, cota, CNPJ divergente, schema recusado pela
        Focus -- significa que nada foi transmitido. Isso NAO e rejeicao: a
        SEFAZ nao viu a nota, nao ha protocolo, nao ha codigo de rejeicao e o
        numero reservado nao foi queimado.

        O codigo antigo devolvia `{"status": "erro"}` para este caso, e `erro`
        vira REJEITADA em `_aplicar_resultado`. Era assim que uma nota que nunca
        saiu do predio virava "rejeitada pela SEFAZ" na tela -- misturada, na
        mesma lista, com as que de fato foram recusadas la.

        O discriminador e o `codigo_sefaz`: se a SEFAZ respondeu, existe numero.
        Quando ele vier, respeitamos o que a resposta diz e nao chutamos.
        """
        try:
            resultado = self._parse_response(resposta.json())
        except Exception:
            return {
                "status": RESULTADO_NAO_TRANSMITIDO,
                "mensagem_sefaz": (
                    f"A plataforma recusou a emissao (HTTP {resposta.status_code}) "
                    f"antes de enviar a SEFAZ."
                ),
            }

        if resultado.get("codigo_sefaz") is not None:
            return resultado

        resultado["status"] = RESULTADO_NAO_TRANSMITIDO
        return resultado

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
            # rota inexistente). Nada foi para a SEFAZ -- e por isso NAO e
            # rejeicao. Ver `_recusa_local`.
            return self._recusa_local(exc.response)
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
            # 4xx: recusa ANTES de transmitir (CNPJ divergente, sem config,
            # rota inexistente). Nada foi para a SEFAZ -- e por isso NAO e
            # rejeicao. Ver `_recusa_local`.
            return self._recusa_local(exc.response)
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

    def enviar_certificado(
        self, arquivo_base64: str, senha: str
    ) -> EnvioCertificadoResultado:
        """
        Entrega o certificado A1 à plataforma, que o cadastra na emissora.

        É a plataforma quem tem a conta na Focus e o `POST /v2/empresas` com
        `arquivo_certificado_base64` — o ERP nunca fala com a emissora direto.

        ROTA AINDA NÃO EXISTE do outro lado (ver docs/fiscal-onboarding-plano.md
        §4.1). Enquanto não existir, o 404 volta como `indisponivel=True`, e não
        como recusa: quem chama grava o certificado como validado localmente e
        diz a verdade na tela. Confundir "ainda não dá" com "recusado" mandaria
        o lojista procurar defeito no arquivo dele.

        Nem a senha nem o arquivo entram em log -- `_CHAVES_SENSIVEIS` ja
        censura, e aqui nem chegamos a montar corpo para o logger.
        """
        url = f"{self.base_url}/erp/fiscal/certificado"
        corpo = {"arquivo_base64": arquivo_base64, "senha": senha}

        try:
            with httpx.Client(timeout=60.0) as client:
                resposta = client.post(url, json=corpo, headers=self.headers)
        except Exception as exc:
            logger.warning("[FISCAL] Sem resposta ao enviar certificado: %s", exc)
            return {
                "aceito": False,
                "indisponivel": True,
                "mensagem": "Não foi possível falar com a plataforma de emissão.",
            }

        if resposta.status_code in (404, 405, 501):
            logger.info(
                "[FISCAL] A plataforma ainda nao recebe certificado (HTTP %s).",
                resposta.status_code,
            )
            return {
                "aceito": False,
                "indisponivel": True,
                "mensagem": (
                    "A plataforma de emissão ainda não recebe o certificado. "
                    "Ele ficou validado neste computador."
                ),
            }

        if resposta.status_code >= 400:
            logger.error(
                "[FISCAL] Certificado recusado: %s - %s",
                resposta.status_code, _resposta_para_log(resposta),
            )
            detalhe = None
            try:
                corpo_erro = resposta.json()
                detalhe = corpo_erro.get("mensagem") or corpo_erro.get("message")
            except Exception:
                pass
            return {
                "aceito": False,
                "indisponivel": False,
                "mensagem": detalhe or (
                    f"A plataforma recusou o certificado (HTTP {resposta.status_code})."
                ),
            }

        try:
            dados = resposta.json() or {}
        except Exception:
            dados = {}

        return {
            "aceito": True,
            "indisponivel": False,
            "mensagem": dados.get("mensagem"),
            "cnpj": dados.get("cnpj"),
            "valido_ate": dados.get("valido_ate") or dados.get("certificado_valido_ate"),
        }

    def consultar_config(self) -> dict:
        """
        Configuração fiscal desta licença, como a PLATAFORMA a enxerga.

        É a fonte de verdade para coisas que não moram aqui: o ambiente
        (homologação × produção é decidido lá, por cliente), se o token da Focus
        foi preenchido, se o CSC está cadastrado e o status do certificado.

        Não exige módulo do lado de lá, de propósito: é justamente quem ainda
        não emite que precisa desta resposta.

        Devolve {} quando não dá para saber. Quem chama trata isso como "não
        sei", nunca como "não configurado" -- derrubar uma emissão por causa de
        um diagnóstico indisponível seria trocar a nota por um detalhe.
        """
        url = f"{self.base_url}/erp/fiscal/config"
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json() or {}
        except Exception as exc:
            logger.warning("[FISCAL] Não foi possível ler a config da plataforma: %s", exc)
            return {}

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
            if exc.response.status_code == 404:
                # Desfecho PROPRIO, nao "erro desconhecido" -- e, sobretudo,
                # nao rejeicao.
                #
                # Tres situacoes chegam aqui como o mesmo 404: a emissora
                # dizendo "essa ref nao existe", e a plataforma dizendo
                # "licenca nao encontrada" ou "empresa sem configuracao
                # fiscal". So a primeira afirma algo sobre a NOTA. O `codigo`
                # do corpo e o que separa as tres; quem decide e
                # `_aplicar_resultado`.
                corpo = {}
                try:
                    corpo = exc.response.json() or {}
                except Exception:
                    pass
                return {
                    "status": RESULTADO_NAO_ENCONTRADO,
                    "codigo": corpo.get("codigo"),
                    "mensagem_sefaz": corpo.get("message") or corpo.get("mensagem") or (
                        "Esta nota nao consta na emissora."
                    ),
                }
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
            # `ano` NÃO está na doc publicada da Focus, que lista cinco campos
            # obrigatórios e nenhum opcional. Mandamos assim mesmo porque o
            # custo é zero e o risco de não mandar não é: sem ele, quem decide o
            # ano é a Focus, e quase certamente será o ANO CORRENTE -- então
            # inutilizar em janeiro uma faixa aberta em dezembro iria para o ano
            # errado. Se a Focus ignorar, nada muda; se honrar, a faixa vai para
            # o ano certo.
            #
            # ENQUANTO NINGUÉM CONFIRMAR com o suporte da Focus que ela honra:
            # inutilize a faixa no mesmo ano em que ela foi aberta.
            "ano": payload.get("ano"),
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
