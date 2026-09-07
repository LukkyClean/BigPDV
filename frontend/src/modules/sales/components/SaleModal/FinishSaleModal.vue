<script setup lang="ts">
import { ref, computed, nextTick, watch, onUnmounted } from 'vue';
import { storeToRefs } from 'pinia';
import {
  X,
  Trash2,
  CreditCard,
  Wallet,
  QrCode,
  Banknote,
  FileText,
  RotateCcw,
  Percent,
} from 'lucide-vue-next';

import { formatCurrency } from '@/shared/utils/finance';
import {
  getPaymentDisplayName,
  inferPaymentType,
  inferPermiteParcelamento,
} from '@/shared/utils/print.utils';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import PixQrCode from '@/shared/components/commons/PixQrCode/PixQrCode.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseDateInput from '@/shared/components/ui/BaseDateInput/BaseDateInput.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import BaseCheckbox from '@/shared/components/ui/BaseCheckbox/BaseCheckbox.vue';

import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';
import { useBalcaoStore } from '@/shared/stores/balcao.store';
import PendenciasFiscaisModal from '@/shared/components/commons/PendenciasFiscaisModal.vue';
import { useEmitirFiscal } from '@/shared/composables/useEmitirFiscal';
import { useNfcePrintFlow } from '../../composables/flows/useNfcePrintFlow';
import FiscalFechamentoSection from './FiscalFechamentoSection.vue';
import { useFinishSaleModal } from '../../composables/flows/useFinishSaleModal';
import { useFinishSaleMutation } from '../../composables/mutates/useFinishSaleMutation';
import { usePaymentMethodsQuery } from '../../composables/queries/usePaymentMethodsQuery';
import {
  useJurosPagamento,
  JUROS_RESPONSAVEL_OPTIONS,
} from '@/shared/composables/useJurosPagamento';

import { documentoDoCliente } from '../../schemas/customers.schema';
import type { SaleRead } from '../../schemas/sale.schema';
import type { CardFlag } from '../../schemas/paymentSale.schema';
import type { PaymentFormReadDataType } from '@/shared/schemas/payments/payment.schema';

const props = defineProps<{
  sale: SaleRead | undefined;
}>();

const emit = defineEmits<{
  finalized: [sale: SaleRead];
}>();

const saleTotal = computed(() => props.sale?.total ?? 0);

const {
  payments,
  finishModalIsOpen,
  showPaymentDetails,
  closeFinishModal,
  addPayment,
  removePayment,
  totalPago,
  acrescimo,
  jurosLoja,
  troco,
  restante,
  canFinish,
} = useFinishSaleModal(saleTotal);

// Juros do pagamento que está sendo montado no sub-modal.
const {
  taxaInput: jurosTaxaInput,
  responsavel: jurosResponsavel,
  temJuros: jurosAtivo,
  lojaAbsorve: jurosLojaAbsorve,
  calcular: calcularJuros,
  normalizar: normalizarJuros,
  reset: resetJuros,
} = useJurosPagamento();

const finishMutation = useFinishSaleMutation();
const { formasPagamento } = usePaymentMethodsQuery();
const { permitirParcelamento, parcelasMaximas } = storeToRefs(useConfiguracoesStore());
const { modoBalcao } = storeToRefs(useBalcaoStore());

// Estado local do sub-modal de detalhes do pagamento
// `showPaymentDetails` vem do composable (era `ref` local): a hierarquia do
// Escape precisa ve-lo para nao fechar a venda inteira por cima dele.
const currentPaymentMethod = ref<PaymentFormReadDataType | null>(null);
const paymentValueReais = ref(0);
const moneyInputRef = ref();
const confirmacao = ref(false);

const paymentDetails = ref<{
  parcelas: number;
  bandeira: CardFlag | '';
  vencimento?: string;
  banco_destino?: string;
  codigo_transacao?: string;
}>({
  parcelas: 1,
  bandeira: '',
  vencimento: new Date().toISOString().split('T')[0],
  banco_destino: '',
  codigo_transacao: '',
});

// Computed values
const activePaymentMethods = computed(() =>
  formasPagamento.value.filter((fp) => fp.ativo),
);

const displaySubtotal = computed(() => formatCurrency(props.sale?.subtotal ?? 0));
const displayDiscount = computed(() => formatCurrency(props.sale?.descontos ?? 0));
const displayDelivery = computed(() => formatCurrency(props.sale?.entrega ?? 0));
const totalComAcrescimo = computed(() => saleTotal.value + acrescimo.value);
const displayTotal = computed(() => formatCurrency(totalComAcrescimo.value));
const displayTotalPago = computed(() => formatCurrency(totalPago.value));
const displayTroco = computed(() => formatCurrency(troco.value));

/**
 * Venda a prazo: parcelada, ou boleto com data de vencimento.
 *
 * É a linha que separa "recebi agora, o dinheiro está na gaveta" de "combinei
 * de receber depois". A primeira o operador confere olhando; a segunda vira
 * compromisso e merece a conferência explícita.
 */
const temPagamentoAPrazo = computed(() =>
  payments.value.some((p) => p.parcelado || !!p.vencimento),
);

/**
 * O checkbox de confirmação some no Modo Balcão — mas só na venda à vista.
 *
 * Ele custa um clique por venda, e numa adega isso é o dia inteiro conferindo
 * o que já está na mão. Em pagamento a prazo ele CONTINUA: ali a conferência
 * protege de verdade, porque o combinado é o que vai ser cobrado depois.
 */
