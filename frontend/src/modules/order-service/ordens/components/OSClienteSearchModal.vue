<script setup lang="ts">
import { ref, toRef, computed, nextTick, watch } from 'vue';
import { UserCircle2, Building2, Plus, ChevronRight } from 'lucide-vue-next';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import { useQueryClient } from '@tanstack/vue-query';
import { useOSClientSearch } from '../composables/request/relationship/useOSClientSearch.queries';
import { useCustomerModal } from '@/modules/customers/composables/modal/useCustomerModal';
import type { CustomerUnionReadSchemaDataType } from '../schemas/relationship/customer/customer.schema';
import type { ObjetoBuscaItemDataType } from '../schemas/relationship/objetoBusca.schema';
import { useObjetoLabels } from '@/modules/order-service/shared/segmento/useObjetoLabels';
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
  selectObjeto: [objeto: ObjetoBuscaItemDataType];
}>();

const isOpen = toRef(props, 'isOpen');
const queryClient = useQueryClient();
const { searchQuery, clientes, objetos, isLoading, lastCreatedId } = useOSClientSearch(isOpen);
const { openCreateModalWithCallback } = useCustomerModal();

// Ícone e rótulo do identificador vêm do segmento: oficina mostra "Placa",
// informática "Nº de Série", serigrafia "Código da arte". Segmento novo herda
// sem tocar neste arquivo.
const { objetoIcon, labelIdentificador } = useObjetoLabels();

const placeholderBusca = computed(
  () => `Buscar por nome, CPF/CNPJ, e-mail ou ${labelIdentificador.value.toLowerCase()}...`,
);

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

/**
 * Clicar na linha do objeto entrega o cliente E o bem: quem digitou a placa já
 * disse qual é o carro, e perguntar de novo na tela seguinte seria repetir o
 * que ele acabou de responder.
 */
function handleSelectObjeto(objeto: ObjetoBuscaItemDataType) {
  emit('selectObjeto', objeto);
  emit('close');
}

function nomeObjeto(objeto: ObjetoBuscaItemDataType): string {
  return [objeto.marca, objeto.modelo].filter(Boolean).join(' ') || '—';
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
    <!--
      Nome, documento e e-mail são o que o servidor de fato varre
      (`_campos_busca`, no crud de cliente). Telefone estava escrito aqui e nunca
      foi pesquisável: prometer campo que não busca produz exatamente o "digitei
      certo e não achou" que a gente quer nunca mais ver.

      O identificador (placa / nº de série / código da arte) entrou no
      placeholder pela mesma régua: agora ele É pesquisado, por uma segunda
      consulta que corre em paralelo (`/ordens-servico/objeto/buscar`).
    -->
    <BaseSearchInput
      v-model="searchQuery"
      :placeholder="placeholderBusca"
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

      <!--
        Achados pelo identificador. Vêm primeiro porque são a resposta mais
        específica: quem digita uma placa inteira está procurando UM bem, não
        uma lista de clientes.
      -->
      <template v-else-if="objetos.length > 0">
        <div v-if="clientes.length > 0" class="px-2 pt-1 pb-2">
          <p class="text-[10px] font-bold tracking-wider text-zinc-400 uppercase">
            Por {{ labelIdentificador }}
          </p>
        </div>
        <button
          v-for="objeto in objetos"
          :key="objeto.objeto_id"
          type="button"
          class="w-full flex items-center gap-3 px-2 py-3 rounded-xl text-left transition-colors hover:bg-zinc-50 cursor-pointer"
          @click="handleSelectObjeto(objeto)"
        >
          <div class="w-9 h-9 rounded-full bg-brand-primary/10 flex items-center justify-center shrink-0">
            <component :is="objetoIcon" :size="16" class="text-brand-primary" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-zinc-900 truncate">
              {{ nomeObjeto(objeto) }}
              <span v-if="objeto.numero_serie" class="font-normal text-zinc-500">
                · {{ objeto.numero_serie }}
              </span>
            </p>
            <!--
              O nome do dono não é enfeite: quando o bem foi VENDIDO ele existe
              no nome de dois clientes, e sem esta linha as duas opções ficam
              idênticas na tela.
            -->
            <p class="text-[11px] text-zinc-400 truncate">
              {{ objeto.cliente_nome || 'Cliente sem nome' }}
            </p>
          </div>
          <ChevronRight :size="15" class="text-zinc-300 shrink-0" />
        </button>
      </template>

      <!-- Lista de clientes -->
      <template v-if="!isLoading && clientes.length > 0">
        <!--
          Cabeçalhos só aparecem quando as duas listas estão na tela ao mesmo
          tempo. No caso comum (só clientes, como sempre foi) a tela continua
          exatamente como o atendente conhece.
        -->
        <div v-if="objetos.length > 0" class="px-2 pt-3 pb-2">
          <p class="text-[10px] font-bold tracking-wider text-zinc-400 uppercase">
            Clientes
          </p>
        </div>
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
      <div
        v-if="!isLoading && objetos.length === 0 && clientes.length === 0"
        class="py-10 text-center text-zinc-400"
      >
        <template v-if="!searchQuery">
          <p class="text-sm font-medium">Digite para buscar</p>
          <p class="text-xs mt-1">
            Busque por nome, CPF/CNPJ, e-mail ou {{ labelIdentificador.toLowerCase() }}.
          </p>
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
