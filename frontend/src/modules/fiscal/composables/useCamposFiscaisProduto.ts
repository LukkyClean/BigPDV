import { computed } from 'vue';
import { useQuery } from '@tanstack/vue-query';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys } from '../constants/fiscal.constants';

/**
 * Quais campos fiscais o cadastro de produto mostra e exige.
 *
 * Quem decide é o backend, a partir do CRT da empresa — o mesmo `obter_crt`
 * que a emissão usa. A tela fazia `regime.includes('Simples Nacional')`, que
 * errava o CRT 2 (Simples com excesso de sublimite usa CST, não CSOSN) e, sem
 * regime preenchido, mostrava CST e CSOSN juntos.
 *
 * FALHA NÃO ESCONDE CAMPO. Se a consulta não responder, `mostrar()` devolve
 * `true` para tudo: sumir com um campo obrigatório por causa de um erro de
 * rede produziria um cadastro incompleto que ninguém consegue explicar. O
 * contrário — mostrar um campo a mais — custa uma pergunta ao contador.
 *
 * O regime só muda no cadastro da empresa, então o dado fica fresco por meia
 * hora em vez de ser buscado a cada abertura do modal.
 */
export function useCamposFiscaisProduto(habilitado = true) {
  const { data, isLoading } = useQuery({
    queryKey: fiscalKeys.camposProduto(),
    queryFn: () => fiscalService.camposProduto(),
    staleTime: 1000 * 60 * 30,
    retry: 1,
    enabled: habilitado,
  });

  const regime = computed(() => data.value?.regime ?? '');
  const regimeConhecido = computed(() => !!data.value);
  const usaCsosn = computed(() => data.value?.usa_csosn ?? false);

  /** O campo aparece na tela? Sem resposta do servidor, aparece. */
  function mostrar(campo: string): boolean {
    return data.value?.campos?.[campo]?.visivel ?? true;
  }

  /** O campo é exigido? Sem resposta do servidor, não é. */
  function obrigatorio(campo: string): boolean {
    return data.value?.campos?.[campo]?.obrigatorio ?? false;
  }

  return { regime, regimeConhecido, usaCsosn, mostrar, obrigatorio, isLoading };
}