const exigeConfirmacao = computed(() => !modoBalcao.value || temPagamentoAPrazo.value);

// --- Fiscal (NFC-e) ---
// O bloqueio vem do FiscalFechamentoSection: CSC ausente, certificado vencido
// ou venda acima do teto sem CPF. Entra no MESMO gate do botão Finalizar em
// vez de aparecer só como aviso — deixar finalizar e falhar depois na emissão
// queimaria um número da NFC-e por um impedimento que já era conhecido aqui.
const emitirFiscal = ref(false);
const documentoConsumidor = ref<string | null>(null);
const fiscalBloqueado = ref(false);
// `pendencias` e `pendenciasModalOpen` PRECISAM vir daqui: o composable liga
// a flag ao encontrar pendência, e sem alguém renderizando o modal a venda
// finalizava, o cupom não saía e NADA aparecia na tela. O operador só
// descobria no fechamento do caixa.
const {
  emitirNFCeVenda,
  isVerificando: emitindoNFCe,
  pendencias,
  pendenciasModalOpen,
} = useEmitirFiscal();

/** Nome da forma de pagamento como sai impresso no cupom. */
function resolverNomePagamento(formaId: number): string {
  const forma = formasPagamento.value.find((fp) => fp.id === formaId);
  return getPaymentDisplayName(forma?.nome ?? 'Desconhecido');
}

const { imprimirDanfeNfce } = useNfcePrintFlow(resolverNomePagamento);

// A emissão acontece com o modal ainda aberto e pode levar segundos (o
// client tem timeout de 30s). Sem isto o operador vê a tela parada sem
// saber se travou — e aperta o botão de novo com o cliente esperando.
const finalizando = computed(
  () => finishMutation.isPending.value || emitindoNFCe.value,
);

/** Documento do cliente já cadastrado na venda, quando houver. */
const documentoDoClienteDaVenda = computed(
  () => documentoDoCliente(props.sale?.cliente) || null,
);

const canFinishWithConfirmation = computed(
  () =>
    canFinish.value
    && (!exigeConfirmacao.value || confirmacao.value)
    && !fiscalBloqueado.value,
);

const paymentBaseCentavos = computed(() => Math.round(paymentValueReais.value * 100));
/** Juros do pagamento em edição. Só existe para cartão. */
const jurosDoPagamentoAtual = computed(() =>
  currentPaymentMethod.value && getMethodTipo(currentPaymentMethod.value).includes('CARTAO')
    ? calcularJuros(paymentBaseCentavos.value)
    : 0,
);
/** O que o cliente efetivamente paga: só sobe se o juros for repassado. */
const valorCobradoDoCliente = computed(
  () => paymentBaseCentavos.value + (jurosLojaAbsorve.value ? 0 : jurosDoPagamentoAtual.value),
);

// Parcelas com o valor de cada parcela já refletindo o que o cliente vai pagar.
const parcelasOptions = computed(() => {
  const options = [{ value: 1, label: 'À vista' }];
  const totalParcelar = valorCobradoDoCliente.value;
  const max = Math.max(2, parcelasMaximas.value || 12);
  for (let i = 2; i <= max; i++) {
    options.push({ value: i, label: `${i}x de ${formatCurrency(Math.round(totalParcelar / i))}` });
  }
  return options;
});

// Helpers de pagamento
function getMethodTipo(method: PaymentFormReadDataType): string {
  return method.tipo ?? inferPaymentType(method.nome);
}

function getMethodPermiteParcelamento(method: PaymentFormReadDataType): boolean {
  return method.permite_parcelamento ?? inferPermiteParcelamento(getMethodTipo(method));
}

// Exibe parcelamento quando a config permite e a forma aceita (cartão ou boleto).
function displayParcelasFor(method: PaymentFormReadDataType): boolean {
  if (!permitirParcelamento.value) return false;
  return getMethodPermiteParcelamento(method) || getMethodTipo(method) === 'BOLETO';
}

function getPaymentIcon(tipo: string) {
  switch (tipo) {
    case 'DINHEIRO':       return Banknote;
    case 'PIX':            return QrCode;
    case 'CARTAO_CREDITO': return CreditCard;
    case 'CARTAO_DEBITO':  return Wallet;
    case 'BOLETO':         return FileText;
    default:               return Banknote;
  }
}

function getPaymentIconById(id: number) {
  const method = formasPagamento.value.find((f) => f.id === id);
  return getPaymentIcon(method ? getMethodTipo(method) : '');
}

function getPaymentMethodName(formaId: number): string {
  const method = formasPagamento.value.find((fp) => fp.id === formaId);
  return getPaymentDisplayName(method?.nome ?? 'Desconhecido');
}

function getValorPorMetodo(formaId: number): number {
  return payments.value
    .filter(p => p.forma_pagamento_id === formaId)
    .reduce((sum, p) => sum + p.valor, 0);
}

function clearPayments() {
  while (payments.value.length > 0) {
    removePayment(0);
  }
}

/**
 * As setas andam pelo grid de formas de pagamento.
 *
 * O Tab só anda para FRENTE, e no Modo Balcão o foco nasce no Dinheiro — que é
 * o 4º dos 6 botões. Na prática o operador alcançava só as formas seguintes
 * (Pix, Transferência); as três de cima ficavam ATRÁS do foco e exigiam
 * Shift+Tab ou mouse. Num grid de botões a seta é o que a mão espera, e ela não
 * tira nada de quem usa o Tab.
 *
 * Não dá a volta de propósito: chegar na borda e reaparecer do outro lado faz o
 * operador perder de vista onde está, e aqui cada botão é uma forma de dinheiro
 * diferente.
 */
