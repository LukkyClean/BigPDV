<script setup lang="ts">
/**
 * @component BaseColorPicker
 * @description Seletor de cor embutido na página: quadrado de saturação/brilho,
 * barra de matiz e campo hex. Sem biblioteca externa.
 *
 * É embutido, e não o diálogo nativo do sistema (`<input type="color">`), porque
 * o valor da feature está na prévia ao vivo: o diálogo do Windows é uma janela
 * modal que cobre o app, então o dono escolheria a cor sem ver o sistema
 * recolorindo atrás. Aqui ele arrasta e vê.
 *
 * Trabalha em HSV — o espaço que descreve este tipo de seletor. A conversão que
 * importa (para a paleta) é feita em OKLCH lá em `shared/theme/paleta.ts`; aqui é
 * só a mecânica do widget.
 */
import { ref, computed, watch } from 'vue';

const modelo = defineModel<string>({ default: '#045ca1' });

withDefaults(defineProps<{ disabled?: boolean }>(), { disabled: false });

const matiz = ref(0);      // 0..360
const saturacao = ref(0);  // 0..1
const brilho = ref(0);     // 0..1

const quadradoRef = ref<HTMLElement | null>(null);
const barraRef = ref<HTMLElement | null>(null);

const limitar = (n: number) => Math.min(1, Math.max(0, n));

function hsvParaHex(h: number, s: number, v: number): string {
  const canal = (n: number) => {
    const k = (n + h / 60) % 6;
    const c = v - v * s * Math.max(0, Math.min(k, 4 - k, 1));
    return Math.round(c * 255).toString(16).padStart(2, '0');
  };
  return `#${canal(5)}${canal(3)}${canal(1)}`;
}

