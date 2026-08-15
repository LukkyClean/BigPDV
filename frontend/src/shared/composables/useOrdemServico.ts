import { computed } from 'vue';

import { useAuthStore } from '@/shared/stores/auth.store';

/**
 * Esta loja trabalha com Ordem de Serviço?
 *
 * Lê `usa_ordem_servico` de `/usuarios/me` — quem decide é o registry do
 * backend (`segmento_usa_ordem_servico`), não uma lista aqui. Assim um segmento
 * novo sem OS entra por declaração, e não editando `v-if` espalhado por dez
 * telas.
 *
 * POR QUE VEM DO /me E NÃO DE UMA QUERY PRÓPRIA: esta resposta é necessária no
 * primeiro render do menu. Uma requisição separada faria "Serviços" aparecer e
 * sumir — o pisca que o `useCapacidades` já teve que resolver com fallback.
 *
 * O PADRÃO É TER OS. Enquanto o `/me` não respondeu, e para qualquer resposta
 * sem o campo (backend mais antigo que o frontend), o valor é `true`. Errar
 * para "tem OS" mostra um menu a mais por um instante; errar para "não tem"
 * esconderia o módulo inteiro de uma oficina que estava trabalhando.
 */
export function useOrdemServico() {
  const authStore = useAuthStore();

  const usaOrdemServico = computed<boolean>(
    () => authStore.userData?.empresa?.usa_ordem_servico ?? true,
  );

  return { usaOrdemServico };
}
