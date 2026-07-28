<script setup lang="ts">
import { computed } from 'vue';
import { Fuel } from 'lucide-vue-next';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseTextarea from '@/shared/components/ui/BaseInput/BaseTextarea.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import type { SelectOption } from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import type { ObjetoHistorico } from '@/modules/customers/types/clientes.types';
import { OS_EQUIP_TYPE_OPTIONS } from '../../constants/ordemServico.constants';
import { useCapacidades } from '@/modules/order-service/shared/segmento/useCapacidades';
import { useObjetoLabels } from '@/modules/order-service/shared/segmento/useObjetoLabels';

interface ObjetoForm {
  objeto: string;
  marca: string;
  modelo: string;
  numero_serie: string;
  imei: string;
  cor: string;
  senha_aparelho: string;
  acessorios: string;
  defeito_relatado: string;
  condicoes_aparelho: string;
}

interface Props {
  modelValue: ObjetoForm;
  /** dados_adicionais do objeto (ex: oficina → chassi, ano). */
  objetoDados?: Record<string, unknown>;
  /** dados_adicionais da OS / check-in (ex: oficina → km_entrada, combustível). */
  osDados?: Record<string, unknown>;
  objetosHistorico?: ObjetoHistorico[];
  selectedHistorico?: string;
  isLocked?: boolean;
  isCreateMode?: boolean;
  errors?: Record<string, string | undefined>;
}

const props = withDefaults(defineProps<Props>(), {
  objetoDados: () => ({}),
  osDados: () => ({}),
  objetosHistorico: () => [],
  selectedHistorico: '',
  isLocked: false,
  errors: () => ({}),
});

// Rótulos e campos vêm do contrato do segmento (/definicao-campos). O usuário
// nunca vê "objeto": oficina → "Veículo/Placa"; informática → "Equipamento/Nº Série".
//
// Cada campo pergunta por SI ao contrato (`temCampo('imei')`) em vez de perguntar
// quem é o cliente (`!isOficinaMecanica`). A negação fazia a regra ser "todo mundo
// que não é oficina vê IMEI/senha" — ou seja, um segmento novo (mercado,
// marcenaria) herdaria a tela de informática sem ninguém pedir. Agora só vê quem
// declara o campo no registry do backend.
const { objetoIcon, labelSingular, labelIdentificador } = useObjetoLabels();
const { temCampo } = useCapacidades();

function fieldError(field: string): string | undefined {
  return props.errors?.[`objeto.${field}`] ?? props.errors?.[field];
}

const emit = defineEmits<{
  'update:modelValue': [value: ObjetoForm];
  'update:objetoDados': [value: Record<string, unknown>];
  'update:osDados': [value: Record<string, unknown>];
  'update:selectedHistorico': [value: string];
  applyHistorico: [];
}>();

const historicoOptions = computed<SelectOption[]>(() => [
  { value: '', label: 'Usar anterior...' },
  ...props.objetosHistorico.map((objeto, idx) => ({
    value: String(idx),
    label: `${objeto.objeto}${objeto.numero_serie ? ` (S/N: ${objeto.numero_serie})` : ''}`,
  })),
]);

const tipoEquipamentoOptions: SelectOption[] = [
  { value: '', label: '-- Selecione --' },
  ...OS_EQUIP_TYPE_OPTIONS.map(o => ({ value: o.value, label: o.label })),
];

const combustivelNivelOptions: SelectOption[] = [
  { value: '', label: '-- Nível --' },
  { value: 'VAZIO', label: 'Vazio' },
  { value: '1/4', label: '1/4' },
  { value: '1/2', label: '1/2' },
  { value: '3/4', label: '3/4' },
  { value: 'CHEIO', label: 'Cheio' },
];

const combustivelTipoOptions: SelectOption[] = [
  { value: '', label: '-- Combustível --' },
  { value: 'ALCOOL', label: 'Álcool' },
  { value: 'GASOLINA', label: 'Gasolina' },
  { value: 'DIESEL', label: 'Diesel' },
];

function updateField<K extends keyof ObjetoForm>(field: K, value: ObjetoForm[K]) {
  emit('update:modelValue', { ...props.modelValue, [field]: value });
}

/** Lê uma chave de um dicionário dinâmico como string (para inputs). */
function dadoStr(obj: Record<string, unknown> | undefined, key: string): string {
  const v = obj?.[key];
  return v === null || v === undefined ? '' : String(v);
}

function updateObjetoDado(key: string, value: unknown) {
  emit('update:objetoDados', { ...props.objetoDados, [key]: value });
}

function updateOsDado(key: string, value: unknown) {
  emit('update:osDados', { ...props.osDados, [key]: value });
}

function updateKmEntrada(value: string) {
  const num = value.replace(/\D/g, '');
  updateOsDado('km_entrada', num ? Number(num) : undefined);
}

function handleHistoricoSelectChange(value: string) {
  emit('update:selectedHistorico', value);
  if (value) {
    emit('applyHistorico');
  }
}
</script>

