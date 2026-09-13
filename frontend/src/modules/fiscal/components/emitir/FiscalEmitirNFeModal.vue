<script setup lang="ts">
import { ref, computed } from 'vue';
import { refDebounced } from '@vueuse/core';
import { User, Loader2, Package, Receipt, Building2, ShieldCheck, AlertTriangle, CreditCard, AlertCircle, RefreshCw, Layers, CheckCircle, XCircle } from 'lucide-vue-next';
import { useRouter } from 'vue-router';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

import { useSalesListQuery } from '@/modules/sales/composables/queries/useSalesListQuery';
import { useFiscalEmitirNfeMutation } from '../../composables/useFiscalEmitirNfeMutation';
import { useFiscalEmitirBatchMutation } from '../../composables/useFiscalEmitirBatchMutation';
import { useFiscalPreviewMutation } from '../../composables/useFiscalPreviewMutation';
import { useFiscalPendenciasQuery } from '../../composables/useFiscalPendenciasQuery';
import { useFiscalVerificacaoBatchQuery } from '../../composables/useFiscalVerificacaoBatchQuery';
import { useToast } from '@/shared/composables/useToast';
import { formatCurrency } from '@/shared/utils/finance';
import { formatCPF, formatCNPJ } from '@/shared/utils/document.utils';
import { formatDataHora } from '@/shared/utils/date.utils';

import type { SaleSimpleRead } from '@/modules/sales/schemas/sale.schema';
import type { EmissaoPreviewResponse, VerificacaoBatchItem, EmissaoBatchResponse } from '../../types/fiscal.types';

const props = defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'abrir-detalhes-documento', documentoId: number): void;
}>();

const step = ref<1 | 2 | 3>(1);
const searchTerm = ref('');
const debouncedSearch = refDebounced(searchTerm, 400);

// --- Modo Lote ---
const modoLote = ref(false);
const vendasSelecionadasLote = ref<Set<number>>(new Set());
const batchResultado = ref<EmissaoBatchResponse | null>(null);

/**
 * Três desfechos possíveis numa emissão em lote, e eles não se agrupam em dois:
 *
 *  - sucesso : a SEFAZ aceitou (ou ainda está processando)
 *  - recusa  : a SEFAZ respondeu e NEGOU — a nota não existe, mas o sistema
 *              funcionou. É problema de cadastro, e o operador precisa vê-lo.
 *  - erro    : falha antes ou durante o envio (rede, validação local)
 *
 * Juntar recusa com sucesso, como fazia o `!== 'ERRO'`, faz o lojista acreditar
 * que emitiu notas que a SEFAZ recusou.
 */
const STATUS_SUCESSO = ['AUTORIZADA', 'PROCESSANDO'];
const STATUS_RECUSA = ['REJEITADA', 'DENEGADA'];

function ehSucesso(status: string): boolean {
  return STATUS_SUCESSO.includes(status);
}
function ehRecusa(status: string): boolean {
  return STATUS_RECUSA.includes(status);
}

import FiscalEditarVendaModal from '../detalhes/FiscalEditarVendaModal.vue';
import { UserPlus, UserX } from 'lucide-vue-next';

// Lista de Vendas p/ emissão
const { data, isLoading } = useSalesListQuery(
  computed(() => props.isOpen && step.value === 1 ? {
    search: debouncedSearch.value || undefined,
    status: 'FINALIZADA' as const,
  } : null),
);

const todasVendas = computed(() => data.value?.vendas ?? []);
const vendas = computed(() => todasVendas.value);

const vendaSelecionada = ref<SaleSimpleRead | null>(null);
const vendaSelecionadaId = ref<number | null>(null);
const previewData = ref<EmissaoPreviewResponse | null>(null);

// Modal de edição / vinculação de cliente na venda
const modalEditarVendaOpen = ref(false);
const vendaParaEditar = ref<SaleSimpleRead | null>(null);

function abrirVincularCliente(venda: SaleSimpleRead) {
  vendaParaEditar.value = venda;
  modalEditarVendaOpen.value = true;
}

const router = useRouter();
const toast = useToast();
const emitirMutation = useFiscalEmitirNfeMutation();
const emitirBatchMutation = useFiscalEmitirBatchMutation();
const previewMutation = useFiscalPreviewMutation();

// Pre-check: emitente completo?
const { data: pendenciasData } = useFiscalPendenciasQuery();
const emitenteIncompleto = computed(() => pendenciasData.value ? !pendenciasData.value.emitente_completo : false);

/**
 * O que exatamente falta no emitente.
 *
 * A resposta SEMPRE veio no `emitente_pendencias` e a tela só dizia "os dados
 * estão incompletos". O lojista ficava sem saber o que abrir: foi o que
 * aconteceu numa loja real em 12/09/2026, na tentativa da nota de R$ 1,00.
 */
const pendenciasEmitente = computed(() => pendenciasData.value?.emitente_pendencias ?? []);

/**
 * Cadastro errado que NÃO impede emitir.
 *
 * Aparece em amarelo e não trava botão nenhum. Misturar isto com pendência
 * seria travar quem está emitindo bem por causa de um campo que nem vai no
 * XML.
 */
