import { useMutation, useQueryClient } from '@tanstack/vue-query';

import { useToast } from '@/shared/composables/useToast';

import {
  abrirCaixa,
  fecharCaixa,
  registrarSangria,
  registrarSuprimento,
} from '../../services/caixa.service';
import { caixaKeys } from '../../caixa.keys';
import type {
  AbrirCaixaPayload,
  FecharCaixaPayload,
  MovimentoCaixaPayload,
} from '../../schemas/caixa.schema';

/**
 * Mutations do turno de caixa.
 *
 * Todas invalidam o prefixo `caixa` — e só ele. O resumo do turno é a única
 * coisa que muda: venda, estoque e relatório seguem seus próprios prefixos e
 * não são tocados aqui.
 */
function useInvalidarCaixa() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: caixaKeys.all });
}

export function useAbrirCaixaMutation() {
  const invalidar = useInvalidarCaixa();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (payload: AbrirCaixaPayload) => abrirCaixa(payload),
    onSuccess: async () => {
      await invalidar();
      success('Caixa aberto');
    },
    onError: (e: any) => {
      error(e?.response?.data?.detail ?? 'Não foi possível abrir o caixa');
    },
  });
}

export function useSuprimentoMutation() {
  const invalidar = useInvalidarCaixa();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (payload: MovimentoCaixaPayload) => registrarSuprimento(payload),
    onSuccess: async () => {
      await invalidar();
      success('Suprimento registrado');
    },
    onError: (e: any) => {
      error(e?.response?.data?.detail ?? 'Não foi possível registrar o suprimento');
    },
  });
}

export function useSangriaMutation() {
  const invalidar = useInvalidarCaixa();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (payload: MovimentoCaixaPayload) => registrarSangria(payload),
    onSuccess: async () => {
      await invalidar();
      success('Sangria registrada');
    },
    onError: (e: any) => {
      error(e?.response?.data?.detail ?? 'Não foi possível registrar a sangria');
    },
  });
}

export function useFecharCaixaMutation() {
  const invalidar = useInvalidarCaixa();
  const { success, error } = useToast();

  return useMutation({
    mutationFn: (payload: FecharCaixaPayload) => fecharCaixa(payload),
    onSuccess: async () => {
      await invalidar();
      success('Caixa fechado');
    },
    onError: (e: any) => {
      error(e?.response?.data?.detail ?? 'Não foi possível fechar o caixa');
    },
  });
}
