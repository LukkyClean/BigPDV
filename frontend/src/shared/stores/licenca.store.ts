import { defineStore } from 'pinia';
import { ref } from 'vue';

/**
 * O estado "somente renovação".
 *
 * Antes, licença vencida barrava ANTES do login: a pessoa nem entrava, e a
 * única saída era um link para a página de planos. Isso trata quem deixou de
 * pagar como se fosse um erro do sistema — e, pior, esconde a saída dentro de
 * um navegador que talvez nem esteja instalado naquela máquina.
 *
 * Agora o dono entra, o sistema fica inativo e só a cobrança funciona. Quem
 * decide isso é o `router.beforeEach`, que pergunta a este flag em toda
 * navegação.
 *
 * Só `LICENCA_EXPIRADA` cai aqui. Clonagem, falta de internet e bloqueio
 * administrativo continuam na tela de erro de sempre: nenhum deles se resolve
 * pagando, e mandar essas pessoas para uma tela de pagamento é empurrá-las para
 * o lugar errado.
 *
 * Vive só em memória, de propósito: se a licença voltar a valer, some sozinho
 * na próxima verificação, sem resíduo em disco para limpar depois.
 */
export const useLicencaStore = defineStore('licenca', () => {
  const expirada = ref(false);
  const mensagem = ref('');

  function marcarExpirada(msg?: string) {
    expirada.value = true;
    mensagem.value = msg || 'Sua assinatura expirou.';
  }

  function limpar() {
    expirada.value = false;
    mensagem.value = '';
  }

  return { expirada, mensagem, marcarExpirada, limpar };
});
