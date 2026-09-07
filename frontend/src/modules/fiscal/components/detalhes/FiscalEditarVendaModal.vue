<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import {
  User,
  Building2,
  Check,
  Save,
  RotateCcw,
  UserX,
  X,
} from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect, { type SelectOption } from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import { useCustomerQueryAll } from '@/modules/customers/composables/request/useCustomerGet.queries';
import { useFiscalCorrecaoVendaMutation } from '../../composables/useFiscalCorrecaoVendaMutation';
import { useFiscalReemitirMutation } from '../../composables/useFiscalReemitirMutation';
import { formatCPF, formatCNPJ } from '@/shared/utils/document.utils';
import {
  isCustomerPF,
  type CustomerUnionReadSchemaDataType,
} from '@/modules/customers/schemas/customerQuery.schema';

// O cadastro de cliente e uma uniao discriminada por `tipo`: PF tem nome/cpf,
// PJ tem razao_social/cnpj. Estes dois helpers concentram o narrowing para o
// template nao precisar repeti-lo em cada interpolacao.
function nomeCliente(c: CustomerUnionReadSchemaDataType): string {
  return isCustomerPF(c) ? c.nome : c.razao_social;
}

function docCliente(c: CustomerUnionReadSchemaDataType): string {
  return isCustomerPF(c) ? c.cpf : c.cnpj;
}

const props = defineProps<{
  isOpen: boolean;
  vendaId: number | null;
  numeroVenda?: number | null;
  clienteAtualId?: number | null;
  documentoId?: number | null;
  naturezaOperacaoInicial?: string | null;
  observacaoInicial?: string | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'saved'): void;
  (e: 'reemitido', novoDocId: number): void;
}>();

const { searchQuery, customers } = useCustomerQueryAll();
const correcaoMutation = useFiscalCorrecaoVendaMutation();
const reemitirMutation = useFiscalReemitirMutation();

const clienteSelecionado = ref<CustomerUnionReadSchemaDataType | null>(null);
const desvincularCliente = ref(false);

const naturezaOperacao = ref('Venda de Mercadoria');
const observacao = ref('');
const consumidorFinal = ref(true);
const indicadorPresenca = ref<string | number>(1);

const indicadorPresencaOptions: SelectOption[] = [
  { value: 1, label: '1 - Operação Presencial' },
  { value: 2, label: '2 - Operação Não Presencial (Internet)' },
  { value: 3, label: '3 - Operação Não Presencial (Teleatendimento)' },
  { value: 4, label: '4 - NF-e em Operação com Entrega a Domicílio' },
  { value: 9, label: '9 - Operação Não Presencial (Outros)' },
];

// Sincronizar estado inicial ao abrir modal
watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      searchQuery.value = '';
      desvincularCliente.value = false;
      naturezaOperacao.value = props.naturezaOperacaoInicial || 'Venda de Mercadoria';
      observacao.value = props.observacaoInicial || '';
      consumidorFinal.value = true;
      indicadorPresenca.value = 1;

      if (props.clienteAtualId) {
        const c = customers.value.find((item) => item.id === props.clienteAtualId);
        clienteSelecionado.value = c || null;
      } else {
        clienteSelecionado.value = null;
      }
    }
  },
  { immediate: true },
);

function selecionarCliente(cliente: CustomerUnionReadSchemaDataType) {
  clienteSelecionado.value = cliente;
  desvincularCliente.value = false;
  searchQuery.value = '';
}

function definirConsumidorFinalSemCliente() {
  clienteSelecionado.value = null;
  desvincularCliente.value = true;
  searchQuery.value = '';
}

function removerSelecaoCliente() {
  clienteSelecionado.value = null;
  desvincularCliente.value = false;
  searchQuery.value = '';
}

const docFormatado = computed(() => {
  if (!clienteSelecionado.value) return '';
  const doc = docCliente(clienteSelecionado.value);
  const digits = doc.replace(/\D/g, '');
  if (digits.length === 14) return formatCNPJ(digits);
  if (digits.length === 11) return formatCPF(digits);
  return doc;
});

