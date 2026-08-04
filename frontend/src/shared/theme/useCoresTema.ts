/**
 * @fileoverview Cores do tema para quem NÃO usa CSS: gráficos em `<canvas>`.
 *
 * Um `<div class="bg-brand-primary">` muda de cor sozinho quando a variável muda.
 * Um gráfico não — ele recebe o valor da cor uma vez, na hora de montar o
 * dataset, e fica com ela até ser redesenhado. Por isso aqui a cor é lida do CSS
 * computado e amarrada a `versaoPaleta`: quando a paleta troca, o computed
 * reavalia, o `config` do gráfico muda e o ChartCanvas repinta.
 *
 * Sem isso o gráfico acompanharia o tema no boot mas ficaria parado durante a
 * prévia ao vivo — que é justamente onde o dono está olhando.
 */
import { computed } from 'vue';

import { versaoPaleta } from './aplicar';
import { PALETA_PADRAO } from './paleta';

/** Valor computado de um token, com o padrão de fábrica como rede de segurança. */
function lerToken(token: keyof typeof PALETA_PADRAO): string {
  const valor = getComputedStyle(document.documentElement)
    .getPropertyValue(`--color-${token}`)
    .trim();
  return valor || PALETA_PADRAO[token];
}

/** `#045ca1` + 0.08 → `rgba(4, 92, 161, 0.08)`, para áreas preenchidas. */
export function comAlpha(hex: string, alpha: number): string {
  const limpo = hex.replace(/^#/, '');
  if (!/^[0-9a-fA-F]{6}$/.test(limpo)) return hex;
  const r = parseInt(limpo.slice(0, 2), 16);
  const g = parseInt(limpo.slice(2, 4), 16);
  const b = parseInt(limpo.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function useCoresTema() {
  return {
    primaria: computed(() => (versaoPaleta.value, lerToken('brand-primary'))),
    secundaria: computed(() => (versaoPaleta.value, lerToken('brand-secondary'))),
  };
}
