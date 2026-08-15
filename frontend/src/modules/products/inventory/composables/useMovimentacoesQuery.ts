/**
 * @fileoverview Composables para movimentações de estoque
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query';
import { useToast } from '@/shared/composables/useToast';
import { getMovimentacoes, createMovimentacao } from '../services/movimentacao.service';
import type { MovimentacaoCreate } from '../types/products.types';
import { PRODUTOS_QUERY_KEY, PRODUTOS_REFETCH_INTERVAL } from '../../shared/constants/queryKeys';
import { dashboardKeys } from '@/modules/home/constants/dashboard.constants';
import { invalidarRelatorios } from '@/shared/utils/invalidarRelatorios';

export const MOVIMENTACOES_QUERY_KEY = 'movimentacoes-estoque';

export function useMovimentacoesQuery(produto_id?: number) {
  return useQuery({
    queryKey: [MOVIMENTACOES_QUERY_KEY, produto_id ?? null],
    queryFn: () => getMovimentacoes(produto_id),
    staleTime: 1000 * 30, // 30s — histórico muda com frequência
    refetchInterval: PRODUTOS_REFETCH_INTERVAL,
  });
}

export function useCreateMovimentacaoMutation() {
  const toast = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ produto_id, data }: { produto_id: number; data: MovimentacaoCreate }) =>
      createMovimentacao(produto_id, data),
    onSuccess: (result) => {
      const label = result.tipo === 'ENTRADA' ? 'Entrada' : result.tipo === 'SAIDA' ? 'Saída' : 'Ajuste';
      toast.success(`${label} registrada com sucesso!`);
      queryClient.invalidateQueries({ queryKey: [MOVIMENTACOES_QUERY_KEY] });
      queryClient.invalidateQueries({ queryKey: [PRODUTOS_QUERY_KEY] });
      queryClient.invalidateQueries({ queryKey: dashboardKeys.estoqueBaixo() });
      // Movimentação manual muda o relatório de estoque (curva ABC, capital
      // imobilizado, itens parados), não só a lista de produtos.
      invalidarRelatorios(queryClient);
    },
    onError: () => {
      toast.error('Erro ao registrar movimentação. Verifique os dados.');
    },
  });
}