const avisosEmitente = computed(() => pendenciasData.value?.emitente_avisos ?? []);
const emitenteExpandido = ref(false);

/** Pendências abertas por venda — a linha mostra a lista ali mesmo. */
const vendaPendenciasAbertas = ref<Set<number>>(new Set());

function alternarPendencias(vendaId: number) {
  const abertas = new Set(vendaPendenciasAbertas.value);
  if (abertas.has(vendaId)) abertas.delete(vendaId);
  else abertas.add(vendaId);
  vendaPendenciasAbertas.value = abertas;
}

/**
 * Leva à tela que resolve a pendência.
 *
 * A categoria vem do backend (`emitente`, `destinatario`, `item`,
 * `pagamento`), e é ela que diz qual cadastro está incompleto.
 */
function irParaCadastro(categoria: string) {
  const destino =
    categoria === 'item' ? 'products'
    : categoria === 'destinatario' ? 'customers'
    : 'enterprise';
  fecharModal();
  router.push({ name: destino });
}

function rotuloDoAtalho(categoria: string): string {
  if (categoria === 'item') return 'Abrir Produtos';
  if (categoria === 'destinatario') return 'Abrir Clientes';
  if (categoria === 'pagamento') return 'Abrir Formas de Pagamento';
  return 'Abrir Dados da Empresa';
}

// Verificação fiscal batch — dispara quando vendas com cliente carregam
const vendaIds = computed(() => {
  const comCliente = vendas.value.filter(v => v.cliente);
  return comCliente.length > 0 ? comCliente.map(v => v.id) : null;
});
const { data: verificacaoBatch, isLoading: isLoadingVerificacao } = useFiscalVerificacaoBatchQuery(vendaIds);

const verificacaoMap = computed(() => {
  if (!verificacaoBatch.value) return new Map<number, VerificacaoBatchItem>();
  return new Map(verificacaoBatch.value.resultados.map(r => [r.venda_id, r]));
});

type StatusVenda = 'carregando' | 'emitida' | 'processando' | 'incompleta' | 'apta' | 'rejeitada' | 'sem_cliente';

function getStatusVenda(venda: SaleSimpleRead): StatusVenda {
  if (!venda.cliente) return 'sem_cliente';
  const item = verificacaoMap.value.get(venda.id);
  if (!item) return 'carregando';
  if (item.documento_ativo) {
    if (item.documento_ativo.status === 'AUTORIZADA') return 'emitida';
    if (item.documento_ativo.status === 'REJEITADA' || item.documento_ativo.status === 'DENEGADA') return 'rejeitada';
    return 'processando';
  }
  if (!item.completo) return 'incompleta';
  return 'apta';
}

// --- Modo Lote helpers ---
const vendasAptas = computed(() => vendas.value.filter(v => getStatusVenda(v) === 'apta'));

function toggleModoLote() {
  modoLote.value = !modoLote.value;
  vendasSelecionadasLote.value.clear();
  vendaSelecionadaId.value = null;
  vendaSelecionada.value = null;
}

function toggleLoteVenda(vendaId: number) {
  const set = vendasSelecionadasLote.value;
  if (set.has(vendaId)) {
    set.delete(vendaId);
  } else {
    set.add(vendaId);
  }
}

function toggleLoteTodas() {
  if (vendasSelecionadasLote.value.size === vendasAptas.value.length) {
    vendasSelecionadasLote.value.clear();
  } else {
    vendasSelecionadasLote.value = new Set(vendasAptas.value.map(v => v.id));
  }
}

const vendasLoteResumo = computed(() =>
  vendas.value.filter(v => vendasSelecionadasLote.value.has(v.id)),
);

async function handleEmitirLote() {
  if (vendasSelecionadasLote.value.size === 0) return;
  step.value = 2;
}

async function confirmarEmissaoLote() {
  const ids = [...vendasSelecionadasLote.value];
  emitirBatchMutation.mutate(ids, {
    onSuccess: (data) => {
      batchResultado.value = data;
      step.value = 3;
    },
  });
}

function handleClickVenda(venda: SaleSimpleRead) {
  const status = getStatusVenda(venda);
  const item = verificacaoMap.value.get(venda.id);

  if (status === 'sem_cliente') {
    abrirVincularCliente(venda);
    return;
  }
  if (status === 'emitida') {
    toast.info(
      'NF-e já emitida',
      `Venda #${venda.numero_venda ?? venda.id} já possui NF-e autorizada. Consulte no Centro Fiscal.`,
    );
    return;
  }
  if (status === 'processando') {
    toast.info(
      'Emissão em andamento',
      'Aguarde o retorno da SEFAZ antes de tentar novamente.',
    );
    return;
  }
  if (status === 'rejeitada' && item?.documento_ativo) {
    emit('abrir-detalhes-documento', item.documento_ativo.documento_id);
    fecharModal();
    return;
  }
  if (status === 'incompleta' && item) {
    const desc = item.pendencias.slice(0, 5).map(p => p.mensagem).join('\n');
    toast.warning(
      `Venda #${venda.numero_venda ?? venda.id} — ${item.pendencias.length} pendência(s)`,
      desc,
    );
    return;
  }
  if (status === 'carregando') return;

  // Seleção segura: apenas destaca a linha, sem avançar
  vendaSelecionadaId.value = vendaSelecionadaId.value === venda.id ? null : venda.id;
  vendaSelecionada.value = vendaSelecionadaId.value ? venda : null;
}

