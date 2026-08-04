<script setup lang="ts">
import { ref, toRef, nextTick, watch } from 'vue';
import { UserCircle2, Building2, Plus } from 'lucide-vue-next';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import { useQueryClient } from '@tanstack/vue-query';
import { useOSClientSearch } from '../composables/request/relationship/useOSClientSearch.queries';
import { useCustomerModal } from '@/modules/customers/composables/modal/useCustomerModal';
import type { CustomerUnionReadSchemaDataType } from '../schemas/relationship/customer/customer.schema';
import { getInitials } from '@/shared/utils/string.utils';
import { formatCPF, formatCNPJ, formatTelefone } from '@/shared/utils/document.utils';
import { OS_CUSTOMER_QUERY_KEY } from '../constants/core.constant';

interface Props {
  isOpen: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  close: [];
  selectCliente: [cliente: CustomerUnionReadSchemaDataType];
}>();

const isOpen = toRef(props, 'isOpen');
const queryClient = useQueryClient();
const { searchQuery, clientes, isLoading, lastCreatedId } = useOSClientSearch(isOpen);
const { openCreateModalWithCallback } = useCustomerModal();

function handleCadastrarNovo() {
  emit('close');
  openCreateModalWithCallback((customer) => {
    queryClient.invalidateQueries({ queryKey: OS_CUSTOMER_QUERY_KEY });
    emit('selectCliente', customer as CustomerUnionReadSchemaDataType);
  });
}

const listRef = ref<HTMLElement | null>(null);

watch(lastCreatedId, async (id) => {
  if (id) {
    await nextTick();
    listRef.value
      ?.querySelector(`[data-id="${id}"]`)
      ?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
});

function handleSelect(cliente: CustomerUnionReadSchemaDataType) {
  emit('selectCliente', cliente);
  emit('close');
}

function getClienteNome(cliente: CustomerUnionReadSchemaDataType): string {
  const c = cliente as { tipo: string; nome?: string; nome_fantasia?: string; razao_social?: string };
  if (c.tipo === 'PF') return c.nome || '-';
  return c.nome_fantasia || c.razao_social || '-';
}

function getClienteDocumento(cliente: CustomerUnionReadSchemaDataType): string {
  const c = cliente as { tipo: string; cpf?: string; cnpj?: string };
  if (c.tipo === 'PF') return c.cpf ? formatCPF(c.cpf) : '—';
  return c.cnpj ? formatCNPJ(c.cnpj) : '—';
}

function getClienteTelefone(cliente: CustomerUnionReadSchemaDataType): string | null {
  const phone = (cliente as any).celular || (cliente as any).telefone;
  return phone ? formatTelefone(phone) : null;
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    title="Selecionar Cliente"
    size="md"
    @close="emit('close')"
  >
    <!-- Busca -->
    <BaseSearchInput
      v-model="searchQuery"
      placeholder="Buscar por nome, CPF/CNPJ, telefone..."
    />

    <!-- Lista -->
    <div ref="listRef" class="mt-3 max-h-80 overflow-y-auto divide-y divide-zinc-100 -mx-1 px-1">
      <!-- Skeleton de loading -->
      <template v-if="isLoading">
        <div v-for="n in 5" :key="n" class="flex items-center gap-3 px-2 py-3 animate-pulse">
          <div class="w-9 h-9 rounded-full bg-zinc-200 shrink-0" />
          <div class="flex-1 space-y-1.5">
            <div class="h-3 w-1/2 bg-zinc-200 rounded" />
            <div class="h-2.5 w-1/3 bg-zinc-100 rounded" />
          </div>
        </div>
      </template>

      <!-- Lista de clientes -->
      <template v-else-if="clientes.length > 0">
        <button
          v-for="cliente in clientes"
          :key="cliente.id"
          :data-id="cliente.id"
          type="button"
          :class="[
            'w-full flex items-center gap-3 px-2 py-3 rounded-xl text-left transition-colors hover:bg-zinc-50 cursor-pointer',
            lastCreatedId === cliente.id ? 'ring-1 ring-brand-primary bg-brand-primary/5' : '',
          ]"
          @click="handleSelect(cliente)"
        >
          <div class="w-9 h-9 rounded-full bg-brand-primary/10 flex items-center justify-center shrink-0">
            <span class="text-[11px] font-bold text-brand-primary">
              {{ getInitials(getClienteNome(cliente)) }}
            </span>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-zinc-900 truncate">{{ getClienteNome(cliente) }}</p>
            <p class="text-[11px] text-zinc-400 truncate">
              {{ getClienteDocumento(cliente) }}
              <template v-if="getClienteTelefone(cliente)">
                · {{ getClienteTelefone(cliente) }}
              </template>
            </p>
          </div>
          <component
            :is="(cliente as any).tipo === 'PF' ? UserCircle2 : Building2"
            :size="15"
            class="text-zinc-300 shrink-0"
          />
        </button>
      </template>

      <!-- Estado vazio -->
      <div v-else class="py-10 text-center text-zinc-400">
        <template v-if="!searchQuery">
          <p class="text-sm font-medium">Digite para buscar</p>
          <p class="text-xs mt-1">Busque por nome, CPF/CNPJ ou telefone.</p>
        </template>
        <template v-else>
          <p class="text-sm font-medium">Nenhum cliente encontrado</p>
          <p class="text-xs mt-1">Tente outro termo ou cadastre um novo cliente.</p>
        </template>
      </div>
    </div>

    <template #footer>
      <BaseButton variant="primary" class="w-full" @click="handleCadastrarNovo">
        <Plus :size="16" class="mr-1.5" />
        Cadastrar novo cliente
      </BaseButton>
    </template>
  </BaseModal>
</template>
