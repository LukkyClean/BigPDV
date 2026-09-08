import api from '@/api/axios';
import type { EmissaoPreviewResponse,
  DocumentoFiscalHistorico,
  DocumentoFiscalListRead,
  DocumentoFiscalRead,
  DocumentoFiscalResumo,
  DocumentoFiscalTipo,
  DocumentoFiscalFilters,
  EmissaoNFeRequest,
  EmissaoResponse,
  EmissaoBatchResponse,
  FiscalConfiguracao,
  PendenciasGlobais,
  ResultadoVerificacaoBatch,
  VendaCorrecaoFiscalPayload,
  SugestoesFiscaisResponse,
} from '../types/fiscal.types';
import { TIMEOUT_CONSULTA, TIMEOUT_EMISSAO, TIMEOUT_LOTE } from '../constants/fiscal.constants';

const FISCAL_ENDPOINT = '/fiscal';

export const fiscalService = {
  // --- Existentes ---

  async listarDocumentos(
    filters: DocumentoFiscalFilters = {},
    pagina: number = 1,
  ): Promise<DocumentoFiscalListRead> {
    const params: Partial<DocumentoFiscalFilters & { pagina: number }> = { pagina };
    if (filters.status) params.status = filters.status;
    if (filters.tipo) params.tipo = filters.tipo;
    if (filters.origem) params.origem = filters.origem;
    if (filters.busca) params.busca = filters.busca;
    if (filters.data_inicio) params.data_inicio = filters.data_inicio;
    if (filters.data_fim) params.data_fim = filters.data_fim;

    const { data } = await api.get<DocumentoFiscalListRead>(
      `${FISCAL_ENDPOINT}/documentos`,
      { params },
    );
    return data;
  },

  /** `tipo` restringe os contadores a um modelo (NFE, NFCE, NFSE). */
  async obterResumo(tipo?: DocumentoFiscalTipo): Promise<DocumentoFiscalResumo> {
    const { data } = await api.get<DocumentoFiscalResumo>(
      `${FISCAL_ENDPOINT}/resumo`,
      { params: tipo ? { tipo } : undefined },
    );
    return data;
  },

  async obterPendencias(): Promise<PendenciasGlobais> {
    const { data } = await api.get<PendenciasGlobais>(
      `${FISCAL_ENDPOINT}/pendencias`,
    );
    return data;
  },

  async obterDocumento(id: number): Promise<DocumentoFiscalRead> {
    const { data } = await api.get<DocumentoFiscalRead>(
      `${FISCAL_ENDPOINT}/documentos/${id}`,
    );
    return data;
  },

  async reemitirDocumento(id: number): Promise<DocumentoFiscalRead> {
    const { data } = await api.post<DocumentoFiscalRead>(
      `${FISCAL_ENDPOINT}/documentos/${id}/reemitir`,
      undefined,
      { timeout: TIMEOUT_EMISSAO },
    );
    return data;
  },

  // --- Novos (emissao, consulta, cancelamento) ---

  async previewNfe(payload: EmissaoNFeRequest): Promise<EmissaoPreviewResponse> {
    const { data } = await api.post<EmissaoPreviewResponse>(
      `${FISCAL_ENDPOINT}/preview/nfe`,
      payload,
      { timeout: TIMEOUT_EMISSAO },
    );
    return data;
  },

  async emitirNfe(payload: EmissaoNFeRequest): Promise<EmissaoResponse> {
    const { data } = await api.post<EmissaoResponse>(
      `${FISCAL_ENDPOINT}/emitir/nfe`,
      payload,
      { timeout: TIMEOUT_EMISSAO },
    );
    return data;
  },

  /**
   * Emite NFC-e (modelo 65). Síncrono: a resposta já traz o resultado da
   * SEFAZ, porque o cliente está no balcão esperando o cupom.
   */
  async emitirNfce(payload: EmissaoNFeRequest): Promise<EmissaoResponse> {
    const { data } = await api.post<EmissaoResponse>(
      `${FISCAL_ENDPOINT}/emitir/nfce`,
      payload,
      { timeout: TIMEOUT_EMISSAO },
    );
    return data;
  },

  async emitirTesteNfe(): Promise<EmissaoResponse> {
    const { data } = await api.post<EmissaoResponse>(
      `${FISCAL_ENDPOINT}/emitir/teste/nfe`,
      undefined,
      { timeout: TIMEOUT_EMISSAO },
    );
    return data;
  },

  async consultarDocumento(id: number): Promise<DocumentoFiscalRead> {
    const { data } = await api.get<DocumentoFiscalRead>(
      `${FISCAL_ENDPOINT}/documentos/${id}/consultar`,
      { timeout: TIMEOUT_CONSULTA },
    );
    return data;
  },

  async cancelarDocumento(id: number, justificativa: string): Promise<DocumentoFiscalRead> {
    const { data } = await api.post<DocumentoFiscalRead>(
      `${FISCAL_ENDPOINT}/documentos/${id}/cancelar`,
      { justificativa },
      { timeout: TIMEOUT_EMISSAO },
    );
    return data;
  },

  async obterHistorico(id: number): Promise<DocumentoFiscalHistorico> {
    const { data } = await api.get<DocumentoFiscalHistorico>(
      `${FISCAL_ENDPOINT}/documentos/${id}/historico`,
    );
    return data;
  },

  /**
   * Campos fiscais que o sistema deduz para um produto novo.
   *
   * Não exige o plano fiscal: sugerir não emite nada, e o lojista pode deixar
   * o catálogo pronto antes de contratar.
   */
  async sugerirCamposProduto(): Promise<SugestoesFiscaisResponse> {
    const { data } = await api.get<SugestoesFiscaisResponse>(
      `${FISCAL_ENDPOINT}/sugestao/produto`,
      { timeout: TIMEOUT_CONSULTA },
    );
    return data;
  },

  async obterConfiguracao(): Promise<FiscalConfiguracao> {
    const { data } = await api.get<FiscalConfiguracao>(
      `${FISCAL_ENDPOINT}/configuracao`,
    );
    return data;
  },

  async atualizarConfiguracao(payload: Partial<FiscalConfiguracao>): Promise<FiscalConfiguracao> {
    const { data } = await api.put<FiscalConfiguracao>(
      `${FISCAL_ENDPOINT}/configuracao`,
      payload,
    );
    return data;
  },

  async emitirNfeBatch(vendaIds: number[]): Promise<EmissaoBatchResponse> {
    const { data } = await api.post<EmissaoBatchResponse>(
      `${FISCAL_ENDPOINT}/emitir/nfe/batch`,
      { venda_ids: vendaIds },
      { timeout: TIMEOUT_LOTE },
    );
    return data;
  },

  async verificarFiscalBatch(vendaIds: number[]): Promise<ResultadoVerificacaoBatch> {
    const { data } = await api.get<ResultadoVerificacaoBatch>(
      '/vendas/verificar-fiscal-batch',
      { params: { ids: vendaIds.join(',') } },
    );
    return data;
  },

  async corrigirVendaFiscal(vendaId: number, payload: VendaCorrecaoFiscalPayload): Promise<unknown> {
    const { data } = await api.patch(`/vendas/${vendaId}/correcao-fiscal`, payload);
    return data;
  },
};
