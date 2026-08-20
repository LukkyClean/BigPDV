import { nextTick } from 'vue';

/**
 * Devolve o cursor à busca de produto — e confere que ele chegou lá.
 *
 * A busca é a posição de descanso do PDV: toda vez que uma tarefa termina
 * (quantidade digitada, desconto aprovado, sub-modal fechado), o cursor volta
 * para cá. Sem isso o foco fica órfão e a próxima bipada digita o código de
 * barras dentro do último campo que teve o cursor.
 *
 * A segunda tentativa no quadro seguinte não é paranoia: a venda e seus modais
 * abrem dentro de `<Transition>`, e mais de uma vez o `nextTick` chegou antes de
 * o elemento estar focável — a tela abria sem cursor em lugar nenhum e a mão
 * era obrigada a ir no mouse.
 */
export function focarBuscaDeProduto() {
  const tentar = () => {
    const input = document.querySelector<HTMLInputElement>('[data-search-products] input');
    if (!input) return false;
    input.focus();
    return document.activeElement === input;
  };

  nextTick(() => {
    if (tentar()) return;
    requestAnimationFrame(() => void tentar());
  });
}