function navegarFormasPagamento(e: KeyboardEvent) {
  // 3 é o `grid-cols-3` do container logo abaixo — mudou lá, muda aqui.
  const COLUNAS = 3;
  const passos: Record<string, number> = {
    ArrowRight: 1,
    ArrowLeft: -1,
    ArrowDown: COLUNAS,
    ArrowUp: -COLUNAS,
  };
  const passo = passos[e.key];
  if (passo === undefined) return;

  const botoes = Array.from(
    document.querySelectorAll<HTMLButtonElement>('[data-payment-grid] button'),
  ).filter((b) => !b.disabled);
  const atual = botoes.indexOf(document.activeElement as HTMLButtonElement);
  if (atual === -1) return;

  const alvo = botoes[atual + passo];
  if (!alvo) return;

  e.preventDefault(); // senão a seta rola a coluna atrás do grid
  alvo.focus();
}

// Ações de pagamento
function handleAddPaymentClick(method: PaymentFormReadDataType) {
  currentPaymentMethod.value = method;
  paymentValueReais.value = restante.value / 100;
  paymentDetails.value = {
    parcelas: 1,
    bandeira: '',
    vencimento: new Date().toISOString().split('T')[0],
    banco_destino: '',
    codigo_transacao: '',
  };
  resetJuros();
  showPaymentDetails.value = true;
  nextTick(() => {
    if (moneyInputRef.value?.inputRef) {
      moneyInputRef.value.inputRef.select();
    }
  });
}

/**
 * O último Enter da venda.
 *
 * Confirmado o pagamento, o foco ficava no vazio: `confirmAddPayment` zera o
 * `currentPaymentMethod`, e é exatamente isso que impede o watcher de devolver
 * o foco à forma de pagamento — senão o Enter reabriria a tela do valor. Sem
 * dono, a tecla não tinha onde bater, e o operador terminava a venda no mouse:
 * no ÚLTIMO passo de um fluxo que já era todo de teclado.
 *
 * ⚠️ `aguardarSoltarTecla` NÃO é preciosismo — é o que separa os dois Enters.
 * O `MoneyInput` emite `enter` no **keydown**, então focar o botão aqui e agora
 * o entrega à MESMA tecla: o Chromium dispara o clique do botão como ação
 * padrão daquele keydown, já com o foco novo. O resultado era um Enter só
 * confirmando o pagamento E finalizando a venda — o troco aparecia e sumia
 * junto com o recibo, sem o operador conferir nada. Esperar o `keyup` faz o
 * segundo Enter ser um segundo aperto de verdade.
 *
 * Só no Modo Balcão e só com a venda paga. Fora dele o botão espera o checkbox
 * de confirmação, e roubar o foco mudaria o comportamento das lojas que já
 * rodam.
 *
 * ⚠️ O ALVO DEPENDE DO CHECKBOX. Com `exigeConfirmacao` ligado (venda a prazo:
 * cartão parcelado, boleto) o botão nasce `disabled`, e elemento desabilitado
 * não recebe foco NEM é alcançado por Tab. A versão anterior mirava o botão
 * sempre, falhava nas duas tentativas e desistia calada — o foco caía no
 * `<body>`, e como o `BaseModal` não prende o Tab, a tecla seguinte começava a
 * andar pela tela de venda ATRÁS do modal. O fluxo de teclado morria no último
 * passo, justamente onde ele mais importa. O alvo agora é o passo que de fato
 * vem a seguir: o checkbox enquanto ele não estiver marcado, o botão depois.
 */
function focarProximoPasso(aguardarSoltarTecla = false) {
  if (!modoBalcao.value || restante.value > 0) return;

  // O `data-` cai na div raiz do BaseCheckbox (fallthrough do Vue), não no
  // input — daí o ` input` no seletor. Assim o componente compartilhado, que
  // outras telas usam, fica intocado.
  const alvo = () =>
    exigeConfirmacao.value && !confirmacao.value
      ? document.querySelector<HTMLInputElement>('[data-confirmar-recebimento] input')
      : document.querySelector<HTMLButtonElement>('[data-finalizar-venda]');

  // Duas tentativas, como na busca de produto: o sub-modal sai dentro de um
  // <Transition> e o foco pode ser desfeito enquanto ele ainda desmonta.
  const tentar = () => {
    const el = alvo();
    if (!el || el.disabled) return false;
    el.focus();
    return document.activeElement === el;
  };

  const focar = () => {
    nextTick(() => {
      if (tentar()) return;
      requestAnimationFrame(() => void tentar());
    });
  };

  if (!aguardarSoltarTecla) {
    focar();
    return;
  }
  document.addEventListener('keyup', focar, { once: true });
}