<template>
  <div class="space-y-5 animate-fadeIn">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="space-y-4">
        <h5 class="flex items-center justify-between text-xs font-bold text-slate-500 uppercase border-b border-slate-100 pb-2">
          <div class="flex items-center gap-2">
            <component :is="objetoIcon" :size="14" />
            Dados do {{ labelSingular }}
          </div>
          <div v-if="objetosHistorico.length > 0 && !isLocked && isCreateMode" class="flex items-center gap-2">
            <BaseSelect
              :model-value="selectedHistorico"
              :options="historicoOptions"
              class="max-w-37.5"
              @update:model-value="handleHistoricoSelectChange($event as string)"
            />
          </div>
        </h5>

        <!-- Tipo de equipamento: enum de TI; só quem declara IMEI usa esse mundo -->
        <BaseSelect
          v-if="temCampo('imei')"
          :model-value="modelValue.objeto || ''"
          label="Tipo de Equipamento"
          :options="tipoEquipamentoOptions"
          required
          :error="fieldError('tipo_equipamento')"
          @update:model-value="updateField('objeto', $event as string)"
        />

        <div class="grid grid-cols-2 gap-3">
          <BaseInput :model-value="modelValue.marca" label="Marca" placeholder="Marca" required :error="fieldError('marca')" @update:model-value="updateField('marca', $event)" />
          <BaseInput :model-value="modelValue.modelo" label="Modelo" placeholder="Modelo" required :error="fieldError('modelo')" @update:model-value="updateField('modelo', $event)" />
        </div>

        <BaseInput
          :model-value="modelValue.numero_serie"
          :label="labelIdentificador"
          :placeholder="temCampo('placa') ? 'ABC1D23' : 'Número de série'"
          required
          :error="fieldError('numero_serie')"
          @update:model-value="updateField('numero_serie', $event)"
        />
      </div>

      <div class="space-y-4">
        <h5 class="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase border-b border-slate-100 pb-2">
          {{ temCampo('senha_aparelho') ? 'Detalhes & Segurança' : 'Detalhes' }}
        </h5>

        <div class="grid grid-cols-2 gap-3">
          <!-- IMEI: apenas segmentos de TI -->
          <BaseInput v-if="temCampo('imei')" :model-value="modelValue.imei" label="IMEI" placeholder="IMEI (opcional)" :error="fieldError('imei')" @update:model-value="updateField('imei', $event)" />
          <BaseInput :model-value="modelValue.cor" label="Cor" placeholder="Ex: Preto" @update:model-value="updateField('cor', $event)" />
        </div>

        <!-- Chassi e ano: só segmentos que os declaram -->
        <div v-if="temCampo('chassi') || temCampo('ano')" class="grid grid-cols-2 gap-3">
          <BaseInput :model-value="dadoStr(objetoDados, 'chassi')" label="Chassi" placeholder="17 caracteres (opcional)" @update:model-value="updateObjetoDado('chassi', $event)" />
          <BaseInput :model-value="dadoStr(objetoDados, 'ano')" label="Ano" placeholder="Ex: 2020" @update:model-value="updateObjetoDado('ano', $event)" />
        </div>

        <!-- Senha e acessórios: só segmentos que os declaram -->
        <template v-if="temCampo('senha_aparelho')">
          <BaseInput :model-value="modelValue.senha_aparelho" label="Senha / Padrão" placeholder="Senha de desbloqueio" @update:model-value="updateField('senha_aparelho', $event)" />
          <BaseInput :model-value="modelValue.acessorios" label="Acessórios (Deixados)" placeholder="Ex: Carregador, Capa..." @update:model-value="updateField('acessorios', $event)" />
        </template>
      </div>
    </div>

    <!-- Check-in de entrada: só segmentos que declaram KM/combustível -->
    <div v-if="temCampo('km_entrada')" class="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-4">
      <h5 class="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase">
        <Fuel :size="14" />
        Check-in de Entrada
      </h5>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <BaseInput
          :model-value="dadoStr(osDados, 'km_entrada')"
          label="KM de Entrada"
          placeholder="Ex: 85000"
          @update:model-value="updateKmEntrada($event)"
        />
        <BaseSelect
          :model-value="dadoStr(osDados, 'combustivel_nivel')"
          label="Nível de Combustível"
          :options="combustivelNivelOptions"
          @update:model-value="updateOsDado('combustivel_nivel', $event)"
        />
        <BaseSelect
          :model-value="dadoStr(osDados, 'combustivel_tipo')"
          label="Tipo de Combustível"
          :options="combustivelTipoOptions"
          @update:model-value="updateOsDado('combustivel_tipo', $event)"
        />
      </div>
    </div>

    <div class="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-4">
      <div>
        <BaseTextarea
          :model-value="modelValue.defeito_relatado"
          label="Defeito Relatado"
          :rows="3"
          placeholder="Descreva o problema principal relatado pelo cliente..."
          required
          :error="fieldError('defeito_relatado')"
          @update:model-value="updateField('defeito_relatado', $event as string)"
        />
      </div>

      <!-- Condições físicas de entrada: só segmentos que a declaram (oficina usa a vistoria) -->
      <div v-if="temCampo('condicoes_aparelho')">
        <label class="block text-xs font-bold text-slate-600 mb-1 uppercase">
          Condições Físicas (Entrada)
        </label>
        <BaseInput
          :model-value="modelValue.condicoes_aparelho"
          placeholder="Riscos, trincas ou danos prévios..."
          @update:model-value="updateField('condicoes_aparelho', $event)"
        />
      </div>
    </div>
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
