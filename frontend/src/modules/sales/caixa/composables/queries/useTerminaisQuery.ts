import { computed } from 'vue';
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query';

import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage } from '@/shared/utils/error.utils';
import { REFETCH_CADASTROS } from '@/core/config/queryIntervals';

import { terminaisKeys } from '../../caixa.keys';
import {
  atualizarTerminal,
  getEsteTerminal,
  listarTerminais,
  type PapelTerminal,
} from '../../services/terminal.service';

/** A lista de máquinas da loja — só quem tem visão gerencial recebe. */
export function useTerminaisQuery() {
  const query = useQuery({
    queryKey: terminaisKeys.lista(),
    queryFn: listarTerminais,
    // Cadastro de máquina muda quando alguém configura, não sozinho.
    refetchInterval: REFETCH_CADASTROS,
    // 403 de quem não é gerente não melhora com repetição.
    retry: false,
  });

  return {
    ...query,
    terminais: computed(() => query.data.value ?? []),
  };
}

/**
 * Quem é ESTA máquina.
 *
 * `e_retaguarda` só é verdadeiro com o papel RETAGUARDA explícito. Máquina
 * desconhecida, HWID indisponível ou consulta que falhou resultam todos em
 * `false` — a mesma resposta, e é a segura: na dúvida a máquina é um caixa e
 * continua sendo cobrada por turno aberto.
 */
export function useEsteTerminalQuery() {
  const query = useQuery({
    queryKey: terminaisKeys.este(),
    queryFn: getEsteTerminal,
    staleTime: 1000 * 60 * 5,
    retry: false,
  });

  return {
    ...query,
    esteTerminal: computed(() => query.data.value ?? null),
    eRetaguarda: computed(() => query.data.value?.e_retaguarda === true),
  };
}

export function useAtualizarTerminalMutation() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn: (vars: {
      id: number;
      nome?: string | null;
      papel?: PapelTerminal | null;
    }) => atualizarTerminal(vars.id, { nome: vars.nome, papel: vars.papel }),

    onSuccess: () => {
      toast.success('Terminal atualizado');
      // Invalida o PREFIXO: a lista e o "quem sou eu" pendem do mesmo galho, e
      // marcar a própria máquina como retaguarda precisa chegar nos dois.
      queryClient.invalidateQueries({ queryKey: terminaisKeys.all });
    },

    onError: (error: unknown) => {
      toast.error(getErrorMessage(error as never, 'Erro ao atualizar o terminal'));
    },
  });
}