function confirmAddPayment(viaTeclado = false) {
  const method = currentPaymentMethod.value;
  if (!method || paymentValueReais.value <= 0) return;

  const tipo = getMethodTipo(method);
  const baseValor = paymentBaseCentavos.value;
  const jurosAmount = jurosDoPagamentoAtual.value;
  const responsavel = jurosResponsavel.value;

  const podeParcelar = displayParcelasFor(method);
  const parcelado = podeParcelar && paymentDetails.value.parcelas > 1;

  let detalhes: Record<string, unknown> | undefined;
  if (tipo.includes('TRANSFERENCIA') && (paymentDetails.value.banco_destino || paymentDetails.value.codigo_transacao)) {
    detalhes = {
      banco_destino: paymentDetails.value.banco_destino || undefined,
      codigo_transacao: paymentDetails.value.codigo_transacao || undefined,
    };
  }

  addPayment({
    forma_pagamento_id: method.id,
    parcelado,
    qtd_parcelas: parcelado ? paymentDetails.value.parcelas : null,
    // Quando a loja absorve, o cliente paga só a base — o juros fica registrado
    // à parte, como custo, e não infla o total da venda.
    valor: responsavel === 'LOJA' ? baseValor : baseValor + jurosAmount,
    juros_valor: jurosAmount,
    juros_responsavel: responsavel,
    bandeira_cartao: tipo.includes('CARTAO') ? (paymentDetails.value.bandeira || undefined) : undefined,
    vencimento: tipo === 'BOLETO' ? paymentDetails.value.vencimento : undefined,
    detalhes,
  });

  showPaymentDetails.value = false;
  currentPaymentMethod.value = null;
  focarProximoPasso(viaTeclado);
}

function handleRemovePayment(index: number) {
  removePayment(index);
}

/**
 * Enter também marca o recebimento.
 *
 * Checkbox em HTML só alterna com ESPAÇO — o Enter não faz nada, e isso é o
 * navegador, não uma escolha nossa. Só que o resto da venda é todo Enter (o
 * `MoneyInput` confirma no Enter, o botão finaliza no Enter), e um único passo
 * exigindo outra tecla no meio do fluxo é o bastante para a mão do operador
 * parar e procurar o mouse.
 *
 * `marcadoViaEnter` existe para o watcher abaixo saber que precisa esperar a
 * tecla subir. Sem isso o MESMO Enter marcaria o checkbox e finalizaria a
 * venda: é o Enter duplo que o `aguardarSoltarTecla` já descreve.
 */
const marcadoViaEnter = ref(false);

function marcarRecebimentoComEnter(e: KeyboardEvent) {
  if (confirmacao.value) return;
  e.preventDefault();
  marcadoViaEnter.value = true;
  confirmacao.value = true;
}

/**
 * Marcou o recebimento, o foco vai para o botão.
 *
 * Sem isto o Tab ainda passaria por "Cancelar" antes de chegar em "Finalizar",
 * e quem acabou de conferir o valor tem um só próximo passo — não dois.
 *
 * No Espaço não espera o `keyup`: o Chromium dispara o clique do checkbox no
 * keyup, então quando este watcher roda a tecla JÁ subiu. E esperar deixaria o
 * foco preso quando o checkbox fosse marcado no mouse, que não gera keyup
 * nenhum. No Enter é o contrário — ali a tecla ainda está descendo.
 */
watch(confirmacao, (marcado) => {
  if (!marcado) return;
  const aguardar = marcadoViaEnter.value;
  marcadoViaEnter.value = false;
  focarProximoPasso(aguardar);
});

/**
 * Zerar devolve o foco às formas de pagamento.
 *
 * O botão "Zerar" tem `:disabled="payments.length === 0"` — ele se desabilita
 * no mesmo clique que esvazia a lista. Quem apertou pelo teclado ficava com o
 * foco num elemento morto, que cai no `<body>`: o mesmo foco órfão do
 * `focarProximoPasso`, em outro canto da tela.
 *
 * O destino é o "Dinheiro", a mesma posição de descanso de quando o modal
 * abre — e que só agora volta a aceitar foco, porque o grid fica `disabled`
 * enquanto o restante é zero.
 */
function zerarPagamentos() {
  clearPayments();
  if (!modoBalcao.value) return;
  nextTick(() => {
    document.querySelector<HTMLButtonElement>('[data-forma-dinheiro]')?.focus();
  });
}

/**
 * O Tab não sai do modal.
 *
 * O `BaseModal` não prende o foco. Chegando ao último elemento, o Tab seguinte
 * ia parar na tela de venda ATRÁS do modal — invisível, sob o backdrop, e sem
 * caminho de volta a não ser o mouse. Aqui ele dá a volta e recomeça.
 *
 * A ordem é a do DOM, de propósito: formas → Zerar → lixeiras → checkbox →
 * Cancelar → Finalizar. Uma ordem inventada brigaria com a leitura da tela e
 * com o leitor de tela, e é mais uma coisa para desencontrar quando alguém
 * mexer no layout.
 *
 * Elemento `disabled` fica de fora porque o navegador já o pula — é assim que
 * o grid de formas some do ciclo com a venda paga e o Finalizar some enquanto
 * o checkbox não foi marcado.
 *
 * Só no Modo Balcão, como todo o resto do teclado neste arquivo: prender o Tab
 * é correto em qualquer modal, mas promover isso ao `BaseModal` muda 37 telas
 * de uma vez e merece ser decidido à parte.
 */
function prenderTab(e: KeyboardEvent) {
  if (e.key !== 'Tab' || showPaymentDetails.value) return;

  const focaveis = Array.from(
    document.querySelectorAll<HTMLElement>(
      '[data-finalizar-modal] button, [data-finalizar-modal] input, [data-finalizar-modal] select, [data-finalizar-modal] textarea',
    ),
  ).filter((el) => !(el as HTMLButtonElement).disabled && el.offsetParent !== null);

  if (focaveis.length === 0) return;

  const atual = focaveis.indexOf(document.activeElement as HTMLElement);
  const passo = e.shiftKey ? -1 : 1;
  // `atual === -1` é o foco perdido no <body>: recomeça em vez de ignorar.
  const proximo =
    atual === -1 ? focaveis[0] : focaveis[(atual + passo + focaveis.length) % focaveis.length];

  e.preventDefault();
  proximo.focus();
}

