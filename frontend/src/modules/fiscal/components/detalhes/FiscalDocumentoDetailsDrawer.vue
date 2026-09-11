<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
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
  User,
  Maximize2,
  Minimize2,
  Package,
  History,
  Info,
  Settings,
  Edit3,
  RefreshCw,
  Clock,
  ExternalLink,
  Printer,
} from 'lucide-vue-next';

import { useToast } from '@/shared/composables/useToast';
import { abrirArquivo } from '../../utils/abrirArquivo';
import { STATUS_COLORS, STATUS_LABELS } from '../../constants/fiscal.constants';
import { useFiscalHistoricoQuery } from '../../composables/useFiscalHistoricoQuery';
import { useFiscalConsultarMutation } from '../../composables/useFiscalConsultarMutation';
import { useFiscalCancelarMutation } from '../../composables/useFiscalCancelarMutation';
import { useFiscalReemitirMutation } from '../../composables/useFiscalReemitirMutation';
import { useNfceReimpressao } from '../../composables/useNfceReimpressao';
import { formatCurrency } from '@/shared/utils/finance';
import { formatCPF, formatCNPJ } from '@/shared/utils/document.utils';
import { formatDataHora } from '@/shared/utils/date.utils';
import {
  analisarDiagnosticoFiscal,
  formatarDiagnosticoParaSuporte,
} from '../../utils/fiscalDiagnostic';
import FiscalEditarVendaModal from './FiscalEditarVendaModal.vue';

// Integração com Edição de Produtos do Sistema
import ProductModal from '@/modules/products/inventory/components/ProductModal.vue';
import { useProductModal } from '@/modules/products/inventory/composables/useProductModal';
import { getProdutoById, getProdutos } from '@/modules/products/inventory/services/product.service';
import type { DocumentoItemResumo } from '../../types/fiscal.types';

const props = defineProps<{
  documentoId: number | null;
  isOpen: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:isOpen', value: boolean): void;
  (e: 'reemitir', id: number): void;
  (e: 'abrir-resolucao-produtos'): void;
}>();

const router = useRouter();
const toast = useToast();
const isExpanded = ref(false);
const activeTab = ref<'geral' | 'itens' | 'historico'>('geral');
const showEditarVendaModal = ref(false);
const isLoadingProductModal = ref(false);

const { openEditModal, openViewModal } = useProductModal();

const podeEditarDados = computed(() => {
  if (!documento.value) return false;
  // Só REJEITADA pode ter dados corrigidos para reemissão. DENEGADA não é
  // reemitível (ver `podeReemitir`), e as demais são imutáveis: AUTORIZADA,
  // CANCELADA e PROCESSANDO já estão (ou podem estar) na SEFAZ.
  return documento.value.status === 'REJEITADA';
});

const close = () => {
  emit('update:isOpen', false);
};

// --- Queries & Mutations ---
const docIdRef = computed(() => props.documentoId);
const { data: historicoData, isLoading: isLoadingHistorico } = useFiscalHistoricoQuery(docIdRef);

const consultarMutation = useFiscalConsultarMutation();
const cancelarMutation = useFiscalCancelarMutation();
const reemitirMutation = useFiscalReemitirMutation();

const documento = computed(() => {
  if (!historicoData.value || historicoData.value.tentativas.length === 0) return null;
  return historicoData.value.tentativas[0];
});

// Segunda via do cupom — só faz sentido na NFC-e (ver `podeReimprimir`).
const { reimprimir, podeReimprimir, isReimprimindo } = useNfceReimpressao();

// Diagnóstico inteligente
const diagnostico = computed(() => analisarDiagnosticoFiscal(documento.value));

// --- Status helpers ---
function getStatusColors(status: string) {
  const colors = STATUS_COLORS[status];
  if (!colors) return { bg: 'bg-zinc-100', text: 'text-zinc-600', border: 'border-zinc-200' };
  return colors;
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'AUTORIZADA':
      return CheckCircle;
    case 'REJEITADA':
    case 'DENEGADA':
      return AlertTriangle;
    case 'CANCELADA':
      return Ban;
    case 'PENDENTE':
    case 'PROCESSANDO':
    // Sem retorno confirmado ainda conta como "em aberto" — o relogio diz isso
    // melhor que o triangulo de alerta, que sugeriria recusa.
    case 'INDETERMINADA':
      return Clock;
    case 'NAO_TRANSMITIDA':
      return Ban;
    default:
      return Loader2;
  }
}

function isAnimated(status: string) {
  return status === 'PROCESSANDO';
}

// --- Actions ---
const isConsultando = ref(false);
const handleConsultar = async () => {
  if (!documento.value) return;
  isConsultando.value = true;
  try {
    await consultarMutation.mutateAsync(documento.value.id);
    toast.success('Status sincronizado com a SEFAZ.');
  } finally {
    isConsultando.value = false;
  }
};

