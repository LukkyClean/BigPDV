<script setup lang="ts">
import { ref, computed } from 'vue';
import {
  X,
  RotateCcw,
  AlertTriangle,
  FileText,
  FileCode,
  CheckCircle,
  Ban,
  Loader2,
  Copy,
  Check,
} from 'lucide-vue-next';
import { useToast } from '@/shared/composables/useToast';
import { abrirArquivo } from '../../utils/abrirArquivo';
import { STATUS_COLORS } from '../../constants/fiscal.constants';
import { useFiscalHistoricoQuery } from '../../composables/useFiscalHistoricoQuery';
import { useFiscalConsultarMutation } from '../../composables/useFiscalConsultarMutation';
import { useFiscalCancelarMutation } from '../../composables/useFiscalCancelarMutation';
import { formatCurrency } from '@/shared/utils/finance';

const props = defineProps<{
  documentoId: number | null;
  isOpen: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:isOpen', value: boolean): void;
  (e: 'reemitir', id: number): void;
}>();

const close = () => {
  emit('update:isOpen', false);
};

// --- Queries ---
const docIdRef = computed(() => props.documentoId);
const { data: historicoData, isLoading: isLoadingHistorico } = useFiscalHistoricoQuery(docIdRef);

const toast = useToast();
const consultarMutation = useFiscalConsultarMutation();
const cancelarMutation = useFiscalCancelarMutation();

const documento = computed(() => {
  if (!historicoData.value || historicoData.value.tentativas.length === 0) return null;
  return historicoData.value.tentativas[0];
});

// --- Status helpers ---
function getStatusColors(status: string) {
  const colors = STATUS_COLORS[status];
  if (!colors) return 'bg-zinc-100 text-zinc-600';
  return `${colors.bg} ${colors.text}`;
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'AUTORIZADA': return CheckCircle;
    case 'REJEITADA':
    case 'DENEGADA': return AlertTriangle;
    case 'CANCELADA': return Ban;
    default: return Loader2;
  }
}

function isAnimated(status: string) {
  return status === 'PROCESSANDO' || status === 'PENDENTE';
}

// --- Actions ---
const isConsultando = ref(false);
const handleConsultar = async () => {
  if (!documento.value) return;
  isConsultando.value = true;
  try {
    await consultarMutation.mutateAsync(documento.value.id);
  } finally {
    isConsultando.value = false;
  }
};

const justificativaCancelamento = ref('');
const isCancelando = ref(false);
const modalCancelarOpen = ref(false);

const handleCancelar = async () => {
  if (!documento.value || !justificativaCancelamento.value) return;
  isCancelando.value = true;
  try {
    await cancelarMutation.mutateAsync({
      id: documento.value.id,
      justificativa: justificativaCancelamento.value,
    });
    modalCancelarOpen.value = false;
    justificativaCancelamento.value = '';
  } finally {
    isCancelando.value = false;
  }
};

const handleDownload = (tipo: 'pdf' | 'xml') => {
  if (!documento.value) return;
  const url = tipo === 'pdf' ? documento.value.url_pdf : documento.value.url_xml;
  if (!url) {
    toast.warning('URL do ' + tipo.toUpperCase() + ' não disponível');
    return;
  }
  abrirArquivo(url, 'nfe-' + documento.value.id + '.' + tipo);
};

// --- Copy to clipboard ---
const copied = ref(false);
const copyChave = async () => {
  if (!documento.value?.chave_acesso) return;
  try {
    await navigator.clipboard.writeText(documento.value.chave_acesso);
    copied.value = true;
    setTimeout(() => { copied.value = false; }, 2000);
  } catch {
    toast.error('Falha ao copiar');
  }
};