watch(finishModalIsOpen, (aberto) => {
  if (aberto && modoBalcao.value) document.addEventListener('keydown', prenderTab);
  else document.removeEventListener('keydown', prenderTab);
});

onUnmounted(() => document.removeEventListener('keydown', prenderTab));

/**
 * Modo Balcão: o foco nasce no botão "Dinheiro".
 *
 * O sub-modal de valor já resolve o resto sozinho — abre com o restante
 * preenchido e SELECIONADO, e o Enter confirma. O que faltava era só chegar
 * nele sem o mouse: sem isto, o operador larga o teclado só para clicar na
 * forma de pagamento que ele usa em toda venda.
 *
 * O F6 já existia (`useSaleShortcuts`), mas foca o PRIMEIRO botão do grid, que
 * hoje é Boleto. Aqui a mira é a espécie.
 */
watch(finishModalIsOpen, (aberto) => {
  if (!aberto || !modoBalcao.value) return;
  nextTick(() => {
    document.querySelector<HTMLButtonElement>('[data-forma-dinheiro]')?.focus();
  });
});

/**
 * Quem abriu o sub-modal de pagamento, para receber o foco de volta.
 *
 * Fechar uma tela nao pode custar o foco: sem isto o Esc devolvia a Finalizar
 * Venda com o foco no vazio, e a unica saida era o mouse -- justamente o que o
 * caminho de teclado existe para evitar.
 *
 * SO O CANCELAMENTO devolve o foco. Confirmar um pagamento zera
 * `currentPaymentMethod`; cancelar (Esc, botao Cancelar, X) nao -- e e essa
 * diferenca que distingue os dois aqui. Devolver o foco tambem na confirmacao
 * quebraria o "Enter, Enter" do Modo Balcao: o segundo Enter cairia na forma de
 * pagamento e reabriria esta mesma tela em vez de finalizar a venda.
 */
let origemDoFoco: HTMLElement | null = null;

watch(showPaymentDetails, (aberto, estavaAberto) => {
  if (aberto) {
    origemDoFoco = document.activeElement as HTMLElement | null;
    return;
  }
  if (!estavaAberto) return;

  const alvo = origemDoFoco;
  origemDoFoco = null;
  if (!alvo || currentPaymentMethod.value === null) return;

  // Duas tentativas, como na busca de produto: o sub-modal sai dentro de um
  // <Transition>, e um focus() disparado enquanto ele ainda esta desmontando
  // pode ser desfeito pelo proprio navegador.
  nextTick(() => {
    if (!alvo.isConnected) return;
    alvo.focus();
    if (document.activeElement !== alvo) {
      requestAnimationFrame(() => {
        if (alvo.isConnected) alvo.focus();
      });
    }
  });
});

function handleCloseFinishModal() {
  confirmacao.value = false;
  closeFinishModal();
}

function handleFinish() {
  if (!props.sale || !canFinishWithConfirmation.value) return;

  finishMutation.mutate(
    { saleId: props.sale.id, payments: payments.value, acrescimo: acrescimo.value },
    {
      onSuccess: async (finishedSale) => {
        confirmacao.value = false;

        // A venda já está finalizada; a NFC-e vem DEPOIS e de propósito.
        // Só uma venda finalizada pode gerar cupom, e uma recusa da SEFAZ não
        // pode desfazer o recebimento que já aconteceu no caixa — o operador
        // resolve a nota pelo Centro Fiscal, com o dinheiro já na gaveta.
        if (emitirFiscal.value) {
          const documento = await emitirNFCeVenda(
            finishedSale.id, documentoConsumidor.value,
          );
          // Cupom só quando a SEFAZ autorizou. Imprimir um DANFE de nota
          // rejeitada entregaria ao cliente um papel que parece fiscal e não é.
          if (documento) {
            await imprimirDanfeNfce(finishedSale, documento, {
              documentoConsumidor: documentoConsumidor.value,
            });
          }
        }

        closeFinishModal();
        emit('finalized', finishedSale);
      },
    },
  );
}
</script>

