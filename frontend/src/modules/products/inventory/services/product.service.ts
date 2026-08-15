/**
 * @fileoverview API service for products
 * @description Handles all produto-related API calls
 */

import api from '@/api/axios';
import { ENDPOINT_PERMISSION_MAP } from '@/shared/constants/permissions.constants';
import type {
  ProdutoCreate,
  ProdutoRead,
  ProdutoUpdate,
} from '../types/products.types';

const BASE_URL = 'produtos' as const;
export const PRODUCT_PERMISSION = ENDPOINT_PERMISSION_MAP[BASE_URL];

/**
 * Lista produtos ativos ou busca por termo
 * @param buscar - Termo de busca opcional (nome, codigo, codigo de barras, marca ou categoria)
 * @param limite - Teto de resultados. Sem valor, o backend devolve tudo —
 *                 a tela de Produtos depende disso para listar o catalogo.
 */
export async function getProdutos(buscar?: string, limite?: number): Promise<ProdutoRead[]> {
  const params = {
    ...(buscar && { buscar }),
    ...(limite && { limite }),
  };
  const { data } = await api.get<ProdutoRead[]>(`${BASE_URL}/`, {
    params: Object.keys(params).length ? params : undefined,
  });
  return data;
}

/**
 * Cria um novo produto com estoque inicial
 * @param produto - Dados do produto
 */
export async function createProduto(produto: ProdutoCreate): Promise<ProdutoRead> {
  const { data } = await api.post<ProdutoRead>(`${BASE_URL}/`, produto);
  return data;
}

export async function uploadProdutoImage(produtoId: number, file: File, principal = true): Promise<void> {
  const formData = new FormData();
  formData.append('image_file', file);
  formData.append('principal', String(principal));

  await api.post(
    `produtos/${produtoId}/fotos`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
}

export async function replaceProdutoPrincipalImage(produtoId: number, file: File): Promise<void> {
  const formData = new FormData();
  formData.append('image_file', file);

  await api.put(
    `produtos/${produtoId}/fotos/principal`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
}

/**
 * Atualiza um produto existente
 * @param id - ID do produto
 * @param produto - Dados para atualizar
 */
export async function updateProduto(
  id: number,
  produto: ProdutoUpdate,
): Promise<ProdutoRead> {
  const { data } = await api.put<ProdutoRead>(`${BASE_URL}/${id}`, produto);
  return data;
}

/**
 * Ativa ou desativa um produto
 * @param id - ID do produto
 */
export async function toggleProdutoAtivo(id: number): Promise<ProdutoRead> {
  const { data } = await api.put<ProdutoRead>(`${BASE_URL}/toggle_ativo/${id}`);
  return data;
}