const enderecoCliente = computed(() => {
  if (!clienteSelecionado.value?.endereco) return null;
  const end = Array.isArray(clienteSelecionado.value.endereco)
    ? clienteSelecionado.value.endereco[0]
    : clienteSelecionado.value.endereco;
  return end || null;
});

const isSalvando = computed(
  () => correcaoMutation.isPending.value || reemitirMutation.isPending.value,
);

async function salvarAlteracoes(reemitirAposSalvar = false) {
  if (!props.vendaId) return;

  const novoClienteId = desvincularCliente.value
    ? null
    : clienteSelecionado.value
      ? clienteSelecionado.value.id
      : props.clienteAtualId;

  await correcaoMutation.mutateAsync({
    vendaId: props.vendaId,
    payload: {
      cliente_id: novoClienteId,
      observacao: observacao.value || undefined,
      natureza_operacao: naturezaOperacao.value || undefined,
      consumidor_final: consumidorFinal.value,
      indicador_presenca: Number(indicadorPresenca.value),
    },
  });

  emit('saved');

  if (reemitirAposSalvar && props.documentoId) {
    const novoDoc = await reemitirMutation.mutateAsync(props.documentoId);
    emit('reemitido', novoDoc.id);
  }

  emit('close');
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    :title="`Editar Dados da Venda #${numeroVenda ?? vendaId ?? ''}`"
    subtitle="Ajuste o cliente vinculado, observações e parâmetros fiscais para emissão de NF-e."
    size="lg"
    @close="emit('close')"
  >
    <div class="space-y-6 py-2">

      <!-- Seção 1: Destinatário / Cliente -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <div>
            <h4 class="text-xs font-bold uppercase tracking-wider text-zinc-700">
              Destinatário da Venda
            </h4>
            <p class="text-[11px] text-zinc-400 mt-0.5">
              Selecione o cliente que receberá a emissão da NF-e
            </p>
          </div>

          <button
            type="button"
            @click="definirConsumidorFinalSemCliente"
            class="inline-flex items-center gap-1.5 rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-zinc-600 transition-colors hover:bg-zinc-50 hover:text-zinc-900 cursor-pointer shadow-2xs"
          >
            <UserX class="h-3.5 w-3.5 text-zinc-400" />
            Consumidor Balcão (Sem Cadastro)
          </button>
        </div>

        <!-- Card de Cliente Selecionado -->
        <div
          v-if="clienteSelecionado && !desvincularCliente"
          class="rounded-xl border border-emerald-200/90 bg-emerald-50/60 p-3.5 flex items-center justify-between gap-3 shadow-2xs transition-all"
        >
          <div class="flex items-center gap-3 min-w-0">
            <div class="h-9 w-9 rounded-lg bg-emerald-100 flex items-center justify-center shrink-0 text-emerald-700">
              <component
                :is="clienteSelecionado.tipo === 'PJ' ? Building2 : User"
                class="h-4 w-4"
              />
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <p class="text-xs font-bold text-zinc-900 truncate">
                  {{ nomeCliente(clienteSelecionado) }}
                </p>
                <span class="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.2 text-[10px] font-bold text-emerald-800 shrink-0">
                  <Check class="h-3 w-3" /> Selecionado
                </span>
              </div>
              <p class="text-[11px] text-zinc-600 mt-0.5 font-mono">
                {{ clienteSelecionado.tipo === 'PJ' ? 'CNPJ' : 'CPF' }}: {{ docFormatado || 'Não informado' }}
                <span v-if="enderecoCliente" class="font-sans text-zinc-500">
                  · {{ enderecoCliente.cidade }}/{{ enderecoCliente.estado }}
                </span>
              </p>
            </div>
          </div>

          <button
            type="button"
            @click="removerSelecaoCliente"
            class="rounded-lg p-1.5 text-zinc-400 hover:bg-emerald-100/60 hover:text-zinc-700 transition-colors cursor-pointer"
            title="Trocar cliente"
          >
            <X class="h-4 w-4" />
          </button>
        </div>

        <!-- Card Sem Cliente (Balcão) -->
        <div
          v-else-if="desvincularCliente"
          class="rounded-xl border border-amber-200/90 bg-amber-50/60 p-3.5 flex items-center justify-between gap-3 shadow-2xs"
        >
          <div class="flex items-center gap-2.5">
            <div class="h-8 w-8 rounded-lg bg-amber-100 flex items-center justify-center shrink-0 text-amber-700">
              <UserX class="h-4 w-4" />
            </div>
            <div>
              <p class="text-xs font-bold text-amber-900">Consumidor Balcão</p>
              <p class="text-[11px] text-amber-700">Venda sem CPF/CNPJ de cliente identificado.</p>
            </div>
          </div>

          <button
            type="button"
            @click="desvincularCliente = false"
            class="rounded-lg p-1.5 text-zinc-400 hover:bg-amber-100 hover:text-zinc-700 transition-colors cursor-pointer"
            title="Buscar outro cliente"
          >
            <X class="h-4 w-4" />
          </button>
        </div>

        <!-- Campo de busca padrão do sistema -->
        <div v-else class="space-y-1.5">
          <BaseSearchInput
            v-model="searchQuery"
            placeholder="Buscar cliente por nome, razão social ou CPF/CNPJ..."
          />

          <!-- Lista suspensa de clientes correspondentes -->
          <div
            v-if="customers.length > 0 && searchQuery"
            class="max-h-44 overflow-y-auto divide-y divide-zinc-100 rounded-xl border border-zinc-200 bg-white shadow-sm"
          >
            <button
              v-for="c in customers"
              :key="c.id"
              type="button"
              @click="selecionarCliente(c)"
              class="flex w-full items-center justify-between p-3 text-left text-xs transition-colors hover:bg-zinc-50 cursor-pointer"
              :class="{ 'bg-emerald-50/50': clienteSelecionado?.id === c.id }"
            >
              <div class="min-w-0 flex items-center gap-2.5">
                <component
                  :is="c.tipo === 'PJ' ? Building2 : User"
                  class="h-4 w-4 text-zinc-400 shrink-0"
                />
                <div class="truncate">
                  <p class="font-semibold text-zinc-900 truncate">
                    {{ nomeCliente(c) }}
                  </p>
                  <p class="text-[11px] text-zinc-500 font-mono">
                    {{ docCliente(c) || 'Sem documento' }}
                  </p>
                </div>
              </div>
              <Check
                v-if="clienteSelecionado?.id === c.id"
                class="h-4 w-4 text-emerald-600 shrink-0"
              />
            </button>
          </div>
        </div>
      </div>

      <!-- Seção 2: Parâmetros Fiscais da Operação -->
      <div class="space-y-4 pt-4 border-t border-zinc-100">
        <div>
          <h4 class="text-xs font-bold uppercase tracking-wider text-zinc-700">
            Parâmetros Fiscais da Operação
          </h4>
          <p class="text-[11px] text-zinc-400 mt-0.5">
            Defina a natureza da venda e modalidade de atendimento
          </p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <BaseInput
            v-model="naturezaOperacao"
            label="Natureza da Operação"
            placeholder="Ex: Venda de Mercadoria"
          />

          <BaseSelect
            v-model="indicadorPresenca"
            label="Indicador de Presença"
            :options="indicadorPresencaOptions"
            placeholder="Selecione o indicador"
          />
        </div>

        <BaseInput
          v-model="observacao"
          label="Informações Complementares / Observações da Nota"
          placeholder="Observações de interesse do fisco ou do contribuinte..."
        />
      </div>

    </div>

    <template #footer>
      <div class="flex items-center justify-between w-full pt-3">
        <BaseButton
          variant="ghost"
          type="button"
          :disabled="isSalvando"
          @click="emit('close')"
        >
          Cancelar
        </BaseButton>

        <div class="flex items-center gap-2.5">
          <BaseButton
            variant="secondary"
            type="button"
            :is-loading="isSalvando"
            @click="salvarAlteracoes(false)"
          >
            <Save class="h-4 w-4 mr-1.5" />
            Salvar Alterações
          </BaseButton>

          <BaseButton
            v-if="documentoId"
            variant="primary"
            type="button"
            :is-loading="isSalvando"
            @click="salvarAlteracoes(true)"
          >
            <RotateCcw class="h-4 w-4 mr-1.5" />
            Salvar e Reemitir NF-e
          </BaseButton>
        </div>
      </div>
    </template>
  </BaseModal>
</template>
