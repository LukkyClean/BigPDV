import { ref } from 'vue';

/**
 * Um pedido para abrir o caixa, vindo de fora da barra do caixa.
 *
 * O modal de abertura vive na `CaixaBar`, junto com a validação do PIN de
 * gerente e o tratamento das sentinelas. Quem está fora dela — a `SalesView`,
 * quando avisa que o caixa está fechado — precisa disparar aquele fluxo SEM
 * duplicá-lo: um segundo lugar chamando `AbrirCaixaModal` seria um segundo lugar
 * para esquecer o PIN.
 *
 * Por isso o que viaja aqui é um PEDIDO, não o estado do modal. A `CaixaBar`
 * observa o contador e chama a própria `pedirAberturaDeCaixa`, que continua
 * sendo a única dona da regra.
 *
 * Contador e não booleano: dois pedidos seguidos precisam disparar duas vezes.
 * Com um `ref<boolean>` o segundo `true` não muda nada e o watcher não roda —
 * o operador clicaria de novo e a tela ficaria parada.
 *
 * ⚠️ Só funciona onde a `CaixaBar` está montada. Numa máquina RETAGUARDA sem
 * turno ela não renderiza o convite de abertura, de propósito: aquele PC não é
 * um caixa. Quem chama daqui precisa checar isso antes de oferecer o botão,
 * senão oferece uma ação que não acontece.
 */
const pedidoDeAbertura = ref(0);

export function useAberturaCaixa() {
  function solicitarAbertura() {
    pedidoDeAbertura.value += 1;
  }

  return { pedidoDeAbertura, solicitarAbertura };
}
