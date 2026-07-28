/**
 * @fileoverview TanStack Query composable for products list
 * @description Manages product listing with search and mutations
 */

import { computed, type Ref } from 'vue';
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';
import type { ApiError } from '@/shared/types/axios.types';
import { useToast } from '@/shared/composables/useToast';
import {
  getProdutos,
  createProduto,
  uploadProdutoImage,
  replaceProdutoPrincipalImage,
  updateProduto,
  toggleProdutoAtivo,
} from '../services/product.service';
import type {
  ProdutoCreate,
  ProdutoRead,
  ProdutoUpdate,
} from '../types/products.types';
import { getErrorMessage, getConflictErrors, isConflictError } from '@/shared/utils/error.utils';

import { PRODUTOS_QUERY_KEY as QUERY_KEY, PRODUTOS_STALE_TIME as STALE_TIME, PRODUTOS_REFETCH_INTERVAL } from '../../shared/constants/queryKeys';
import { MOVIMENTACOES_QUERY_KEY } from './useMovimentacoesQuery';


/**
 * Query for listing products
 * @param searchTerm - Optional reactive search term
 * @param limite - Teto de resultados. Use em auto-complete; a listagem da
 *                 tela de Produtos deve omitir para receber o catálogo todo.
 */
export function useProductsQuery(searchTerm?: Ref<string | null>, limite?: number) {
  const cleanSearch = computed(() => searchTerm?.value?.trim() || undefined);

  return useQuery({
    queryKey: [QUERY_KEY, cleanSearch, limite],
    queryFn: () => getProdutos(cleanSearch.value, limite),
    staleTime: STALE_TIME,
    refetchInterval: PRODUTOS_REFETCH_INTERVAL,
  });
}

/**
 * Mutation for creating product
 */
export function useCreateProductMutation(setErrors: any, selectedFile: Ref<File | null>) {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation<ProdutoRead, AxiosError<ApiError>, ProdutoCreate>({
    mutationFn: createProduto,
    onSuccess: async (product) => {
      if (selectedFile.value) {
        await uploadProdutoImage(product.id, selectedFile.value)
      }
      toast.success('Produto cadastrado com sucesso!');
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
      queryClient.invalidateQueries({ queryKey: [MOVIMENTACOES_QUERY_KEY] });
    },
    onError: (error) => {
      if (isConflictError(error)) {
        const conflictedErrors = getConflictErrors(error);
        if (conflictedErrors) {
          setErrors(conflictedErrors);
          toast.error('Erro ao cadastrar produto', 'Dados ja registrados');
          return;
        }
      }
      toast.error(getErrorMessage(error, 'Erro ao cadastrar produto') as string);
    },
  });
}

/**
 * Mutation for updating product
 */
export function useUpdateProductMutation(setErrors: any, selectedFile: Ref<File | null>) {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation<
    ProdutoRead,
    AxiosError<ApiError>,
    { id: number; data: ProdutoUpdate }
  >({
    mutationFn: ({ id, data }) => updateProduto(id, data),
    onSuccess: async (product) => {
      if (selectedFile.value) {
        await replaceProdutoPrincipalImage(product.id, selectedFile.value)
      }
      toast.success('Produto atualizado com sucesso!');
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
      queryClient.invalidateQueries({ queryKey: [MOVIMENTACOES_QUERY_KEY] });
    },
    onError: (error) => {
      if (isConflictError(error)) {
        const conflictedErrors = getConflictErrors(error);
        if (conflictedErrors) {
          setErrors(conflictedErrors);
          toast.error('Erro ao atualizar produto', 'Dados ja registrados');
          return;
        }
      }
      toast.error(getErrorMessage(error, 'Erro ao atualizar produto') as string);
    },
  });
}

/**
 * Mutation for toggling product active status
 */
export function useToggleProductActiveMutation() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation<ProdutoRead, AxiosError<ApiError>, number>({
    mutationFn: toggleProdutoAtivo,
    onSuccess: (data) => {
      const status = data.ativo ? 'ativado' : 'desativado';
      toast.success(`Produto ${status} com sucesso!`);
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
      queryClient.invalidateQueries({ queryKey: [MOVIMENTACOES_QUERY_KEY] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Erro ao alterar status do produto') as string);
    },
  });
}