// Reemite AGORA (vai à SEFAZ) e troca o drawer para o documento novo, que é
// onde está o desfecho. Antes este handler só emitia o id do documento
// atual: a view gravava o mesmo id e nada acontecia -- o único caminho que
// funcionava era o "Salvar e Reemitir" do modal de edição.
const handleReemitir = async () => {
  if (!documento.value) return;
  try {
    const novoDoc = await reemitirMutation.mutateAsync(documento.value.id);
    emit('reemitir', novoDoc.id);
  } catch {
    // A mutação já mostrou o erro no toast.
  }
};

// Só REJEITADA volta à SEFAZ. DENEGADA é decisão sobre o contribuinte:
// reenviar volta denegada e queima outro número (o backend recusa com 422).
const podeReemitir = computed(() => documento.value?.status === 'REJEITADA');
const rotuloDocumento = computed(() =>
  documento.value?.tipo_documento === 'NFCE' ? 'NFC-e' : 'NF-e',
);

// --- Abrir View/Edição de Item ---
async function handleAbrirItemProduto(item: DocumentoItemResumo) {
  isLoadingProductModal.value = true;
  try {
    let produto = null;
    if (item.produto_id) {
      produto = await getProdutoById(item.produto_id);
    }
    if (!produto && (item.codigo_barras || item.nome)) {
      const lista = await getProdutos(item.codigo_barras || item.nome, 5);
      produto = lista.find(p => (item.produto_id && p.id === item.produto_id) || p.nome === item.nome) || lista[0];
    }
    if (produto) {
      if (podeEditarDados.value) {
        openEditModal(produto);
      } else {
        openViewModal(produto);
      }
    } else {
      toast.warning('Produto não localizado no cadastro.');
    }
  } catch (error) {
    console.error('Erro ao carregar produto:', error);
    toast.error('Não foi possível carregar os detalhes do produto.');
  } finally {
    isLoadingProductModal.value = false;
  }
}

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
  // `abrirArquivo` delega ao opener do Tauri (ou a uma nova aba): quem nomeia o
  // arquivo e o destino, entao nao ha nome de arquivo a passar aqui.
  abrirArquivo(url);
};

// --- Copy helpers ---
const copiedChave = ref(false);
const copyChave = async () => {
  if (!documento.value?.chave_acesso) return;
  try {
    await navigator.clipboard.writeText(documento.value.chave_acesso);
    copiedChave.value = true;
    toast.success('Chave de acesso copiada!');
    setTimeout(() => {
      copiedChave.value = false;
    }, 2000);
  } catch {
    toast.error('Falha ao copiar');
  }
};

const copiedDiagnostico = ref(false);
const copyDiagnostico = async () => {
  if (!documento.value) return;
  try {
    const texto = formatarDiagnosticoParaSuporte(documento.value);
    await navigator.clipboard.writeText(texto);
    copiedDiagnostico.value = true;
    toast.success('Diagnóstico completo copiado para a área de transferência!');
    setTimeout(() => {
      copiedDiagnostico.value = false;
    }, 2000);
  } catch {
    toast.error('Falha ao copiar diagnóstico');
  }
};

function handleActionDiagnostico(tipo?: string) {
  if (!tipo) return;
  if (tipo === 'CONFIG_FISCAL') {
    router.push({ name: 'enterprise' });
    close();
  } else if (tipo === 'EDITAR_VENDA') {
    showEditarVendaModal.value = true;
  } else if (tipo === 'RESOLVER_PRODUTOS') {
    emit('abrir-resolucao-produtos');
  } else if (tipo === 'RECONSULTAR') {
    handleConsultar();
  } else if (tipo === 'REEMITIR') {
    handleReemitir();
  }
}

const docClienteFormatado = computed(() => {
  if (!documento.value?.destinatario_documento) return '';
  const doc = documento.value.destinatario_documento.replace(/\D/g, '');
  if (doc.length === 14) return formatCNPJ(doc);
  if (doc.length === 11) return formatCPF(doc);
  return documento.value.destinatario_documento;
});

