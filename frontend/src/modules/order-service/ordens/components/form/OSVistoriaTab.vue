<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue';
import { ClipboardCheck, Check, Printer, Smartphone, RefreshCw } from 'lucide-vue-next';

import { useOSFieldDefinition } from '@/modules/order-service/shared/segmento/useOSFieldDefinition.queries';
import type { SegmentField } from '@/modules/order-service/shared/segmento/segmentDefinition.type';
import type { MarcaDano } from '../../types/mapeamentoDanos.types';
import OSQrCodeModal from '../OSQrCodeModal.vue';
import OSMapeamentoDanos from './danos/OSMapeamentoDanos.vue';
import api from '@/api/axios';

interface Props {
  /** dados_adicionais da OS (guarda acessorios + vistoria). */
  osDados?: Record<string, unknown>;
  /**
   * dados_adicionais PERSISTIDO (o que está salvo no banco). Base do merge de 3
   * vias do polling: distingue o que o PC editou (local ≠ salvo) do que não tocou.
   */
  osDadosPersistido?: Record<string, unknown>;
  isLocked?: boolean;
  /** Numero da OS (ex: OS-2026-000001). Necessario para QR code e polling. */
  osNumber?: string;
  /** True quando a OS esta sendo criada (ainda nao existe no backend). */
  isCreateMode?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  osDados: () => ({}),
  osDadosPersistido: () => ({}),
  isLocked: false,
  osNumber: '',
  isCreateMode: false,
});

const emit = defineEmits<{
  'update:osDados': [value: Record<string, unknown>];
  imprimirFichaEntrada: [];
  imprimirFichaSaida: [];
  imprimirVistoriaPreenchida: [];
}>();

// --- QR Code Modal ---
const showQrModal = ref(false);

// --- Polling automatico (10s) ---
const isPolling = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;
/** IDs de marcadores deletados localmente — polling deve ignorá-los. */
const deletedMarkerIds = new Set<string>();

