/**
 * @fileoverview Store do Modo Balcão.
 * @description Configuração LOCAL por PC (persiste em localStorage, não no
 * backend), pela mesma razão da configuração de impressão: o balcão é
 * característica da MÁQUINA, não da empresa. O PC da frente atende fila; o do
 * escritório emite a mesma venda com calma. Guardar isso na empresa obrigaria as
 * duas máquinas a concordarem.
 *
 * O QUE ESTE MODO É: um acelerador de fluxo para venda de balcão. Ele não muda
 * nenhuma regra do backend — nenhuma trava, nenhum valor, nenhuma permissão.
 * Tudo que ele faz é pular passos que o operador de balcão repetiria em toda
 * venda (escolher cliente, voltar para a lista, marcar confirmação).
 *
 * O QUE ELE NÃO É: um segmento nem um perfil de loja. Desligado — que é o
 * padrão — o módulo de vendas se comporta exatamente como sempre se comportou.
 * É essa inércia que permite ligá-lo numa adega sem tocar nas lojas de
 * assistência, oficina e serigrafia que já rodam.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'startbig-modo-balcao'

/**
 * Lê a chave do disco. Desligado é o padrão em qualquer dúvida: um localStorage
 * corrompido ou ausente não pode ligar sozinho um modo que muda o fluxo da
 * venda numa loja que nunca pediu por ele.
 */
function carregarDoDisco(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

export const useBalcaoStore = defineStore('balcao', () => {
  // Lido na criação do store, não num `carregar()` chamado no boot: é um
  // booleano só, e assim nenhum arquivo de inicialização precisa ser tocado.
  const modoBalcao = ref<boolean>(carregarDoDisco())

  function definir(ativo: boolean) {
    modoBalcao.value = ativo
    try {
      localStorage.setItem(STORAGE_KEY, String(ativo))
    } catch {
      // Sem localStorage (modo privado, política de grupo) o modo continua
      // valendo para esta sessão. Perder a preferência é bem melhor do que
      // derrubar a tela de vendas por causa dela.
    }
  }

  function alternar() {
    definir(!modoBalcao.value)
  }

  return { modoBalcao, definir, alternar }
})