async function handleAvancar() {
  if (!vendaSelecionada.value) return;
  await selecionarVenda(vendaSelecionada.value);
}

function temItemIncompleto(): boolean {
  if (!previewData.value) return false;
  return previewData.value.itens.some(i => !i.ncm || !i.cfop);
}

async function handleAtualizarPreview() {
  if (!vendaSelecionada.value) return;
  try {
    const preview = await previewMutation.mutateAsync({ venda_id: vendaSelecionada.value.id });
    previewData.value = preview;
    toast.success('Preview atualizado');
  } catch {
    // erro tratado no mutation
  }
}

function navegarProduto(produtoId: number | null) {
  if (!produtoId) return;
  router.push({ name: 'products', query: { editar: produtoId } });
}

// --- Ações ---
async function selecionarVenda(venda: SaleSimpleRead) {
  vendaSelecionada.value = venda;
  previewData.value = null;
  
  // Buscar preview
  try {
    const preview = await previewMutation.mutateAsync({ venda_id: venda.id });
    previewData.value = preview;
    step.value = 2; // Avança pro resumo
  } catch (error) {
    // erro tratado no mutation (toast) ou reset vendaSelecionada se falhar
    vendaSelecionada.value = null;
  }
}

function handleVoltar() {
  step.value = 1;
  vendaSelecionadaId.value = null;
  vendaSelecionada.value = null;
  previewData.value = null;
  batchResultado.value = null;
}

function handleEmitir() {
  if (!vendaSelecionada.value) return;

  emitirMutation.mutate(
    { venda_id: vendaSelecionada.value.id },
    {
      onSuccess: () => {
        fecharModal();
      },
    },
  );
}

// --- Helpers ---
const mutacaoPendente = computed(() =>
  emitirMutation.isPending.value ||
  emitirBatchMutation.isPending.value ||
  previewMutation.isPending.value
);

function fecharModal() {
  if (mutacaoPendente.value) return;
  step.value = 1;
  searchTerm.value = '';
  vendaSelecionada.value = null;
  vendaSelecionadaId.value = null;
  previewData.value = null;
  modoLote.value = false;
  vendasSelecionadasLote.value.clear();
  batchResultado.value = null;
  emit('close');
}

function getNomeCliente(venda: SaleSimpleRead): string {
  if (!venda.cliente) return 'Sem cliente';
  if (venda.cliente.tipo === 'PF') return venda.cliente.nome || 'Sem nome';
  return venda.cliente.razao_social || 'Sem razão social';
}

function getDocumentoCliente(venda: SaleSimpleRead): string {
  if (!venda.cliente) return '';
  if (venda.cliente.tipo === 'PF') return venda.cliente.cpf || '';
  return venda.cliente.cnpj || '';
}

function formatarData(iso: string): string {
  if (!iso) return '-';
  return formatDataHora(iso);
}

