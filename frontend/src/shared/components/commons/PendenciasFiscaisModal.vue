<script setup lang="ts">
/**
 * @component PendenciasFiscaisModal
 * @description Modal reutilizável que exibe pendências fiscais agrupadas por categoria.
 * Usado antes da emissão de NF-e/NFSe para mostrar ao operador o que precisa ser corrigido.
 */

import { computed } from 'vue';
import { Building2, User, Package, CreditCard } from 'lucide-vue-next';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import type { PendenciaFiscal } from '@/shared/types/fiscal.types';

interface Props {
  isOpen: boolean;
  pendencias: PendenciaFiscal[];
  titulo?: string;
}

const props = withDefaults(defineProps<Props>(), {
  titulo: 'Pendências Fiscais',
});

const emit = defineEmits<{
  close: [];
}>();

const CATEGORIA_CONFIG: Record<string, { label: string; icon: any; color: string }> = {
  emitente: { label: 'Emitente', icon: Building2, color: 'text-blue-500' },
  destinatario: { label: 'Destinatário', icon: User, color: 'text-amber-500' },
  item: { label: 'Itens', icon: Package, color: 'text-purple-500' },
  pagamento: { label: 'Pagamentos', icon: CreditCard, color: 'text-emerald-500' },
};

const grupos = computed(() => {
  const map = new Map<string, PendenciaFiscal[]>();
  for (const p of props.pendencias) {
    const lista = map.get(p.categoria) ?? [];
    lista.push(p);
    map.set(p.categoria, lista);
  }
  return Array.from(map.entries()).map(([categoria, pendencias]) => ({
    categoria,
    config: CATEGORIA_CONFIG[categoria] ?? { label: categoria, icon: Package, color: 'text-zinc-500' },
    pendencias,
  }));
});
</script>

<template>
  <BaseModal :is-open="isOpen" :title="titulo" size="md" @close="emit('close')">
    <div class="flex flex-col gap-4">
      <p class="text-sm text-zinc-500">
        Os seguintes dados precisam ser preenchidos antes da emissão:
      </p>

      <div
        v-for="grupo in grupos"
        :key="grupo.categoria"
        class="border border-zinc-200 rounded-xl overflow-hidden"
      >
        <!-- Cabeçalho do grupo -->
        <div class="flex items-center gap-2 px-4 py-2.5 bg-zinc-50 border-b border-zinc-200">
          <component :is="grupo.config.icon" :size="16" :class="grupo.config.color" />
          <span class="text-xs font-semibold text-zinc-600 uppercase tracking-wide">
            {{ grupo.config.label }}
          </span>
          <span class="ml-auto text-[10px] text-zinc-400 font-medium">
            {{ grupo.pendencias.length }}
          </span>
        </div>

        <!-- Lista de pendências -->
        <ul class="divide-y divide-zinc-100">
          <li
            v-for="(pendencia, idx) in grupo.pendencias"
            :key="idx"
            class="px-4 py-2.5 text-sm text-zinc-700"
          >
            <span>{{ pendencia.mensagem }}</span>
            <span
              v-if="pendencia.referencia_nome"
              class="ml-1 text-xs text-zinc-400"
            >
              ({{ pendencia.referencia_nome }})
            </span>
          </li>
        </ul>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end w-full">
        <BaseButton variant="secondary" class="px-5" @click="emit('close')">
          Entendi
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