function formatarData(iso: string): string {
  return new Date(iso).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="isOpen" class="fixed inset-0 z-50 overflow-hidden">
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/30 backdrop-blur-sm transition-opacity"
          @click="close"
        />

        <!-- Drawer panel -->
        <div class="absolute inset-y-0 right-0 flex max-w-full pl-10">
          <div class="w-screen max-w-lg">
            <div class="flex h-full flex-col bg-white shadow-2xl">
              <!-- Header -->
              <div class="flex items-center justify-between border-b border-zinc-200 bg-zinc-50 px-6 py-4">
                <div>
                  <h2 class="text-lg font-semibold text-zinc-900">Detalhes da NF-e</h2>
                  <p v-if="documento" class="text-xs text-zinc-500 mt-0.5">
                    Nº {{ documento.numero_documento ?? '-' }} · Série {{ documento.serie ?? '-' }}
                  </p>
                </div>
                <button
                  @click="close"
                  class="rounded-lg p-1.5 text-zinc-400 transition-colors hover:bg-zinc-200 hover:text-zinc-600"
                >
                  <X class="h-5 w-5" />
                </button>
              </div>

              <!-- Loading state -->
              <div v-if="isLoadingHistorico" class="flex flex-1 items-center justify-center">
                <div class="text-center">
                  <Loader2 class="mx-auto h-8 w-8 animate-spin text-brand-primary" />
                  <p class="mt-2 text-sm text-zinc-500">Carregando detalhes...</p>
                </div>
              </div>

              <!-- Content -->
              <div v-else-if="documento" class="flex-1 overflow-y-auto">
                <div class="space-y-5 p-6">

                  <!-- Status Banner -->
                  <div
                    :class="['flex items-start gap-3 rounded-xl p-4', getStatusColors(documento.status)]"
                  >
                    <component
                      :is="getStatusIcon(documento.status)"
                      class="mt-0.5 h-5 w-5 shrink-0"
                      :class="{ 'animate-spin': isAnimated(documento.status) }"
                    />
                    <div class="min-w-0 flex-1">
                      <h3 class="text-sm font-semibold">{{ documento.status }}</h3>
                      <p class="mt-0.5 text-sm opacity-80">
                        {{ documento.mensagem_sefaz || 'Sem detalhes disponíveis' }}
                      </p>
                    </div>
                  </div>

                  <!-- Key Info Grid -->
                  <div class="rounded-xl border border-zinc-200 bg-white">
                    <div class="grid grid-cols-2 divide-x divide-zinc-100">
                      <div class="p-4">
                        <span class="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Valor Total</span>
                        <p class="mt-1 text-lg font-bold text-emerald-600">
                          {{ documento.valor_total != null ? formatCurrency(documento.valor_total) : 'R$ 0,00' }}
                        </p>
                      </div>
                      <div class="p-4">
                        <span class="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Ambiente</span>
                        <p class="mt-1 text-lg font-bold text-zinc-800">
                          {{ documento.ambiente_emissao === 1 ? 'Produção' : 'Homologação' }}
                        </p>
                      </div>
                    </div>

                    <!-- Chave de Acesso -->
                    <div class="border-t border-zinc-100 p-4">
                      <div class="flex items-center justify-between">
                        <span class="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Chave de Acesso</span>
                        <button
                          v-if="documento.chave_acesso"
                          @click="copyChave"
                          class="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-700"
                        >
                          <Check v-if="copied" class="h-3 w-3 text-emerald-500" />
                          <Copy v-else class="h-3 w-3" />
                          {{ copied ? 'Copiado!' : 'Copiar' }}
                        </button>
                      </div>
                      <p class="mt-1 break-all rounded-lg bg-zinc-50 p-2.5 font-mono text-xs leading-relaxed text-zinc-700">
                        {{ documento.chave_acesso || 'Não disponível' }}
                      </p>
                    </div>

                    <!-- Protocolo -->
                    <div class="border-t border-zinc-100 p-4">
                      <span class="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Protocolo de Autorização</span>
                      <p class="mt-1 font-mono text-sm text-zinc-700">
                        {{ documento.protocolo_autorizacao || '-' }}
                      </p>
                    </div>
                  </div>

                  <!-- Quick Actions -->
                  <div>
                    <h4 class="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-400">Ações</h4>
                    <div class="grid grid-cols-2 gap-2">
                      <button
                        @click="handleDownload('pdf')"
                        :disabled="!documento.url_pdf"
                        class="flex items-center justify-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2.5 text-sm font-medium text-zinc-700 transition-all hover:border-zinc-300 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        <FileText class="h-4 w-4 text-red-500" /> DANFE (PDF)
                      </button>
                      <button
                        @click="handleDownload('xml')"
                        :disabled="!documento.url_xml"
                        class="flex items-center justify-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2.5 text-sm font-medium text-zinc-700 transition-all hover:border-zinc-300 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        <FileCode class="h-4 w-4 text-blue-500" /> XML
                      </button>

                      <button
                        v-if="documento.status === 'PROCESSANDO' || documento.status === 'PENDENTE'"
                        @click="handleConsultar"
                        :disabled="isConsultando"
                        class="col-span-2 flex items-center justify-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2.5 text-sm font-medium text-blue-700 transition-all hover:bg-blue-100 disabled:opacity-50"
                      >
                        <RotateCcw class="h-4 w-4" :class="{ 'animate-spin': isConsultando }" />
                        Consultar Status SEFAZ
                      </button>

                      <button
                        v-if="documento.status === 'REJEITADA'"
                        @click="emit('reemitir', documento.id)"
                        class="col-span-2 flex items-center justify-center gap-2 rounded-lg bg-brand-primary px-3 py-2.5 text-sm font-medium text-white transition-all hover:opacity-90"
                      >
                        <RotateCcw class="h-4 w-4" />
                        Corrigir e Reemitir
                      </button>

                      <button
                        v-if="documento.status === 'AUTORIZADA'"
                        @click="modalCancelarOpen = !modalCancelarOpen"
                        class="col-span-2 flex items-center justify-center gap-2 rounded-lg border border-red-200 px-3 py-2.5 text-sm font-medium text-red-600 transition-all hover:bg-red-50"
                      >
                        <Ban class="h-4 w-4" />
                        Cancelar NF-e
                      </button>
                    </div>
                  </div>

                  <!-- Cancel Form (inline) -->
                  <Transition name="fade">
                    <div v-if="modalCancelarOpen" class="rounded-xl border border-red-200 bg-red-50 p-4">
                      <label class="mb-2 block text-sm font-medium text-red-800">
                        Justificativa do Cancelamento
                      </label>
                      <textarea
                        v-model="justificativaCancelamento"
                        class="mb-3 w-full rounded-lg border border-red-200 bg-white p-3 text-sm shadow-sm transition-colors focus:border-red-400 focus:outline-none focus:ring-2 focus:ring-red-100"
                        rows="3"
                        placeholder="Informe a justificativa (mínimo 15 caracteres)..."
                      />
                      <div class="flex justify-end gap-2">
                        <button
                          @click="modalCancelarOpen = false"
                          class="rounded-lg px-3 py-2 text-sm text-zinc-600 transition-colors hover:bg-zinc-100"
                        >
                          Fechar
                        </button>
                        <button
                          @click="handleCancelar"
                          :disabled="justificativaCancelamento.length < 15 || isCancelando"
                          class="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
                        >
                          {{ isCancelando ? 'Cancelando...' : 'Confirmar Cancelamento' }}
                        </button>
                      </div>
                    </div>
                  </Transition>

                  <!-- Timeline -->
                  <div v-if="historicoData && historicoData.tentativas.length > 0">
                    <h4 class="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                      Histórico de Emissão ({{ historicoData.tentativas.length }})
                    </h4>
                    <div class="relative space-y-0">
                      <div
                        v-for="(tentativa, index) in historicoData.tentativas"
                        :key="tentativa.id"
                        class="relative flex gap-3 pb-4 last:pb-0"
                      >
                        <!-- Vertical line -->
                        <div
                          v-if="index !== historicoData.tentativas.length - 1"
                          class="absolute left-[11px] top-6 bottom-0 w-px bg-zinc-200"
                        />
                        <!-- Dot -->
                        <div
                          class="relative z-10 mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 bg-white"
                          :class="{
                            'border-emerald-500': tentativa.status === 'AUTORIZADA',
                            'border-red-500': tentativa.status === 'REJEITADA' || tentativa.status === 'DENEGADA',
                            'border-zinc-400': tentativa.status === 'CANCELADA',
                            'border-blue-400': tentativa.status === 'PROCESSANDO' || tentativa.status === 'PENDENTE',
                          }"
                        >
                          <div
                            class="h-2 w-2 rounded-full"
                            :class="{
                              'bg-emerald-500': tentativa.status === 'AUTORIZADA',
                              'bg-red-500': tentativa.status === 'REJEITADA' || tentativa.status === 'DENEGADA',
                              'bg-zinc-400': tentativa.status === 'CANCELADA',
                              'bg-blue-400': tentativa.status === 'PROCESSANDO' || tentativa.status === 'PENDENTE',
                            }"
                          />
                        </div>
                        <!-- Content -->
                        <div class="min-w-0 flex-1">
                          <div class="flex items-baseline gap-2">
                            <span class="text-sm font-semibold text-zinc-800">{{ tentativa.status }}</span>
                            <span class="text-xs text-zinc-400">{{ formatarData(tentativa.data_criacao) }}</span>
                          </div>
                          <p
                            v-if="tentativa.mensagem_sefaz"
                            class="mt-1 rounded-lg bg-zinc-50 p-2 text-xs leading-relaxed text-zinc-600"
                          >
                            {{ tentativa.mensagem_sefaz }}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                </div>
              </div>

              <!-- Empty state -->
              <div v-else class="flex flex-1 items-center justify-center">
                <p class="text-sm text-zinc-500">Documento não encontrado.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.2s ease;
}
.drawer-enter-active > div:last-child,
.drawer-leave-active > div:last-child {
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from > div:last-child,
.drawer-leave-to > div:last-child {
  transform: translateX(100%);
}

.fade-enter-active,
.fade-leave-active {
  transition: all 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
