# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/http/client.py
# DESCRIÇÃO: Protocol (interface) do client fiscal e tipo de retorno padrão.
#
# Qualquer implementação (mock, StartBig API, etc.) deve seguir este contrato.
# ---------------------------------------------------------------------------

from typing import NotRequired, Optional, Protocol, TypedDict


# ---------------------------------------------------------------------------
# Vocabulário de `EmissaoResultado.status`
# ---------------------------------------------------------------------------
# Existe como constante, e não como literal espalhado, porque estes valores são
# escritos pelo client e lidos por `_aplicar_resultado` — dois arquivos que
# precisam concordar. Enquanto eram strings soltas, um teste conferia o literal
# `"erro"` embaixo de uma docstring que dizia "nada foi para a SEFAZ": a
# intenção e a codificação viviam separadas, e só a codificação estava travada.
RESULTADO_AUTORIZADO = "autorizado"
RESULTADO_PROCESSANDO = "processando"
RESULTADO_CANCELADO = "cancelado"

# A SEFAZ respondeu "não".
RESULTADO_ERRO = "erro"

# Recusa ANTES da SEFAZ (4xx na emissão). Nada foi transmitido: não há
# protocolo, não há código de rejeição, e o número reservado não foi queimado.
RESULTADO_NAO_TRANSMITIDO = "nao_transmitido"

# 404 na consulta. Sozinho NÃO conclui nada — ver `CODIGO_NOTA_INEXISTENTE`.
RESULTADO_NAO_ENCONTRADO = "nao_encontrado"


# ---------------------------------------------------------------------------
# Códigos que a plataforma põe no corpo do 404
# ---------------------------------------------------------------------------
# Três situações muito diferentes chegavam como o mesmo 404, e uma delas produz
# nota duplicada se for lida errado:
#
#   NOTA_NAO_ENCONTRADA_NA_EMISSORA -> a nota não chegou lá. Conclusivo.
#   LICENCA_NAO_ENCONTRADA          -> pré-voo da plataforma. Não diz nada
#   SEM_CONFIGURACAO_FISCAL            sobre a nota.
#
# Só o primeiro autoriza marcar o documento como não transmitido. Os outros
# dois, e a AUSÊNCIA de código (plataforma antiga, ainda não atualizada),
# deixam o status intocado — que é o padrão seguro durante a janela em que uma
# loja já atualizou e a outra não.
CODIGO_NOTA_INEXISTENTE = "NOTA_NAO_ENCONTRADA_NA_EMISSORA"


class EmissaoResultado(TypedDict):
    """Retorno padronizado de qualquer operação de emissão/consulta/cancelamento."""

    status: str  # ver as constantes RESULTADO_* acima
    chave_acesso: Optional[str]
    protocolo: Optional[str]
    numero: Optional[int]
    serie: Optional[int]
    url_pdf: Optional[str]
    url_xml: Optional[str]
    codigo_sefaz: Optional[int]
    mensagem_sefaz: Optional[str]

    # Código estável do corpo do erro da plataforma (ver CODIGO_NOTA_INEXISTENTE).
    # NotRequired: só a consulta o preenche, e só quando a plataforma o manda.
    codigo: NotRequired[Optional[str]]

    # --- Só na NFC-e (modelo 65) ---
    # NotRequired porque a NF-e não devolve nenhum dos três, e exigi-los
    # quebraria todo `_parse_response` que já existe.
    #
    # `qrcode` é o texto que vai no QR do cupom — quem o monta é o provedor,
    # que tem o CSC e a regra de hash da UF. `url_consulta` é o endereço da
    # SEFAZ impresso abaixo do código, e `valor_tributos` é o total aproximado
    # da Lei 12.741/2012 (IBPT), obrigatório no cupom.
    qrcode: NotRequired[Optional[str]]
    url_consulta: NotRequired[Optional[str]]
    valor_tributos: NotRequired[Optional[float]]


class EnvioCertificadoResultado(TypedDict):
    """Retorno do envio do certificado A1 para a plataforma.

    `aceito=False` com `indisponivel=True` significa "a plataforma ainda não
    recebe certificado" — é diferente de "recusou o certificado". O primeiro é
    uma funcionalidade que falta do outro lado; o segundo é problema do arquivo
    ou do CNPJ, e o lojista precisa saber qual dos dois aconteceu.
    """

    aceito: bool
    indisponivel: bool
    mensagem: Optional[str]
    cnpj: NotRequired[Optional[str]]
    valido_ate: NotRequired[Optional[str]]


class FiscalClientProtocol(Protocol):
    """Contrato que todo client de emissão fiscal deve implementar."""

    def enviar_certificado(
        self, arquivo_base64: str, senha: str
    ) -> "EnvioCertificadoResultado":
        """
        Entrega o certificado A1 à plataforma, que o cadastra na emissora.

        NUNCA levanta por indisponibilidade: quem chama precisa distinguir
        "ainda não dá" de "recusado", e uma exceção apaga essa diferença.
        """
        ...

    def emitir_nfe(
        self, ref: str, payload: dict, idempotency_key: Optional[str] = None
    ) -> EmissaoResultado:
        """
        Envia NF-e para emissão. Retorna resultado imediato ou 'processando'.

        `idempotency_key` viaja em X-Idempotency-Key: a retentativa após
        timeout reusa a chave e a API intermediária reconhece a mesma emissão
        em vez de criar uma segunda nota.
        """
        ...

    def emitir_nfce(
        self, ref: str, payload: dict, idempotency_key: Optional[str] = None
    ) -> EmissaoResultado:
        """
        Envia NFC-e (modelo 65) para emissão SÍNCRONA.

        Ao contrário da NF-e, aqui não há 'processando' aceitável: o cliente
        está no balcão esperando o cupom. O resultado vem na própria resposta,
        e o QR Code montado pelo provedor volta em `qrcode`.

        `idempotency_key` tem o mesmo papel da NF-e — e pesa mais no PDV, onde
        o operador reaperta o botão assim que a rede demora.
        """
        ...

    def baixar_xml(self, caminho: str) -> Optional[str]:
        """Baixa o XML autorizado e devolve o conteúdo, ou None se falhar.

        Existe por causa do `vTotTrib`: a Focus calcula o valor aproximado dos
        tributos (Lei 12.741/2012) pela tabela IBPT, mas só o grava no XML —
        o JSON da emissão não o devolve, e o DANFE NFC-e é obrigado a imprimir
        esse valor.

        `caminho` pode ser relativo (como a Focus devolve em
        `caminho_xml_nota_fiscal`) ou uma URL completa.

        NUNCA levanta: falhar aqui não pode derrubar uma emissão que a SEFAZ
        já autorizou.
        """
        ...

    def consultar_config(self) -> dict:
        """Config fiscal como a plataforma a enxerga. {} = não foi possível saber."""
        ...

    def consultar_nfe(
        self, ref: str, tipo_documento: str = "NFE"
    ) -> EmissaoResultado:
        """Consulta status de uma NF-e já enviada."""
        ...

    def cancelar_nfe(
        self, ref: str, justificativa: str, tipo_documento: str = "NFE"
    ) -> EmissaoResultado:
        """Solicita cancelamento de NF-e autorizada."""
        ...

    def inutilizar_numeracao(
        self, ref: str, payload: dict, idempotency_key: Optional[str] = None
    ) -> EmissaoResultado:
        """
        Declara à SEFAZ que uma faixa de numeração não foi usada.

        Necessário sempre que um número é reservado e a nota não chega a ser
        autorizada — ver services/fiscal/inutilizacao.py.
        """
        ...
