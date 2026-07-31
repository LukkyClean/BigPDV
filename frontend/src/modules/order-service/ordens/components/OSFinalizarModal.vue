<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue';
import { CheckCircle2, AlertTriangle, XCircle, ShieldCheck, User, Cpu, Calendar, Banknote, BookmarkCheck, CalendarClock, Gauge, ChevronDown } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseTextarea from '@/shared/components/ui/BaseInput/BaseTextarea.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import BaseCheckbox from '@/shared/components/ui/BaseCheckbox/BaseCheckbox.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseDateInput from '@/shared/components/ui/BaseDateInput/BaseDateInput.vue';

import type { OrderServiceReadDataType } from '../schemas/orderServiceQuery.schema';
import type { OsEquipSituacaoEnumDataType } from '../schemas/enums/osEnums.schema';
import { formatCurrency } from '@/shared/utils/finance';
import { useCapacidades } from '@/modules/order-service/shared/segmento/useCapacidades';
import { useToast } from '@/shared/composables/useToast';
import { useImpressaoStore } from '@/shared/stores/impressao.store';
import { updateObjetoOS } from '../services/orderServiceUpdate.service';


export interface DadosFinalizacaoOS {
  situacao_equipamento?: OsEquipSituacaoEnumDataType;
  garantia?: string;
  solucao?: string;
  observacoes?: string;
  desconto: number;
  zerarAdiantamento?: boolean;
  shouldPrint?: boolean;
}

interface Props {
  isOpen: boolean;
  osNumero: string | null;
  ordemServico: OrderServiceReadDataType | null;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  close: [];
  advance: [data: DadosFinalizacaoOS];
}>();

const { temRevisoes } = useCapacidades();
const toast = useToast();
const impressaoStore = useImpressaoStore();

// ─── Próxima revisão (oficina) — agendamento por intervalo ("o que vencer primeiro") ──
const proximaRevisaoData = ref<string>('');
const proximaRevisaoKm = ref<number | null>(null);
const revisaoAberta = ref(false); // colapsado por padrão (campo opcional)
const revisaoBlock = ref<HTMLElement | null>(null);

// Abre/fecha o bloco de revisão; ao abrir, rola até ele (a barra de ação fica sticky).
function toggleRevisao() {
  revisaoAberta.value = !revisaoAberta.value;
  if (revisaoAberta.value) {
    nextTick(() => {
      revisaoBlock.value?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    });
  }
}

// Resumo exibido na barra quando o bloco está fechado (ex: "12/10/2026 · 105.000 km").
const revisaoResumo = computed(() => {
  const partes: string[] = [];
  if (proximaRevisaoData.value) {
    const [y, m, d] = proximaRevisaoData.value.split('-');
    if (y && m && d) partes.push(`${d}/${m}/${y}`);
  }
  if (proximaRevisaoKm.value != null) partes.push(`${proximaRevisaoKm.value.toLocaleString('pt-BR')} km`);
  return partes.join(' · ');
});

// Só faz sentido agendar retorno quando o objeto foi reparado (não em condenado/sem reparo).
const mostrarRevisao = computed(
  () => temRevisoes.value && situacao_equipamento.value === 'REPARADO',
);

// KM base para os presets = KM de entrada registrado nesta OS (último conhecido do veículo).
const kmBaseRevisao = computed<number>(() => {
  const km = (props.ordemServico?.dados_adicionais as Record<string, unknown> | undefined)?.['km_entrada'];
  return typeof km === 'number' ? km : 0;
});

function agendarRevisaoMeses(meses: number) {
  const d = new Date();
  d.setMonth(d.getMonth() + meses);
  proximaRevisaoData.value = d.toISOString().slice(0, 10);
}

function agendarRevisaoKm(delta: number) {
  proximaRevisaoKm.value = kmBaseRevisao.value + delta;
}