function formatDocumento(doc: string): string {
  const digits = doc.replace(/\D/g, '');
  if (digits.length === 14) return formatCNPJ(doc);
  if (digits.length === 11) return formatCPF(doc);
  return doc;
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    :title="
      step === 1 ? 'Emitir NF-e - Selecionar Venda' :
      step === 2 && modoLote ? `Emissão em Lote — ${vendasLoteResumo.length} Vendas` :
      step === 2 ? 'Pré-visualização da NF-e' :
      'Resultado da Emissão em Lote'
    "
    :subtitle="
      step === 1 ? 'Selecione uma venda finalizada para emissão.' :
      step === 2 && modoLote ? 'Confirme as vendas antes de transmitir para a SEFAZ.' :
      step === 2 ? 'Confira os dados antes de transmitir para a SEFAZ.' :
      undefined
    "
    :size="step === 1 ? 'lg' : 'xl'"
    @close="fecharModal"
  >
    <!-- Etapa 1: Selecionar venda -->
    <template v-if="step === 1">
      <!-- Alerta: emitente incompleto -->
      <div v-if="emitenteIncompleto" class="rounded-lg bg-red-50 border border-red-200 px-3.5 py-2.5 mb-3">
        <div class="flex items-start gap-2.5">
          <AlertTriangle :size="16" class="text-red-500 mt-0.5 shrink-0" />
          <div class="flex-1 min-w-0">
            <p class="text-xs text-red-700 leading-relaxed">
              Os <strong>dados do emitente estão incompletos</strong>.
              <button
                v-if="pendenciasEmitente.length"
                type="button"
                class="underline underline-offset-2 font-semibold cursor-pointer hover:text-red-900"
                @click="emitenteExpandido = !emitenteExpandido"
              >
                {{ emitenteExpandido ? 'Ocultar' : `Ver o que falta (${pendenciasEmitente.length})` }}
              </button>
            </p>

            <ul v-if="emitenteExpandido" class="mt-2 space-y-1">
              <li
                v-for="(msg, i) in pendenciasEmitente"
                :key="i"
                class="text-xs text-red-700 flex items-start gap-1.5"
              >
                <span class="mt-1 w-1 h-1 rounded-full bg-red-400 shrink-0" />
                <span>{{ msg }}</span>
              </li>
            </ul>

            <button
              v-if="emitenteExpandido"
              type="button"
              class="mt-2 text-xs font-semibold text-red-700 bg-white border border-red-200 hover:bg-red-100 rounded-lg px-2.5 py-1 cursor-pointer transition-colors"
              @click="irParaCadastro('emitente')"
            >
              Abrir Dados da Empresa
            </button>
          </div>
        </div>
      </div>

      <!-- Avisos de cadastro: contam, não travam -->
      <div
        v-if="avisosEmitente.length"
        class="flex items-start gap-2.5 rounded-lg bg-amber-50 border border-amber-200 px-3.5 py-2.5 mb-3"
      >
        <AlertCircle :size="16" class="text-amber-500 mt-0.5 shrink-0" />
        <ul class="text-xs text-amber-800 leading-relaxed space-y-1">
          <li v-for="(aviso, i) in avisosEmitente" :key="i">{{ aviso }}</li>
        </ul>
      </div>

      <!-- Toggle Modo Lote -->
      <div class="flex items-center justify-between mb-3">
        <BaseSearchInput
          v-model="searchTerm"
          placeholder="Buscar por número da venda ou nome do cliente"
          class="flex-1"
        />
        <button
          type="button"
          class="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold transition-all shrink-0 ml-3"
          :class="modoLote
            ? 'bg-brand-primary text-white shadow-sm'
            : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'"
          @click="toggleModoLote"
        >
          <Layers :size="14" />
          Modo Lote
        </button>
      </div>

      <!-- Selecionar todas (modo lote) -->
      <div v-if="modoLote && vendasAptas.length > 0" class="flex items-center justify-between mb-1 px-1">
        <button
          type="button"
          class="text-xs text-brand-primary font-semibold hover:underline"
          @click="toggleLoteTodas"
        >
          {{ vendasSelecionadasLote.size === vendasAptas.length ? 'Desmarcar todas' : 'Selecionar todas aptas' }}
        </button>
        <span v-if="vendasSelecionadasLote.size > 0" class="text-xs text-zinc-500">
          {{ vendasSelecionadasLote.size }} selecionada(s)
        </span>
      </div>

      <div class="max-h-80 overflow-y-auto divide-y divide-zinc-100 -mx-1 px-1">
        <template v-if="isLoading || previewMutation.isPending.value">
          <div class="flex flex-col items-center justify-center p-8 text-zinc-400">
            <Loader2 class="w-8 h-8 animate-spin mb-2" />
            <p class="text-sm">Carregando...</p>
          </div>
        </template>
        <template v-else-if="vendas.length > 0">
          <button
            v-for="venda in vendas"
            :key="venda.id"
            type="button"
            class="w-full flex items-center gap-3 px-3 py-3 rounded-xl text-left transition-all cursor-pointer disabled:cursor-default group"
            :class="{
              'hover:bg-zinc-50': getStatusVenda(venda) === 'apta' && vendaSelecionadaId !== venda.id && !vendasSelecionadasLote.has(venda.id),
              'bg-blue-50/70 ring-1 ring-brand-primary shadow-sm': !modoLote && vendaSelecionadaId === venda.id,
              'bg-brand-primary/5 ring-1 ring-brand-primary/40': modoLote && vendasSelecionadasLote.has(venda.id),
              'opacity-60': getStatusVenda(venda) === 'emitida' || getStatusVenda(venda) === 'processando' || getStatusVenda(venda) === 'rejeitada',
              'opacity-75': getStatusVenda(venda) === 'incompleta',
              'bg-zinc-50/60 border border-dashed border-zinc-200': getStatusVenda(venda) === 'sem_cliente',
              'opacity-50': getStatusVenda(venda) === 'carregando',
            }"
            :disabled="previewMutation.isPending.value || emitenteIncompleto || isLoadingVerificacao"
            @click="modoLote && getStatusVenda(venda) === 'apta' ? toggleLoteVenda(venda.id) : handleClickVenda(venda)"
          >
            <!-- Checkbox no modo lote -->
            <div v-if="modoLote" class="shrink-0">
              <div
                class="w-5 h-5 rounded border-2 flex items-center justify-center transition-colors"
                :class="vendasSelecionadasLote.has(venda.id)
                  ? 'bg-brand-primary border-brand-primary'
                  : getStatusVenda(venda) === 'apta'
                    ? 'border-zinc-300'
                    : 'border-zinc-200 bg-zinc-50 cursor-not-allowed'"
              >
                <svg v-if="vendasSelecionadasLote.has(venda.id)" class="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                  <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
            </div>
            <div
              v-else
              class="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
              :class="getStatusVenda(venda) === 'sem_cliente' ? 'bg-amber-100/80 text-amber-700' : 'bg-brand-primary/10 text-brand-primary'"
            >
              <UserX v-if="getStatusVenda(venda) === 'sem_cliente'" :size="16" />
              <User v-else :size="16" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-2">
                <div class="flex items-center gap-2 min-w-0">
                  <p class="text-sm font-semibold text-zinc-900 truncate">
                    {{ getNomeCliente(venda) }}
                  </p>
                  <!-- Badge de status fiscal -->
                  <span
                    v-if="getStatusVenda(venda) === 'sem_cliente'"
                    class="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold whitespace-nowrap shrink-0"
                  >
                    Consumidor Balcão
                  </span>
                  <span
                    v-else-if="getStatusVenda(venda) === 'emitida'"
                    class="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 font-medium whitespace-nowrap shrink-0"
                  >NF-e Emitida</span>
                  <span
                    v-else-if="getStatusVenda(venda) === 'processando'"
                    class="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium whitespace-nowrap shrink-0"
                  >Processando</span>
                  <span
                    v-else-if="getStatusVenda(venda) === 'rejeitada'"
                    class="text-[10px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 font-medium whitespace-nowrap shrink-0"
                  >Rejeitada</span>
                  <!--
                    Clicável de propósito: antes era só um número, e a lista
                    só aparecia num toast que some sozinho. Quem precisa
                    corrigir cadastro precisa LER a lista com calma.
                  -->
                  <button
                    v-else-if="getStatusVenda(venda) === 'incompleta'"
                    type="button"
                    class="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 hover:bg-amber-200 font-medium whitespace-nowrap shrink-0 cursor-pointer transition-colors underline underline-offset-2"
                    @click.stop="alternarPendencias(venda.id)"
                  >
                    {{ verificacaoMap.get(venda.id)?.pendencias.length }} pendência(s) —
                    {{ vendaPendenciasAbertas.has(venda.id) ? 'ocultar' : 'ver' }}
                  </button>
                </div>

                <div class="flex items-center gap-2 shrink-0">
                  <button
                    v-if="getStatusVenda(venda) === 'sem_cliente'"
                    type="button"
                    @click.stop="abrirVincularCliente(venda)"
                    class="text-[11px] font-semibold text-brand-primary bg-blue-50 border border-blue-200 hover:bg-blue-100 rounded-lg px-2.5 py-1 flex items-center gap-1 transition-colors cursor-pointer"
                  >
                    <UserPlus class="h-3.5 w-3.5" />
                    Vincular Cliente
                  </button>
                  <span class="text-sm font-bold text-zinc-800 whitespace-nowrap group-hover:text-brand-primary transition-colors">
                    {{ formatCurrency(venda.total) }}
                  </span>
                </div>
              </div>
              <p class="text-xs text-zinc-400 truncate mt-0.5">
                Venda #{{ venda.numero_venda ?? venda.id }}
                <template v-if="getDocumentoCliente(venda)"> · {{ getDocumentoCliente(venda) }}</template>
                <template v-else-if="getStatusVenda(venda) === 'sem_cliente'"> · Sem cliente cadastrado (exige cliente p/ NF-e)</template>
                · {{ formatarData(venda.criado_em) }}
              </p>

              <!-- O que falta nesta venda, com atalho para o cadastro certo -->
              <div
                v-if="vendaPendenciasAbertas.has(venda.id)"
                class="mt-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2"
                @click.stop
              >
                <ul class="space-y-1.5">
                  <li
                    v-for="(pend, i) in verificacaoMap.get(venda.id)?.pendencias ?? []"
                    :key="i"
                    class="text-xs text-amber-800 flex items-start justify-between gap-3"
                  >
                    <span class="flex items-start gap-1.5 min-w-0">
                      <span class="mt-1 w-1 h-1 rounded-full bg-amber-500 shrink-0" />
                      <span class="whitespace-normal">{{ pend.mensagem }}</span>
                    </span>
                    <button
                      type="button"
                      class="text-[11px] font-semibold text-amber-900 bg-white border border-amber-200 hover:bg-amber-100 rounded-lg px-2 py-0.5 shrink-0 cursor-pointer transition-colors"
                      @click.stop="irParaCadastro(pend.categoria)"
                    >
                      {{ rotuloDoAtalho(pend.categoria) }}
                    </button>
                  </li>
                </ul>
              </div>
            </div>
          </button>
        </template>
        <template v-else>
          <div class="py-12 text-center text-sm text-zinc-500">
            Nenhuma venda encontrada para os filtros.
          </div>
        </template>
      </div>
      
      <div class="mt-6 flex justify-end gap-3">
        <BaseButton variant="secondary" @click="fecharModal">Cancelar</BaseButton>
        <template v-if="modoLote">
          <BaseButton
            variant="primary"
            :disabled="vendasSelecionadasLote.size === 0 || emitenteIncompleto"
            @click="handleEmitirLote"
          >
            <Layers :size="14" class="mr-1.5" />
            Emitir {{ vendasSelecionadasLote.size }} Venda{{ vendasSelecionadasLote.size !== 1 ? 's' : '' }} em Lote
          </BaseButton>
        </template>
        <template v-else>
          <BaseButton
            variant="primary"
            :disabled="!vendaSelecionadaId || previewMutation.isPending.value || emitenteIncompleto"
            :is-loading="previewMutation.isPending.value"
            @click="handleAvancar"
          >
            Avançar para Revisão
          </BaseButton>
        </template>
      </div>
    </template>

    <!-- Etapa 2 (Lote): Confirmação de Emissão em Lote -->
    <template v-if="step === 2 && modoLote">
      <div class="space-y-4">
        <div class="flex items-start gap-2.5 rounded-lg bg-blue-50 border border-blue-200 px-3.5 py-2.5">
          <Layers :size="16" class="text-blue-500 mt-0.5 shrink-0" />
          <p class="text-xs text-blue-700 leading-relaxed">
            Serão emitidas <strong>{{ vendasLoteResumo.length }} NF-e(s)</strong> sequencialmente.
            Cada venda será processada individualmente pela SEFAZ.
          </p>
        </div>

        <div class="rounded-xl border border-zinc-200 bg-white overflow-hidden">
          <div class="max-h-60 overflow-y-auto">
            <table class="w-full text-left text-xs">
              <thead class="bg-zinc-50/80 border-b border-zinc-100 sticky top-0">
                <tr>
                  <th class="px-4 py-2 font-semibold text-zinc-500 w-8">#</th>
                  <th class="px-4 py-2 font-semibold text-zinc-500">Cliente</th>
                  <th class="px-4 py-2 font-semibold text-zinc-500 text-right">Valor</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-50">
                <tr v-for="venda in vendasLoteResumo" :key="venda.id" class="even:bg-zinc-50/30">
                  <td class="px-4 py-2.5 text-zinc-400 font-mono">{{ venda.numero_venda ?? venda.id }}</td>
                  <td class="px-4 py-2.5 text-zinc-800 font-medium truncate max-w-60">{{ getNomeCliente(venda) }}</td>
                  <td class="px-4 py-2.5 text-right font-semibold text-zinc-800 font-mono">{{ formatCurrency(venda.total) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="flex items-start gap-2.5 rounded-lg bg-amber-50 border border-amber-200 px-3.5 py-2.5">
          <ShieldCheck :size="16" class="text-amber-500 mt-0.5 shrink-0" />
          <p class="text-xs text-amber-700 leading-relaxed">
            Após confirmar, cada nota será transmitida para a SEFAZ. O processo pode levar alguns segundos por venda.
          </p>
        </div>
      </div>

      <div class="mt-6 flex justify-end gap-3 pt-4 border-t border-zinc-100">
        <BaseButton variant="secondary" @click="step = 1" :disabled="emitirBatchMutation.isPending.value">Voltar</BaseButton>
        <BaseButton
          variant="primary"
          :disabled="emitirBatchMutation.isPending.value"
          :is-loading="emitirBatchMutation.isPending.value"
          @click="confirmarEmissaoLote"
        >
          Confirmar Emissão em Lote
        </BaseButton>
      </div>
    </template>

    <!-- Etapa 3 (Lote): Resultado -->
    <template v-if="step === 3 && batchResultado">
      <div class="space-y-4">
        <!-- Resumo geral -->
        <div class="grid grid-cols-3 gap-3">
          <div class="rounded-xl border border-zinc-200 bg-white p-4 text-center">
            <p class="text-2xl font-bold text-zinc-800">{{ batchResultado.total }}</p>
            <p class="text-xs text-zinc-500 mt-0.5">Total</p>
          </div>
          <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center">
            <p class="text-2xl font-bold text-emerald-600">{{ batchResultado.sucesso }}</p>
            <p class="text-xs text-emerald-600 mt-0.5">Sucesso</p>
          </div>
          <div class="rounded-xl border border-red-200 bg-red-50 p-4 text-center">
            <p class="text-2xl font-bold text-red-600">{{ batchResultado.falha }}</p>
            <p class="text-xs text-red-600 mt-0.5">Falha</p>
          </div>
        </div>

        <!-- Detalhes por venda -->
        <div class="rounded-xl border border-zinc-200 bg-white overflow-hidden">
          <div class="max-h-60 overflow-y-auto divide-y divide-zinc-100">
            <div
              v-for="resultado in batchResultado.resultados"
              :key="resultado.venda_id"
              class="flex items-center gap-3 px-4 py-3"
            >
              <!--
                Três desfechos, não dois. REJEITADA e DENEGADA caíam no ramo
                verde porque a condição era `!== 'ERRO'` — o lojista via um ✓
                esmeralda em notas que a SEFAZ tinha recusado.
              -->
              <CheckCircle v-if="ehSucesso(resultado.status)" :size="16" class="text-emerald-500 shrink-0" />
              <AlertTriangle v-else-if="ehRecusa(resultado.status)" :size="16" class="text-amber-500 shrink-0" />
              <XCircle v-else :size="16" class="text-red-500 shrink-0" />
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-zinc-800">
                  Venda #{{ resultado.venda_id }}
                </p>
                <p class="text-xs text-zinc-500 truncate mt-0.5" :title="resultado.mensagem">
                  {{ resultado.mensagem }}
                </p>
              </div>
              <span
                class="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
                :class="ehSucesso(resultado.status)
                  ? 'bg-emerald-100 text-emerald-700'
                  : ehRecusa(resultado.status)
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-red-100 text-red-700'"
              >
                {{ resultado.status }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="mt-6 flex justify-end pt-4 border-t border-zinc-100">
        <BaseButton variant="primary" @click="fecharModal">
          Fechar
        </BaseButton>
      </div>
    </template>

    <!-- Etapa 2 (Individual): Resumo/Preview -->
    <template v-if="step === 2 && !modoLote && previewData">
      <div class="space-y-5">

        <!-- Destinatário -->
        <div class="rounded-xl border border-zinc-200 bg-white overflow-hidden">
          <div class="flex items-center gap-2 px-4 py-2.5 bg-zinc-50 border-b border-zinc-100">
            <Building2 :size="14" class="text-zinc-400" />
            <h4 class="text-xs font-semibold uppercase tracking-wider text-zinc-500">Destinatário</h4>
          </div>
          <div class="p-4 flex items-center gap-4">
            <div class="w-10 h-10 rounded-full bg-brand-primary/10 flex items-center justify-center shrink-0">
              <User :size="18" class="text-brand-primary" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-zinc-900 truncate">
                {{ previewData.destinatario.nome }}
              </p>
              <p class="text-xs text-zinc-500 mt-0.5">
                {{ previewData.destinatario.documento ? formatDocumento(previewData.destinatario.documento) : 'Consumidor Final — sem documento informado' }}
              </p>
            </div>
          </div>
        </div>

        <!-- Itens -->
        <div class="rounded-xl border border-zinc-200 bg-white overflow-hidden">
          <div class="flex items-center justify-between px-4 py-2.5 bg-zinc-50 border-b border-zinc-100">
            <div class="flex items-center gap-2">
              <Package :size="14" class="text-zinc-400" />
              <h4 class="text-xs font-semibold uppercase tracking-wider text-zinc-500">Itens da Nota</h4>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs font-medium text-zinc-400">
                {{ previewData.itens.length }} {{ previewData.itens.length === 1 ? 'item' : 'itens' }}
              </span>
              <button
                v-if="temItemIncompleto()"
                type="button"
                class="flex items-center gap-1 text-[10px] font-semibold text-amber-600 hover:text-amber-700 transition-colors"
                :disabled="previewMutation.isPending.value"
                @click="handleAtualizarPreview"
              >
                <RefreshCw :size="12" :class="{ 'animate-spin': previewMutation.isPending.value }" />
                Atualizar
              </button>
            </div>
          </div>
          <div class="max-h-48 overflow-y-auto">
            <table class="w-full text-left text-xs">
              <thead class="bg-zinc-50/80 border-b border-zinc-100 sticky top-0">
                <tr>
                  <th class="px-4 py-2 font-semibold text-zinc-500 w-8">#</th>
                  <th class="px-4 py-2 font-semibold text-zinc-500">Descrição</th>
                  <th class="px-4 py-2 font-semibold text-zinc-500 text-center">Qtd</th>
                  <th class="px-4 py-2 font-semibold text-zinc-500 text-right">V. Unit.</th>
                  <th class="px-4 py-2 font-semibold text-zinc-500 text-center">CFOP</th>
                  <th class="px-4 py-2 font-semibold text-zinc-500 text-center">CST/CSOSN</th>
                  <th class="px-4 py-2 font-semibold text-zinc-500 text-center">NCM</th>
                  <th class="px-4 py-2 font-semibold text-zinc-500 text-right">Total</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-50">
                <tr
                  v-for="item in previewData.itens"
                  :key="item.numero_item"
                  class="transition-colors hover:bg-zinc-50/50 even:bg-zinc-50/30"
                >
                  <td class="px-4 py-2.5 text-zinc-400 font-mono">{{ item.numero_item }}</td>
                  <td class="px-4 py-2.5 text-zinc-800 font-medium truncate max-w-40" :title="item.nome">
                    {{ item.nome }}
                  </td>
                  <td class="px-4 py-2.5 text-zinc-600 text-center">{{ item.quantidade }}</td>
                  <td class="px-4 py-2.5 text-zinc-600 text-right font-mono">{{ formatCurrency(item.valor_unitario) }}</td>
                  <td class="px-4 py-2.5 text-center">
                    <span v-if="item.cfop" class="inline-block px-1.5 py-0.5 bg-zinc-100 text-zinc-600 rounded text-[10px] font-mono">{{ item.cfop }}</span>
                    <button
                      v-else
                      type="button"
                      class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-amber-50 text-amber-600 rounded text-[10px] font-semibold hover:bg-amber-100 transition-colors"
                      title="CFOP não cadastrado — clique para corrigir"
                      @click.stop="navegarProduto(item.produto_id)"
                    >
                      <AlertCircle :size="10" />
                      Vazio
                    </button>
                  </td>
                  <td class="px-4 py-2.5 text-center">
                    <span v-if="item.cst_csosn" class="inline-block px-1.5 py-0.5 bg-zinc-100 text-zinc-600 rounded text-[10px] font-mono">{{ item.cst_csosn }}</span>
                    <span v-else class="text-zinc-300">—</span>
                  </td>
                  <td class="px-4 py-2.5 text-center">
                    <span v-if="item.ncm" class="inline-block px-1.5 py-0.5 bg-zinc-100 text-zinc-600 rounded text-[10px] font-mono">{{ item.ncm }}</span>
                    <button
                      v-else
                      type="button"
                      class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-amber-50 text-amber-600 rounded text-[10px] font-semibold hover:bg-amber-100 transition-colors"
                      title="NCM não cadastrado — clique para corrigir"
                      @click.stop="navegarProduto(item.produto_id)"
                    >
                      <AlertCircle :size="10" />
                      Vazio
                    </button>
                  </td>
                  <td class="px-4 py-2.5 text-right font-semibold text-zinc-800 font-mono">{{ formatCurrency(item.valor_total) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Resumo Financeiro -->
        <div class="rounded-xl border border-zinc-200 bg-white overflow-hidden">
          <div class="flex items-center gap-2 px-4 py-2.5 bg-zinc-50 border-b border-zinc-100">
            <Receipt :size="14" class="text-zinc-400" />
            <h4 class="text-xs font-semibold uppercase tracking-wider text-zinc-500">Resumo Financeiro</h4>
          </div>
          <div class="p-4 space-y-2.5">
            <div class="flex justify-between text-sm">
              <span class="text-zinc-500">Subtotal dos Produtos</span>
              <span class="font-medium text-zinc-800 font-mono">{{ formatCurrency(previewData.totais.valor_produtos) }}</span>
            </div>
            <div v-if="previewData.totais.descontos > 0" class="flex justify-between text-sm">
              <span class="text-zinc-500">Descontos</span>
              <span class="font-medium text-red-600 font-mono">− {{ formatCurrency(previewData.totais.descontos) }}</span>
            </div>
            <div v-if="previewData.totais.frete > 0" class="flex justify-between text-sm">
              <span class="text-zinc-500">Frete / Entrega</span>
              <span class="font-medium text-zinc-800 font-mono">{{ formatCurrency(previewData.totais.frete) }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-zinc-500 flex items-center gap-1">
                Tributos Aproximados
                <span class="text-[10px] text-zinc-400">(Lei 12.741)</span>
              </span>
              <span class="font-medium text-amber-600 font-mono">{{ formatCurrency(previewData.totais.total_tributos) }}</span>
            </div>

            <!-- Divider + Total -->
            <div class="border-t border-dashed border-zinc-200 pt-3 mt-3">
              <div class="flex justify-between items-center">
                <span class="text-sm font-semibold text-zinc-700">Valor Total da Nota</span>
                <span class="text-xl font-bold text-brand-primary font-mono">{{ formatCurrency(previewData.totais.valor_nota) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Formas de Pagamento -->
        <div v-if="previewData.formas_pagamento.length > 0" class="rounded-xl border border-zinc-200 bg-white overflow-hidden">
          <div class="flex items-center gap-2 px-4 py-2.5 bg-zinc-50 border-b border-zinc-100">
            <CreditCard :size="14" class="text-zinc-400" />
            <h4 class="text-xs font-semibold uppercase tracking-wider text-zinc-500">Formas de Pagamento</h4>
          </div>
          <div class="p-4 space-y-2">
            <div
              v-for="(pag, idx) in previewData.formas_pagamento"
              :key="idx"
              class="flex justify-between items-center text-sm"
            >
              <div class="flex items-center gap-2 min-w-0">
                <span class="text-zinc-700 font-medium truncate">{{ pag.nome }}</span>
                <span class="text-[10px] px-1.5 py-0.5 bg-zinc-100 text-zinc-500 rounded font-mono shrink-0">{{ pag.codigo_sefaz }}</span>
              </div>
              <span class="font-medium text-zinc-800 font-mono whitespace-nowrap">{{ formatCurrency(pag.valor) }}</span>
            </div>
          </div>
        </div>

        <!-- Aviso de simulação -->
        <div class="flex items-start gap-2.5 rounded-lg bg-amber-50 border border-amber-200 px-3.5 py-2.5">
          <ShieldCheck :size="16" class="text-amber-500 mt-0.5 shrink-0" />
          <p class="text-xs text-amber-700 leading-relaxed">
            Esta é uma <strong>simulação</strong>. Os valores de tributos são aproximados e podem variar após a transmissão para a SEFAZ.
          </p>
        </div>

      </div>

      <div class="mt-6 flex justify-end gap-3 pt-4 border-t border-zinc-100">
        <BaseButton variant="secondary" @click="handleVoltar" :disabled="emitirMutation.isPending.value">Voltar</BaseButton>
        <BaseButton 
          variant="primary" 
          @click="handleEmitir" 
          :disabled="emitirMutation.isPending.value"
          :is-loading="emitirMutation.isPending.value"
        >
          Confirmar Emissão
        </BaseButton>
      </div>
    </template>
  </BaseModal>

  <!-- Modal de Edição / Vinculação de Cliente -->
  <FiscalEditarVendaModal
    v-if="vendaParaEditar"
    :is-open="modalEditarVendaOpen"
    :venda-id="vendaParaEditar.id"
    :numero-venda="vendaParaEditar.numero_venda ?? vendaParaEditar.id"
    :cliente-atual-id="vendaParaEditar.cliente?.id ?? null"
    @close="modalEditarVendaOpen = false"
    @saved="() => {
      modalEditarVendaOpen = false;
      toast.success('Cliente vinculado à venda com sucesso!');
    }"
  />
</template>