function hexParaHsv(hex: string): { h: number; s: number; v: number } | null {
  const limpo = hex.trim().replace(/^#/, '');
  const completo = limpo.length === 3 ? limpo.split('').map((c) => c + c).join('') : limpo;
  if (!/^[0-9a-fA-F]{6}$/.test(completo)) return null;

  const r = parseInt(completo.slice(0, 2), 16) / 255;
  const g = parseInt(completo.slice(2, 4), 16) / 255;
  const b = parseInt(completo.slice(4, 6), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const d = max - min;

  let h = 0;
  if (d > 0) {
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h = (h * 60 + 360) % 360;
  }
  return { h, s: max === 0 ? 0 : d / max, v: max };
}

// Sincroniza o estado interno quando a cor vem de fora (carregou do servidor,
// digitaram no campo, clicaram em "restaurar padrão").
//
// O guard evita laço: ao arrastar, nós mesmos escrevemos no modelo, e reagir a
// isso reconverteria hex→HSV com perda de precisão, fazendo o ponto tremer.
// Também preserva a matiz quando a cor é preta ou cinza — nesses casos o hex não
// carrega matiz nenhuma, e sem isto a barra saltaria para o vermelho.
watch(modelo, (hex) => {
  if (hex === hsvParaHex(matiz.value, saturacao.value, brilho.value)) return;
  const hsv = hexParaHsv(hex ?? '');
  if (!hsv) return;
  if (hsv.s > 0 && hsv.v > 0) matiz.value = hsv.h;
  saturacao.value = hsv.s;
  brilho.value = hsv.v;
}, { immediate: true });

function emitir() {
  modelo.value = hsvParaHex(matiz.value, saturacao.value, brilho.value);
}

/** Cor pura da matiz atual — o fundo do quadrado. */
const corDaMatiz = computed(() => hsvParaHex(matiz.value, 1, 1));

function posicionarNoQuadrado(evento: PointerEvent) {
  const caixa = quadradoRef.value?.getBoundingClientRect();
  if (!caixa) return;
  saturacao.value = limitar((evento.clientX - caixa.left) / caixa.width);
  brilho.value = 1 - limitar((evento.clientY - caixa.top) / caixa.height);
  emitir();
}

function posicionarNaBarra(evento: PointerEvent) {
  const caixa = barraRef.value?.getBoundingClientRect();
  if (!caixa) return;
  matiz.value = limitar((evento.clientX - caixa.left) / caixa.width) * 360;
  emitir();
}

/** `setPointerCapture` mantém o arraste funcionando mesmo com o cursor fora do
 *  elemento — sem ele, sair do quadrado no meio do movimento congela a escolha. */
function iniciarArraste(evento: PointerEvent, mover: (e: PointerEvent) => void) {
  const alvo = evento.currentTarget as HTMLElement;
  alvo.setPointerCapture(evento.pointerId);
  mover(evento);

  const aoMover = (e: PointerEvent) => mover(e);
  const aoSoltar = () => {
    alvo.removeEventListener('pointermove', aoMover);
    alvo.removeEventListener('pointerup', aoSoltar);
    alvo.removeEventListener('pointercancel', aoSoltar);
  };
  alvo.addEventListener('pointermove', aoMover);
  alvo.addEventListener('pointerup', aoSoltar);
  alvo.addEventListener('pointercancel', aoSoltar);
}

/** Só propaga hex completo e válido — enquanto digita "#0", o resto da tela não
 *  deve recolorir para preto. */
function aoDigitarHex(evento: Event) {
  const bruto = (evento.target as HTMLInputElement).value;
  const normalizado = bruto.startsWith('#') ? bruto : `#${bruto}`;
  if (/^#[0-9a-fA-F]{6}$/.test(normalizado)) modelo.value = normalizado.toLowerCase();
}
</script>

<template>
  <div class="flex gap-4" :class="{ 'opacity-50 pointer-events-none': disabled }">
    <div class="flex flex-col gap-2">
      <!-- Quadrado saturação (→) × brilho (↑) sobre a matiz atual -->
      <div
        ref="quadradoRef"
        class="relative w-40 h-32 rounded-lg cursor-crosshair touch-none border border-zinc-200 overflow-hidden"
        :style="{ backgroundColor: corDaMatiz }"
        @pointerdown.prevent="iniciarArraste($event, posicionarNoQuadrado)"
      >
        <div class="absolute inset-0" style="background: linear-gradient(to right, #fff, transparent)" />
        <div class="absolute inset-0" style="background: linear-gradient(to top, #000, transparent)" />
        <span
          class="absolute w-3 h-3 -ml-1.5 -mt-1.5 rounded-full border-2 border-white shadow ring-1 ring-black/30 pointer-events-none"
          :style="{ left: `${saturacao * 100}%`, top: `${(1 - brilho) * 100}%` }"
        />
      </div>

      <!-- Barra de matiz -->
      <div
        ref="barraRef"
        class="relative w-40 h-4 rounded-full cursor-pointer touch-none border border-zinc-200"
        style="background: linear-gradient(to right, #f00 0%, #ff0 17%, #0f0 33%, #0ff 50%, #00f 67%, #f0f 83%, #f00 100%)"
        @pointerdown.prevent="iniciarArraste($event, posicionarNaBarra)"
      >
        <span
          class="absolute top-1/2 w-3.5 h-3.5 -ml-1.75 -mt-1.75 rounded-full border-2 border-white shadow ring-1 ring-black/30 pointer-events-none"
          :style="{ left: `${(matiz / 360) * 100}%`, backgroundColor: corDaMatiz }"
        />
      </div>
    </div>

    <div class="flex flex-col gap-2 justify-start">
      <label class="text-xs font-medium text-zinc-600">Cor escolhida</label>
      <div class="flex items-center gap-2">
        <span
          class="w-9 h-9 rounded-lg border border-zinc-200 shrink-0"
          :style="{ backgroundColor: modelo }"
        />
        <input
          :value="modelo"
          type="text"
          maxlength="7"
          spellcheck="false"
          class="w-24 px-2 py-1.5 border border-zinc-200 rounded-lg text-sm font-mono uppercase text-zinc-700 focus:outline-none focus:ring-2 focus:ring-brand-primary/40"
          @input="aoDigitarHex"
        />
      </div>
    </div>
  </div>
</template>
