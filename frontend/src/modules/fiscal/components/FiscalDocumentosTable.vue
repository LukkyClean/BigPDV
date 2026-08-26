<script setup lang="ts">
import { ref, computed } from 'vue';
import { FileText, FileCode, RefreshCw, Search, Ban } from 'lucide-vue-next';
import { useMutation, useQueryClient } from '@tanstack/vue-query';

import BaseTableContainer from '@/shared/components/commons/BaseTableContainer/BaseTableContainer.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import BaseFilter from '@/shared/components/ui/BaseFilter/BaseFilter.vue';
import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage } from '@/shared/utils/error.utils';
import type { AxiosError } from 'axios';
import type { ApiError } from '@/shared/types/axios.types';

import { useFiscalDocumentosQuery } from '../composables/useFiscalDocumentosQuery';
import { useFiscalConsultarMutation } from '../composables/useFiscalConsultarMutation';
import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys, STATUS_COLORS, TIPO_LABELS, ORIGEM_LABELS } from '../constants/fiscal.constants';
import { abrirArquivo } from '../utils/abrirArquivo';
import FiscalCancelarModal from './FiscalCancelarModal.vue';
import type { DocumentoFiscalFilters, DocumentoFiscalStatus, DocumentoFiscalTipo } from '../types/fiscal.types';

interface Props {
  tipoFiltro?: DocumentoFiscalTipo;
  isHomologacao?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  tipoFiltro: undefined,
  isHomologacao: false,
});

const toast = useToast();
const queryClient = useQueryClient();

const busca = ref('');
const statusFilter = ref<string | null>(null);
const tipoFilterInterno = ref<string | null>(null);
const pagina = ref(1);

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
};

const tipoFilterConfig: Record<string, { label: string; class: string; color: string }> = {
  NFE: { label: 'NF-e', class: '', color: 'bg-blue-400' },
  NFCE: { label: 'NFC-e', class: '', color: 'bg-emerald-400' },
  NFSE: { label: 'NFS-e', class: '', color: 'bg-purple-400' },
};

const reemitirMutation = useMutation({
  mutationFn: (id: number) => fiscalService.reemitirDocumento(id),
  onSuccess: () => {
    toast.success('Documento reenviado para emissão.');
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
const cancelarDocId = ref<number | null>(null);

function abrirCancelarModal(id: number) {
  cancelarDocId.value = id;
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
  return new Date(iso).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
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
        placeholder="Buscar por chave ou origem..."
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

    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-zinc-100 text-left text-xs font-semibold uppercase text-zinc-400">
          <th class="px-4 py-3 md:px-6">Tipo</th>
          <th class="px-4 py-3 md:px-6">N / Série</th>
          <th class="px-4 py-3 md:px-6">Origem</th>
          <th class="px-4 py-3 md:px-6">Status</th>
          <th class="px-4 py-3 md:px-6">Data</th>
          <th class="px-4 py-3 md:px-6 text-right">Ações</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="doc in items"
          :key="doc.id"
          class="border-b border-zinc-50 hover:bg-zinc-50/50 transition-colors"
        >
          <td class="px-4 py-3 md:px-6">
            <span class="inline-block px-2 py-0.5 rounded-md text-xs font-semibold bg-zinc-100 text-zinc-600">
              {{ TIPO_LABELS[doc.tipo_documento] ?? doc.tipo_documento }}
            </span>
          </td>
          <td class="px-4 py-3 md:px-6 text-zinc-700">
            {{ doc.numero_documento ?? '-' }}
            <span v-if="doc.serie != null" class="text-zinc-400"> / {{ doc.serie }}</span>
          </td>
          <td class="px-4 py-3 md:px-6 text-zinc-600">
            {{ origemLabel(doc.origem_tipo, doc.origem_id, doc.origem_numero_os) }}
          </td>
          <td class="px-4 py-3 md:px-6">
            <span
              :class="['inline-block px-2 py-0.5 rounded-full text-xs font-semibold', statusClasses(doc.status)]"
            >
              {{ doc.status }}
            </span>
          </td>
          <td class="px-4 py-3 md:px-6 text-zinc-500 whitespace-nowrap">
            {{ formatarData(doc.data_emissao ?? doc.data_criacao) }}
          </td>
          <td class="px-4 py-3 md:px-6">
            <div class="flex items-center justify-end gap-1">
              <button
                v-if="doc.url_pdf"
                class="p-1.5 rounded-lg text-zinc-400 hover:text-brand-primary hover:bg-brand-primary/5 transition-colors"
                title="Abrir PDF"
                @click="abrirArquivo(doc.url_pdf!)"
              >
                <FileText :size="16" />
              </button>
              <button
                v-if="doc.url_xml"
                class="p-1.5 rounded-lg text-zinc-400 hover:text-brand-primary hover:bg-brand-primary/5 transition-colors"
                title="Abrir XML"
                @click="abrirArquivo(doc.url_xml!)"
              >
                <FileCode :size="16" />
              </button>
              <button
                v-if="podeConsultar(doc.status)"
                class="p-1.5 rounded-lg text-zinc-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                title="Consultar status"
                :disabled="consultarMutation.isPending.value"
                @click="consultarMutation.mutate(doc.id)"
              >
                <Search :size="16" />
              </button>
              <button
                v-if="podeReemitir(doc.status)"
                class="p-1.5 rounded-lg text-zinc-400 hover:text-amber-600 hover:bg-amber-50 transition-colors"
                title="Reemitir"
                :disabled="reemitirMutation.isPending.value"
                @click="reemitirMutation.mutate(doc.id)"
              >
                <RefreshCw :size="16" />
              </button>
              <button
                v-if="podeCancelar(doc.status)"
                class="p-1.5 rounded-lg text-zinc-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                title="Cancelar documento"
                @click="abrirCancelarModal(doc.id)"
              >
                <Ban :size="16" />
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </BaseTableContainer>

  <FiscalCancelarModal
    :is-open="showCancelarModal"
    :documento-id="cancelarDocId"
    @close="showCancelarModal = false"
  />
</template>
