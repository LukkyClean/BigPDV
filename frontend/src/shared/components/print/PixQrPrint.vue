<script setup lang="ts">
/**
 * @component PixQrPrint
 * @description Bloco do QR do PIX nas vias em papel (A4 e cupom do navegador).
 *
 * Desenha o QR como SVG montado **na hora, de forma síncrona**. Isso não é
 * preciosismo de vetor: `QRCode.toDataURL` é assíncrono, e o fluxo de impressão
 * chama `window.print()` logo depois de montar o template — um QR assíncrono
 * perde essa corrida de vez em quando e o cliente recebe o papel com um buraco
 * onde deveria estar o código. `QRCode.create()` devolve a matriz na hora, então
 * não existe corrida para perder. De quebra, vetor sai nítido em qualquer DPI.
 *
 * Preto e branco literal (`#000`/`#fff`): documento impresso não segue a cor da
 * marca — ver `scripts/check-print-bw.mjs`.
 */
import { computed } from 'vue'
import * as QRCode from 'qrcode'
import { formatCurrency } from '@/shared/utils/finance'

const props = defineProps<{
  /** BR Code pronto, vindo de `pixParaImpressao`. */
  payload: string
  /** Valor cobrado no QR, em centavos. */
  valorCentavos: number
  /** Lado do QR no papel. O cupom é estreito, o A4 tem folga. */
  lado?: string
}>()

/** Quiet zone: 4 módulos de margem branca, exigidos para o código ser lido. */
const MARGEM = 4

const desenho = computed(() => {
  if (!props.payload) return null
  try {
    const { modules } = QRCode.create(props.payload, { errorCorrectionLevel: 'M' })
    const lado = modules.size
    let caminho = ''
    for (let linha = 0; linha < lado; linha++) {
      for (let coluna = 0; coluna < lado; coluna++) {
        if (modules.data[linha * lado + coluna]) caminho += `M${coluna} ${linha}h1v1h-1z`
      }
    }
    const total = lado + MARGEM * 2
    return { caminho, total, viewBox: `${-MARGEM} ${-MARGEM} ${total} ${total}` }
  } catch {
    // Payload longo demais para caber num QR. O comprovante sai sem o bloco —
    // nunca com um quadrado quebrado.
    return null
  }
})
</script>

<template>
  <div v-if="desenho" class="pix-qr-print">
    <div class="pix-qr-print__titulo">PAGUE COM PIX</div>
    <div class="pix-qr-print__valor">Valor: {{ formatCurrency(valorCentavos) }}</div>
    <svg
      :viewBox="desenho.viewBox"
      :style="{ width: lado ?? '32mm', height: lado ?? '32mm' }"
      shape-rendering="crispEdges"
      role="img"
      aria-label="QR Code para pagamento via PIX"
    >
      <!-- Fundo branco cobrindo a quiet zone: sem ele, um papel amarelado ou um
           fundo cinza do template comem a margem e o leitor desiste. -->
      <rect
        :x="-MARGEM"
        :y="-MARGEM"
        :width="desenho.total"
        :height="desenho.total"
        fill="#fff"
      />
      <path :d="desenho.caminho" fill="#000" />
    </svg>
    <div class="pix-qr-print__ajuda">Aponte a câmera do celular</div>
  </div>
</template>

<style scoped>
.pix-qr-print {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1mm;
  padding: 2mm 0;
}
.pix-qr-print__titulo {
  font-weight: 700;
}
.pix-qr-print__valor,
.pix-qr-print__ajuda {
  font-size: 0.9em;
}
</style>
