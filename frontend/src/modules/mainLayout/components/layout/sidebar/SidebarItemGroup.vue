<script setup lang="ts">
/**
 * Item de menu que agrupa sub-itens (ex.: Gestão Financeira).
 *
 * Um item com `children` deixa de navegar por conta própria: o clique no pai só
 * abre e fecha a lista, e quem navega são os filhos. Isso evita a tela-índice
 * que não faz nada além de repetir o menu que já está do lado.
 *
 * A filtragem NÃO acontece aqui. `BaseSidebar` resolve permissão e módulo de
 * cada filho e entrega a lista pronta, porque é lá que as stores já estão
 * abertas e porque a mesma regra vale para pai e filho — dois lugares decidindo
 * acesso é como se abre brecha.
 */
import { ref, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ChevronDown, Lock } from 'lucide-vue-next';

import type { SidebarSubItem } from '@/modules/mainLayout/types/layout.types';
import type { Component } from 'vue';

/** Sub-item já resolvido: `bloqueado` = a loja não tem o módulo dele. */
export type SidebarSubItemResolvido = SidebarSubItem & { bloqueado: boolean };

const props = defineProps<{
  icon: Component;
  label: string;
  children: SidebarSubItemResolvido[];
  activeTab: string;
}>();

const router = useRouter();

const grupoAtivo = computed(() => props.children.some((c) => c.id === props.activeTab));

// Começa aberto se o usuário já está numa tela de dentro — senão, quem entra
// por link direto vê o menu colapsado e nenhuma pista de onde está.
const expandido = ref(grupoAtivo.value);

watch(grupoAtivo, (ativo) => {
  if (ativo) expandido.value = true;
});

function navegar(filho: SidebarSubItemResolvido) {
  // Bloqueado não navega. O guard do router mandaria de volta para a home de
  // qualquer forma, e um clique que pisca e volta parece defeito — o cadeado
  // já diz o que está acontecendo.
  if (filho.bloqueado) return;
  router.push({ name: filho.id });
}
</script>

<template>
  <div>
    <button
      type="button"
      :aria-expanded="expandido"
      @click="expandido = !expandido"
      class="w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 cursor-pointer"
      :class="[
        grupoAtivo ? 'text-white bg-zinc-800/60' : 'text-zinc-400 hover:bg-zinc-800 hover:text-white',
      ]"
    >
      <span class="flex items-center space-x-3">
        <component :is="icon" :size="20" />
        <span class="font-medium text-sm">{{ label }}</span>
      </span>
      <ChevronDown
        :size="16"
        class="transition-transform duration-200 shrink-0"
        :class="expandido ? 'rotate-180' : ''"
      />
    </button>

    <div v-show="expandido" class="ml-4 mt-1 space-y-0.5">
      <button
        v-for="filho in children"
        :key="filho.id"
        type="button"
        :disabled="filho.bloqueado"
        :title="filho.bloqueado ? 'Disponível em um plano superior. Fale com o suporte.' : undefined"
        @click="navegar(filho)"
        class="w-full flex items-center px-4 py-2 rounded-lg text-sm transition-all duration-200"
        :class="[
          filho.bloqueado
            ? 'text-zinc-600 cursor-not-allowed'
            : activeTab === filho.id
              ? 'bg-brand-primary text-white shadow-lg shadow-brand-primary/15 cursor-pointer'
              : 'text-zinc-500 hover:bg-zinc-800 hover:text-white cursor-pointer',
        ]"
      >
        <span
          class="w-1.5 h-1.5 rounded-full mr-3 shrink-0"
          :class="activeTab === filho.id ? 'bg-white' : 'bg-zinc-600'"
        />
        <span class="font-medium">{{ filho.label }}</span>
        <Lock v-if="filho.bloqueado" :size="13" class="ml-auto shrink-0" />
      </button>
    </div>
  </div>
</template>