function startPolling() {
  if (pollTimer || props.isCreateMode || !props.osNumber) return;
  isPolling.value = true;
  pollTimer = setInterval(async () => {
    if (!props.osNumber) return;
    try {
      const { data } = await api.get(`/ordens-servico/${props.osNumber}`);
      const remoteDados = data?.dados_adicionais ?? {};
      const local = props.osDados as Record<string, unknown>;
      // Base do merge = estado PERSISTIDO (o que já está salvo no banco). Merge 3
      // vias por chave: se o PC editou a chave (local ≠ salvo) mantém o do PC (não
      // perde digitação); se não tocou (local == salvo) vale o do servidor,
      // refletindo ao vivo o que foi preenchido pelo celular.
      const base = props.osDadosPersistido as Record<string, unknown>;
      const merged: Record<string, unknown> = { ...local };
      const chaves = new Set([
        ...Object.keys(remoteDados),
        ...Object.keys(local),
        ...Object.keys(base),
      ]);
      for (const chave of chaves) {
        if (chave === 'mapeamento_danos') continue; // tratado à parte abaixo
        const pcEditou = JSON.stringify(local[chave]) !== JSON.stringify(base[chave]);
        if (!pcEditou) merged[chave] = remoteDados[chave];
      }

      // mapeamento_danos: merge por ID — nunca perde marcadores locais e acrescenta
      // os novos vindos do remoto (celular), ignorando os deletados localmente.
      const localDanos = local.mapeamento_danos;
      const remotoDanos = remoteDados.mapeamento_danos;
      const filterDeleted = (arr: any[]) => arr.filter((m: any) => !deletedMarkerIds.has(m.id));
      if (Array.isArray(localDanos) && localDanos.length > 0) {
        if (!Array.isArray(remotoDanos) || remotoDanos.length === 0) {
          merged.mapeamento_danos = localDanos;
        } else {
          const localIds = new Set(localDanos.map((m: any) => m.id));
          const novosDoRemoto = filterDeleted(remotoDanos).filter((m: any) => !localIds.has(m.id));
          merged.mapeamento_danos = [...localDanos, ...novosDoRemoto];
        }
      } else if (Array.isArray(remotoDanos) && remotoDanos.length > 0) {
        merged.mapeamento_danos = filterDeleted(remotoDanos);
      }

      const localJson = JSON.stringify(local);
      const mergedJson = JSON.stringify(merged);
      if (localJson !== mergedJson) {
        emit('update:osDados', merged);
      }
    } catch {
      // Silencioso: polling nao deve interromper o usuario
    }
  }, 10000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  isPolling.value = false;
}

// Inicia polling se OS existente e nao trancada
watch(
  () => [props.osNumber, props.isCreateMode, props.isLocked] as const,
  ([num, create, locked]) => {
    if (num && !create && !locked) {
      startPolling();
    } else {
      stopPolling();
    }
  },
  { immediate: true },
);

onUnmounted(stopPolling);

// A vistoria é dirigida pelo contrato do backend (/definicao-campos): acessórios
// e grupos de inspeção vêm de lá, então novos segmentos/checklists não mexem aqui.
const { data } = useOSFieldDefinition();
const definicao = computed(() => data.value?.definicao ?? null);
const acessorios = computed<string[]>(() => definicao.value?.acessorios ?? []);
const grupos = computed(() => definicao.value?.vistoria ?? []);

// Campos de check-in do tipo "opção" para marcar na tela (ex: pneus, estepe).
// Vêm do backend, então novos segmentos ganham seus campos sem mexer aqui.
// Combustível fica de fora aqui de propósito: só na ficha impressa (preenchido no papel).
const checkinOpcoes = computed<SegmentField[]>(
  () => (definicao.value?.checkin ?? []).filter(
    (c) => c.tipo === 'opcao' && !!c.opcoes?.length && !c.nome.startsWith('combustivel'),
  ),
);

const ESTADOS: { value: string; label: string; selected: string }[] = [
  { value: 'OK', label: 'OK', selected: 'bg-emerald-500 text-white border-emerald-500' },
  { value: 'N_OK', label: 'N/OK', selected: 'bg-amber-500 text-white border-amber-500' },
  { value: 'REPARAR', label: 'Reparar', selected: 'bg-red-500 text-white border-red-500' },
];

const acessoriosSel = computed<Record<string, boolean>>(
  () => (props.osDados.acessorios as Record<string, boolean>) ?? {},
);
const vistoriaSel = computed<Record<string, string>>(
  () => (props.osDados.vistoria as Record<string, string>) ?? {},
);

/** Converte o slug do backend (ex: chave_de_roda) em rótulo (Chave de roda). */
function rotulo(slug: string): string {
  const s = slug.replace(/_/g, ' ');
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Chave estável do item na vistoria (evita colisão de "percepcoes_de_uso" entre grupos). */
function chaveItem(grupoIdx: number, item: string): string {
  return `${grupoIdx}_${item}`;
}

function toggleAcessorio(key: string) {
  if (props.isLocked) return;
  const novoValor = !acessoriosSel.value[key];
  const acessoriosNovos = { ...acessoriosSel.value, [key]: novoValor };
  const patch: Record<string, unknown> = { ...props.osDados, acessorios: acessoriosNovos };
  // Ao desmarcar "Outros", limpa a descrição pra não ficar dado fantasma.
  if (key === 'outros' && !novoValor) patch.acessorios_outros = '';
  emit('update:osDados', patch);
}

/** Descrição livre do acessório "Outros" (só usada quando "outros" está marcado). */
const acessoriosOutros = computed<string>(() => (props.osDados.acessorios_outros as string) ?? '');

function setAcessoriosOutros(valor: string) {
  if (props.isLocked) return;
  emit('update:osDados', { ...props.osDados, acessorios_outros: valor });
}

function setVistoria(grupoIdx: number, item: string, estado: string) {
  if (props.isLocked) return;
  const key = chaveItem(grupoIdx, item);
  const atual = vistoriaSel.value[key];
  // Clicar no estado já selecionado limpa (toggle).
  const vistoriaNova = { ...vistoriaSel.value, [key]: atual === estado ? '' : estado };
  emit('update:osDados', { ...props.osDados, vistoria: vistoriaNova });
}

/** Valor atual de um campo de check-in (ex: pneus_estado) salvo direto em osDados. */
function valorCheckin(nome: string): string {
  return (props.osDados[nome] as string) ?? '';
}

function setCheckin(nome: string, valor: string) {
  if (props.isLocked) return;
  // Clicar na opção já marcada limpa (toggle).
  const atual = valorCheckin(nome);
  emit('update:osDados', { ...props.osDados, [nome]: atual === valor ? '' : valor });
}

/** "BOM" -> "Bom"; mantém "1/4" como está. */
function rotuloOpcao(op: string): string {
  return op.charAt(0) + op.slice(1).toLowerCase();
}

// --- Mapeamento de danos ---
const mapeamentoDanos = computed<MarcaDano[]>(
  () => (props.osDados.mapeamento_danos as MarcaDano[]) ?? [],
);

function setMapeamentoDanos(marcas: MarcaDano[]) {
  if (props.isLocked) return;
  // Rastrear IDs removidos para que o polling não os ressuscite
  const currentDanos = (props.osDados.mapeamento_danos as MarcaDano[]) ?? [];
  const novosIds = new Set(marcas.map((m) => m.id));
  for (const m of currentDanos) {
    if (!novosIds.has(m.id)) deletedMarkerIds.add(m.id);
  }
  emit('update:osDados', { ...props.osDados, mapeamento_danos: marcas });
}
</script>

<template>
  <div class="space-y-5 animate-fadeIn">
    <div class="flex items-center gap-3 border-b border-slate-200 pb-3">
      <div class="bg-brand-primary-light p-2 rounded-lg text-brand-primary">
        <ClipboardCheck :size="20" />
      </div>
      <div>
        <h5 class="text-sm font-bold text-slate-700">Vistoria de Entrada</h5>
        <p class="text-xs text-slate-500">Acessórios e checklist de inspeção do veículo</p>
      </div>
      <div class="ml-auto flex items-center gap-2">
        <!-- QR Code para preencher pelo celular -->
        <button
          v-if="osNumber && !isCreateMode"
          type="button"
          title="Preencher checklist pelo celular (QR code)"
          class="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border border-brand-primary/30 bg-brand-primary/5 text-xs font-semibold text-brand-primary hover:bg-brand-primary/10 transition-colors"
          @click="showQrModal = true"
        >
          <Smartphone :size="14" />
          Preencher pelo celular
        </button>
        <!-- Indicador de polling -->
        <div
          v-if="isPolling"
          title="Sincronizando com celular a cada 10s..."
          class="flex items-center gap-1 text-xs text-slate-400"
        >
          <RefreshCw :size="12" class="animate-spin" style="animation-duration: 3s" />
        </div>
        <button
          type="button"
          title="Imprimir ficha de entrada em branco (preencher no carro)"
          class="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:border-brand-primary hover:text-brand-primary transition-colors"
          @click="emit('imprimirFichaEntrada')"
        >
          <Printer :size="14" />
          Ficha de Entrada
        </button>
        <button
          type="button"
          title="Imprimir ficha de saída em branco (preencher no carro)"
          class="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:border-brand-primary hover:text-brand-primary transition-colors"
          @click="emit('imprimirFichaSaida')"
        >
          <Printer :size="14" />
          Ficha de Saída
        </button>
      </div>
    </div>

    <!-- Tip: QR disponível após salvar -->
    <div v-if="isCreateMode" class="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
      <Smartphone :size="16" class="text-brand-primary shrink-0" />
      <p class="text-xs text-slate-600">
        <strong>Dica:</strong> Após salvar a OS, você poderá preencher a vistoria pelo celular
        usando um QR code.
      </p>
    </div>

    <div
      v-if="!definicao"
      class="flex flex-col items-center justify-center py-12 text-slate-400 border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50"
    >
      <div class="w-14 h-14 bg-slate-100 rounded-full flex items-center justify-center mb-3">
        <ClipboardCheck :size="28" stroke-width="1.5" class="text-slate-300" />
      </div>
      <p class="text-sm font-semibold text-slate-500">Vistoria não disponível</p>
      <p class="text-xs text-slate-400 mt-1">Este segmento não possui checklist de vistoria.</p>
    </div>

    <fieldset v-else :disabled="isLocked" class="contents space-y-3">
      <!-- Estado do veículo: combustível, pneus, estepe (check-in tipo "opção") -->
      <div v-if="checkinOpcoes.length" class="space-y-4">
        <h6 class="text-xs font-bold text-slate-500 uppercase">Estado do veículo</h6>
        <div class="grid sm:grid-cols-2 gap-2">
          <div
            v-for="campo in checkinOpcoes"
            :key="campo.nome"
            class="flex items-center justify-between gap-2 p-3 bg-white border border-slate-200 rounded-lg"
          >
            <p class="text-sm text-slate-700 truncate">{{ campo.label }}</p>
            <div class="flex items-center gap-1 shrink-0 flex-wrap justify-end">
              <button
                v-for="op in campo.opcoes"
                :key="op"
                type="button"
                class="px-2 py-1 text-xs font-bold rounded-md border transition-colors"
                :class="valorCheckin(campo.nome) === op
                  ? 'bg-brand-primary text-white border-brand-primary'
                  : 'bg-slate-50 border-slate-200 text-slate-400 hover:text-slate-600'"
                @click="setCheckin(campo.nome, op)"
              >
                {{ rotuloOpcao(op) }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Acessórios presentes -->
      <div v-if="acessorios.length" class="space-y-3">
        <h6 class="text-xs font-bold text-slate-500 uppercase">Acessórios presentes</h6>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
          <button
            v-for="ac in acessorios"
            :key="ac"
            type="button"
            class="flex items-center gap-2 p-2.5 rounded-lg border text-sm text-left transition-colors"
            :class="acessoriosSel[ac]
              ? 'bg-brand-primary-light border-brand-primary/30 text-brand-primary font-semibold'
              : 'bg-white border-slate-200 text-slate-600 hover:border-brand-primary/20'"
            @click="toggleAcessorio(ac)"
          >
            <span
              class="w-4 h-4 rounded flex items-center justify-center shrink-0 border"
              :class="acessoriosSel[ac] ? 'bg-brand-primary border-brand-primary text-white' : 'border-slate-300'"
            >
              <Check v-if="acessoriosSel[ac]" :size="12" />
            </span>
            {{ rotulo(ac) }}
          </button>
        </div>

        <!-- Descrição livre quando "Outros" está marcado -->
        <input
          v-if="acessoriosSel['outros']"
          type="text"
          :value="acessoriosOutros"
          :disabled="isLocked"
          placeholder="Descreva os outros acessórios..."
          maxlength="120"
          class="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:border-brand-primary focus:outline-none disabled:bg-slate-50 disabled:text-slate-400"
          @input="setAcessoriosOutros(($event.target as HTMLInputElement).value)"
        />
      </div>

      <!-- Grupos de inspeção (OK / N-OK / Reparar) -->
      <div v-for="(grupo, gi) in grupos" :key="grupo.titulo" class="space-y-2">
        <h6 class="text-xs font-bold text-slate-500 uppercase">{{ grupo.titulo }}</h6>
        <div class="space-y-2">
          <div
            v-for="item in grupo.itens"
            :key="item"
            class="flex items-center justify-between gap-3 p-3 bg-white border border-slate-200 rounded-lg"
          >
            <p class="text-sm text-slate-700 truncate">{{ rotulo(item) }}</p>
            <div class="flex items-center gap-1 shrink-0">
              <button
                v-for="estado in ESTADOS"
                :key="estado.value"
                type="button"
                class="px-2.5 py-1 text-xs font-bold rounded-md border transition-colors"
                :class="vistoriaSel[chaveItem(gi, item)] === estado.value
                  ? estado.selected
                  : 'bg-slate-50 border-slate-200 text-slate-400 hover:text-slate-600'"
                @click="setVistoria(gi, item, estado.value)"
              >
                {{ estado.label }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Mapeamento visual de danos -->
      <div class="space-y-3">
        <h6 class="text-xs font-bold text-slate-500 uppercase">Mapeamento de Danos</h6>
        <OSMapeamentoDanos
          :marcas="mapeamentoDanos"
          :is-locked="isLocked"
          @update:marcas="setMapeamentoDanos"
        />
      </div>
    </fieldset>

    <!-- Imprimir a vistoria já preenchida (fora do fieldset: funciona mesmo com a OS trancada) -->
    <div v-if="definicao" class="flex justify-end pt-3 border-t border-slate-200">
      <button
        type="button"
        title="Imprimir a ficha de vistoria com o que já foi preenchido na tela"
        class="inline-flex items-center gap-2 h-10 px-4 rounded-lg bg-brand-primary text-white text-sm font-semibold hover:bg-brand-primary/90 transition-colors"
        @click="emit('imprimirVistoriaPreenchida')"
      >
        <Printer :size="16" />
        Imprimir vistoria preenchida
      </button>
    </div>

    <!-- Modal do QR Code -->
    <OSQrCodeModal
      v-if="osNumber"
      :is-open="showQrModal"
      :os-number="osNumber"
      @close="showQrModal = false"
    />
  </div>
</template>

<style scoped>
.animate-fadeIn {
  animation: fadeIn 0.3s ease-in-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
