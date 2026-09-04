<script setup lang="ts">
import { computed, ref } from 'vue';
import { ChevronDown } from 'lucide-vue-next';
import { onClickOutside } from '@vueuse/core';
import { useAuthStore } from '@/shared/stores/auth.store';
import type { SelectOption } from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import type { OsStatusEnumDataType, OsPriorityEnumDataType } from '../../schemas/enums/osEnums.schema';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseDateInput from '@/shared/components/ui/BaseDateInput/BaseDateInput.vue';
import { useObjetoLabels } from '@/modules/order-service/shared/segmento/useObjetoLabels';

/**
 * "Técnico" pressupõe conserto. Em serigrafia quem toca o pedido é o
 * "Responsável" — vem do contrato, como o resto dos rótulos do segmento.
 */
const { labelResponsavel } = useObjetoLabels();

const props = defineProps<{
  status?: OsStatusEnumDataType;
  funcionarioId?: string | number;
  prioridade?: OsPriorityEnumDataType;
  dataPrevisao?: string;
  statusOptions: SelectOption[];
  prioridadeOptions: SelectOption[];
  funcionariosOptions: SelectOption[];
  canSelectTecnico?: boolean;
  isCreateMode?: boolean;
  isLocked?: boolean;
  errors?: Record<string, string | string[] | undefined>;
}>();

const emit = defineEmits<{
  'update:status': [value: OsStatusEnumDataType];
  'update:funcionarioId': [value: string];
  'update:prioridade': [value: OsPriorityEnumDataType];
  'update:dataPrevisao': [value: string];
}>();

const authStore = useAuthStore();

const localStatus = computed({
  get: () => String(props.status || ''),
  set: (val) => emit('update:status', val as OsStatusEnumDataType)
});

const localFuncionarioId = computed({
  get: () => String(props.funcionarioId || ''),
  set: (val) => emit('update:funcionarioId', val)
});

const localPrioridade = computed({
  get: () => String(props.prioridade || ''),
  set: (val) => emit('update:prioridade', val as OsPriorityEnumDataType)
});

const localDataPrevisao = computed({
  get: () => props.dataPrevisao || '',
  set: (val) => emit('update:dataPrevisao', val)
});

// --- Inline select dropdown logic ---

const openDropdown = ref<string | null>(null);
const statusRef = ref<HTMLDivElement | null>(null);
const tecnicoRef = ref<HTMLDivElement | null>(null);
const prioridadeRef = ref<HTMLDivElement | null>(null);

onClickOutside(statusRef, () => { if (openDropdown.value === 'status') openDropdown.value = null; });
onClickOutside(tecnicoRef, () => { if (openDropdown.value === 'tecnico') openDropdown.value = null; });
onClickOutside(prioridadeRef, () => { if (openDropdown.value === 'prioridade') openDropdown.value = null; });

function toggleDropdown(name: string) {
  openDropdown.value = openDropdown.value === name ? null : name;
}

function selectStatus(opt: SelectOption) {
  localStatus.value = String(opt.value);
  openDropdown.value = null;
}

function selectTecnico(opt: SelectOption) {
  localFuncionarioId.value = String(opt.value);
  openDropdown.value = null;
}

function selectPrioridade(opt: SelectOption) {
  localPrioridade.value = String(opt.value);
  openDropdown.value = null;
}

function getSelectedLabel(options: SelectOption[], value: string) {
  return options.find(opt => String(opt.value) === value)?.label || '';
}
</script>

