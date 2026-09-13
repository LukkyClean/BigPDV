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
  DiagnosticoPlataforma,
  ResultadoVerificacaoBatch,
  VendaCorrecaoFiscalPayload,
  SugestoesFiscaisResponse,
  CamposFiscaisProdutoResponse,
  TributacaoPadrao,
  ValidacaoFiscalProduto,
  BuscaNcmResposta,
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

  async obterDiagnosticoPlataforma(): Promise<DiagnosticoPlataforma> {
    const { data } = await api.get<DiagnosticoPlataforma>(
      `${FISCAL_ENDPOINT}/plataforma`,
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

  /**
   * ZIP com os XMLs do período (autorizadas, canceladas, inutilizações e a
   * relação em CSV). O contador pede isso todo dia 5. O timeout é o do lote:
   * a plataforma entrega um XML por vez.
   */
  async exportarXmlPeriodo(
    dataInicio: string,
    dataFim: string,
    tipo?: 'NFE' | 'NFCE',
  ): Promise<{ arquivo: Blob; nome: string; documentos: number; baixados: number; naoBaixados: number }> {
    const resposta = await api.get<Blob>(`${FISCAL_ENDPOINT}/documentos/exportar-xml`, {
      params: { data_inicio: dataInicio, data_fim: dataFim, tipo },
      responseType: 'blob',
      timeout: TIMEOUT_LOTE,
    });
    const h = resposta.headers as Record<string, string | undefined>;
    return {
      arquivo: resposta.data,
      nome: `xml-fiscal-${dataInicio}_${dataFim}.zip`,
      documentos: Number(h['x-fiscal-documentos'] ?? 0),
      baixados: Number(h['x-fiscal-baixados'] ?? 0),
      naoBaixados: Number(h['x-fiscal-nao-baixados'] ?? 0),
    };
  },

  /**
   * O XML de uma nota. O backend lê do disco da loja quando existe — e aí
   * funciona sem internet.
   */
  async baixarXmlDocumento(id: number): Promise<Blob> {
    const { data } = await api.get<Blob>(
      `${FISCAL_ENDPOINT}/documentos/${id}/xml`,
      { responseType: 'blob', timeout: TIMEOUT_CONSULTA },
    );
    return data;
  },

  /** O DANFE de uma nota, lido do disco da loja quando existe. */
  async baixarPdfDocumento(id: number): Promise<Blob> {
    const { data } = await api.get<Blob>(
      `${FISCAL_ENDPOINT}/documentos/${id}/pdf`,
      { responseType: 'blob', timeout: TIMEOUT_CONSULTA },
    );
    return data;
  },

  /** Guarda nesta máquina os XMLs das notas emitidas antes do arquivamento local. */
  async sincronizarArquivosFiscais(limite = 200): Promise<{
    pendentes_encontrados: number;
    guardados: number;
    falharam: number;
    restam: number;
  }> {
    const { data } = await api.post(
      `${FISCAL_ENDPOINT}/documentos/arquivos/sincronizar`,
      undefined,
      { params: { limite }, timeout: TIMEOUT_LOTE },
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

  /**
   * Quais campos fiscais o cadastro de produto deve mostrar e exigir.
   *
   * Quem responde é o mesmo `obter_crt` que decide na emissão — por isso a
   * pergunta vai ao servidor em vez de virar `v-if` na tela.
   */
  async camposProduto(): Promise<CamposFiscaisProdutoResponse> {
    const { data } = await api.get<CamposFiscaisProdutoResponse>(
      `${FISCAL_ENDPOINT}/campos/produto`,
      { timeout: TIMEOUT_CONSULTA },
    );
    return data;
  },

  /** A tributação padrão da loja. `null` enquanto ninguém configurou. */
  async obterTributacaoPadrao(): Promise<TributacaoPadrao | null> {
    const { data } = await api.get<TributacaoPadrao | null>(
      `${FISCAL_ENDPOINT}/tributacao-padrao`,
    );
    return data ?? null;
  },

  async salvarTributacaoPadrao(dados: Partial<TributacaoPadrao>): Promise<TributacaoPadrao> {
    const { data } = await api.put<TributacaoPadrao>(
      `${FISCAL_ENDPOINT}/tributacao-padrao`,
      dados,
    );
    return data;
  },

  /**
   * Confere os dados fiscais de um produto SEM emitir nada.
   *
   * Roda a mesma regra do gate de emissão, sobre o rascunho e já com a cascata
   * aplicada — por isso um produto só com NCM não aparece cheio de erro quando
   * a loja já respondeu na tributação padrão.
   */
  async validarProdutoFiscal(
    dados: Record<string, unknown>,
    nomeProduto?: string,
  ): Promise<ValidacaoFiscalProduto> {
    const { data } = await api.post<ValidacaoFiscalProduto>(
      `${FISCAL_ENDPOINT}/validar/produto`,
      dados,
      { params: nomeProduto ? { nome_produto: nomeProduto } : undefined },
    );
    return data;
  },

  /**
   * Busca na tabela NCM embarcada. Funciona sem internet.
   *
   * Aceita o código (com ou sem pontos) e a descrição. Quem filtra é o
   * servidor, com o mesmo motor de busca de produto e cliente.
   */
  async buscarNcm(termo: string, limite = 20): Promise<BuscaNcmResposta> {
    const { data } = await api.get<BuscaNcmResposta>(`${FISCAL_ENDPOINT}/ncm`, {
      params: { buscar: termo, limite },
      timeout: TIMEOUT_CONSULTA,
    });
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
