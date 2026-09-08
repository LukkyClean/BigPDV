export type StatusFilter = 'ativos' | 'inativos';
export type ModalMode = 'create' | 'edit' | 'view';

export interface ServicoFilters {
  buscar?: string;
  status?: StatusFilter | 'todos';
}

export interface ServicosStats {
  total: number;
  ativos: number;
  inativos: number;
  media_valor: number;
}

export interface ServicoFormData {
  descricao: string;
  valor: number;

  // Dados fiscais (opcionais — preenchidos apenas quando módulo fiscal ativo)
  fiscal_codigo_servico_lc116: string;
  fiscal_cnae: string;
  fiscal_aliquota_iss_display: string;
  fiscal_codigo_tributacao_municipio: string;
  fiscal_cfop_padrao: string;
  fiscal_cst_icms: string;
  fiscal_csosn: string;
  fiscal_unidade_tributavel: string;
  fiscal_c_class_trib: string;
  fiscal_cst_ibs_cbs: string;
  fiscal_aliquota_ibs_display: string;
  fiscal_aliquota_cbs_display: string;
  fiscal_c_benef: string;
}

export interface QueryParams {
  page?: number;
  limit?: number;
}

export interface ServicosQuerySearch extends QueryParams {
  search?: string;
  active?: boolean;
}

// =============================================
// FISCAL TYPES (tabela satélite servico_fiscal)
// =============================================

export interface ServicoFiscalRead {
  id: number;
  servico_id: number;
  codigo_servico_lc116?: string | null;
  cnae?: string | null;
  aliquota_iss?: number | null;
  codigo_tributacao_municipio?: string | null;
  cfop_padrao?: string | null;
  cst_icms?: string | null;
  csosn?: string | null;
  unidade_tributavel?: string | null;
  c_class_trib?: string | null;
  cst_ibs_cbs?: string | null;
  aliquota_ibs?: number | null;
  aliquota_cbs?: number | null;
  c_benef?: string | null;
  data_atualizacao: string;
}

export interface ServicoFiscalUpdate {
  codigo_servico_lc116?: string | null;
  cnae?: string | null;
  aliquota_iss?: number | null;
  codigo_tributacao_municipio?: string | null;
  cfop_padrao?: string | null;
  cst_icms?: string | null;
  csosn?: string | null;
  unidade_tributavel?: string | null;
  c_class_trib?: string | null;
  cst_ibs_cbs?: string | null;
  aliquota_ibs?: number | null;
  aliquota_cbs?: number | null;
  c_benef?: string | null;
}
