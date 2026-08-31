<script setup lang="ts">
/**
 * @component RenovarAssinaturaModal
 * @description Renovação da assinatura do StartBig, pela própria loja.
 *
 * NÃO confundir com `shared/components/commons/PixQrCode`. Aquele monta o BR
 * Code com a chave PIX **da loja**, para o cliente dela pagar. Aqui o sentido é
 * o inverso: a loja é quem paga, e o código vem pronto do servidor. Reaproveitar
 * aquele componente aqui geraria um QR que manda o dinheiro para a própria loja.
 *
 * Preço, período e liberação são decididos no servidor. Esta tela pergunta,
 * mostra e espera — nunca calcula valor nem data.
 */
import { computed, ref, toRef, watch, nextTick } from 'vue';
import { CreditCard, QrCode, Copy, Check, ExternalLink, RefreshCw, PartyPopper } from 'lucide-vue-next';
import * as QRCode from 'qrcode';
import { openUrl } from '@tauri-apps/plugin-opener';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { useToast } from '@/shared/composables/useToast';
import { formatCurrency } from '@/shared/utils/finance';
import { formatData } from '@/shared/utils/date.utils';
import { LINKS } from '@/shared/config/links';

import { useRenovacaoAssinatura } from '../composables/useRenovacaoAssinatura';

