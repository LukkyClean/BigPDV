import { ref, computed } from 'vue';

export type PeriodoPreset = 'hoje' | 'ontem' | '7dias' | 'mes' | 'personalizado';

/** Formata uma Date como YYYY-MM-DD no fuso LOCAL (o que o usuário espera ver). */
function isoLocal(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dia = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${dia}`;
}

/**
 * Estado do filtro de período. Os presets calculam o intervalo; "personalizado"
 * usa as datas escolhidas manualmente. Expõe `range` reativo {inicio, fim}.
 */
export function usePeriodo(inicial: PeriodoPreset = 'mes') {
  const preset = ref<PeriodoPreset>(inicial);
  const inicioCustom = ref(isoLocal(new Date()));
  const fimCustom = ref(isoLocal(new Date()));

  const range = computed<{ inicio: string; fim: string }>(() => {
    const hoje = new Date();
    const y = hoje.getFullYear();
    const m = hoje.getMonth();
    const d = hoje.getDate();

    switch (preset.value) {
      case 'hoje':
        return { inicio: isoLocal(hoje), fim: isoLocal(hoje) };
      case 'ontem': {
        const o = new Date(y, m, d - 1);
        return { inicio: isoLocal(o), fim: isoLocal(o) };
      }
      case '7dias':
        return { inicio: isoLocal(new Date(y, m, d - 6)), fim: isoLocal(hoje) };
      case 'mes':
        return { inicio: isoLocal(new Date(y, m, 1)), fim: isoLocal(hoje) };
      case 'personalizado':
      default:
        return { inicio: inicioCustom.value, fim: fimCustom.value };
    }
  });

  return { preset, inicioCustom, fimCustom, range };
}
