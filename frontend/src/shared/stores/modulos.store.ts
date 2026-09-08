import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

import { MODULOS } from '@/shared/constants/modulos.constants';

/**
 * Módulos em que "ainda não sei" significa NÃO.
 *
 * A regra normal do `temModulo` é liberar quando não há resposta útil, porque
 * negar tiraria do ar um recurso que o cliente JÁ USAVA — por token velho,
 * rede fora, ou porque a plataforma ainda não cadastrou módulo nenhum.
 *
 * NF-e não corre esse risco: é recurso novo, ninguém em campo tem, então não
 * há acesso a proteger. E errar para "tem" abriria emissão de documento
 * fiscal em nome da loja na SEFAZ — caro demais para ser o padrão.
 *
 * O backend aplica a MESMA exceção em app/core/modulos.py. Mudar de ideia
 * exige mexer nos dois: aqui só se esconde o menu, lá é que se barra a rota.
 */
const MODULOS_NEGADOS_SEM_RESPOSTA = new Set<string>([MODULOS.NFE, MODULOS.NFCE]);

/**
 * Os módulos que esta licença tem contratados.
 *
 * A lista vem dentro do JWT assinado que a plataforma emite e chega aqui pelo
 * `GET /licenca/status`, que o `router.beforeEach` já chama a cada 5 minutos.
 * Não há requisição própria: uma segunda chamada faria o menu piscar, e a
 * resposta precisa estar pronta no primeiro render da sidebar.
 *
 * Vive só em memória, de propósito. Guardar os módulos em disco criaria uma
 * segunda verdade ao lado do token — que envelhece quando o plano muda, e que
 * fica no banco da máquina do cliente, editável. Quem manda é sempre o token
 * corrente; aqui é só o eco dele nesta execução.
 *
 * `null` e `[]` NÃO são "nenhum módulo": são "ainda não sei". Ver `temModulo`.
 */
export const useModulosStore = defineStore('modulos', () => {
  const modulos = ref<string[] | null>(null);

  /**
   * Esta licença pode usar `identificador`?
   *
   * SEM RESPOSTA ÚTIL, LIBERA. São três casos, e os três exigem liberar:
   *
   * 1. O `/licenca/status` ainda não respondeu (primeiro render, ou a
   *    verificação falhou por rede). Errar para "tem" mostra um item a mais
   *    por um instante; errar para "não tem" esconderia o sistema inteiro de
   *    quem está trabalhando.
   * 2. O token é anterior aos módulos e não carrega a claim. O JWT vive 7
   *    dias, então no dia em que a trava estreia boa parte da base ainda está
   *    com token antigo — e bloquear derrubaria cliente pagante por uma
   *    semana, sem mensagem de erro nenhuma, só com o menu sumindo.
   * 3. A lista veio VAZIA. Já foi tratada como "nenhum módulo liberado", e
   *    estava errado: nenhuma licença em campo tem módulo cadastrado ainda,
   *    então toda licença chega aqui com `[]`. Bloquear nesse caso esconderia
   *    o recurso de 100% dos clientes — inclusive de quem pagou por ele —
   *    porque a PLATAFORMA ainda não foi configurada, não porque a loja
   *    deixou de contratar. Lista vazia é "não sei", não é "não tem".
   *
   * O bloqueio real acontece quando a lista vem PREENCHIDA e o identificador
   * não está nela. Aí sim a plataforma falou, e falou que esta loja não tem.
   *
   * EXCEÇÃO: `MODULOS_NEGADOS_SEM_RESPOSTA`. Ver o comentário da constante.
   */
  const temModulo = (identificador: string): boolean => {
    if (modulos.value === null || modulos.value.length === 0) {
      return !MODULOS_NEGADOS_SEM_RESPOSTA.has(identificador);
    }
    return modulos.value.includes(identificador);
  };

  /**
   * Conhecido = a plataforma já disse quais são, e disse algo.
   *
   * Lista vazia não conta: ver o caso 3 de `temModulo`.
   */
  const conhecido = computed(() => modulos.value !== null && modulos.value.length > 0);

  function definir(lista: string[] | null | undefined) {
    modulos.value = lista ?? null;
  }

  return { modulos, conhecido, temModulo, definir };
});