function onProximaRevisaoKmInput(v: string) {
  const digitos = String(v).replace(/\D/g, '');
  proximaRevisaoKm.value = digitos ? Number(digitos) : null;
}

// Grava o alvo no veículo (endpoint de objeto, update parcial) ANTES de finalizar,
// enquanto a OS ainda está editável. Desacoplado do fluxo de finalização.
async function salvarProximaRevisao() {
  if (!mostrarRevisao.value || !props.osNumero) return;
  if (!proximaRevisaoData.value && proximaRevisaoKm.value == null) return;
  try {
    await updateObjetoOS({
      osNumber: props.osNumero,
      updatedObjeto: {
        proxima_revisao_data: proximaRevisaoData.value || null,
        proxima_revisao_km: proximaRevisaoKm.value ?? null,
      },
    });
  } catch {
    toast.error('OS finalizada, mas não foi possível agendar a próxima revisão.');
  }
}

// ─── Estado ──────────────────────────────────────────────────────────────────
const situacao_equipamento = ref<OsEquipSituacaoEnumDataType | undefined>('REPARADO');
const garantia = ref<string | undefined>(undefined);
const hasAttemptedAdvance = ref(false);
const showOsVaziaModal = ref(false);
const solucao = ref('');
const observacoes = ref('');
const descontoDisplay = ref(0);
const descontoPercentual = ref(0);
const descontoTipo = ref<'valor' | 'percentual'>('valor');
const stepAdiantamento = ref(false)
const shouldPrint = ref(false);
const showResumo = ref(false);

const opcoesGarantia = ['Sem garantia', '30 dias', '60 dias', '90 dias', '6 meses', '1 ano'];

// ─── Computeds ───────────────────────────────────────────────────────────────
const clienteNome = computed(() => {
  const c = props.ordemServico?.cliente as any;
  return c?.nome ?? c?.razao_social ?? '—';
});

const clienteDoc = computed(() => {
  const c = props.ordemServico?.cliente as any;
  return c?.cpf ?? c?.cnpj ?? null;
});

const subtotalItens = computed(() => {
  if (!props.ordemServico?.itens) return 0;
  return props.ordemServico.itens.reduce((sum, item) => sum + item.valor_total, 0);
});

// Valor pago em finalizações anteriores — deduzido do cálculo atual como crédito
const pagoAnteriormente = computed(() => props.ordemServico?.credito_anterior ?? 0);

const taxaEntrega = computed(() => props.ordemServico?.taxa_entrega ?? 0);

// Desconto já gravado na OS — somente leitura; o backend ACUMULA o desconto novo em
// cima deste, então ele precisa ser sempre o os.desconto atual. NÃO condicionar ao
// credito_anterior: numa reabertura "não pagou" o crédito é zerado mas o desconto
// permanece, e amarrar ao crédito fazia o modal ignorar o desconto existente.
const existingDesconto = computed(() => props.ordemServico?.desconto ?? 0);

const valorEntrada = computed(() => props.ordemServico?.valor_entrada ?? 0);

const aCobrar = computed(() => {
  const total = Math.max(0, subtotalItens.value + taxaEntrega.value - existingDesconto.value - desconto.value);
  return Math.max(0, total - pagoAnteriormente.value - valorEntrada.value);
});

const jaPago = computed(() => pagoAnteriormente.value + valorEntrada.value);

const desconto = computed(() => {
  if (descontoTipo.value === 'percentual') {
    const pct = Math.min(100, Math.max(0, descontoPercentual.value));
    return Math.round(subtotalItens.value * (pct / 100));
  }
  return Math.round(descontoDisplay.value * 100);
});