function formatarData(iso?: string | null): string {
  if (!iso) return '-';
  return formatDataHora(iso);
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
        <div class="absolute inset-y-0 right-0 flex max-w-full pl-6">
          <div
            :class="[
              'w-screen transition-all duration-300 ease-in-out',
              isExpanded ? 'max-w-4xl' : 'max-w-2xl',
            ]"
          >
            <div class="flex h-full flex-col bg-white shadow-2xl">
              
              <!-- Header -->
              <div class="flex items-center justify-between border-b border-zinc-200 bg-zinc-50/80 px-6 py-4">
                <div class="flex items-center gap-3">
                  <div
                    v-if="documento"
                    :class="[
                      'flex h-10 w-10 items-center justify-center rounded-xl border shadow-2xs',
                      getStatusColors(documento.status).bg,
                      getStatusColors(documento.status).text,
                      getStatusColors(documento.status).border,
                    ]"
                  >
                    <component
                      :is="getStatusIcon(documento.status)"
                      class="h-5 w-5"
                      :class="{ 'animate-spin': isAnimated(documento.status) }"
                    />
                  </div>
                  <div>
                    <div class="flex items-center gap-2.5">
                      <h2 class="text-lg font-bold text-zinc-900">Detalhes da NF-e</h2>
                      <span
                        v-if="documento"
                        :class="[
                          'rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider',
                          getStatusColors(documento.status).bg,
                          getStatusColors(documento.status).text,
                        ]"
                      >
                        {{ STATUS_LABELS[documento.status] ?? documento.status }}
                      </span>
                    </div>
                    <p v-if="documento" class="text-xs text-zinc-500 mt-0.5">
                      Nº {{ documento.numero_documento ?? '-' }} · Série {{ documento.serie ?? '-' }}
                      <span v-if="documento.origem_id || documento.venda_id">
                        · Venda #{{ documento.origem_id ?? documento.venda_id }}
                      </span>
                    </p>
                  </div>
                </div>

                <div class="flex items-center gap-1.5">
                  <!-- Segunda via do cupom: só na NFC-e autorizada. A NF-e tem
                       DANFE em PDF, que sai pelo botão de download. -->
                  <button
                    v-if="podeReimprimir(documento)"
                    type="button"
                    data-reimprimir-cupom
                    :disabled="isReimprimindo"
                    @click="documento && reimprimir(documento)"
                    class="rounded-lg p-2 text-zinc-400 transition-colors hover:bg-zinc-200 hover:text-zinc-700 cursor-pointer disabled:opacity-50 disabled:cursor-wait"
                    title="Reimprimir cupom (2a via)"
                  >
                    <component
                      :is="isReimprimindo ? Loader2 : Printer"
                      class="h-4 w-4"
                      :class="{ 'animate-spin': isReimprimindo }"
                    />
                  </button>
                  <button
                    type="button"
                    @click="isExpanded = !isExpanded"
                    class="rounded-lg p-2 text-zinc-400 transition-colors hover:bg-zinc-200 hover:text-zinc-700 cursor-pointer"
                    :title="isExpanded ? 'Reduzir painel' : 'Expandir painel'"
                  >
                    <component :is="isExpanded ? Minimize2 : Maximize2" class="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    @click="close"
                    class="rounded-lg p-2 text-zinc-400 transition-colors hover:bg-zinc-200 hover:text-zinc-700 cursor-pointer"
                  >
                    <X class="h-5 w-5" />
                  </button>
                </div>
              </div>

              <!-- Loading state -->
              <div v-if="isLoadingHistorico" class="flex flex-1 items-center justify-center">
                <div class="text-center">
                  <Loader2 class="mx-auto h-8 w-8 animate-spin text-brand-primary" />
                  <p class="mt-2 text-sm text-zinc-500 font-medium">Carregando detalhes fiscais...</p>
                </div>
              </div>

              <!-- Content -->
              <div v-else-if="documento" class="flex flex-1 flex-col overflow-hidden">
                
                <!-- Navegação em Abas (Espaçosa e Organizada) -->
                <div class="px-6 pt-4 pb-4 border-b border-zinc-200/80 bg-white">
                  <div class="flex items-center gap-1.5 bg-zinc-100/90 p-1.5 rounded-xl border border-zinc-200/80">
                    <button
                      type="button"
                      @click="activeTab = 'geral'"
                      class="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer"
                      :class="
                        activeTab === 'geral'
                          ? 'bg-white text-zinc-900 shadow-sm font-bold'
                          : 'text-zinc-500 hover:text-zinc-900 hover:bg-white/60'
                      "
                    >
                      <Info class="h-4 w-4" />
                      <span>Visão Geral</span>
                    </button>

                    <button
                      type="button"
                      @click="activeTab = 'itens'"
                      class="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer"
                      :class="
                        activeTab === 'itens'
                          ? 'bg-white text-zinc-900 shadow-sm font-bold'
                          : 'text-zinc-500 hover:text-zinc-900 hover:bg-white/60'
                      "
                    >
                      <Package class="h-4 w-4" />
                      <span>Itens & Tributos</span>
                      <span
                        v-if="documento.itens_resumo?.length"
                        class="rounded-full bg-zinc-200 px-1.5 py-0.2 text-[10px] text-zinc-700 font-bold"
                      >
                        {{ documento.itens_resumo.length }}
                      </span>
                    </button>

                    <button
                      type="button"
                      @click="activeTab = 'historico'"
                      class="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer"
                      :class="
                        activeTab === 'historico'
                          ? 'bg-white text-zinc-900 shadow-sm font-bold'
                          : 'text-zinc-500 hover:text-zinc-900 hover:bg-white/60'
                      "
                    >
                      <History class="h-4 w-4" />
                      <span>Histórico SEFAZ</span>
                      <span
                        v-if="historicoData?.tentativas?.length"
                        class="rounded-full bg-zinc-200 px-1.5 py-0.2 text-[10px] text-zinc-700 font-bold"
                      >
                        {{ historicoData.tentativas.length }}
                      </span>
                    </button>
                  </div>
                </div>

                <!-- Corpo com Rolagem -->
                <div class="flex-1 overflow-y-auto p-6 space-y-6">

                  <!-- ABA 1: VISÃO GERAL & DIAGNÓSTICO -->
                  <div v-show="activeTab === 'geral'" class="space-y-5">
                    
                    <!-- Banner Especial para Status PENDENTE ou PROCESSANDO -->
                    <div
                      v-if="documento.status === 'PENDENTE' || documento.status === 'PROCESSANDO'"
                      class="rounded-2xl border border-blue-200 bg-blue-50/70 p-4.5 shadow-sm space-y-3"
                    >
                      <div class="flex items-center justify-between gap-3">
                        <div class="flex items-center gap-2.5">
                          <Clock class="h-5 w-5 text-blue-600 animate-pulse" />
                          <h4 class="text-sm font-bold text-blue-950">
                            Emissão Pendente de Retorno
                          </h4>
                        </div>
                        <span class="rounded-md bg-blue-100 border border-blue-200 px-2 py-0.5 text-[11px] font-bold text-blue-800 uppercase tracking-wider">
                          Aguardando SEFAZ
                        </span>
                      </div>

                      <p class="text-xs text-blue-900 leading-relaxed">
                        Esta nota fiscal foi enviada e está aguardando a autorização final dos servidores da SEFAZ. Clique abaixo para consultar se o documento já foi processado.
                      </p>

                      <div class="pt-1">
                        <button
                          type="button"
                          @click="handleConsultar"
                          :disabled="isConsultando"
                          class="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-blue-700 transition-colors disabled:opacity-50 cursor-pointer"
                        >
                          <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': isConsultando }" />
                          <span>{{ isConsultando ? 'Sincronizando com a SEFAZ...' : 'Sincronizar Status SEFAZ' }}</span>
                        </button>
                      </div>
                    </div>

                    <!-- Banner de Diagnóstico Inteligente (Moderno, Clean e Integrado) -->
                    <div
                      v-if="documento.status === 'REJEITADA' || documento.status === 'DENEGADA'"
                      class="relative overflow-hidden rounded-2xl border border-rose-200/90 bg-gradient-to-b from-rose-50/40 via-white to-rose-50/20 p-5 shadow-xs transition-all"
                    >
                      <!-- Top Accent Line -->
                      <div class="absolute top-0 left-0 right-0 h-1.5 bg-rose-500" />

                      <div class="flex items-center justify-between gap-3 mb-3 pt-1">
                        <div class="flex items-center gap-2.5">
                          <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-rose-100 text-rose-600 shadow-2xs">
                            <AlertTriangle class="h-4.5 w-4.5" />
                          </div>
                          <span class="inline-block rounded-md bg-rose-50 border border-rose-200 px-2.5 py-0.5 text-[10px] font-bold text-rose-700 uppercase tracking-wider">
                            {{ diagnostico.badge.label }}
                          </span>
                        </div>

                        <button
                          type="button"
                          @click="copyDiagnostico"
                          class="inline-flex items-center gap-1.5 rounded-lg border border-zinc-200 bg-white px-2.5 py-1 text-xs font-semibold text-zinc-600 shadow-2xs transition-colors hover:bg-zinc-50 hover:text-zinc-900 cursor-pointer"
                        >
                          <Check v-if="copiedDiagnostico" class="h-3.5 w-3.5 text-emerald-600" />
                          <Copy v-else class="h-3.5 w-3.5 text-zinc-400" />
                          <span>{{ copiedDiagnostico ? 'Copiado!' : 'Copiar Diagnóstico' }}</span>
                        </button>
                      </div>

                      <h4 class="text-sm font-bold text-zinc-900 tracking-tight">
                        {{ diagnostico.titulo }}
                      </h4>
                      <p class="mt-1 text-xs leading-relaxed text-zinc-600">
                        {{ diagnostico.explicacao }}
                      </p>

                      <!-- Mensagem Original da SEFAZ -->
                      <div
                        v-if="documento.mensagem_sefaz"
                        class="mt-3.5 rounded-xl bg-zinc-50 border border-zinc-200/70 p-3 text-xs leading-relaxed font-mono text-zinc-700"
                      >
                        <span class="text-[10px] uppercase font-bold text-zinc-400 block mb-1 font-sans tracking-wider">
                          Retorno Oficial da SEFAZ
                        </span>
                        {{ documento.mensagem_sefaz }}
                      </div>

                      <!-- Caixa Como Resolver -->
                      <div class="mt-3.5 rounded-xl bg-amber-50/60 border border-amber-200/70 p-3.5 flex items-start gap-2.5">
                        <div class="h-5 w-5 rounded-full bg-amber-100 flex items-center justify-center shrink-0 text-amber-700 text-xs font-bold mt-0.5">
                          💡
                        </div>
                        <p class="text-xs text-amber-950 leading-relaxed">
                          <strong class="font-bold text-amber-900">Como resolver:</strong>
                          {{ diagnostico.comoResolver }}
                        </p>
                      </div>

                      <!-- Botões de Ação Contextuais -->
                      <div class="mt-4 flex flex-wrap items-center gap-2.5 pt-1">
                        <button
                          v-if="diagnostico.acaoPrincipal"
                          type="button"
                          @click="handleActionDiagnostico(diagnostico.acaoPrincipal.tipo)"
                          class="inline-flex items-center gap-2 rounded-xl bg-zinc-900 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-zinc-800 transition-all cursor-pointer"
                        >
                          <Edit3 v-if="diagnostico.acaoPrincipal.tipo === 'EDITAR_VENDA'" class="h-3.5 w-3.5" />
                          <Settings v-else-if="diagnostico.acaoPrincipal.tipo === 'CONFIG_FISCAL'" class="h-3.5 w-3.5" />
                          <Package v-else-if="diagnostico.acaoPrincipal.tipo === 'RESOLVER_PRODUTOS'" class="h-3.5 w-3.5" />
                          <RotateCcw v-else class="h-3.5 w-3.5" />
                          <span>{{ diagnostico.acaoPrincipal.label }}</span>
                        </button>

                        <button
                          v-if="podeReemitir"
                          type="button"
                          @click="handleReemitir"
                          :disabled="reemitirMutation.isPending.value"
                          class="inline-flex items-center gap-2 rounded-xl bg-brand-primary px-4 py-2 text-xs font-bold text-white shadow-xs hover:opacity-90 transition-all cursor-pointer disabled:opacity-50"
                        >
                          <RotateCcw class="h-3.5 w-3.5" :class="{ 'animate-spin': reemitirMutation.isPending.value }" />
                          <span>{{ reemitirMutation.isPending.value ? 'Enviando à SEFAZ...' : `Reemitir ${rotuloDocumento}` }}</span>
                        </button>
                        <p v-else class="text-xs text-zinc-500">
                          Nota denegada: a SEFAZ recusou pela situação cadastral do contribuinte,
                          e reenviar volta denegada. Regularize junto à SEFAZ antes de emitir de novo.
                        </p>
                      </div>
                    </div>

                    <!-- Card de Totais & Ambiente -->
                    <div class="grid grid-cols-2 gap-3">
                      <div class="rounded-xl border border-zinc-200 bg-white p-4 shadow-2xs">
                        <span class="text-[10px] font-bold uppercase tracking-wider text-zinc-400 block">
                          Valor Total da Nota
                        </span>
                        <p class="mt-1 text-xl font-bold text-emerald-600">
                          {{ documento.valor_total != null ? formatCurrency(documento.valor_total) : 'R$ 0,00' }}
                        </p>
                      </div>

                      <div class="rounded-xl border border-zinc-200 bg-white p-4 shadow-2xs">
                        <span class="text-[10px] font-bold uppercase tracking-wider text-zinc-400 block">
                          Ambiente de Emissão
                        </span>
                        <div class="mt-1 flex items-center gap-2">
                          <span
                            :class="[
                              'inline-flex h-2.5 w-2.5 rounded-full',
                              documento.ambiente_emissao === 1 ? 'bg-emerald-500' : 'bg-amber-500',
                            ]"
                          />
                          <p class="text-base font-bold text-zinc-800">
                            {{ documento.ambiente_emissao === 1 ? 'Produção' : 'Homologação' }}
                          </p>
                        </div>
                      </div>
                    </div>

                    <!-- Destinatário Card -->
                    <div class="rounded-xl border border-zinc-200 bg-white p-4 shadow-2xs space-y-3">
                      <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                          <User class="h-4 w-4 text-zinc-500" />
                          <span class="text-xs font-bold uppercase tracking-wider text-zinc-500">
                            Destinatário
                          </span>
                        </div>
                        <button
                          v-if="podeEditarDados"
                          type="button"
                          @click="showEditarVendaModal = true"
                          class="flex items-center gap-1 text-xs font-semibold text-brand-primary hover:underline cursor-pointer"
                        >
                          <Edit3 class="h-3.5 w-3.5" />
                          Editar / Trocar Cliente
                        </button>
                      </div>

                      <div class="rounded-lg bg-zinc-50 p-3 flex items-start justify-between gap-3">
                        <div>
                          <p class="text-sm font-bold text-zinc-900">
                            {{ documento.destinatario_nome || 'Consumidor Final (Não identificado)' }}
                          </p>
                          <p class="text-xs text-zinc-600 mt-0.5">
                            Documento:
                            <span class="font-mono font-medium">
                              {{ docClienteFormatado || 'Sem CPF/CNPJ' }}
                            </span>
                            <span v-if="documento.destinatario_uf" class="ml-2 text-zinc-500">
                              · {{ documento.destinatario_municipio || '' }} / {{ documento.destinatario_uf }}
                            </span>
                          </p>
                        </div>
                      </div>
                    </div>

                    <!-- Origem Card (Venda / OS) -->
                    <div class="rounded-xl border border-zinc-200 bg-white p-4 shadow-2xs space-y-3">
                      <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                          <FileText class="h-4 w-4 text-zinc-500" />
                          <span class="text-xs font-bold uppercase tracking-wider text-zinc-500">
                            Origem da Emissão
                          </span>
                        </div>
                        <button
                          v-if="podeEditarDados"
                          type="button"
                          @click="showEditarVendaModal = true"
                          class="flex items-center gap-1 text-xs font-semibold text-brand-primary hover:underline cursor-pointer"
                        >
                          <Edit3 class="h-3.5 w-3.5" />
                          Editar Dados da Venda
                        </button>
                      </div>

                      <div class="grid grid-cols-2 gap-2 text-xs text-zinc-600">
                        <div class="rounded-lg bg-zinc-50 p-2.5">
                          <span class="text-zinc-400 block text-[10px] uppercase font-semibold">Documento de Origem</span>
                          <span class="font-bold text-zinc-800 text-sm">
                            {{ documento.origem_tipo }} #{{ documento.origem_id ?? documento.venda_id ?? '-' }}
                          </span>
                        </div>
                        <div class="rounded-lg bg-zinc-50 p-2.5">
                          <span class="text-zinc-400 block text-[10px] uppercase font-semibold">Data da Emissão</span>
                          <span class="font-medium text-zinc-800">
                            {{ formatarData(documento.data_emissao ?? documento.data_criacao) }}
                          </span>
                        </div>
                      </div>
                    </div>

                    <!-- Chave de Acesso & Protocolo -->
                    <div class="rounded-xl border border-zinc-200 bg-white p-4 shadow-2xs space-y-3">
                      <div class="flex items-center justify-between">
                        <span class="text-xs font-bold uppercase tracking-wider text-zinc-500">
                          Chave de Acesso
                        </span>
                        <button
                          v-if="documento.chave_acesso"
                          type="button"
                          @click="copyChave"
                          class="flex items-center gap-1 rounded px-2 py-1 text-xs text-zinc-600 hover:bg-zinc-100 transition-colors cursor-pointer"
                        >
                          <Check v-if="copiedChave" class="h-3.5 w-3.5 text-emerald-600" />
                          <Copy v-else class="h-3.5 w-3.5" />
                          <span>{{ copiedChave ? 'Copiado!' : 'Copiar Chave' }}</span>
                        </button>
                      </div>
                      <p class="break-all rounded-lg bg-zinc-50 p-3 font-mono text-xs text-zinc-800 leading-relaxed border border-zinc-100">
                        {{ documento.chave_acesso || 'Chave não gerada para esta tentativa.' }}
                      </p>

                      <div class="border-t border-zinc-100 pt-3 flex items-center justify-between text-xs">
                        <span class="font-semibold text-zinc-400 uppercase tracking-wider text-[10px]">
                          Protocolo de Autorização
                        </span>
                        <span class="font-mono font-medium text-zinc-800">
                          {{ documento.protocolo_autorizacao || '-' }}
                        </span>
                      </div>
                    </div>

                    <!-- Ações Principais quando AUTORIZADA -->
                    <div v-if="documento.status === 'AUTORIZADA'" class="space-y-2">
                      <span class="text-xs font-bold uppercase tracking-wider text-zinc-400 block">
                        Ações do Documento Autorizado
                      </span>
                      <div class="grid grid-cols-2 gap-2">
                        <button
                          type="button"
                          @click="handleDownload('pdf')"
                          :disabled="!documento.url_pdf"
                          class="flex items-center justify-center gap-2 rounded-xl border border-zinc-200 bg-white p-3 text-sm font-semibold text-zinc-700 shadow-2xs hover:bg-zinc-50 transition-colors disabled:opacity-40 cursor-pointer"
                        >
                          <FileText class="h-4 w-4 text-rose-500" /> DANFE (PDF)
                        </button>
                        <button
                          type="button"
                          @click="handleDownload('xml')"
                          :disabled="!documento.url_xml"
                          class="flex items-center justify-center gap-2 rounded-xl border border-zinc-200 bg-white p-3 text-sm font-semibold text-zinc-700 shadow-2xs hover:bg-zinc-50 transition-colors disabled:opacity-40 cursor-pointer"
                        >
                          <FileCode class="h-4 w-4 text-blue-500" /> XML
                        </button>

                        <button
                          type="button"
                          @click="modalCancelarOpen = !modalCancelarOpen"
                          class="col-span-2 flex items-center justify-center gap-2 rounded-xl border border-rose-200 bg-rose-50/50 p-2.5 text-xs font-semibold text-rose-700 hover:bg-rose-100 transition-colors cursor-pointer"
                        >
                          <Ban class="h-4 w-4" />
                          Cancelar NF-e na SEFAZ
                        </button>
                      </div>
                    </div>

                    <!-- Form Inline de Cancelamento -->
                    <Transition name="fade">
                      <div v-if="modalCancelarOpen" class="rounded-xl border border-rose-200 bg-rose-50 p-4 space-y-3">
                        <label class="block text-xs font-bold text-rose-900 uppercase tracking-wider">
                          Justificativa do Cancelamento
                        </label>
                        <textarea
                          v-model="justificativaCancelamento"
                          rows="3"
                          class="w-full rounded-lg border border-rose-200 bg-white p-2.5 text-xs shadow-sm focus:border-rose-400 focus:outline-none"
                          placeholder="Informe o motivo do cancelamento (mínimo 15 caracteres)..."
                        />
                        <div class="flex justify-end gap-2">
                          <button
                            type="button"
                            @click="modalCancelarOpen = false"
                            class="rounded-lg px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-100 cursor-pointer"
                          >
                            Fechar
                          </button>
                          <button
                            type="button"
                            @click="handleCancelar"
                            :disabled="justificativaCancelamento.length < 15 || isCancelando"
                            class="rounded-lg bg-rose-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-50 cursor-pointer"
                          >
                            {{ isCancelando ? 'Cancelando...' : 'Confirmar Cancelamento' }}
                          </button>
                        </div>
                      </div>
                    </Transition>
                  </div>

                  <!-- ABA 2: ITENS E TRIBUTOS -->
                  <div v-show="activeTab === 'itens'" class="space-y-4">
                    <div class="flex items-center justify-between">
                      <div>
                        <h4 class="text-xs font-bold uppercase tracking-wider text-zinc-500">
                          Lista de Produtos da Venda
                        </h4>
                        <p class="text-[11px] text-zinc-400 mt-0.5">
                          {{
                            podeEditarDados
                              ? 'Clique em qualquer item para abrir a tela de edição do cadastro do produto para correção.'
                              : 'Itens e tributação consolidados desta nota fiscal.'
                          }}
                        </p>
                      </div>
                      <button
                        v-if="podeEditarDados"
                        type="button"
                        @click="emit('abrir-resolucao-produtos')"
                        class="text-xs font-semibold text-brand-primary hover:underline flex items-center gap-1 cursor-pointer shrink-0"
                      >
                        <Settings class="h-3.5 w-3.5" />
                        Ajustar Tributação dos Produtos
                      </button>
                    </div>

                    <div
                      v-if="documento.itens_resumo && documento.itens_resumo.length > 0"
                      class="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-2xs"
                    >
                      <table class="w-full text-left text-xs">
                        <thead class="bg-zinc-50 text-[10px] font-bold uppercase text-zinc-400 border-b border-zinc-100">
                          <tr>
                            <th class="py-2.5 px-3">Item / Produto</th>
                            <th class="py-2.5 px-2">NCM</th>
                            <th class="py-2.5 px-2">CFOP</th>
                            <th class="py-2.5 px-2 text-right">Qtd</th>
                            <th class="py-2.5 px-2 text-right">Unitário</th>
                            <th class="py-2.5 px-3 text-right">Total</th>
                          </tr>
                        </thead>
                        <tbody class="divide-y divide-zinc-100">
                          <tr
                            v-for="item in documento.itens_resumo"
                            :key="item.id || item.nome"
                            @click="handleAbrirItemProduto(item)"
                            class="hover:bg-blue-50/50 transition-colors cursor-pointer group"
                            :title="podeEditarDados ? 'Clique para abrir e editar este produto' : 'Clique para visualizar detalhes deste produto'"
                          >
                            <td class="py-2.5 px-3">
                              <div class="flex items-center gap-2">
                                <div class="min-w-0">
                                  <p class="font-medium text-zinc-900 group-hover:text-brand-primary transition-colors truncate max-w-xs flex items-center gap-1.5">
                                    <span>{{ item.nome }}</span>
                                    <ExternalLink class="h-3 w-3 opacity-0 group-hover:opacity-100 text-brand-primary transition-opacity" />
                                  </p>
                                  <p v-if="item.codigo_barras" class="font-mono text-[10px] text-zinc-400">
                                    EAN: {{ item.codigo_barras }}
                                  </p>
                                </div>
                              </div>
                            </td>
                            <td class="py-2.5 px-2 font-mono">
                              <span
                                v-if="item.ncm"
                                class="rounded bg-zinc-100 px-1.5 py-0.5 text-[11px] text-zinc-700"
                              >
                                {{ item.ncm }}
                              </span>
                              <span v-else class="text-rose-500 font-bold text-[10px]">
                                Pendente
                              </span>
                            </td>
                            <td class="py-2.5 px-2 font-mono text-zinc-600">
                              {{ item.cfop || '-' }}
                            </td>
                            <td class="py-2.5 px-2 text-right font-medium text-zinc-700">
                              {{ item.quantidade }}
                            </td>
                            <td class="py-2.5 px-2 text-right text-zinc-600">
                              {{ formatCurrency(item.valor_unitario) }}
                            </td>
                            <td class="py-2.5 px-3 text-right font-bold text-zinc-900">
                              {{ formatCurrency(item.subtotal) }}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    <div v-else class="rounded-xl border border-zinc-200 bg-zinc-50/50 p-8 text-center">
                      <Package class="mx-auto h-8 w-8 text-zinc-400" />
                      <p class="mt-2 text-xs font-medium text-zinc-500">
                        Nenhum item detalhado disponível para este documento.
                      </p>
                    </div>
                  </div>

                  <!-- ABA 3: HISTÓRICO DE TENTATIVAS SEFAZ -->
                  <div v-show="activeTab === 'historico'" class="space-y-4">
                    <h4 class="text-xs font-bold uppercase tracking-wider text-zinc-500">
                      Linha do Tempo de Emissão
                    </h4>

                    <div
                      v-if="historicoData && historicoData.tentativas.length > 0"
                      class="relative space-y-0"
                    >
                      <div
                        v-for="(tentativa, index) in historicoData.tentativas"
                        :key="tentativa.id"
                        class="relative flex gap-3.5 pb-5 last:pb-0"
                      >
                        <!-- Linha vertical conectora -->
                        <div
                          v-if="index !== historicoData.tentativas.length - 1"
                          class="absolute left-[11px] top-6 bottom-0 w-px bg-zinc-200"
                        />
                        <!-- Ponto visual de status -->
                        <div
                          class="relative z-10 mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 bg-white"
                          :class="[getStatusColors(tentativa.status).border]"
                        >
                          <div
                            class="h-2 w-2 rounded-full"
                            :class="{
                              'bg-emerald-500': tentativa.status === 'AUTORIZADA',
                              'bg-rose-500': tentativa.status === 'REJEITADA' || tentativa.status === 'DENEGADA',
                              'bg-zinc-400': tentativa.status === 'CANCELADA',
                              'bg-blue-500': tentativa.status === 'PROCESSANDO' || tentativa.status === 'PENDENTE',
                            }"
                          />
                        </div>

                        <!-- Conteúdo da tentativa -->
                        <div class="min-w-0 flex-1 rounded-xl border border-zinc-200 bg-white p-3 shadow-2xs">
                          <div class="flex items-center justify-between gap-2">
                            <span
                              :class="[
                                'rounded-full px-2 py-0.5 text-[10px] font-bold uppercase',
                                getStatusColors(tentativa.status).bg,
                                getStatusColors(tentativa.status).text,
                              ]"
                            >
                              {{ tentativa.status }}
                            </span>
                            <span class="text-[11px] text-zinc-400">
                              {{ formatarData(tentativa.data_criacao) }}
                            </span>
                          </div>

                          <p
                            v-if="tentativa.mensagem_sefaz"
                            class="mt-2 rounded-lg bg-zinc-50 p-2.5 text-xs leading-relaxed text-zinc-700 font-mono border border-zinc-100"
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
                <p class="text-sm text-zinc-500">Documento fiscal não encontrado.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Modal Integrado de Edição de Venda -->
    <FiscalEditarVendaModal
      v-if="documento"
      :is-open="showEditarVendaModal"
      :venda-id="documento.venda_id || documento.origem_id"
      :numero-venda="documento.origem_id || documento.venda_id"
      :cliente-atual-id="documento.destinatario_id"
      :documento-id="documento.id"
      :observacao-inicial="''"
      @close="showEditarVendaModal = false"
      @saved="() => { toast.success('Venda atualizada!'); }"
      @reemitido="(novoId) => emit('reemitir', novoId)"
    />

    <!-- Modal Integrado de Edição de Produto Padrão do Sistema -->
    <ProductModal />
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
  transform: translateY(-6px);
}
</style>
