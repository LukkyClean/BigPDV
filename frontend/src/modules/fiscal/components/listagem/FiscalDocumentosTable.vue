<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { FileText, FileCode, RefreshCw, Search, Ban, AlertCircle, X, Ellipsis } from 'lucide-vue-next';
import { useMutation, useQueryClient } from '@tanstack/vue-query';

import BaseTableContainer from '@/shared/components/commons/BaseTableContainer/BaseTableContainer.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import BaseFilter from '@/shared/components/ui/BaseFilter/BaseFilter.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage } from '@/shared/utils/error.utils';
import { formatCurrency } from '@/shared/utils/finance';
import { formatDataHora } from '@/shared/utils/date.utils';
import type { AxiosError } from 'axios';
import type { ApiError } from '@/shared/types/axios.types';

import { useFiscalDocumentosQuery } from '../../composables/useFiscalDocumentosQuery';
import { useFiscalConsultarMutation } from '../../composables/useFiscalConsultarMutation';
import { fiscalService } from '../../services/fiscal.service';
import { fiscalKeys, STATUS_COLORS, STATUS_LABELS, ORIGEM_LABELS } from '../../constants/fiscal.constants';
import { abrirArquivo } from '../../utils/abrirArquivo';
import FiscalCancelarModal from '../detalhes/FiscalCancelarModal.vue';
import type { DocumentoFiscalFilters, DocumentoFiscalStatus, DocumentoFiscalTipo } from '../../types/fiscal.types';

interface Props {
  tipoFiltro?: DocumentoFiscalTipo;
  isHomologacao?: boolean;
  statusFilterExterno?: DocumentoFiscalStatus | null;
}

const props = withDefaults(defineProps<Props>(), {
  tipoFiltro: undefined,
  isHomologacao: false,
  statusFilterExterno: undefined,
});

defineEmits<{
  (e: 'abrir-detalhes', id: number): void;
}>();

const toast = useToast();
const queryClient = useQueryClient();

const busca = ref('');
const statusFilter = ref<string | null>(null);
const tipoFilterInterno = ref<string | null>(null);
const pagina = ref(1);

// Sincronizar filtro externo (vindo dos stats cards) com o filtro interno
watch(() => props.statusFilterExterno, (val) => {
  if (val !== undefined) {
    statusFilter.value = val;
    pagina.value = 1;
  }
});

const filters = computed<DocumentoFiscalFilters>(() => ({
  busca: busca.value || undefined,
  status: (statusFilter.value as DocumentoFiscalStatus) || undefined,
  tipo: (props.tipoFiltro ?? tipoFilterInterno.value) as DocumentoFiscalFilters['tipo'] || undefined,
}));

const { data, isLoading, isError } = useFiscalDocumentosQuery(filters, pagina);

const items = computed(() => data.value?.items ?? []);
const totalPages = computed(() => data.value?.paginas ?? 1);
const totalItems = computed(() => data.value?.total ?? 0);

const statusFilterConfig: Record<string, { label: string; class: string; color: string }> = {
  PENDENTE: { label: 'Pendentes', class: '', color: 'bg-amber-400' },
  PROCESSANDO: { label: 'Processando', class: '', color: 'bg-blue-400' },
  AUTORIZADA: { label: 'Autorizadas', class: '', color: 'bg-green-400' },
  REJEITADA: { label: 'Rejeitadas', class: '', color: 'bg-red-400' },
  CANCELADA: { label: 'Canceladas', class: '', color: 'bg-zinc-400' },
  DENEGADA: { label: 'Denegadas', class: '', color: 'bg-red-400' },
  INDETERMINADA: { label: 'Sem retorno', class: '', color: 'bg-orange-400' },
  NAO_TRANSMITIDA: { label: 'Nao transmitidas', class: '', color: 'bg-slate-400' },
};

const tipoFilterConfig: Record<string, { label: string; class: string; color: string }> = {
  NFE: { label: 'NF-e', class: '', color: 'bg-blue-400' },
  NFCE: { label: 'NFC-e', class: '', color: 'bg-emerald-400' },
  NFSE: { label: 'NFS-e', class: '', color: 'bg-purple-400' },
};