interface Props {
  isOpen: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{ close: [] }>();

const isOpen = toRef(props, 'isOpen');
const toast = useToast();

const {
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
} = useRenovacaoAssinatura(isOpen);

const canvasRef = ref<HTMLCanvasElement | null>(null);
const copiado = ref(false);

/**
 * Desenha o QR a partir do copia-e-cola que o servidor mandou.
 *
 * Se o servidor mandar a imagem pronta (`qr_code_base64`), ela vence: quem
 * gerou a cobrança sabe melhor do que nós como ela deve ser lida.
 */
watch(
  () => cobranca.value?.pix_copia_e_cola,
  async (payload) => {
    if (!payload || cobranca.value?.qr_code_base64) return;
    await nextTick();
    if (!canvasRef.value) return;
    try {
      await QRCode.toCanvas(canvasRef.value, payload, { width: 208, margin: 1 });
    } catch {
      // Sem QR o cliente ainda tem o copia-e-cola logo abaixo — que é, no fim,
      // o caminho que mais gente usa no celular.
    }
  },
  { immediate: true },
);

async function copiarCodigo() {
  const codigo = cobranca.value?.pix_copia_e_cola;
  if (!codigo) return;

  try {
    await navigator.clipboard.writeText(codigo);
    copiado.value = true;
    toast.success('Código PIX copiado');
    setTimeout(() => { copiado.value = false; }, 2000);
  } catch {
    toast.error('Não foi possível copiar. Selecione o código e copie manualmente.');
  }
}

async function pagarComCartao() {
  const nova = await escolherMetodo('CARTAO');
  if (nova?.url_checkout) {
    await openUrl(nova.url_checkout);
  }
}

/**
 * "até 3 computadores ao mesmo tempo".
 *
 * É a diferença real entre os planos, e é o que o dono precisa ver antes de
 * pagar — preço sozinho não diz o que se está comprando.
 */
const limiteTexto = computed(() => {
  const limite = limiteTerminais.value;
  if (!limite) return null;
  return limite === 1
    ? 'até 1 computador ao mesmo tempo'
    : `até ${limite} computadores ao mesmo tempo`;
});

/** "3 meses" / "1 ano" — o que se leva pelo preço. */
function duracaoTexto(meses?: number | null, dias?: number | null): string | null {
  if (meses === 12) return '1 ano';
  if (meses) return `${meses} ${meses === 1 ? 'mês' : 'meses'}`;
  if (dias) return `${dias} dias`;
  return null;
}

/** O desconto vem em fração (0.054). Abaixo de 1% não vale ocupar a tela. */
function descontoTexto(desconto?: number | null): string | null {
  if (!desconto || desconto < 0.01) return null;
  return `economize ${Math.round(desconto * 100)}%`;
}

const vencimentoFormatado = computed(
  () => (novoVencimento.value ? formatData(novoVencimento.value) : null),
);

function falarComSuporte() {
  openUrl(LINKS.whatsapp);
}

function verPlanos() {
  openUrl(LINKS.planos);
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    title="Renovar Assinatura"
    size="md"
    @close="emit('close')"
  >
    <!-- Carregando os períodos -->
    <div v-if="carregandoPeriodos" class="py-10 flex flex-col items-center gap-3">
      <RefreshCw :size="20" class="text-zinc-300 animate-spin" />
      <p class="text-sm text-zinc-400">Consultando os planos…</p>
    </div>

    <!--
      Indisponível NÃO é erro: é o estado enquanto a cobrança pelo sistema não
      está no ar. A tela diz isso e oferece o caminho que funciona hoje.
    -->
    <div v-else-if="!disponivel" class="py-8 text-center flex flex-col items-center gap-3">
      <p class="text-sm font-medium text-zinc-700">
        A renovação pelo sistema ainda não está disponível
      </p>
      <p v-if="motivoIndisponivel" class="text-xs text-zinc-400 max-w-xs">
        {{ motivoIndisponivel }}
      </p>
      <!--
        A página de planos é o caminho que funciona HOJE: ela está no ar, aceita
        cartão e resolve a renovação enquanto a cobrança pelo sistema não sobe.
        Sem este botão o modal vira um aviso sem saída — o cliente abriu a tela
        justamente para pagar.
      -->
      <BaseButton variant="primary" size="md" class="mt-1 w-full" @click="verPlanos">
        <ExternalLink :size="16" class="mr-2" />
        Renovar no site
      </BaseButton>
      <BaseButton variant="ghost" size="md" class="w-full" @click="falarComSuporte">
        Falar com o suporte
      </BaseButton>
    </div>

    <!-- Passo 1 — escolher período e método -->
    <div v-else-if="passo === 'escolha'" class="flex flex-col gap-4">
      <!--
        Qual plano está sendo renovado, e o que ele dá. Sem isto a tela é uma
        lista de preços sem objeto: o dono vê "R$ 89,90" e não vê o que compra.
      -->
      <div v-if="plano || limiteTexto" class="rounded-xl bg-zinc-50 border border-zinc-200 px-3.5 py-3">
        <p v-if="plano" class="text-sm font-semibold text-zinc-900">{{ plano }}</p>
        <p v-if="limiteTexto" class="text-[11px] text-zinc-500">{{ limiteTexto }}</p>
      </div>

      <div class="flex flex-col gap-2">
        <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Período</p>
        <button
          v-for="periodo in periodos"
          :key="periodo.codigo"
          type="button"
          :class="[
            'w-full flex items-center justify-between gap-3 px-3.5 py-3 rounded-xl border text-left transition-colors cursor-pointer',
            periodoSelecionado === periodo.codigo
              ? 'border-brand-primary bg-brand-primary/5'
              : 'border-zinc-200 hover:border-zinc-300',
          ]"
          @click="periodoSelecionado = periodo.codigo"
        >
          <div class="min-w-0">
            <p class="text-sm font-semibold text-zinc-900">{{ periodo.nome }}</p>
            <p v-if="duracaoTexto(periodo.meses, periodo.dias)" class="text-[11px] text-zinc-400">
              + {{ duracaoTexto(periodo.meses, periodo.dias) }} de uso
            </p>
          </div>
          <div class="flex flex-col items-end shrink-0">
            <span class="text-sm font-bold text-zinc-900">
              {{ formatCurrency(periodo.valor_centavos) }}
            </span>
            <span
              v-if="descontoTexto(periodo.desconto)"
              class="text-[10px] font-semibold text-emerald-600"
            >
              {{ descontoTexto(periodo.desconto) }}
            </span>
          </div>
        </button>
      </div>

      <div class="flex flex-col gap-2">
        <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
          Como você quer pagar?
        </p>

        <!--
          A diferença entre os dois não é forma de pagamento, é o que acontece
          depois — e esconder isso faz o cliente do PIX achar que renovou
          sozinho, e o do cartão achar que precisa pagar de novo todo mês.
        -->
        <BaseButton
          v-if="aceitaPix"
          variant="primary"
          size="lg"
          class="w-full justify-start"
          :disabled="gerandoCobranca || !periodoAtual"
          @click="escolherMetodo('PIX')"
        >
          <QrCode :size="18" class="mr-2.5" />
          <span class="flex flex-col items-start leading-tight">
            <span class="font-semibold">PIX</span>
            <span class="text-[11px] opacity-80">Paga uma vez · libera na hora</span>
          </span>
        </BaseButton>

