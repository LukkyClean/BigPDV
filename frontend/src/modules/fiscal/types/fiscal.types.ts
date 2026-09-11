export type DocumentoFiscalStatus =
  | 'PENDENTE'
  | 'PROCESSANDO'
  | 'AUTORIZADA'
  | 'REJEITADA'
  | 'CANCELADA'
  | 'DENEGADA'
  // Transmitida, sem resposta confirmada. NUNCA reemitir: pode estar
  // autorizada na SEFAZ, e a segunda nota valeria tanto quanto a primeira.
  | 'INDETERMINADA'
  // Houve tentativa e a nota nao chegou na SEFAZ. Nao e rejeicao: nao ha
  // protocolo, nao ha codigo, e o numero reservado nao foi queimado.
  | 'NAO_TRANSMITIDA';
export type DocumentoFiscalTipo = 'NFE' | 'NFCE' | 'NFSE';
export type DocumentoFiscalOrigem = 'VENDA' | 'ORDEM_SERVICO';

export interface DocumentoItemResumo {
  id?: number | null;
  produto_id?: number | null;
  nome: string;
  codigo_barras?: string | null;
  quantidade: number;
  valor_unitario: number;
  subtotal: number;
  desconto?: number;
  ncm?: string | null;
  cfop?: string | null;
}

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
  /** Status cru da emissora ('autorizado', 'denegado', 'erro_autorizacao'). */
  status_focus?: string | null;
  motivo_rejeicao: string | null;
  valor_total: number | null;
  /** Texto do QR Code do DANFE NFC-e, montado pelo provedor com o CSC. */
  qrcode: string | null;
  /** Endereço de consulta da SEFAZ impresso abaixo do QR Code. */
  url_consulta: string | null;
  /** Tributos aproximados em CENTAVOS (Lei 12.741/2012 — IBPT). */
  valor_tributos: number | null;
  ref_api: string | null;
  ambiente_emissao: number | null;
  tentativa_anterior_id: number | null;
  data_emissao: string | null;
  data_criacao: string;
  data_atualizacao: string;
  
  // Metadados enriquecidos
  venda_id?: number | null;
  destinatario_id?: number | null;
  destinatario_nome?: string | null;
  destinatario_documento?: string | null;
  destinatario_uf?: string | null;
  destinatario_municipio?: string | null;
  itens_resumo?: DocumentoItemResumo[] | null;
}

export interface VendaCorrecaoFiscalPayload {
  cliente_id?: number | null;
  observacao?: string | null;
  observacao_interna?: string | null;
  natureza_operacao?: string | null;
  consumidor_final?: boolean | null;
  indicador_presenca?: number | null;
  finalidade_emissao?: number | null;
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

/**
 * O que a plataforma de emissão enxerga desta licença.
 *
 * `consultou: false` é "não sei" — a plataforma não respondeu. A tela precisa
 * mostrar isso como indisponibilidade, nunca como "não configurado".
 */
export interface DiagnosticoPlataforma {
  consultou: boolean;
  ambiente?: number | null;
  ambiente_nome?: string | null;
  configurado?: boolean | null;
  token_configurado?: boolean | null;
  csc_configurado?: boolean | null;
  certificado_status?: string | null;
  pendencias: string[];
  cnpj_erp?: string | null;
  cnpj_plataforma?: string | null;
  /** null = a plataforma ainda não devolve o CNPJ dela; não é divergência. */
  cnpj_confere?: boolean | null;
}

export interface PendenciasGlobais {
  emitente_completo: boolean;
  emitente_pendencias: string[];
  /** Aviso (não pendência): certificado vence em até 30 dias, ou já venceu. */
  certificado_aviso?: string | null;
  /** Negativo = vencido; null = sem validade conhecida. */
  certificado_dias_restantes?: number | null;
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
  certificado_status?: string | null;
  certificado_cnpj?: string | null;
  certificado_validade?: string | null;
  /** Negativo = vencido; null = sem validade conhecida. */
  certificado_dias_restantes?: number | null;
  serie_nfe?: number;
  ultimo_numero_nfe?: number;
  serie_nfce?: number;
  ultimo_numero_nfce?: number;
  /**
   * MASCARADO pelo backend (ex.: `••••••••AB12`) — só os últimos caracteres,
   * o bastante para reconhecer qual token está cadastrado. Reenviar a máscara
   * no salvamento não sobrescreve o CSC guardado.
   */
  csc_token?: string | null;
  /** True quando há CSC cadastrado. É o que a tela deve exibir, não o token. */
  csc_configurado?: boolean;
  csc_id?: string | null;
  /** Teto em CENTAVOS para emitir NFC-e sem CPF/CNPJ do comprador. */
  limite_consumidor_anonimo?: number;
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


/**
 * Sugestão de campo fiscal vinda do backend.
 *
 * Nunca é só o valor: `fundamentacao` é o "por quê?" que a tela mostra ao lado
 * do campo, e é o que permite ao contador discordar com base. Sugestão sem
 * explicação, em campo tributário, é pior que campo vazio.
 */
export interface CampoSugerido {
  campo: string;
  valor: string | null;
  fonte: 'derivado' | 'default_regime' | 'default_uf' | 'base_ncm' | 'base_cest';
  confianca: 'certa' | 'provavel' | 'ambigua';
  fundamentacao: string;
  /** (valor, descrição) — preenchido quando a confiança é `ambigua`. */
  alternativas: [string, string][];
  /** Bloqueia auto-aplicação: errar aqui produz nota aceita e errada. */
  exige_confirmacao: boolean;
}

export interface SugestoesFiscaisResponse {
  sugestoes: CampoSugerido[];
}
