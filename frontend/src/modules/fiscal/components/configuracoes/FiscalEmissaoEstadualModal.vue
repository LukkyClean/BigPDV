<script setup lang="ts">
import { ref, watch } from 'vue';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { useFiscalConfiguracaoMutation } from '../../composables/useFiscalConfiguracaoMutation';
import type { FiscalConfiguracao } from '../../types/fiscal.types';
import { Building, ShieldAlert, CheckCircle2 } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';

const props = defineProps<{
  isOpen: boolean;
  configuracao?: FiscalConfiguracao;
}>();

const emit = defineEmits<{
  'update:isOpen': [value: boolean];
  'saved': [];
}>();

const ambiente = ref(2);
const serieNfe = ref<number | string>(1);
const ultimoNumeroNfe = ref<number | string>(0);
const serieNfce = ref<number | string>(1);
const ultimoNumeroNfce = ref<number | string>(0);
const cscId = ref('');
const cscToken = ref('');

const error = ref('');
const success = ref(false);

const { mutateAsync: salvarConfig, isPending } = useFiscalConfiguracaoMutation();

const ambienteOptions = [
  { value: 2, label: 'Homologação (Ambiente de Testes)' },
  { value: 1, label: 'Produção (Ambiente Oficial SEFAZ)' },
];

watch(
  () => [props.isOpen, props.configuracao],
  () => {
    if (props.isOpen && props.configuracao) {
      ambiente.value = props.configuracao.ambiente ?? 2;
      serieNfe.value = props.configuracao.serie_nfe ?? 1;
      ultimoNumeroNfe.value = props.configuracao.ultimo_numero_nfe ?? 0;
      serieNfce.value = props.configuracao.serie_nfce ?? 1;
      ultimoNumeroNfce.value = props.configuracao.ultimo_numero_nfce ?? 0;
      cscId.value = props.configuracao.csc_id ?? '';
      cscToken.value = props.configuracao.csc_token ?? '';
      error.value = '';
      success.value = false;
    }
  },
  { immediate: true }
);

function close() {
  emit('update:isOpen', false);
}

async function handleSave() {
  error.value = '';
  success.value = false;

  try {
    await salvarConfig({
      ambiente_emissao: Number(ambiente.value),
      serie_nfe: Number(serieNfe.value) || 1,
      ultimo_numero_nfe: Number(ultimoNumeroNfe.value) || 0,
      serie_nfce: Number(serieNfce.value) || 1,
      ultimo_numero_nfce: Number(ultimoNumeroNfce.value) || 0,
      csc_id: cscId.value?.trim() || null,
      csc_token: cscToken.value?.trim() || null,
    } as any);

    success.value = true;
    emit('saved');
    setTimeout(() => {
      close();
    }, 1200);
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Erro ao salvar as configurações fiscais.';
  }
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    title="Configuração de Emissão Estadual"
    subtitle="Configure os parâmetros de emissão da NF-e e NFC-e junto à SEFAZ."
    size="lg"
    @close="close"
  >
    <div class="space-y-6">
      <div v-if="error" class="p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3">
        <LucideIcon :icon="ShieldAlert" class="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
        <p class="text-sm text-red-600 font-medium">{{ error }}</p>
      </div>

      <div v-if="success" class="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-3">
        <LucideIcon :icon="CheckCircle2" class="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
        <p class="text-sm text-emerald-700 font-medium">Configurações salvas com sucesso!</p>
      </div>

      <!-- Ambiente de Emissão -->
      <div class="bg-zinc-50/80 p-5 rounded-xl border border-zinc-200/80 space-y-3">
        <div class="flex items-center gap-2">
          <LucideIcon :icon="Building" class="w-4 h-4 text-brand-primary" />
          <h4 class="text-sm font-bold text-zinc-800">Ambiente de Operação</h4>
        </div>
        <BaseSelect
          v-model="ambiente"
          label="Ambiente SEFAZ"
          :options="ambienteOptions"
          :disabled="isPending || success"
        />
        <p class="text-xs text-zinc-500 leading-relaxed">
          * Em homologação, as notas emitidas não possuem valor fiscal. Altere para Produção apenas quando tudo estiver homologado.
        </p>
      </div>

      <!-- Parâmetros NF-e -->
      <div class="border border-zinc-200/80 rounded-xl p-5 space-y-4">
        <h4 class="text-sm font-bold text-zinc-800 flex items-center justify-between">
          <span>NF-e (Modelo 55)</span>
          <span class="text-xs font-normal text-zinc-500">Nota Fiscal Eletrônica</span>
        </h4>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <BaseInput
            v-model="serieNfe"
            type="number"
            label="Série da NF-e"
            placeholder="Ex: 1"
            :disabled="isPending || success"
          />
          <BaseInput
            v-model="ultimoNumeroNfe"
            type="number"
            label="Último Número Emitido"
            placeholder="Ex: 0"
            :disabled="isPending || success"
          />
        </div>
      </div>

      <!-- Parâmetros NFC-e e CSC -->
      <div class="border border-zinc-200/80 rounded-xl p-5 space-y-4">
        <h4 class="text-sm font-bold text-zinc-800 flex items-center justify-between">
          <span>NFC-e (Modelo 65) & CSC</span>
          <span class="text-xs font-normal text-zinc-500">Nota de Consumidor / Cupom</span>
        </h4>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <BaseInput
            v-model="serieNfce"
            type="number"
            label="Série da NFC-e"
            placeholder="Ex: 1"
            :disabled="isPending || success"
          />
          <BaseInput
            v-model="ultimoNumeroNfce"
            type="number"
            label="Último Número Emitido"
            placeholder="Ex: 0"
            :disabled="isPending || success"
          />
        </div>

        <div class="pt-3 border-t border-zinc-100 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="sm:col-span-1">
            <BaseInput
              v-model="cscId"
              label="ID do Token CSC"
              placeholder="Ex: 000001"
              :disabled="isPending || success"
            />
          </div>
          <div class="sm:col-span-2">
            <BaseInput
              v-model="cscToken"
              label="Código de Segurança (Token CSC)"
              placeholder="Ex: A1B2C3D4E5F6..."
              :disabled="isPending || success"
            />
          </div>
        </div>
        <p class="text-xs text-zinc-500">
          O CSC é obrigatório para a geração do QR Code da NFC-e e deve ser obtido no portal da SEFAZ do seu estado.
        </p>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end gap-3 w-full">
        <BaseButton
          variant="secondary"
          @click="close"
          :disabled="isPending"
        >
          Cancelar
        </BaseButton>
        <BaseButton
          variant="primary"
          @click="handleSave"
          :loading="isPending"
          :disabled="success"
        >
          Salvar Configurações
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>