<template>
  <div class="w-full bg-white border border-slate-200 rounded-xl shadow-sm overflow-visible text-sm">
    <div class="grid grid-cols-2 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-slate-100">

      <!-- Situação -->
      <div ref="statusRef" class="relative flex flex-col px-4 py-2 hover:bg-slate-50 transition-colors">
        <span class="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-0.5">Situação</span>
        <button
          type="button"
          :disabled="isLocked"
          class="flex items-center justify-between w-full text-left font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-70"
          :class="isLocked ? '' : 'cursor-pointer'"
          @click="toggleDropdown('status')"
        >
          <span class="truncate">{{ getSelectedLabel(statusOptions, localStatus) || '--' }}</span>
          <LucideIcon v-if="!isLocked" :icon="ChevronDown" size="uxs" class="text-gray-400 shrink-0 ml-1" />
        </button>
        <Transition
          enter-active-class="transition ease-out duration-100"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition ease-in duration-75"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <ul
            v-if="openDropdown === 'status'"
            class="absolute z-50 left-0 top-full mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto py-1"
          >
            <li
              v-for="opt in statusOptions"
              :key="opt.value"
              class="px-3 py-2 text-sm cursor-pointer transition-colors"
              :class="localStatus === String(opt.value) ? 'bg-brand-primary text-white' : 'text-gray-700 hover:bg-gray-100'"
              @click="selectStatus(opt)"
            >
              {{ opt.label }}
            </li>
          </ul>
        </Transition>
      </div>

      <!-- Técnico -->
      <div ref="tecnicoRef" class="relative flex flex-col px-4 py-2 hover:bg-slate-50 transition-colors">
        <span class="text-[10px] font-bold uppercase tracking-wider mb-0.5" :class="errors?.funcionario_id ? 'text-red-500' : 'text-slate-400'">{{ labelResponsavel }}</span>
        <template v-if="canSelectTecnico && !isLocked">
          <button
            type="button"
            class="flex items-center justify-between w-full text-left font-semibold text-slate-700 cursor-pointer"
            @click="toggleDropdown('tecnico')"
          >
            <span class="truncate">{{ getSelectedLabel(funcionariosOptions, localFuncionarioId) || '-- Selecione --' }}</span>
            <LucideIcon :icon="ChevronDown" size="uxs" class="text-gray-400 shrink-0 ml-1" />
          </button>
          <Transition
            enter-active-class="transition ease-out duration-100"
            enter-from-class="opacity-0 scale-95"
            enter-to-class="opacity-100 scale-100"
            leave-active-class="transition ease-in duration-75"
            leave-from-class="opacity-100 scale-100"
            leave-to-class="opacity-0 scale-95"
          >
            <ul
              v-if="openDropdown === 'tecnico'"
              class="absolute z-50 left-0 top-full mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto py-1"
            >
              <li
                v-for="opt in funcionariosOptions"
                :key="opt.value"
                class="px-3 py-2 text-sm cursor-pointer transition-colors"
                :class="localFuncionarioId === String(opt.value) ? 'bg-brand-primary text-white' : 'text-gray-700 hover:bg-gray-100'"
                @click="selectTecnico(opt)"
              >
                {{ opt.label }}
              </li>
            </ul>
          </Transition>
        </template>
        <span v-else class="font-semibold text-slate-700 mt-0.5 truncate">
          {{ getSelectedLabel(funcionariosOptions, localFuncionarioId) || authStore.userData?.nome || '--' }}
        </span>
        <span v-if="errors?.funcionario_id" class="text-[10px] text-red-500 mt-0.5">
          {{ errors.funcionario_id }}
        </span>
      </div>

      <!-- Prioridade -->
      <div ref="prioridadeRef" class="relative flex flex-col px-4 py-2 hover:bg-slate-50 transition-colors">
        <span class="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-0.5">Prioridade</span>
        <button
          type="button"
          :disabled="isLocked"
          class="flex items-center justify-between w-full text-left font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-70"
          :class="isLocked ? '' : 'cursor-pointer'"
          @click="toggleDropdown('prioridade')"
        >
          <span class="truncate">{{ getSelectedLabel(prioridadeOptions, localPrioridade) || '--' }}</span>
          <LucideIcon v-if="!isLocked" :icon="ChevronDown" size="uxs" class="text-gray-400 shrink-0 ml-1" />
        </button>
        <Transition
          enter-active-class="transition ease-out duration-100"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition ease-in duration-75"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <ul
            v-if="openDropdown === 'prioridade'"
            class="absolute z-50 left-0 top-full mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto py-1"
          >
            <li
              v-for="opt in prioridadeOptions"
              :key="opt.value"
              class="px-3 py-2 text-sm cursor-pointer transition-colors"
              :class="localPrioridade === String(opt.value) ? 'bg-brand-primary text-white' : 'text-gray-700 hover:bg-gray-100'"
              @click="selectPrioridade(opt)"
            >
              {{ opt.label }}
            </li>
          </ul>
        </Transition>
      </div>

      <!-- Previsão -->
      <div class="flex flex-col px-4 py-2 hover:bg-slate-50 transition-colors">
        <span class="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-0.5">Previsão</span>
        <BaseDateInput
          v-model="localDataPrevisao"
          :disabled="isLocked"
          input-class="bg-transparent border-none font-semibold text-slate-700 focus:ring-0 outline-none p-0 disabled:cursor-not-allowed disabled:opacity-70"
        />
      </div>

    </div>
  </div>
</template>
