# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/http/client.py
# DESCRIÇÃO: Protocol (interface) do client fiscal e tipo de retorno padrão.
#
# Qualquer implementação (mock, StartBig API, etc.) deve seguir este contrato.
# ---------------------------------------------------------------------------

from typing import NotRequired, Optional, Protocol, TypedDict


class EmissaoResultado(TypedDict):
    """Retorno padronizado de qualquer operação de emissão/consulta/cancelamento."""

    status: str  # "autorizado" | "processando" | "erro" | "cancelado"
    chave_acesso: Optional[str]
    protocolo: Optional[str]
    numero: Optional[int]
    serie: Optional[int]
    url_pdf: Optional[str]
    url_xml: Optional[str]
    codigo_sefaz: Optional[int]
    mensagem_sefaz: Optional[str]

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


class FiscalClientProtocol(Protocol):
    """Contrato que todo client de emissão fiscal deve implementar."""

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

    def consultar_nfe(self, ref: str) -> EmissaoResultado:
        """Consulta status de uma NF-e já enviada."""
        ...

    def cancelar_nfe(self, ref: str, justificativa: str) -> EmissaoResultado:
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
