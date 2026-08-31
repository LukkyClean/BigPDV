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
 *  - trial     → página de planos no navegador. Quem está testando ainda vai
 *                ESCOLHER um plano, e essa escolha mora no site.
 *  - renovar   → a tela de renovação DENTRO do sistema (a mesma que o menu de
 *                Configurações abre). O cliente pagante não vai escolher plano
 *                de novo: ele renova o que já tem, e isso se resolve aqui, sem
 *                sair para o navegador.
 *
 *                Só para o master: a assinatura é a conta dele, e o backend
 *                recusa a cobrança de quem não é. Funcionário continua indo
 *                para a página de planos — ver o preço não faz mal a ninguém,
 *                e abrir um modal que vai responder 403 sim.
 */

import { computed } from 'vue';
import { Zap, AlertTriangle, Clock } from 'lucide-vue-next';
import { openUrl } from '@tauri-apps/plugin-opener';
import { storeToRefs } from 'pinia';
import { useLicencaStatusQuery } from '@/shared/composables/useLicencaStatusQuery';
import { useAuthStore } from '@/shared/stores/auth.store';
import { useLayoutStore } from '../../store/layout.store';
import { LINKS } from '@/shared/config/links';

const { data, isLoading, isError } = useLicencaStatusQuery();
const layoutStore = useLayoutStore();
const { userData } = storeToRefs(useAuthStore());

const isMaster = computed(() => userData.value?.is_master === true);

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
        titulo: 'Renovar assinatura',
      };
    case 'renovar-urgente':
      return {
        label: `Renovar • ${dias} dias`,
        icon: AlertTriangle,
        classes: 'bg-red-50 text-red-600 hover:bg-red-100 animate-pulse',
        destino: 'renovacao' as Destino,
        titulo: 'Sua assinatura está vencendo — renovar agora',
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
      // A renovação acontece aqui dentro. O modal já sabe se virar quando a
      // cobrança pelo sistema ainda não estiver no ar: nesse caso ele mesmo
      // oferece "Renovar no site".
      if (isMaster.value) {
        layoutStore.openRenovarAssinatura();
      } else {
        openUrl(LINKS.planos);
      }
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