const reemitirMutation = useMutation({
  mutationFn: (id: number) => fiscalService.reemitirDocumento(id),
  onSuccess: () => {
    // A frase era 'Documento reenviado para emissão.' e NADA era enviado:
    // `reemitir_documento` cria a linha nova e nao transmite. O operador saia
    // daqui convencido de que a nota tinha ido, e so descobria o contrario
    // quando alguem perguntava pela nota — no lugar errado, dias depois.
    toast.success('Nova tentativa criada. Emita para transmitir — nada foi enviado ainda.');
    queryClient.invalidateQueries({ queryKey: fiscalKeys.documentos() });
    queryClient.invalidateQueries({ queryKey: fiscalKeys.resumo() });
  },
  onError: (error) => {
    toast.error(getErrorMessage(error as AxiosError<ApiError>));
  },
});

const consultarMutation = useFiscalConsultarMutation();

// --- Modal cancelar ---
const showCancelarModal = ref(false);

function abrirCancelarModal(id: number) {
  cancelarDocIds.value = [id];
  showCancelarModal.value = true;
}

function podeCancelar(status: string): boolean {
  return status === 'AUTORIZADA';
}

function podeConsultar(status: string): boolean {
  return status === 'PROCESSANDO' || status === 'PENDENTE';
}

function formatarData(iso: string | null): string {
  if (!iso) return '-';
  return formatDataHora(iso);
}

function origemLabel(tipo: string, id: number | null, numeroOs: string | null): string {
  const label = ORIGEM_LABELS[tipo] ?? tipo;
  if (tipo === 'ORDEM_SERVICO' && numeroOs) return `${label} #${numeroOs}`;
  if (id) return `${label} #${id}`;
  return label;
}

function statusClasses(status: string) {
  const c = STATUS_COLORS[status];
  return c ? `${c.bg} ${c.text}` : 'bg-zinc-100 text-zinc-500';
}

function podeReemitir(status: string): boolean {
  return status === 'REJEITADA' || status === 'DENEGADA';
}

// --- Seleção em lote ---
const selectedIds = ref<Set<number>>(new Set());

// Limpar seleção ao mudar de página ou filtro
watch([pagina, statusFilter], () => {
  selectedIds.value = new Set();
});

const allPageSelected = computed(() =>
  items.value.length > 0 && items.value.every(doc => selectedIds.value.has(doc.id)),
);

function toggleSelectAll() {
  if (allPageSelected.value) {
    selectedIds.value = new Set();
  } else {
    selectedIds.value = new Set(items.value.map(doc => doc.id));
  }
}

