import { computed } from 'vue';
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys } from '../constants/fiscal.constants';
import { useToast } from '@/shared/composables/useToast';
import type { TributacaoPadrao } from '../types/fiscal.types';

/**
 * A tributação padrão da loja.
 *
 * É o nível mais baixo da cascata (produto → regra por NCM → padrão), e o que
 * permite o lojista cadastrar produto informando só o NCM. Enquanto ninguém
 * configurar, a consulta devolve `null` e cada produto vale pelo que tem
 * gravado nele — o comportamento de antes.
 *
 * Salvar invalida o cadastro inteiro de propósito: mudar o CSOSN padrão muda
 * a nota de todo produto que herda dele, e a tela de produtos mostra a
 * procedência de cada campo.
 */
export function useTributacaoPadrao(habilitado = true) {
  const queryClient = useQueryClient();
  const toast = useToast();

  const { data, isLoading, isError } = useQuery({
    queryKey: fiscalKeys.tributacaoPadrao(),
    queryFn: () => fiscalService.obterTributacaoPadrao(),
    staleTime: 1000 * 60 * 5,
    enabled: habilitado,
  });

  const configurada = computed(() => !!data.value);
  const confirmadaEm = computed(() => data.value?.confirmado_em ?? null);

  const salvar = useMutation({
    mutationFn: (dados: Partial<TributacaoPadrao>) =>
      fiscalService.salvarTributacaoPadrao(dados),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fiscalKeys.tributacaoPadrao() });
      queryClient.invalidateQueries({ queryKey: fiscalKeys.pendencias() });
      toast.success(
        'Tributação padrão salva',
        'Os produtos que não têm tributação própria passam a seguir esta.',
      );
    },
    onError: () => {
      toast.error('Não foi possível salvar', 'Tente novamente em instantes.');
    },
  });

  return {
    tributacao: data,
    configurada,
    confirmadaEm,
    isLoading,
    isError,
    salvar,
    salvando: computed(() => salvar.isPending.value),
  };
}
