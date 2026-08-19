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
  data_emissao: string | null;
  data_criacao: string;
  data_atualizacao: string;
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