<template>
  <BaseModal :is-open="finishModalIsOpen" title="Finalizar Venda" size="3xl" overflow="hidden">
    <template #header>
      <div data-finalizar-modal class="flex items-center justify-between px-6 py-4 border-b border-zinc-200">
        <h2 class="text-xl font-bold text-zinc-800">Finalizar Venda</h2>
        <button
          type="button"
          class="p-2 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
          @click="handleCloseFinishModal"
        >
          <X :size="20" />
        </button>
      </div>
    </template>

    <div data-finalizar-modal class="flex flex-col gap-4 h-[calc(90vh-140px)]">

      <!-- Linha principal: esq (formas + pagamentos) + dir (resumo) -->
      <div class="grid grid-cols-2 gap-4 flex-1 min-h-0">

        <!-- Coluna esquerda: formas de pagamento + lista -->
        <div class="flex flex-col gap-2 min-h-0">

          <!-- Formas de pagamento (compact 3-col) -->
          <div class="shrink-0">
            <p class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide mb-1.5">Selecionar Forma de Pagamento</p>
            <div data-payment-grid class="grid grid-cols-3 gap-1.5" @keydown="navegarFormasPagamento">
              <button
                v-for="method in activePaymentMethods"
                :key="method.id"
                type="button"
                :data-forma-dinheiro="getMethodTipo(method) === 'DINHEIRO' ? '' : undefined"
                :disabled="restante <= 0"
                class="flex flex-col items-center justify-center p-1.5 rounded-lg border-2 transition-all gap-0.5 disabled:opacity-40 disabled:cursor-not-allowed"
                :class="getValorPorMetodo(method.id) > 0
                  ? 'border-brand-primary bg-brand-primary/5 text-brand-primary'
                  : 'border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-500 hover:border-zinc-300'"
                @click="handleAddPaymentClick(method)"
              >
                <component :is="getPaymentIcon(getMethodTipo(method))" :size="14" />
                <span class="text-[9px] font-medium text-center leading-tight">
                  {{ getPaymentDisplayName(method.nome) }}
                </span>
                <span
                  class="text-[9px] font-bold tabular-nums"
                  :class="getValorPorMetodo(method.id) > 0 ? 'text-brand-primary' : 'text-zinc-300'"
                >
                  {{ getValorPorMetodo(method.id) > 0 ? formatCurrency(getValorPorMetodo(method.id)) : '—' }}
                </span>
              </button>
            </div>
          </div>

          <!-- Lista de pagamentos -->
          <div class="border border-zinc-200 rounded-xl overflow-hidden flex flex-col flex-1 min-h-0">
            <div class="bg-zinc-100 px-4 py-2 border-b border-zinc-200 flex items-center justify-between shrink-0">
              <p class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wide">Pagamentos</p>
              <div class="flex items-center gap-2">
                <span class="text-[10px] text-zinc-400">{{ payments.length }} item(s)</span>
                <button
                  type="button"
                  :disabled="payments.length === 0"
                  class="flex items-center gap-1 text-[10px] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  :class="payments.length > 0 ? 'text-red-400 hover:text-red-600 cursor-pointer' : 'text-zinc-400'"
                  @click="zerarPagamentos"
                >
                  <RotateCcw :size="11" />
                  Zerar
                </button>
              </div>
            </div>

            <div class="flex-1 overflow-y-auto p-3 space-y-2">
              <div v-if="payments.length === 0" class="h-full flex items-center justify-center py-8">
                <p class="text-xs text-zinc-400">Nenhum pagamento registrado</p>
              </div>

              <div
                v-for="(payment, idx) in payments"
                :key="idx"
                class="flex items-center justify-between p-2.5 bg-white border border-zinc-100 rounded-lg shadow-sm"
              >
                <div class="flex items-center gap-2.5">
                  <div class="p-1.5 bg-zinc-50 rounded-lg text-brand-primary">
                    <component :is="getPaymentIconById(payment.forma_pagamento_id)" :size="14" />
                  </div>
                  <div>
                    <p class="text-xs font-semibold text-zinc-700">
                      {{ getPaymentMethodName(payment.forma_pagamento_id) }}
                      <span v-if="payment.parcelado" class="font-normal text-zinc-400"> · {{ payment.qtd_parcelas }}x</span>
                      <span v-if="payment.bandeira_cartao" class="font-normal text-zinc-400"> · {{ payment.bandeira_cartao }}</span>
                    </p>
                    <template v-if="(payment.juros_valor ?? 0) > 0 && payment.juros_responsavel !== 'LOJA'">
                      <p class="text-[10px] text-zinc-400">
                        Venda: {{ formatCurrency(payment.valor - (payment.juros_valor ?? 0)) }}
                        <span class="text-amber-500"> + Juros: {{ formatCurrency(payment.juros_valor ?? 0) }}</span>
                        = {{ formatCurrency(payment.valor) }}
                      </p>
                    </template>
                    <template v-else-if="(payment.juros_valor ?? 0) > 0">
                      <p class="text-[10px] text-zinc-400">
                        {{ formatCurrency(payment.valor) }}
                        <span class="text-rose-500"> · loja absorve {{ formatCurrency(payment.juros_valor ?? 0) }}</span>
                      </p>
                    </template>
                    <template v-else>
                      <p class="text-[10px] text-zinc-400">{{ formatCurrency(payment.valor) }}</p>
                    </template>
                  </div>
                </div>
                <button
                  type="button"
                  class="text-zinc-300 hover:text-red-500 p-1.5 cursor-pointer transition-colors"
                  @click="handleRemovePayment(idx)"
                >
                  <Trash2 :size="14" />
                </button>
              </div>
            </div>
          </div>

        </div><!-- fim coluna esquerda -->

        <!-- Coluna direita: Resumo financeiro -->
        <div class="border border-zinc-200 rounded-xl overflow-hidden flex flex-col">
          <div class="bg-zinc-100 px-4 py-2 border-b border-zinc-200">
            <p class="text-[10px] font-semibold text-zinc-500 uppercase tracking-wide">Resumo Financeiro</p>
          </div>
          <div class="p-4 space-y-2.5 overflow-y-auto flex-1 no-scrollbar">

            <div class="flex justify-between items-center">
              <span class="text-xs text-zinc-500">Subtotal dos itens</span>
              <span class="text-base font-semibold text-zinc-800">{{ displaySubtotal }}</span>
            </div>

            <div class="flex justify-between items-center">
              <span class="text-xs text-zinc-500">Desconto</span>
              <span
                class="text-base"
                :class="(sale?.descontos ?? 0) > 0 ? 'font-semibold text-emerald-600' : 'font-medium text-zinc-400'"
              >
                {{ (sale?.descontos ?? 0) > 0 ? `- ${displayDiscount}` : '—' }}
              </span>
            </div>

            <div v-if="(sale?.entrega ?? 0) > 0" class="flex justify-between items-center">
              <span class="text-xs text-zinc-500">Entrega</span>
              <span class="text-base font-medium text-zinc-700">{{ displayDelivery }}</span>
            </div>

            <div v-if="acrescimo > 0" class="flex justify-between items-center">
              <span class="text-xs text-amber-600 flex items-center gap-1">
                <Percent :size="12" /> Juros repassado
              </span>
              <span class="text-base font-medium text-amber-600">+ {{ formatCurrency(acrescimo) }}</span>
            </div>

            <div v-if="jurosLoja > 0" class="flex justify-between items-center">
              <span class="text-xs text-rose-600 flex items-center gap-1">
                <Percent :size="12" /> Juros absorvido pela loja
              </span>
              <span class="text-base font-medium text-rose-600">{{ formatCurrency(jurosLoja) }}</span>
            </div>

            <!-- Divisor -->
            <div class="border-t border-zinc-200 pt-2.5 space-y-3">
              <div class="flex justify-between items-center">
                <span class="text-sm font-bold text-zinc-700">Total a pagar</span>
                <span class="text-xl font-bold text-brand-primary">{{ displayTotal }}</span>
              </div>

              <div
                class="flex justify-between items-center font-semibold"
                :class="totalPago >= totalComAcrescimo ? 'text-emerald-600' : 'text-zinc-400'"
              >
                <span class="text-sm">Total recebido</span>
                <span class="text-lg">{{ displayTotalPago }}</span>
              </div>

              <!-- Breakdown de devolução (só exibe quando há juros, de qualquer origem) -->
              <div
                v-if="(acrescimo > 0 || jurosLoja > 0) && totalPago > 0"
                class="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 space-y-1"
              >
                <p class="text-[10px] font-semibold text-amber-700 uppercase tracking-wide">Em caso de devolução</p>
                <div v-if="acrescimo > 0" class="flex justify-between items-center text-xs text-zinc-600">
                  <span>Venda (sem juros)</span>
                  <span class="font-semibold">{{ formatCurrency(totalPago - acrescimo) }}</span>
                </div>
                <p v-if="acrescimo > 0" class="text-[10px] text-amber-600">
                  Juros pagos à operadora pelo cliente: {{ formatCurrency(acrescimo) }}
                </p>
                <p v-if="jurosLoja > 0" class="text-[10px] text-rose-600">
                  A loja não recupera {{ formatCurrency(jurosLoja) }} de juros absorvidos.
                </p>
              </div>

              <div v-if="restante > 0" class="flex justify-between items-center font-bold text-red-500">
                <span class="text-sm">Faltam</span>
                <span class="text-lg">{{ formatCurrency(restante) }}</span>
              </div>

              <!-- Troco em fonte de balcão: no Modo Balcão ele é o número mais
                   importante da tela — o operador confere com a mão na gaveta,
                   muitas vezes de pé e de longe. E aparece MESMO ZERADO: "Troco
                   R$ 0,00" é a confirmação de que o valor bateu, não ruído. -->
              <div
                v-if="modoBalcao && restante === 0 && payments.length > 0"
                class="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-center"
              >
                <p class="text-[10px] font-bold text-amber-700 uppercase tracking-widest">Troco</p>
                <p class="text-4xl font-extrabold text-amber-600 tabular-nums leading-tight">
                  {{ displayTroco }}
                </p>
              </div>

              <div v-else-if="troco > 0" class="flex justify-between items-center font-bold text-amber-500">
                <span class="text-sm">Troco</span>
                <span class="text-lg">{{ displayTroco }}</span>
              </div>
            </div>
          </div>
        </div>

      </div><!-- fim grid -->

      <!-- Bloco fiscal: emitir cupom? CPF na nota? -->
      <FiscalFechamentoSection
        :total-centavos="totalComAcrescimo"
        :documento-cliente="documentoDoClienteDaVenda"
        @update:emitir-fiscal="emitirFiscal = $event"
        @update:documento="documentoConsumidor = $event"
        @update:bloqueado="fiscalBloqueado = $event"
      />

      <!-- Confirmação + botões (dentro do body) -->
      <div class="flex items-center gap-4 pt-3 border-t border-zinc-200 shrink-0">
        <BaseCheckbox
          v-if="exigeConfirmacao"
          v-model="confirmacao"
          data-confirmar-recebimento
          @keydown.enter="marcarRecebimentoComEnter"
          :label="`Confirmo o recebimento de ${displayTotalPago}`"
        />
        <div class="flex gap-3 ml-auto">
          <BaseButton variant="secondary" class="px-5" @click="handleCloseFinishModal">Cancelar</BaseButton>
          <BaseButton
            variant="primary"
            data-finalizar-venda
            :is-loading="finalizando"
            :disabled="!canFinishWithConfirmation || finalizando"
            class="px-6 shadow-lg shadow-brand-primary/20"
            @click="handleFinish"
          >
            Finalizar Venda
          </BaseButton>
        </div>
      </div>

    </div>
    <template #footer><span></span></template>
  </BaseModal>

  <!-- Sub-modal: Detalhes do pagamento -->
  <BaseModal
    :is-open="showPaymentDetails && !!currentPaymentMethod"
    :title="currentPaymentMethod ? getPaymentDisplayName(currentPaymentMethod.nome) : ''"
    subtitle="Detalhes do pagamento"
    size="sm"
    @close="showPaymentDetails = false"
  >
    <div v-if="currentPaymentMethod" class="space-y-4">
      <div class="flex items-center gap-3 pb-3 border-b border-zinc-100">
        <div class="p-3 bg-brand-primary/10 rounded-xl">
          <component :is="getPaymentIcon(getMethodTipo(currentPaymentMethod))" :size="22" class="text-brand-primary" />
        </div>
        <div>
          <p class="font-bold text-zinc-800">{{ getPaymentDisplayName(currentPaymentMethod.nome) }}</p>
          <p class="text-xs text-zinc-500">Restante: {{ formatCurrency(restante) }}</p>
        </div>
      </div>

      <BaseMoneyInput
        ref="moneyInputRef"
        v-model="paymentValueReais"
        label="Inserir Valor"
        @enter="confirmAddPayment(true)"
      />

      <!-- Parcelamento (cartão de crédito / boleto) -->
      <div v-if="displayParcelasFor(currentPaymentMethod)">
        <BaseSelect
          v-model="paymentDetails.parcelas"
          label="Parcelamento"
          :options="parcelasOptions"
        />
      </div>

      <!-- Boleto: data de vencimento -->
      <div v-if="getMethodTipo(currentPaymentMethod) === 'BOLETO'" class="pt-1">
        <BaseDateInput
          v-model="paymentDetails.vencimento"
          label="Data de Vencimento"
        />
      </div>

      <!-- Cartão: bandeira + taxa de juros -->
      <div v-if="getMethodTipo(currentPaymentMethod).includes('CARTAO')" class="space-y-3">
        <BaseSelect
          v-model="paymentDetails.bandeira"
          label="Bandeira (Opcional)"
          :options="[
            { value: '', label: 'Não informada' },
            { value: 'VISA', label: 'Visa' },
            { value: 'MASTERCARD', label: 'Mastercard' },
            { value: 'ELO', label: 'Elo' },
            { value: 'OUTROS', label: 'Outros' },
          ]"
        />
        <div class="flex justify-between items-center gap-3">
          <label class="text-sm font-medium text-zinc-600 flex items-center gap-1.5">
            <Percent :size="14" /> Taxa de Juros
          </label>
          <div class="w-24">
            <BaseInput
              v-model="jurosTaxaInput"
              type="text"
              inputmode="decimal"
              placeholder="0"
              @blur="normalizarJuros()"
            />
          </div>
        </div>

        <div v-if="jurosAtivo" class="space-y-2">
          <BaseSelect
            v-model="jurosResponsavel"
            label="Quem paga o juros"
            :options="JUROS_RESPONSAVEL_OPTIONS"
          />
          <div
            class="flex justify-between text-xs px-3 py-2 rounded-lg"
            :class="jurosLojaAbsorve ? 'text-rose-600 bg-rose-50' : 'text-amber-600 bg-amber-50'"
          >
            <span>{{ jurosLojaAbsorve ? 'Cliente paga' : 'Valor com juros' }}</span>
            <span class="font-semibold">{{ formatCurrency(valorCobradoDoCliente) }}</span>
          </div>
          <p v-if="jurosLojaAbsorve" class="text-[11px] text-rose-600 px-1">
            A loja absorve {{ formatCurrency(jurosDoPagamentoAtual) }} de juros — o cliente não é
            cobrado a mais e o recebimento da loja fica menor.
          </p>
        </div>
      </div>

      <!-- Transferência: conta de destino + NSU -->
      <div v-if="getMethodTipo(currentPaymentMethod).includes('TRANSFERENCIA')" class="space-y-3">
        <BaseSelect
          v-model="paymentDetails.banco_destino"
          label="Conta de Destino (Opcional)"
          :options="[
            { value: '', label: 'Não informada' },
            { value: 'ITAU', label: 'Itaú' },
            { value: 'BRADESCO', label: 'Bradesco' },
            { value: 'BB', label: 'Banco do Brasil' },
            { value: 'CAIXA', label: 'Caixa Econômica' },
            { value: 'SICREDI', label: 'Sicredi' },
            { value: 'NUBANK', label: 'Nubank' },
            { value: 'OUTROS', label: 'Outros' },
          ]"
        />
        <BaseInput
          v-model="paymentDetails.codigo_transacao"
          type="text"
          label="Código da Transação/NSU (Opcional)"
          placeholder="Ex: E123456789"
        />
      </div>

      <!--
        PIX: QR já com o valor deste pagamento — não com o total da venda. Numa
        venda dividida, cada PIX cobra a sua parte.
      -->
      <div v-if="getMethodTipo(currentPaymentMethod) === 'PIX'" class="py-1">
        <PixQrCode :valor-centavos="paymentBaseCentavos" />
      </div>

      <div class="flex gap-3 pt-2">
        <BaseButton variant="secondary" class="flex-1" type="button" @click="showPaymentDetails = false">Cancelar</BaseButton>
        <BaseButton
          variant="primary"
          class="flex-1"
          type="button"
          :disabled="paymentValueReais <= 0"
          @click="confirmAddPayment()"
        >
          Confirmar
        </BaseButton>
      </div>
    </div>

    <template #footer><span></span></template>
  </BaseModal>

  <!--
    Pendência fiscal no balcão: a venda está registrada e paga, mas o cupom não
    pode ser emitido. Precisa aparecer AQUI, no momento em que acontece.
  -->
  <PendenciasFiscaisModal
    :is-open="pendenciasModalOpen"
    :pendencias="pendencias"
    titulo="Não foi possível emitir o cupom fiscal"
    @close="pendenciasModalOpen = false"
  />
</template>