// ─── Situação ─────────────────────────────────────────────────────────────────
const situacoesEquipamento: {
  value: OsEquipSituacaoEnumDataType;
  label: string;
  icon: unknown;
  activeClass: string;
}[] = [
  { value: 'REPARADO',   label: 'Reparado',   icon: CheckCircle2,  activeClass: 'border-emerald-500 bg-emerald-50 text-emerald-700' },
  { value: 'SEM_REPARO', label: 'Sem reparo', icon: AlertTriangle, activeClass: 'border-amber-400 bg-amber-50 text-amber-700' },
  { value: 'CONDENADO',  label: 'Condenado',  icon: XCircle,       activeClass: 'border-red-500 bg-red-50 text-red-700' },
];

function toggleSituacao(value: OsEquipSituacaoEnumDataType) {
  situacao_equipamento.value = situacao_equipamento.value === value ? undefined : value;
}

function setDescontoTipo(tipo: 'valor' | 'percentual') {
  descontoTipo.value = tipo;
  if (tipo === 'valor') descontoPercentual.value = 0;
  else descontoDisplay.value = 0;
}

// ─── Fluxo de entrega (Sem reparo / Condenado) ───────────────────────────────
const isEntregaFlow = computed(() =>
  situacao_equipamento.value === 'SEM_REPARO' || situacao_equipamento.value === 'CONDENADO'
);

// Valor que sobra do adiantamento após descontar os serviços cobrados (ex: taxa de orçamento)
const excedente = computed(() => {
  const entrada = props.ordemServico?.valor_entrada ?? 0;
  return Math.max(0, entrada - aCobrar.value);
});

const adiantamentoParaDecisao = computed(() => excedente.value > 0);

// ─── Reset ───────────────────────────────────────────────────────────────────
watch(() => props.isOpen, (open) => {
  if (open) {
    // Numa refinalização (OS reaberta) o desfecho anterior já está gravado.
    // Sem isto o modal reabria sempre em "Reparado" e um Condenado virava
    // Reparado no primeiro clique de finalizar, sem ninguém perceber.
    situacao_equipamento.value = props.ordemServico?.situacao_equipamento ?? 'REPARADO';
    // Desconto anterior é preservado via existingDesconto — campo começa vazio.
    // Pré-preenche a próxima revisão com o alvo já cadastrado no veículo (se houver).
    const obj = props.ordemServico?.objeto as
      | { proxima_revisao_data?: string | null; proxima_revisao_km?: number | null }
      | undefined;
    proximaRevisaoData.value = obj?.proxima_revisao_data ?? '';
    proximaRevisaoKm.value = obj?.proxima_revisao_km ?? null;
    // Abre o bloco só se já houver um alvo agendado; senão fica colapsado.
    revisaoAberta.value = !!(obj?.proxima_revisao_data || obj?.proxima_revisao_km != null);
    // "Imprimir Comprovante" segue a config de impressão da OS: 'automatico'
    // (ou 'perguntar') já vem marcado; 'nao' começa desmarcado. Antes começava
    // sempre desmarcado e a impressão automática pós-finalização não saía.
    shouldPrint.value = impressaoStore.config.auto_imprimir_os !== 'nao';
  } else {
    situacao_equipamento.value = 'REPARADO';
    garantia.value = undefined;
    hasAttemptedAdvance.value = false;
    stepAdiantamento.value = false;
    shouldPrint.value = false;
    showResumo.value = false;
    solucao.value = '';
    observacoes.value = '';
    descontoDisplay.value = 0;
    descontoPercentual.value = 0;
    descontoTipo.value = 'valor';
    proximaRevisaoData.value = '';
    proximaRevisaoKm.value = null;
    revisaoAberta.value = false;
  }
});

// ─── Avançar ─────────────────────────────────────────────────────────────────
const garantiaObrigatoria = computed(() => situacao_equipamento.value === 'REPARADO' || !situacao_equipamento.value);

function buildDesconto() {
  return descontoTipo.value === 'percentual'
    ? Math.round(subtotalItens.value * (Math.min(100, Math.max(0, descontoPercentual.value)) / 100))
    : Math.round(descontoDisplay.value * 100);
}

