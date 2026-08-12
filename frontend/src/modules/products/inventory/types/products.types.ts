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
  /**
   * Unidade do produto, para o painel escrever "2,5 kg" em vez de "2,5 un".
   * Vem do produto no momento da consulta; nula se ele não tiver unidade
   * cadastrada — a tela cai em "un", como sempre foi.
   */
  unidade_medida?: string | null;
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
}
