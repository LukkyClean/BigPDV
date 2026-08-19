import api from '@/api/axios';
import type {
  DocumentoFiscalListRead,
  DocumentoFiscalRead,
  DocumentoFiscalResumo,
  DocumentoFiscalFilters,
  PendenciasGlobais,
} from '../types/fiscal.types';

const FISCAL_ENDPOINT = '/fiscal';

export const fiscalService = {
  async listarDocumentos(
    filters: DocumentoFiscalFilters = {},
    pagina: number = 1,
  ): Promise<DocumentoFiscalListRead> {
    const params: Record<string, any> = { pagina };
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
};
