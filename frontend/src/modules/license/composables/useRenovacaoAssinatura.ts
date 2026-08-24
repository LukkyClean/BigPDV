import { computed, ref, watch, onUnmounted, type Ref } from 'vue';

import type { AxiosError } from 'axios';

import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage } from '@/shared/utils/error.utils';
import type { ApiError } from '@/shared/types/axios.types';

import {
  consultarCobranca,
  criarCobranca,
  listarPeriodos,
} from '../services/renovacao.service';
import type {
  CobrancaDataType,
  MetodoPagamento,
  RenovacaoPeriodoDataType,
} from '../schemas/renovacao.schema';

/**
 * O passo em que a tela de renovação está.
 *
 *   escolha  → método e período
 *   pix      → QR na tela, esperando o pagamento cair
 *   cartao   → checkout aberto no navegador, esperando o Stripe confirmar
 *   pago     → a licença JÁ foi revalidada e o vencimento novo está gravado
 */
export type PassoRenovacao = 'escolha' | 'pix' | 'cartao' | 'pago';

/** De 5 em 5 segundos: o contrato diz que a consulta lê o banco da API, não o
 *  gateway, então perguntar com essa frequência é barato e esperado. */
const INTERVALO_POLLING_MS = 5000;

/**
 * Teto do polling. Sem ele, uma tela esquecida aberta no balcão perguntaria o
 * dia inteiro. Quinze minutos cobre com folga o tempo de abrir o app do banco e
 * pagar; depois disso a tela oferece "já paguei, verificar agora".
 */
const LIMITE_POLLING_MS = 15 * 60 * 1000;

/** `catch` entrega `unknown`; o utilitário do projeto pede `AxiosError`. */
function mensagem(error: unknown, padrao: string): string {
  return getErrorMessage(error as AxiosError<ApiError>, padrao);
}

export function useRenovacaoAssinatura(isOpen: Ref<boolean>) {
  const toast = useToast();

  const passo = ref<PassoRenovacao>('escolha');
  const carregandoPeriodos = ref(false);
  const gerandoCobranca = ref(false);
  const verificando = ref(false);

  const periodos = ref<RenovacaoPeriodoDataType[]>([]);
  const periodoSelecionado = ref<string>('');
  const disponivel = ref(false);
  const motivoIndisponivel = ref<string | null>(null);
  const plano = ref<string | null>(null);
  const limiteTerminais = ref<number | null>(null);

  const cobranca = ref<CobrancaDataType | null>(null);
  const novoVencimento = ref<string | null>(null);

  let timer: ReturnType<typeof setInterval> | null = null;
  let iniciadoEm = 0;

  const periodoAtual = computed(
    () => periodos.value.find((p) => p.codigo === periodoSelecionado.value) ?? null,
  );

  /**
   * PIX só aparece onde o servidor disse que aceita PIX.
   *
   * Isso não é detalhe de tela: a API sobe o cartão antes do PIX, e oferecer um
   * botão que o servidor vai recusar transforma "ainda não temos" em "o sistema
   * deu erro".
   */
  const aceitaPix = computed(() => periodoAtual.value?.metodos.includes('PIX') ?? false);
  const aceitaCartao = computed(() => periodoAtual.value?.metodos.includes('CARTAO') ?? false);

  function pararPolling() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  async function carregarPeriodos() {
    carregandoPeriodos.value = true;
    try {
      const resposta = await listarPeriodos();
      disponivel.value = resposta.disponivel;
      motivoIndisponivel.value = resposta.motivo ?? null;
      periodos.value = resposta.periodos;
      plano.value = resposta.plano ?? null;
      limiteTerminais.value = resposta.limite_terminais ?? null;
      periodoSelecionado.value = resposta.periodos[0]?.codigo ?? '';
    } catch (error) {
      // Indisponibilidade já vem como `disponivel: false` sem erro. Cair aqui é
      // outra coisa — licença bloqueada, chave corrompida — e precisa ser dita.
      disponivel.value = false;
      motivoIndisponivel.value = mensagem(error, 'Não foi possível consultar os planos.');
    } finally {
      carregandoPeriodos.value = false;
    }
  }

  async function escolherMetodo(metodo: MetodoPagamento) {
    if (!periodoSelecionado.value) return;

    gerandoCobranca.value = true;
    try {
      const nova = await criarCobranca(metodo, periodoSelecionado.value);
      cobranca.value = nova;
      passo.value = metodo === 'PIX' ? 'pix' : 'cartao';
      iniciarPolling();
      return nova;
    } catch (error) {
      toast.error(mensagem(error, 'Não foi possível gerar a cobrança.'));
      return null;
    } finally {
      gerandoCobranca.value = false;
    }
  }

  /**
   * Uma verificação. Devolve `true` quando a licença renovou de fato.
   *
   * Repare no que decide: `licenca_renovada`, não `status === 'PAGA'`. O
   * pagamento ter caído no gateway não significa que esta máquina já sabe —
   * quem confirma é o vencimento gravado aqui.
   */
  async function verificarUmaVez(): Promise<boolean> {
    const id = cobranca.value?.cobranca_id;
    if (!id) return false;

    try {
      const situacao = await consultarCobranca(id);
      if (situacao.licenca_renovada) {
        novoVencimento.value = situacao.data_vencimento ?? null;
        passo.value = 'pago';
        pararPolling();
        return true;
      }
      if (situacao.status === 'EXPIRADA' || situacao.status === 'CANCELADA') {
        pararPolling();
        toast.error('A cobrança expirou. Gere uma nova para continuar.');
        passo.value = 'escolha';
        cobranca.value = null;
      }
      return false;
    } catch {
      // Silencioso de propósito: é polling. Uma falha de rede no meio do
      // caminho não pode encher a tela de toast enquanto o cliente paga.
      return false;
    }
  }

  /** O botão "já paguei" — mesma verificação, mas com resposta visível. */
  async function verificarAgora() {
    verificando.value = true;
    try {
      const renovou = await verificarUmaVez();
      if (!renovou) {
        toast.info('Pagamento ainda não identificado. Se você acabou de pagar, aguarde alguns instantes.');
      }
    } finally {
      verificando.value = false;
    }
  }

  function iniciarPolling() {
    pararPolling();
    iniciadoEm = Date.now();
    timer = setInterval(() => {
      if (Date.now() - iniciadoEm > LIMITE_POLLING_MS) {
        pararPolling();
        return;
      }
      void verificarUmaVez();
    }, INTERVALO_POLLING_MS);
  }

  function voltarParaEscolha() {
    pararPolling();
    passo.value = 'escolha';
    cobranca.value = null;
  }

  function reiniciar() {
    pararPolling();
    passo.value = 'escolha';
    cobranca.value = null;
    novoVencimento.value = null;
  }

  watch(isOpen, (aberto) => {
    if (aberto) {
      reiniciar();
      void carregarPeriodos();
    } else {
      // Fechar a tela tem que parar o polling. Sem isto, o intervalo continua
      // batendo no servidor com o modal fechado, até a página recarregar.
      pararPolling();
    }
  }, { immediate: true });

  onUnmounted(pararPolling);

  return {
    passo,
    periodos,
    periodoSelecionado,
    periodoAtual,
    disponivel,
    motivoIndisponivel,
    plano,
    limiteTerminais,
    carregandoPeriodos,
    gerandoCobranca,
    verificando,
    cobranca,
    novoVencimento,
    aceitaPix,
    aceitaCartao,
    escolherMetodo,
    verificarAgora,
    voltarParaEscolha,
  };
}
