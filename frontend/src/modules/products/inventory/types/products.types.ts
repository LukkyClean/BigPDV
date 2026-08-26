/**
 * @fileoverview Types for the products module
 * @description Matches backend schemas for Produto and Estoque
 */

import type { Component } from 'vue';

// =============================================
// API TYPES (matching produto.py and estoque.py)
// =============================================

export interface ProdutoFotoRead {
  id: number;
  nome_arquivo?: string | null;
  url: string;
  principal?: boolean;
}

export interface EstoqueCreate {
  valor_varejo: number;
  quantidade?: number;
  valor_entrada?: number;
  valor_atacado?: number;
  quantidade_ideal?: number;
  quantidade_minima?: number;
}

export interface EstoqueRead extends EstoqueCreate {
  id: number;
  /**
   * Custo médio ponderado calculado pelo livro de estoque. Somente leitura —
   * não confundir com `valor_entrada`, que é o último preço de compra digitado
   * no cadastro. É o custo médio que congela o CMV nas saídas; editar o preço
   * de referência não pode reescrever o lucro já apurado.
   * `null` enquanto o produto nunca teve uma compra com valor pago informado.
   */
  custo_medio?: number | null;
}

export interface EstoqueUpdate {
  valor_varejo?: number;
  quantidade?: number;
  valor_entrada?: number;
  valor_atacado?: number;
  quantidade_ideal?: number;
  quantidade_minima?: number;
}

export interface ProdutoBase {
  nome: string;
  codigo_produto: string;
  codigo_barras?: string | null;
  unidade_medida?: string | null;
  observacao?: string | null;
  categoria?: string | null;
  marca?: string | null;
  fornecedor_id?: number | null;
  localizacao_estoque?: string | null;
}

export interface ProdutoCreate extends ProdutoBase {
  estoque: EstoqueCreate;
}

export interface ProdutoRead extends ProdutoBase {
  id: number;
  estoque: EstoqueRead;
  ativo: boolean;
  fotos?: ProdutoFotoRead[];
}

export interface ProdutoUpdate extends Partial<ProdutoBase> {
  estoque?: EstoqueUpdate;
}

// =============================================
// FISCAL TYPES (tabela satélite produto_fiscal)
// =============================================

export interface ProdutoFiscalRead {
  id: number;
  produto_id: number;
  ncm?: string | null;
  cest?: string | null;
  cfop_padrao?: string | null;
  origem_mercadoria?: number | null;
  unidade_tributavel?: string | null;
  gtin_tributavel?: string | null;
  cst_icms?: string | null;
  csosn?: string | null;
  aliquota_icms?: number | null;
  reducao_base_icms?: number | null;
  codigo_beneficio_fiscal?: string | null;
  aliquota_pis?: number | null;
  aliquota_cofins?: number | null;
  cst_pis?: string | null;
  cst_cofins?: string | null;
  c_class_trib?: string | null;
  cst_ibs_cbs?: string | null;
  aliquota_ibs?: number | null;
  aliquota_cbs?: number | null;
  c_benef?: string | null;
  data_atualizacao: string;
}

export interface ProdutoFiscalUpdate {
  ncm?: string | null;
  cest?: string | null;
  cfop_padrao?: string | null;
  origem_mercadoria?: number | null;
  unidade_tributavel?: string | null;
  gtin_tributavel?: string | null;
  cst_icms?: string | null;
  csosn?: string | null;
  aliquota_icms?: number | null;
  reducao_base_icms?: number | null;
  codigo_beneficio_fiscal?: string | null;
  aliquota_pis?: number | null;
  aliquota_cofins?: number | null;
  cst_pis?: string | null;
  cst_cofins?: string | null;
  c_class_trib?: string | null;
  cst_ibs_cbs?: string | null;
  aliquota_ibs?: number | null;
  aliquota_cbs?: number | null;
  c_benef?: string | null;
}

// =============================================
// UI TYPES
// =============================================

export interface TabOption {
  id: string;
  label: string;
}

export type ModalMode = 'create' | 'edit' | 'view';

export interface ModalState {
  isOpen: boolean;
  mode: ModalMode;
  productId: number | null;
}

export interface CardInfo {
  key: string;
  icon: Component;
  label: string;
}

// =============================================
// MOVIMENTAÇÃO TYPES
// =============================================

export type MovimentacaoTipo = 'ENTRADA' | 'SAIDA' | 'AJUSTE' | 'EDICAO_DADOS';

export interface MovimentacaoRead {
  id: number;
  produto_id: number;
  produto_nome: string;
  usuario_id: number | null;
  usuario_nome: string;
  tipo: MovimentacaoTipo;
  quantidade: number;
  quantidade_anterior: number;
  quantidade_posterior: number;
  /** Custo unitário congelado nesta linha (centavos). `null` nas linhas antigas. */
  custo_unitario: number | null;
  observacao: string | null;
  created_at: string;
}

export interface MovimentacaoCreate {
  tipo: MovimentacaoTipo;
  /** ENTRADA/SAIDA: unidades movimentadas. AJUSTE: a quantidade FINAL contada. */
  quantidade: number;
  /**
   * Valor pago por unidade nesta compra, em centavos. Só faz sentido em ENTRADA:
   * é ele que recalcula a média ponderada. Omitir mantém a média intacta — é o
   * caso da devolução, que não é compra.
   */
  custo_unitario?: number;
  observacao?: string;
}

// =============================================
// FORM TYPES
// =============================================

export interface ProductFormData {
  nome: string;
  codigo_produto: string;
  codigo_barras: string;
  unidade_medida: string;
  categoria: string;
  marca: string;
  fornecedor_id: string;
  localizacao_estoque: string;
  observacao: string;

  valor_entrada: number;
  valor_varejo: number;
  valor_atacado: number;
  quantidade: number;
  quantidade_minima: number;
  quantidade_ideal: number;

  image_url: string | null;

  // Dados fiscais (opcionais — preenchidos apenas quando módulo fiscal ativo)
  fiscal_ncm: string;
  fiscal_cest: string;
  fiscal_cfop_padrao: string;
  fiscal_origem_mercadoria: string;
  fiscal_unidade_tributavel: string;
  fiscal_gtin_tributavel: string;
  fiscal_cst_icms: string;
  fiscal_csosn: string;
  fiscal_aliquota_icms_display: string;
  fiscal_reducao_base_icms_display: string;
  fiscal_codigo_beneficio_fiscal: string;
  fiscal_aliquota_pis_display: string;
  fiscal_aliquota_cofins_display: string;
  fiscal_cst_pis: string;
  fiscal_cst_cofins: string;
  fiscal_c_class_trib: string;
  fiscal_cst_ibs_cbs: string;
  fiscal_aliquota_ibs_display: string;
  fiscal_aliquota_cbs_display: string;
  fiscal_c_benef: string;
}
