# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/http/client.py
# DESCRIÇÃO: Protocol (interface) do client fiscal e tipo de retorno padrão.
#
# Qualquer implementação (mock, StartBig API, etc.) deve seguir este contrato.
# ---------------------------------------------------------------------------

from typing import Optional, Protocol, TypedDict


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
