import { defineStore } from 'pinia';
import { ref } from 'vue';

import type { Recurso } from '@/shared/config/planos';

/**
 * Recursos contratados, como o backend os reporta.
 *
 * Espelho local de `GET /licenca/status.recursos`, que por sua vez sai de
 * `app/services/plano.py` — o ponto único que decide direito no backend. Aqui
 * é só cache para a UI: quem barra de verdade é o backend, e a recusa
 * definitiva de emissão acontece na API remota da StartBig.
 *
 * Por que um store e não uma chamada por componente: `recursoDisponivel()` é
 * consumido por ~15 lugares (sidebar, PDV, produtos, serviços, OS, empresa) e
 * precisa ser SÍNCRONO — foi assim que nasceu, como constante local. Manter a
 * assinatura síncrona é o que permitiu trocar a origem do dado sem tocar em
 * nenhum consumidor.
 *
 * Vive só em memória, como o `licenca.store`: o router re-hidrata a cada 5
 * minutos e não há resíduo em disco para ficar desatualizado.
 */
export const usePlanoStore = defineStore('plano', () => {
  /**
   * Começa vazio, e vazio significa NÃO CONTRATADO.
   *
   * Fail-closed no arranque é deliberado: mostrar o módulo fiscal e escondê-lo
   * meio segundo depois é pior do que revelá-lo quando a resposta chega. O
   * backend recusaria a chamada de qualquer jeito.
   */
  const recursos = ref<Partial<Record<Recurso, boolean>>>({});

  /** True depois da primeira resposta do backend — a UI pode distinguir
   *  "ainda não sei" de "sei que não tem". */
  const carregado = ref(false);

  function definirRecursos(novos: Partial<Record<string, boolean>> | undefined) {
    recursos.value = (novos ?? {}) as Partial<Record<Recurso, boolean>>;
    carregado.value = true;
  }

  function limpar() {
    recursos.value = {};
    carregado.value = false;
  }

  return { recursos, carregado, definirRecursos, limpar };
});