function toggleSelect(id: number) {
  const next = new Set(selectedIds.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selectedIds.value = next;
}

const selectedDocs = computed(() =>
  items.value.filter(doc => selectedIds.value.has(doc.id)),
);

const todasReemissiveis = computed(() =>
  selectedDocs.value.length > 0 && selectedDocs.value.every(d => podeReemitir(d.status)),
);

const todasCancelaveis = computed(() =>
  selectedDocs.value.length > 0 && selectedDocs.value.every(d => podeCancelar(d.status)),
);

// Cancelamento em lote
const cancelarDocIds = ref<number[]>([]);

function abrirCancelarLote() {
  cancelarDocIds.value = selectedDocs.value.filter(d => podeCancelar(d.status)).map(d => d.id);
  showCancelarModal.value = true;
}

async function reemitirLote() {
  const ids = selectedDocs.value.filter(d => podeReemitir(d.status)).map(d => d.id);
  for (const id of ids) {
    reemitirMutation.mutate(id);
  }
  selectedIds.value = new Set();
}
</script>

<template>
  <BaseTableContainer
    :is-loading="isLoading"
    :is-error="isError"
    :is-empty="items.length === 0"
    :current-page="pagina"
    :total-pages="totalPages"
    :total-items="totalItems"
    item-label="documento"
    empty-title="Nenhum documento fiscal encontrado"
    empty-description="Os documentos aparecerão aqui quando forem emitidos."
    @update:current-page="pagina = $event"
  >
    <template #toolbar>
      <BaseSearchInput
        v-model="busca"
        placeholder="Buscar por chave, origem ou destinatário..."
      />
      <BaseFilter
        v-model="statusFilter"
        :filter-config="statusFilterConfig"
        title="Filtrar por Status"
        button-label="Status"
      />
      <BaseFilter
        v-if="!tipoFiltro"
        v-model="tipoFilterInterno"
        :filter-config="tipoFilterConfig"
        title="Filtrar por Tipo"
        button-label="Tipo"
      />
    </template>

    <table class="w-full text-left min-w-200">
      <thead>
        <tr class="bg-zinc-50/50 text-[10px] uppercase tracking-wider text-zinc-500 font-bold border-b border-zinc-100">
          <th class="pl-4 pr-2 py-3 md:pl-6 md:pr-3 w-12">
            <input
              type="checkbox"
              class="rounded border-zinc-300 text-brand-primary focus:ring-brand-primary cursor-pointer"
              :checked="allPageSelected"
              @change="toggleSelectAll"
            />
          </th>
          <th class="px-4 md:px-6 py-3 md:py-4">Nº</th>
          <th class="px-4 md:px-6 py-3 md:py-4">Destinatário</th>
          <th class="px-4 md:px-6 py-3 md:py-4 text-right">Valor</th>
          <th class="px-4 md:px-6 py-3 md:py-4">Status</th>
          <th class="px-4 md:px-6 py-3 md:py-4">Data</th>
          <th class="px-4 md:px-6 py-3 md:py-4 text-right min-w-36">Ações Rápidas</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-zinc-100">
        <tr
          v-for="doc in items"
          :key="doc.id"
          class="hover:bg-zinc-50/50 transition-colors cursor-pointer group"
          @click="$emit('abrir-detalhes', doc.id)"
        >
          <!-- Checkbox -->
          <td class="pl-4 pr-2 py-3 md:pl-6 md:pr-3 w-12" @click.stop>
            <input
              type="checkbox"
              class="rounded border-zinc-300 text-brand-primary focus:ring-brand-primary cursor-pointer"
              :checked="selectedIds.has(doc.id)"
              @change="toggleSelect(doc.id)"
            />
          </td>
          <!-- Moldura N/Série -->
          <td class="px-4 md:px-6 py-3 md:py-4">
            <div class="w-10 h-10 bg-brand-primary/10 rounded-xl flex flex-col items-center justify-center text-brand-primary">
              <span class="text-[7px] opacity-70 font-bold leading-none">NF-E</span>
              <span class="text-sm font-black leading-none mt-0.5">{{ doc.numero_documento ?? '-' }}</span>
              <span class="text-[8px] opacity-70 font-semibold leading-none mt-0.5">S{{ doc.serie ?? '-' }}</span>
            </div>
          </td>
          <!-- Destinatário -->
          <td class="px-4 md:px-6 py-3 md:py-4">
            <div class="flex flex-col">
              <span class="text-sm font-semibold text-zinc-900 group-hover:text-brand-primary transition-colors truncate max-w-xs">
                {{ doc.destinatario_nome || 'Consumidor Final' }}
              </span>
              <span class="text-[10px] text-zinc-400 mt-0.5 truncate">
                {{ origemLabel(doc.origem_tipo, doc.origem_id, doc.origem_numero_os) }}
              </span>
              <div
                v-if="doc.status === 'REJEITADA' && (doc.motivo_rejeicao || doc.mensagem_sefaz)"
                class="flex items-center gap-1 mt-1 text-[11px] text-red-600 truncate max-w-xs"
                :title="doc.motivo_rejeicao || doc.mensagem_sefaz || ''"
              >
                <AlertCircle :size="12" class="shrink-0 text-red-500" />
                <span class="truncate">{{ doc.motivo_rejeicao || doc.mensagem_sefaz }}</span>
              </div>
            </div>
          </td>
          <td class="px-4 md:px-6 py-3 md:py-4 text-xs md:text-sm font-medium text-zinc-600 group-hover:text-brand-primary transition-colors text-right whitespace-nowrap">
            {{ doc.valor_total != null ? formatCurrency(doc.valor_total) : '-' }}
          </td>
          <td class="px-4 md:px-6 py-3 md:py-4">
            <span
              :class="[
                'px-2 md:px-3 py-1 rounded-full text-[10px] md:text-[11px] font-bold whitespace-nowrap inline-block',
                statusFilterConfig[doc.status]?.class || statusClasses(doc.status)
              ]"
            >
              {{ STATUS_LABELS[doc.status] ?? doc.status }}
            </span>
          </td>
          <td class="px-4 md:px-6 py-3 md:py-4 text-xs md:text-sm font-medium text-zinc-600 group-hover:text-brand-primary transition-colors whitespace-nowrap">
            {{ formatarData(doc.data_emissao ?? doc.data_criacao) }}
          </td>
          <td class="px-4 md:px-6 py-3 md:py-4 text-right">
            <div class="flex items-center justify-end h-full">
              <div class="hidden group-hover:flex items-center justify-end gap-1">
                <button
                  v-if="doc.url_pdf"
                  type="button"
                  class="p-2 rounded-lg text-zinc-400 hover:text-brand-primary hover:bg-brand-primary/10 transition-colors cursor-pointer"
                  title="Abrir PDF"
                  @click.stop="abrirArquivo(doc.url_pdf!)"
                >
                  <FileText :size="18" />
                </button>
                <button
                  v-if="doc.url_xml"
                  type="button"
                  class="p-2 rounded-lg text-zinc-400 hover:text-brand-primary hover:bg-brand-primary/10 transition-colors cursor-pointer"
                  title="Abrir XML"
                  @click.stop="abrirArquivo(doc.url_xml!)"
                >
                  <FileCode :size="18" />
                </button>
                <button
                  v-if="podeConsultar(doc.status)"
                  type="button"
                  class="p-2 rounded-lg text-zinc-400 hover:text-blue-600 hover:bg-blue-50 transition-colors cursor-pointer"
                  title="Consultar status"
                  :disabled="consultarMutation.isPending.value"
                  @click.stop="consultarMutation.mutate(doc.id)"
                >
                  <Search :size="18" />
                </button>
                <button
                  v-if="podeReemitir(doc.status)"
                  type="button"
                  class="p-2 rounded-lg text-zinc-400 hover:text-amber-600 hover:bg-amber-50 transition-colors cursor-pointer"
                  title="Reemitir"
                  :disabled="reemitirMutation.isPending.value"
                  @click.stop="reemitirMutation.mutate(doc.id)"
                >
                  <RefreshCw :size="18" />
                </button>
                <button
                  v-if="podeCancelar(doc.status)"
                  type="button"
                  class="p-2 rounded-lg text-zinc-400 hover:text-red-600 hover:bg-red-50 transition-colors cursor-pointer"
                  title="Cancelar documento"
                  @click.stop="abrirCancelarModal(doc.id)"
                >
                  <Ban :size="18" />
                </button>
              </div>
              <div class="p-2 text-zinc-400 group-hover:hidden cursor-pointer">
                <Ellipsis :size="20" />
              </div>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </BaseTableContainer>

  <FiscalCancelarModal
    :is-open="showCancelarModal"
    :documento-ids="cancelarDocIds"
    @close="showCancelarModal = false; selectedIds = new Set()"
  />

  <!-- Barra flutuante de ações em lote -->
  <Teleport to="body">
    <Transition name="batch-bar">
      <div
        v-if="selectedIds.size > 0"
        class="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 px-5 py-3 bg-zinc-900 text-white rounded-2xl shadow-2xl"
      >
        <span class="text-sm font-medium whitespace-nowrap">
          {{ selectedIds.size }} {{ selectedIds.size === 1 ? 'documento' : 'documentos' }}
        </span>

        <div class="w-px h-5 bg-zinc-700" />

        <BaseButton
          v-if="todasReemissiveis"
          variant="ghost"
          size="sm"
          class="!text-amber-400 hover:!text-amber-300"
          :disabled="reemitirMutation.isPending.value"
          @click="reemitirLote"
        >
          <RefreshCw :size="14" class="mr-1" />
          Reemitir
        </BaseButton>

        <BaseButton
          v-if="todasCancelaveis"
          variant="ghost"
          size="sm"
          class="!text-red-400 hover:!text-red-300"
          @click="abrirCancelarLote"
        >
          <Ban :size="14" class="mr-1" />
          Cancelar
        </BaseButton>

        <button
          type="button"
          class="p-1 rounded-lg text-zinc-400 hover:text-white transition-colors"
          title="Desmarcar todas"
          @click="selectedIds = new Set()"
        >
          <X :size="16" />
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.batch-bar-enter-active,
.batch-bar-leave-active {
  transition: all 0.2s ease;
}
.batch-bar-enter-from,
.batch-bar-leave-to {
  opacity: 0;
  transform: translate(-50%, 12px);
}
</style>
