import api from '@/api/axios';
import type { EmissaoPreviewResponse,
  DocumentoFiscalHistorico,
  DocumentoFiscalListRead,
  DocumentoFiscalRead,
  DocumentoFiscalResumo,
  DocumentoFiscalFilters,
  EmissaoNFeRequest,
  EmissaoResponse,
  EmissaoBatchResponse,
  FiscalConfiguracao,
  PendenciasGlobais,
  ResultadoVerificacaoBatch,
  VendaCorrecaoFiscalPayload,
} from '../types/fiscal.types';

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

  async obterResumo(): Promise<DocumentoFiscalResumo> {
    const { data } = await api.get<DocumentoFiscalResumo>(
      `${FISCAL_ENDPOINT}/resumo`,
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
    );
    return data;
  },

  // --- Novos (emissao, consulta, cancelamento) ---

  async previewNfe(payload: EmissaoNFeRequest): Promise<EmissaoPreviewResponse> {
    const { data } = await api.post<EmissaoPreviewResponse>(
      `${FISCAL_ENDPOINT}/preview/nfe`,
      payload,
    );
    return data;
  },

  async emitirNfe(payload: EmissaoNFeRequest): Promise<EmissaoResponse> {
    const { data } = await api.post<EmissaoResponse>(
      `${FISCAL_ENDPOINT}/emitir/nfe`,
      payload,
    );
    return data;
  },

  async emitirTesteNfe(): Promise<EmissaoResponse> {
    const { data } = await api.post<EmissaoResponse>(
      `${FISCAL_ENDPOINT}/emitir/teste/nfe`,
    );
    return data;
  },

  async consultarDocumento(id: number): Promise<DocumentoFiscalRead> {
    const { data } = await api.get<DocumentoFiscalRead>(
      `${FISCAL_ENDPOINT}/documentos/${id}/consultar`,
    );
    return data;
  },

  async cancelarDocumento(id: number, justificativa: string): Promise<DocumentoFiscalRead> {
    const { data } = await api.post<DocumentoFiscalRead>(
      `${FISCAL_ENDPOINT}/documentos/${id}/cancelar`,
      { justificativa },
    );
    return data;
  },

  async obterHistorico(id: number): Promise<DocumentoFiscalHistorico> {
    const { data } = await api.get<DocumentoFiscalHistorico>(
      `${FISCAL_ENDPOINT}/documentos/${id}/historico`,
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