async function handleAdvance() {
  hasAttemptedAdvance.value = true;
  if (garantiaObrigatoria.value && !garantia.value) return;

  if (subtotalItens.value === 0 && situacao_equipamento.value === 'REPARADO') {
    showOsVaziaModal.value = true;
    return;
  }

  // Sem reparo / Condenado: pergunta sobre adiantamento antes de emitir
  if (isEntregaFlow.value && adiantamentoParaDecisao.value) {
    stepAdiantamento.value = true;
    return;
  }

  await salvarProximaRevisao();
  emit('advance', {
    situacao_equipamento: situacao_equipamento.value,
    garantia: garantia.value,
    solucao: solucao.value || undefined,
    observacoes: observacoes.value || undefined,
    desconto: buildDesconto(),
    // Sem isto o checkbox "Imprimir Comprovante" se perdia no caminho do
    // pagamento (dadosOs.shouldPrint vinha undefined → false), e a finalização
    // COM pagamento nunca imprimia automaticamente. A via de entrega já mandava.
    shouldPrint: shouldPrint.value,
  });
}

async function handleEmitEntrega(zerarAdiantamento: boolean) {
  await salvarProximaRevisao();
  emit('advance', {
    situacao_equipamento: situacao_equipamento.value,
    garantia: garantia.value,
    solucao: solucao.value || undefined,
    observacoes: observacoes.value || undefined,
    desconto: buildDesconto(),
    zerarAdiantamento,
    shouldPrint: shouldPrint.value,
  });
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    :title="stepAdiantamento ? 'Adiantamento recebido' : 'Finalizar Ordem de Serviço'"
    :subtitle="stepAdiantamento ? '' : (osNumero ? `OS: ${osNumero}` : '')"
    :size="stepAdiantamento ? 'sm' : 'xl'"
    overflow="auto"
    @close="emit('close')"
  >
    <!-- ── Step adiantamento: substitui todo o conteúdo ── -->
    <div v-if="stepAdiantamento" class="flex flex-col items-center gap-5 py-2">
      <div class="p-4 bg-amber-50 rounded-full">
        <Banknote :size="32" class="text-amber-500" />
      </div>
      <div class="text-center space-y-1">
        <p class="text-sm font-semibold text-zinc-800">
          Excedente do adiantamento:
          <span class="text-amber-600 font-bold">{{ formatCurrency(excedente) }}</span>
        </p>
        <p v-if="aCobrar > 0" class="text-xs text-zinc-400">
          Adiantamento {{ formatCurrency(ordemServico?.valor_entrada ?? 0) }} − Serviços {{ formatCurrency(aCobrar) }}
        </p>
        <p class="text-xs text-zinc-500">O que deseja fazer com esse valor?</p>
      </div>
      <div class="grid grid-cols-2 gap-3 w-full">
        <button
          type="button"
          class="flex flex-col items-center gap-2 p-3.5 rounded-xl border-2 border-emerald-400 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-all"
          @click="handleEmitEntrega(false)"
        >
          <BookmarkCheck :size="20" />
          <span class="text-xs font-semibold text-center leading-tight">Manter como<br>crédito</span>
        </button>
        <button
          type="button"
          class="flex flex-col items-center gap-2 p-3.5 rounded-xl border-2 border-brand-primary bg-brand-primary/5 text-brand-primary hover:bg-brand-primary/10 transition-all"
          @click="handleEmitEntrega(true)"
        >
          <Banknote :size="20" />
          <span class="text-xs font-semibold text-center leading-tight">Devolver em<br>dinheiro</span>
        </button>
      </div>
      <div class="flex justify-center">
        <BaseCheckbox v-model="shouldPrint" label="Imprimir Comprovante" />
      </div>

      <button type="button" class="text-xs text-zinc-400 hover:text-zinc-600 transition-colors" @click="stepAdiantamento = false">
        ← Voltar
      </button>
    </div>

    <!-- ── Formulário principal (o corpo do BaseModal rola; a barra fica sticky) ── -->
    <div v-else class="flex flex-col gap-4">

      <!-- ── Linha 1: Cliente + Objeto + Previsão ── -->
      <div class="grid grid-cols-3 gap-3">
        <div class="bg-zinc-50 border border-zinc-200 rounded-xl p-3 flex items-center gap-3">
          <div class="p-2 bg-brand-primary/10 rounded-lg shrink-0">
            <User :size="16" class="text-brand-primary" />
          </div>
          <div class="min-w-0">
            <p class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">Cliente</p>
            <p class="font-semibold text-zinc-800 text-sm truncate leading-tight">{{ clienteNome }}</p>
            <p v-if="clienteDoc" class="mt-0.5 text-xs text-zinc-400">{{ clienteDoc }}</p>
          </div>
        </div>

        <div class="bg-zinc-50 border border-zinc-200 rounded-xl p-3 flex items-center gap-3">
          <div class="p-2 bg-brand-primary/10 rounded-lg shrink-0">
            <Cpu :size="16" class="text-brand-primary" />
          </div>
          <div class="min-w-0">
            <p class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">Objeto</p>
            <p class="font-semibold text-zinc-800 text-sm truncate leading-tight">
              {{ ordemServico?.objeto?.marca }} {{ ordemServico?.objeto?.modelo }}
            </p>
            <p class="mt-0.5 text-xs text-zinc-400">Série: {{ ordemServico?.objeto?.numero_serie }}</p>
          </div>
        </div>

        <div
          class="rounded-xl p-3 flex items-center gap-3 border"
          :class="ordemServico?.data_previsao
            ? new Date(ordemServico.data_previsao) < new Date()
              ? 'bg-red-50 border-red-200'
              : 'bg-zinc-50 border-zinc-200'
            : 'bg-zinc-50 border-zinc-200'"
        >
          <div
            class="p-2 rounded-lg shrink-0"
            :class="ordemServico?.data_previsao && new Date(ordemServico.data_previsao) < new Date()
              ? 'bg-red-100'
              : 'bg-brand-primary/10'"
          >
            <Calendar
              :size="16"
              :class="ordemServico?.data_previsao && new Date(ordemServico.data_previsao) < new Date()
                ? 'text-red-500'
                : 'text-brand-primary'"
            />
          </div>
          <div class="min-w-0">
            <p class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">Data de Entrega</p>
            <p
              class="font-semibold text-sm leading-tight"
              :class="ordemServico?.data_previsao && new Date(ordemServico.data_previsao) < new Date()
                ? 'text-red-600'
                : 'text-zinc-800'"
            >
              {{ ordemServico?.data_previsao
                ? new Date(ordemServico.data_previsao).toLocaleDateString('pt-BR')
                : new Date().toLocaleDateString('pt-BR') }}
            </p>
            <p
              v-if="ordemServico?.data_previsao && new Date(ordemServico.data_previsao) < new Date()"
              class="text-[10px] text-red-500"
            >
              Em atraso
            </p>
          </div>
        </div>
      </div>

      <!-- ── Linha 2: Solução + Observações lado a lado ── -->
      <div class="grid grid-cols-2 gap-3">
        <div>
          <div class="flex items-center gap-1.5 mb-1.5">
            <CheckCircle2 :size="13" class="text-brand-primary" />
            <label class="text-xs font-semibold text-zinc-600">Solução Aplicada</label>
            <span class="text-[10px] text-zinc-400">(opcional)</span>
          </div>
          <BaseTextarea
            v-model="solucao"
            placeholder="Descreva o serviço realizado, peças substituídas..."
            :rows="3"
          />
        </div>
        <div>
          <div class="flex items-center gap-1.5 mb-1.5">
            <label class="text-xs font-semibold text-zinc-600">Observações</label>
            <span class="text-[10px] text-zinc-400">(opcional)</span>
          </div>
          <BaseTextarea
            v-model="observacoes"
            :rows="3"
            placeholder="Garantia, orientações ao cliente..."
          />
        </div>
      </div>

      <!-- ── Linha 3: Situação do Objeto ── -->
      <div>
        <div class="flex items-center gap-1.5 mb-2">
          <ShieldCheck :size="14" class="text-brand-primary" />
          <span class="text-xs font-semibold text-zinc-500 uppercase tracking-wide">Situação do Objeto</span>
          <span class="text-[10px] text-zinc-400">(opcional)</span>
        </div>
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="opcao in situacoesEquipamento"
            :key="opcao.value"
            type="button"
            :class="[
              'flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl border-2 transition-all cursor-pointer',
              situacao_equipamento === opcao.value
                ? opcao.activeClass
                : 'border-zinc-200 bg-white hover:bg-zinc-50 hover:border-brand-primary hover:text-brand-primary',
            ]"
            @click="toggleSituacao(opcao.value)"
          >
            <component :is="opcao.icon" :size="16" />
            <span class="text-xs font-semibold">{{ opcao.label }}</span>
          </button>
        </div>
      </div>

      <!-- ── Linha 4: Garantia ── -->
      <div>
        <div class="flex items-center gap-1.5 mb-2">
          <span class="text-xs font-semibold text-zinc-500 uppercase tracking-wide">Garantia</span>
          <span v-if="garantiaObrigatoria" class="text-[10px] text-red-400">*</span>
          <span v-else class="text-[10px] text-zinc-400">(opcional)</span>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="opcao in opcoesGarantia"
            :key="opcao"
            type="button"
            :class="[
              'px-3 py-1.5 rounded-lg border text-xs font-medium transition-all cursor-pointer',
              garantia === opcao
                ? 'border-brand-primary bg-brand-primary text-white'
                : 'border-zinc-200 bg-white text-zinc-600 hover:border-brand-primary hover:text-brand-primary',
            ]"
            @click="garantia = garantia === opcao ? undefined : opcao"
          >
            {{ opcao }}
          </button>
        </div>
        <p v-if="garantiaObrigatoria && hasAttemptedAdvance && !garantia" class="text-xs text-red-500 mt-1.5">
          Selecione um prazo de garantia para continuar.
        </p>
      </div>

      <!-- ── Linha 5: Próxima Revisão (oficina) — colapsável ── -->
      <div v-if="mostrarRevisao" ref="revisaoBlock" class="bg-brand-primary/5 border border-brand-primary/15 rounded-xl scroll-mb-28">
        <button
          type="button"
          class="w-full flex items-center gap-2 px-3 py-2.5 text-left cursor-pointer"
          @click="toggleRevisao"
        >
          <CalendarClock :size="14" class="text-brand-primary shrink-0" />
          <span class="text-xs font-semibold text-zinc-600 uppercase tracking-wide">Agendar Próxima Revisão</span>
          <span v-if="!revisaoAberta && revisaoResumo" class="text-[11px] font-semibold text-brand-primary truncate">· {{ revisaoResumo }}</span>
          <span v-else class="text-[10px] text-zinc-400">(opcional)</span>
          <ChevronDown
            :size="15"
            class="ml-auto text-zinc-400 shrink-0 transition-transform"
            :class="revisaoAberta ? 'rotate-180' : ''"
          />
        </button>
        <div v-if="revisaoAberta" class="px-3 pb-3">
          <p class="text-[10px] text-zinc-400 mb-2">Vale o que vencer primeiro — data ou KM.</p>
          <div class="grid grid-cols-2 gap-4">
          <!-- Por data -->
          <div>
            <p class="text-[11px] font-semibold text-zinc-500 mb-1.5 flex items-center gap-1">
              <Calendar :size="12" /> Por data
            </p>
            <div class="flex flex-wrap gap-1.5 mb-2">
              <button
                v-for="p in [{ l: '3 meses', m: 3 }, { l: '6 meses', m: 6 }, { l: '1 ano', m: 12 }]"
                :key="p.m"
                type="button"
                class="px-2.5 py-1 rounded-lg border text-[11px] font-medium border-zinc-200 bg-white text-zinc-600 hover:border-brand-primary hover:text-brand-primary transition-all cursor-pointer"
                @click="agendarRevisaoMeses(p.m)"
              >
                {{ p.l }}
              </button>
            </div>
            <BaseDateInput v-model="proximaRevisaoData" />
          </div>
          <!-- Por KM -->
          <div>
            <p class="text-[11px] font-semibold text-zinc-500 mb-1.5 flex items-center gap-1">
              <Gauge :size="12" /> Por KM
              <span v-if="kmBaseRevisao" class="text-zinc-400 font-normal">· atual {{ kmBaseRevisao.toLocaleString('pt-BR') }}</span>
            </p>
            <div class="flex flex-wrap gap-1.5 mb-2">
              <button
                v-for="d in [5000, 10000, 20000]"
                :key="d"
                type="button"
                class="px-2.5 py-1 rounded-lg border text-[11px] font-medium border-zinc-200 bg-white text-zinc-600 hover:border-brand-primary hover:text-brand-primary transition-all cursor-pointer"
                @click="agendarRevisaoKm(d)"
              >
                +{{ d.toLocaleString('pt-BR') }}
              </button>
            </div>
            <BaseInput
              :model-value="proximaRevisaoKm != null ? String(proximaRevisaoKm) : ''"
              placeholder="Ex: 50000"
              @update:model-value="onProximaRevisaoKmInput"
            />
          </div>
          </div>
        </div>
      </div>

      <!-- ── Barra financeira (fixa no rodapé do modal via sticky) ── -->
      <div class="sticky bottom-0 z-10 bg-zinc-50 border border-zinc-200 rounded-xl px-4 py-3 space-y-2 shadow-[0_-6px_16px_-4px_rgba(0,0,0,0.08)]">

        <!-- Resumo expandido (toggle) -->
        <div v-if="showResumo" class="flex items-center gap-2 text-xs pb-2 border-b border-zinc-200 flex-wrap">
          <span class="text-zinc-500">Subtotal: <strong class="text-zinc-700">{{ formatCurrency(subtotalItens) }}</strong></span>
          <template v-if="existingDesconto > 0">
            <span class="text-zinc-300 font-light">−</span>
            <span class="text-zinc-500">Desc. anterior: <strong class="text-emerald-600">{{ formatCurrency(existingDesconto) }}</strong></span>
          </template>
          <template v-if="desconto > 0">
            <span class="text-zinc-300 font-light">−</span>
            <span class="text-zinc-500">Desc. adicional: <strong class="text-emerald-600">{{ formatCurrency(desconto) }}</strong></span>
          </template>
          <span class="text-zinc-300 font-light">=</span>
          <span class="font-semibold text-brand-primary">Total: {{ formatCurrency(subtotalItens - existingDesconto - desconto + taxaEntrega) }}</span>
          <template v-if="jaPago > 0">
            <span class="text-zinc-300 font-light">−</span>
            <span class="text-zinc-500">Já pago: <strong class="text-emerald-600">{{ formatCurrency(jaPago) }}</strong></span>
          </template>
        </div>

        <!-- Linha principal (sempre visível) -->
        <div class="flex items-center gap-3">

          <!-- Campo de desconto -->
          <div class="flex items-center gap-1.5 shrink-0">
            <span class="text-xs font-medium text-zinc-500">{{ existingDesconto > 0 ? 'Desc. adicional:' : 'Desconto:' }}</span>
            <div class="flex rounded-lg border border-zinc-200 overflow-hidden text-[10px] font-semibold">
              <button type="button" :class="['px-2 py-1 transition-colors', descontoTipo === 'valor' ? 'bg-brand-primary text-white' : 'bg-white text-zinc-400 hover:text-zinc-600']" @click="setDescontoTipo('valor')">R$</button>
              <button type="button" :class="['px-2 py-1 transition-colors', descontoTipo === 'percentual' ? 'bg-brand-primary text-white' : 'bg-white text-zinc-400 hover:text-zinc-600']" @click="setDescontoTipo('percentual')">%</button>
            </div>
            <div v-if="descontoTipo === 'valor'" class="w-28">
              <BaseMoneyInput v-model="descontoDisplay" label="" />
            </div>
            <div v-else class="flex items-center gap-1 w-28">
              <BaseInput v-model.number="descontoPercentual" type="number" min="0" max="100" placeholder="0" />
              <span class="text-sm font-semibold text-zinc-500">%</span>
            </div>
          </div>

          <div class="h-8 w-px bg-zinc-200 shrink-0" />

          <!-- Valor em destaque: A cobrar (OS reaberta) ou Total (com desconto) -->
          <div v-if="jaPago > 0" class="shrink-0">
            <p class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide leading-none mb-0.5">A cobrar</p>
            <p class="text-xl font-bold" :class="aCobrar === 0 ? 'text-emerald-600' : 'text-zinc-800'">
              {{ aCobrar === 0 ? 'Nada a cobrar' : formatCurrency(aCobrar) }}
            </p>
          </div>
          <div v-else-if="desconto > 0 || existingDesconto > 0" class="shrink-0">
            <p class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide leading-none mb-0.5">Total</p>
            <p class="text-xl font-bold text-brand-primary">{{ formatCurrency(subtotalItens - existingDesconto - desconto + taxaEntrega) }}</p>
          </div>

          <!-- Link ver/ocultar resumo -->
          <button
            type="button"
            class="text-xs text-zinc-400 hover:text-brand-primary transition-colors shrink-0"
            @click="showResumo = !showResumo"
          >
            {{ showResumo ? '▲ ocultar' : '▼ ver resumo' }}
          </button>

          <!-- Botão -->
          <BaseButton
            type="button"
            variant="primary"
            class="ml-auto px-6 py-2.5 shadow-md shadow-blue-600/20 whitespace-nowrap shrink-0"
            @click="handleAdvance"
          >
            {{ isEntregaFlow ? 'Finalizar Entrega →' : 'Ir para Pagamento →' }}
          </BaseButton>
        </div>

      </div>

    </div>
  </BaseModal>

  <!-- Modal de aviso: OS sem itens -->
  <BaseModal
    :is-open="showOsVaziaModal"
    title="OS sem itens declarados"
    size="sm"
    :overlay="true"
    @close="showOsVaziaModal = false"
  >
    <div class="flex flex-col items-center text-center gap-4">
      <div class="p-4 bg-amber-50 rounded-full">
        <AlertTriangle :size="36" class="text-amber-500" />
      </div>

      <div class="space-y-1.5">
        <p class="text-sm text-zinc-700 font-medium">
          Não é possível finalizar como <span class="font-bold text-emerald-600">Reparado</span> sem nenhum serviço ou peça cadastrado.
        </p>
        <p class="text-xs text-zinc-500">
          Volte ao cadastro da OS e declare o que foi realizado, ou altere a situação do objeto.
        </p>
      </div>

      <div class="flex flex-col gap-2 w-full pt-2">
        <BaseButton
          variant="primary"
          class="w-full"
          @click="emit('close'); showOsVaziaModal = false"
        >
          Voltar ao cadastro da OS
        </BaseButton>
        <BaseButton
          variant="secondary"
          class="w-full"
          @click="showOsVaziaModal = false"
        >
          Alterar situação do objeto
        </BaseButton>
      </div>
    </div>
    <template #footer><span></span></template>
  </BaseModal>
</template>
