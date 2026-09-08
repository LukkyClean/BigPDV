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
  ProdutoFiscalRead,
  ProdutoFiscalUpdate,
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
 * Obtém um produto específico pelo seu ID
 */
export async function getProdutoById(id: number): Promise<ProdutoRead> {
  const { data } = await api.get<ProdutoRead>(`${BASE_URL}/${id}`);
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
 * Atualiza um produto existente.
 * Se `fiscal` estiver presente no payload, envia os dados fiscais em sequência
 * via endpoint separado, de forma transparente para o chamador.
 */
export async function updateProduto(
  id: number,
  produto: ProdutoUpdate & { fiscal?: ProdutoFiscalUpdate | null },
): Promise<ProdutoRead> {
  const { fiscal, ...dadosPrincipais } = produto;
  const { data } = await api.put<ProdutoRead>(`${BASE_URL}/${id}`, dadosPrincipais);

  if (fiscal) {
    await upsertProdutoFiscal(id, fiscal);
  }

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

/**
 * Retorna os dados fiscais de um produto.
 * Lança erro 404 se ainda não foram preenchidos (tratado como `null` no composable).
 */
export async function getProdutoFiscal(produtoId: number): Promise<ProdutoFiscalRead | null> {
  try {
    const { data } = await api.get<ProdutoFiscalRead>(`${BASE_URL}/${produtoId}/fiscal`);
    return data;
  } catch (err: any) {
    if (err?.response?.status === 404) return null;
    throw err;
  }
}

/**
 * Cria ou atualiza os dados fiscais de um produto (upsert).
 */
export async function upsertProdutoFiscal(
  produtoId: number,
  dados: ProdutoFiscalUpdate,
): Promise<ProdutoFiscalRead> {
  const { data } = await api.put<ProdutoFiscalRead>(`${BASE_URL}/${produtoId}/fiscal`, dados);
  return data;
}
