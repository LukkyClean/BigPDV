<script setup lang="ts">
/**
 * @component PixQrCode
 * @description QR do PIX já com o valor da cobrança, montado offline.
 *
 * Existe para resolver a dor concreta do balcão: cliente digitando chave errada
 * ou valor errado. Aqui ele aponta a câmera e pronto — nada é digitado.
 *
 * O componente busca a empresa sozinho de propósito. A regra de quando o QR
 * pode aparecer (`pix_ativo` + chave cadastrada) mora num lugar só, e quem
 * chama passa apenas o valor — não dá para uma tela esquecer o interruptor e
 * exibir QR de uma loja que não configurou PIX.
 *
 * O que ele NÃO faz: confirmar pagamento. O sistema não fica sabendo que o
 * cliente pagou; a conferência segue no app do banco. Conciliação automática
 * exigiria webhook, e o backend roda na rede local da loja.
 */
import { computed, ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { Copy, Check, QrCode, AlertTriangle } from 'lucide-vue-next'
import * as QRCode from 'qrcode'

import { useEmpresaQuery } from '@/modules/enterprise/composables/useEmpresaQuery'
import { useToast } from '@/shared/composables/useToast'
import { formatCurrency } from '@/shared/utils/finance'
import { montarPixBrCode, normalizarChavePix } from '@/shared/utils/pixBrCode'

const props = defineProps<{
  /** Valor desta cobrança em CENTAVOS. Zero gera QR sem valor. */
  valorCentavos: number
  /** Identificador da cobrança (número da OS, por exemplo). Opcional. */
  txid?: string
}>()

const toast = useToast()
const { data: empresa } = useEmpresaQuery()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const hasCopied = ref(false)

const chaveBruta = computed(() => empresa.value?.chave_pix ?? '')
const ativo = computed(() => Boolean(empresa.value?.pix_ativo && chaveBruta.value.trim()))
// `undefined` é a empresa ainda vindo do servidor. Sem esta distinção, o aviso
// de "cadastre a chave" pisca na tela de quem TEM chave cadastrada.
const carregando = computed(() => empresa.value === undefined)

/** Avisa quando a chave não bate com nenhuma das cinco formas — o QR sai, mas
 *  provavelmente não resolve em banco nenhum. */
const chaveSuspeita = computed(
  () => ativo.value && !normalizarChavePix(chaveBruta.value).reconhecida,
)

const payload = computed(() => {
  if (!ativo.value) return ''
  return montarPixBrCode({
    chave: chaveBruta.value,
    valorCentavos: props.valorCentavos,
    // O nome de fachada é o que o cliente reconhece; a razão social é o respaldo.
    nome: empresa.value?.nome_fantasia || empresa.value?.razao_social,
    cidade: empresa.value?.enderecos?.[0]?.cidade,
    txid: props.txid,
  })
})

// Digitar o valor redesenha o QR a cada tecla, e `toCanvas` é assíncrono: sem
// essa guarda, um desenho antigo pode chegar depois do novo e deixar na tela um
// QR de valor que já mudou.
let desenhoAtual = 0

watch(
  [payload, canvasRef],
  async ([texto, canvas]) => {
    if (!texto || !canvas) return
    const meu = ++desenhoAtual
    await nextTick()
    if (meu !== desenhoAtual) return
    try {
      await QRCode.toCanvas(canvas, texto, {
        width: 190,
        margin: 1,
        color: { dark: '#1e293b', light: '#ffffff' },
      })
    } catch {
      // Um QR que não desenha não pode derrubar a finalização da venda: o
      // "copia e cola" abaixo continua servindo.
    }
  },
  { immediate: true },
)

let copyTimeout: ReturnType<typeof setTimeout> | null = null
onBeforeUnmount(() => { if (copyTimeout) clearTimeout(copyTimeout) })

async function copiarPayload() {
  try {
    await navigator.clipboard.writeText(payload.value)
    hasCopied.value = true
    toast.success('Código PIX copiado!', 'success')
    if (copyTimeout) clearTimeout(copyTimeout)
    copyTimeout = setTimeout(() => (hasCopied.value = false), 1500)
  } catch {
    toast.error('Falha ao copiar', 'error')
  }
}
</script>

<template>
  <div v-if="carregando" class="h-4" />

  <!-- Sem chave ou com o PIX desligado: diz onde resolver, em vez de sumir. -->
  <div
    v-else-if="!ativo"
    class="flex items-start gap-2 rounded-lg border border-dashed border-zinc-300 bg-zinc-50 p-3"
  >
    <QrCode :size="16" class="text-zinc-400 shrink-0 mt-0.5" />
    <p class="text-[11px] text-zinc-500">
      Para exibir o QR Code do PIX, cadastre a chave em
      <span class="font-semibold">Configurações → Integrações e APIs</span> e ative a exibição.
    </p>
  </div>

  <div v-else-if="payload" class="flex flex-col items-center gap-3 py-1">
    <div class="bg-white p-3 rounded-xl border border-zinc-200">
      <canvas ref="canvasRef" />
    </div>

    <p v-if="valorCentavos > 0" class="text-xs text-zinc-500">
      Cobrando <span class="font-bold text-zinc-800">{{ formatCurrency(valorCentavos) }}</span>
      — o cliente não digita nada.
    </p>
    <p v-else class="text-xs text-zinc-500">
      QR sem valor: o cliente digita o valor no aplicativo do banco.
    </p>

    <!-- Copia e cola: a saída quando a câmera do cliente não coopera. -->
    <div class="w-full flex items-center gap-2 bg-zinc-50 rounded-lg border border-zinc-200 p-2">
      <p class="flex-1 text-[10px] text-zinc-500 truncate select-all font-mono">{{ payload }}</p>
      <button
        type="button"
        class="shrink-0 flex items-center gap-1 px-2.5 py-1.5 text-[11px] font-semibold rounded-md transition-colors"
        :class="hasCopied ? 'bg-emerald-100 text-emerald-700' : 'bg-brand-primary text-white hover:bg-brand-primary/90'"
        @click="copiarPayload"
      >
        <component :is="hasCopied ? Check : Copy" :size="12" />
        {{ hasCopied ? 'Copiado' : 'Copiar' }}
      </button>
    </div>

    <div
      v-if="chaveSuspeita"
      class="w-full flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2"
    >
      <AlertTriangle :size="14" class="text-amber-500 shrink-0 mt-0.5" />
      <p class="text-[10px] text-amber-700">
        A chave cadastrada não parece um CPF, CNPJ, telefone, e-mail ou chave aleatória.
        Confira em Configurações — o banco pode não reconhecer.
      </p>
    </div>

    <p class="text-[10px] text-zinc-400 text-center">
      Confirme o recebimento no aplicativo do banco: o sistema não é avisado do pagamento.
    </p>
  </div>
</template>
