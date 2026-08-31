export type DocumentoFiscalStatus = 'PENDENTE' | 'PROCESSANDO' | 'AUTORIZADA' | 'REJEITADA' | 'CANCELADA' | 'DENEGADA';
export type DocumentoFiscalTipo = 'NFE' | 'NFCE' | 'NFSE';
export type DocumentoFiscalOrigem = 'VENDA' | 'ORDEM_SERVICO';

export interface DocumentoFiscalRead {
  id: number;
  tipo_documento: DocumentoFiscalTipo;
  origem_tipo: DocumentoFiscalOrigem;
  origem_id: number | null;
  origem_numero_os: string | null;
  status: DocumentoFiscalStatus;
  chave_acesso: string | null;
  numero_documento: number | null;
  serie: number | null;
  protocolo_autorizacao: string | null;
  data_autorizacao: string | null;
  url_pdf: string | null;
  url_xml: string | null;
  mensagem_sefaz: string | null;
  codigo_status_sefaz: number | null;
  motivo_rejeicao: string | null;
  valor_total: number | null;
  ref_api: string | null;
  ambiente_emissao: number | null;
  tentativa_anterior_id: number | null;
  data_emissao: string | null;
  data_criacao: string;
  data_atualizacao: string;
  destinatario_nome: string | null;
}

export interface DocumentoFiscalListRead {
  items: DocumentoFiscalRead[];
  total: number;
  pagina: number;
  paginas: number;
}

export interface DocumentoFiscalResumo {
  pendentes: number;
  autorizadas: number;
  rejeitadas: number;
  canceladas: number;
}

export interface PendenciaGlobalItem {
  id: number;
  nome: string;
  campo_faltante: string;
}

export interface PendenciasGlobais {
  emitente_completo: boolean;
  emitente_pendencias: string[];
  produtos_sem_ncm: PendenciaGlobalItem[];
  servicos_sem_lc116: PendenciaGlobalItem[];
  pagamentos_sem_sefaz: PendenciaGlobalItem[];
}

export interface DocumentoFiscalFilters {
  status?: DocumentoFiscalStatus;
  tipo?: DocumentoFiscalTipo;
  origem?: DocumentoFiscalOrigem;
  busca?: string;
  data_inicio?: string;
  data_fim?: string;
}

export interface DocumentoFiscalHistorico {
  tentativas: DocumentoFiscalRead[];
  total_tentativas: number;
}

export interface EmissaoNFeRequest {
  venda_id?: number;
  numero_os?: string;
}

export interface CancelamentoRequest {
  justificativa: string;
}

export interface EmissaoResponse {
  documento_id: number;
  ref_api: string | null;
  status: string;
  mensagem: string;
  ambiente: number;
}

export interface FiscalConfiguracao {
  ambiente: number;
  ambiente_label: string;
  mock_ativo: boolean;
  certificado_configurado: boolean;
  certificado_valido: boolean;
}
export interface EmissaoPreviewItem {
  numero_item: number;
  produto_id: number | null;
  nome: string;
  quantidade: number;
  valor_unitario: number;
  valor_total: number;
  cfop: string;
  ncm: string;
  cst_csosn: string;
}

export interface EmissaoPreviewPagamento {
  nome: string;
  codigo_sefaz: string;
  valor: number;
}
export interface EmissaoPreviewTotais {
  valor_produtos: number;
  descontos: number;
  frete: number;
  valor_nota: number;
  total_tributos: number;
}
export interface EmissaoPreviewDestinatario {
  nome: string;
  documento: string;
}
export interface EmissaoPreviewResponse {
  destinatario: EmissaoPreviewDestinatario;
  totais: EmissaoPreviewTotais;
  itens: EmissaoPreviewItem[];
  formas_pagamento: EmissaoPreviewPagamento[];
}

// --- Error Detail (409 Conflict) ---

export interface FiscalConflictDetail {
  codigo: string;
  mensagem: string;
  documento_id?: number;
  chave_acesso?: string;
}

// --- Emissão Batch ---

export interface EmissaoBatchItemResult {
  venda_id: number;
  documento_id: number | null;
  status: string;
  mensagem: string;
}

export interface EmissaoBatchResponse {
  resultados: EmissaoBatchItemResult[];
  total: number;
  sucesso: number;
  falha: number;
}

// --- Verificação Fiscal Batch ---

export interface PendenciaFiscal {
  categoria: string;
  campo: string;
  mensagem: string;
  referencia_id: number | null;
  referencia_nome: string | null;
}

export interface DocumentoAtivoResumo {
  documento_id: number;
  status: DocumentoFiscalStatus;
  numero_documento: number | null;
  serie: number | null;
  chave_acesso: string | null;
}

export interface VerificacaoBatchItem {
  venda_id: number;
  numero_venda: number | null;
  completo: boolean;
  pendencias: PendenciaFiscal[];
  documento_ativo: DocumentoAtivoResumo | null;
}

export interface ResultadoVerificacaoBatch {
  resultados: VerificacaoBatchItem[];
  total: number;
  total_aptas: number;
  total_com_pendencias: number;
  total_com_documento: number;
}