        <BaseButton
          v-if="aceitaCartao"
          variant="secondary"
          size="lg"
          class="w-full justify-start"
          :disabled="gerandoCobranca || !periodoAtual"
          @click="pagarComCartao"
        >
          <CreditCard :size="18" class="mr-2.5" />
          <span class="flex flex-col items-start leading-tight">
            <span class="font-semibold">Cartão</span>
            <span class="text-[11px] opacity-70">Renova sozinho todo período</span>
          </span>
        </BaseButton>
      </div>
    </div>

    <!-- Passo 2 — PIX na tela -->
    <div v-else-if="passo === 'pix'" class="flex flex-col items-center gap-4">
      <div class="p-3 bg-white border border-zinc-200 rounded-2xl">
        <img
          v-if="cobranca?.qr_code_base64"
          :src="`data:image/png;base64,${cobranca.qr_code_base64}`"
          alt="QR Code do PIX"
          class="w-52 h-52"
        >
        <canvas v-else ref="canvasRef" class="w-52 h-52" />
      </div>

      <p class="text-sm text-zinc-500 text-center max-w-xs">
        Abra o app do seu banco, escolha PIX e aponte a câmera —
        ou copie o código abaixo.
      </p>

      <div class="w-full flex items-center gap-2">
        <p class="flex-1 text-[10px] font-mono text-zinc-400 truncate bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-2.5">
          {{ cobranca?.pix_copia_e_cola }}
        </p>
        <BaseButton variant="secondary" size="md" @click="copiarCodigo">
          <component :is="copiado ? Check : Copy" :size="15" />
        </BaseButton>
      </div>

      <p class="text-xs text-zinc-400">
        Assim que o pagamento cair, esta tela libera sozinha.
      </p>

      <div class="w-full flex gap-2">
        <BaseButton variant="ghost" size="md" class="flex-1" @click="voltarParaEscolha">
          Voltar
        </BaseButton>
        <BaseButton
          variant="secondary"
          size="md"
          class="flex-1"
          :disabled="verificando"
          @click="verificarAgora"
        >
          {{ verificando ? 'Verificando…' : 'Já paguei' }}
        </BaseButton>
      </div>
    </div>

    <!-- Passo 2 — cartão no navegador -->
    <div v-else-if="passo === 'cartao'" class="py-6 flex flex-col items-center gap-4 text-center">
      <ExternalLink :size="26" class="text-zinc-300" />
      <p class="text-sm font-medium text-zinc-700">
        Abrimos o pagamento no seu navegador
      </p>
      <p class="text-xs text-zinc-400 max-w-xs">
        Conclua por lá. Quando o pagamento for confirmado, esta tela libera sozinha —
        e nas próximas vezes o cartão renova automaticamente.
      </p>

      <div class="w-full flex gap-2 mt-1">
        <BaseButton variant="ghost" size="md" class="flex-1" @click="voltarParaEscolha">
          Voltar
        </BaseButton>
        <BaseButton
          variant="secondary"
          size="md"
          class="flex-1"
          :disabled="verificando"
          @click="verificarAgora"
        >
          {{ verificando ? 'Verificando…' : 'Já paguei' }}
        </BaseButton>
      </div>
    </div>

    <!-- Passo 3 — renovado -->
    <div v-else class="py-8 flex flex-col items-center gap-3 text-center">
      <PartyPopper :size="30" class="text-emerald-500" />
      <p class="text-base font-bold text-zinc-900">Assinatura renovada</p>
      <p v-if="vencimentoFormatado" class="text-sm text-zinc-500">
        Seu acesso vai até <strong class="text-zinc-700">{{ vencimentoFormatado }}</strong>.
      </p>
      <BaseButton variant="primary" size="md" class="mt-2 w-full" @click="emit('close')">
        Voltar ao sistema
      </BaseButton>
    </div>
  </BaseModal>
</template>
