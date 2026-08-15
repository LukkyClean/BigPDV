<script setup lang="ts">
/**
 * @component LicencaStatusBadge
 * @description Badge no header que exibe o status da licença/trial com visual dinâmico.
 * Sempre visível quando o status está disponível; silencioso em erros de rede.
 *
 * Estados:
 *  - trial:           trial ativo, dias > 7  → azul/brand
 *  - trial-urgente:   trial ativo, dias ≤ 7  → laranja pulsante
 *  - renovar:         licença paga, dias ≤ 30 → amarelo
 *  - renovar-urgente: licença paga, dias ≤ 7  → vermelho pulsante
 *  - ativo:           licença saudável        → verde/neutro (sem CTA)
 *
 * NOTA: os estados de trial só aparecem quando o backend enviar `trial` na
 * resposta de /licenca/status (hoje esse campo vem da API StartBig e ainda não
 * é repassado). Sem ele, a badge cai nos estados de licença paga.
 *
 * DESTINOS:
 *  - trial     → página de planos. Quem está testando ainda vai ESCOLHER um plano.
 *  - renovar   → planos TAMBÉM, mas só provisoriamente. O destino certo do
 *                cliente pagante é o link de pagamento (Stripe) gerado na hora,
 *                porque ele renova o que já tem em vez de escolher plano de
 *                novo — fluxo ainda a desenhar. Ver TODO(renovacao) abaixo.
 */

import { computed } from 'vue';
import { Zap, AlertTriangle, Clock } from 'lucide-vue-next';
import { openUrl } from '@tauri-apps/plugin-opener';
import { useLicencaStatusQuery } from '@/shared/composables/useLicencaStatusQuery';
import { LINKS } from '@/shared/config/links';

const { data, isLoading, isError } = useLicencaStatusQuery();

type BadgeEstado = 'trial' | 'trial-urgente' | 'renovar' | 'renovar-urgente' | 'ativo';

const estado = computed((): BadgeEstado | null => {
  if (isLoading.value || isError.value || !data.value) return null;

  const { trial, dias_restantes } = data.value;
  const dias = dias_restantes ?? Infinity;

  if (trial) {
    return dias <= 7 ? 'trial-urgente' : 'trial';
  }
  if (dias <= 7) return 'renovar-urgente';
  if (dias <= 30) return 'renovar';
  return 'ativo';
});

/** Para onde o clique leva. `null` = badge informativa, sem ação. */
type Destino = 'planos' | 'renovacao' | null;

const config = computed(() => {
  const dias = data.value?.dias_restantes;

  switch (estado.value) {
    case 'trial':
      return {
        label: `Trial • ${dias} dias`,
        icon: Zap,
        classes: 'bg-brand-primary/10 text-brand-primary hover:bg-brand-primary/20',
        destino: 'planos' as Destino,
        titulo: 'Ver planos em startbig.com.br',
      };
    case 'trial-urgente':
      return {
        label: `Trial • ${dias} dias`,
        icon: Clock,
        classes: 'bg-orange-50 text-orange-600 hover:bg-orange-100 animate-pulse',
        destino: 'planos' as Destino,
        titulo: 'Seu teste está acabando — ver planos',
      };
    case 'renovar':
      return {
        label: `Renovar • ${dias} dias`,
        icon: AlertTriangle,
        classes: 'bg-yellow-50 text-yellow-700 hover:bg-yellow-100',
        destino: 'renovacao' as Destino,
        titulo: 'Renovar assinatura em startbig.com.br',
      };
    case 'renovar-urgente':
      return {
        label: `Renovar • ${dias} dias`,
        icon: AlertTriangle,
        classes: 'bg-red-50 text-red-600 hover:bg-red-100 animate-pulse',
        destino: 'renovacao' as Destino,
        titulo: 'Sua assinatura está vencendo — renovar em startbig.com.br',
      };
    case 'ativo':
      return {
        label: 'Assinatura Ativa',
        icon: Zap,
        classes: 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100',
        destino: null as Destino,
        titulo: 'Licença ativa',
      };
    default:
      return null;
  }
});

function handleClick() {
  switch (config.value?.destino) {
    case 'planos':
      openUrl(LINKS.planos);
      break;
    case 'renovacao':
      // TODO(renovacao): trocar pelo fluxo de renovação — gerar o link de
      // pagamento (Stripe) na hora e abrir o checkout direto, sem passar pela
      // tabela de planos. Até lá, o site resolve: a página de planos já está
      // no ar e funcionando.
      openUrl(LINKS.planos);
      break;
  }
}
</script>

<template>
  <button
    v-if="config"
    type="button"
    class="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-colors"
    :class="[config.classes, config.destino ? 'cursor-pointer' : 'cursor-default']"
    :title="config.titulo"
    @click="handleClick"
  >
    <component :is="config.icon" :size="13" />
    <span class="hidden md:inline">{{ config.label }}</span>
  </button>
</template>
