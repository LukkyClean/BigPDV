<script setup lang="ts">
/**
 * @component AppLogo
 * @description Logo StartBig que se adapta ao fundo:
 *   - fundo ESCURO  -> "Start" branco  (start-logo-white.png)
 *   - fundo CLARO   -> "Start" preto   (start-logo-black.png)
 *
 * Por padrão (`theme="auto"`) ele detecta o fundo do ancestral mais próximo
 * (primeiro elemento com background-color não-transparente) e escolhe sozinho.
 * Dá pra forçar com `theme="dark"` (fundo escuro) ou `theme="light"` (fundo claro).
 *
 * As classes passadas (tamanho, opacidade, etc.) vão direto no <img>.
 */
import { ref, onMounted, watch } from 'vue';

import logoWhite from '@/shared/assets/images/login/start-logo-white.png'; // Start branco -> fundo escuro
import logoBlack from '@/shared/assets/images/login/start-logo-black.png'; // Start preto  -> fundo claro

const props = withDefaults(
  defineProps<{ theme?: 'auto' | 'dark' | 'light' }>(),
  { theme: 'auto' },
);

const imgEl = ref<HTMLImageElement | null>(null);
// 'dark' = fundo escuro (usa logo de Start branco); 'light' = fundo claro (Start preto)
const fundo = ref<'dark' | 'light'>(props.theme === 'auto' ? 'dark' : props.theme);

/** Luminância (0–255) do background-color do elemento; null se transparente/indefinido. */
function luminanciaFundo(el: HTMLElement): number | null {
  const cor = getComputedStyle(el).backgroundColor;
  const m = cor.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?/);
  if (!m) return null;
  const alpha = m[4] !== undefined ? Number(m[4]) : 1;
  if (alpha === 0) return null; // transparente: ignora e sobe na árvore
  const [r, g, b] = [Number(m[1]), Number(m[2]), Number(m[3])];
  return 0.299 * r + 0.587 * g + 0.114 * b;
}

function detectar() {
  if (props.theme !== 'auto') {
    fundo.value = props.theme;
    return;
  }
  let node: HTMLElement | null = imgEl.value?.parentElement ?? null;
  while (node) {
    const lum = luminanciaFundo(node);
    if (lum !== null) {
      fundo.value = lum < 128 ? 'dark' : 'light';
      return;
    }
    node = node.parentElement;
  }
  fundo.value = 'light'; // fallback seguro
}

onMounted(detectar);
watch(() => props.theme, detectar);
</script>

<template>
  <img
    ref="imgEl"
    :src="fundo === 'dark' ? logoWhite : logoBlack"
    alt="StartBig"
  />
</template>
