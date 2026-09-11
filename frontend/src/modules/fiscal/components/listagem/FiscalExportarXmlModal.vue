<script setup lang="ts">
/**
 * @component FiscalExportarXmlModal
 * @description "XMLs do período" — o pacote que o contador pede todo dia 5.
 *
 * Um mês por padrão (o anterior, que é o que se fecha), ou um intervalo livre
 * de até um ano. Sai um ZIP com NF-e/NFC-e autorizadas e canceladas,
 * inutilizações e a relação em CSV; o que a emissora não devolver vai listado
 * dentro do próprio pacote, sem derrubar o resto.
 */
import { computed, ref } from 'vue';
import { FolderArchive, Loader2 } from 'lucide-vue-next';
import type { AxiosError } from 'axios';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import BaseDateInput from '@/shared/components/ui/BaseDateInput/BaseDateInput.vue';
import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage } from '@/shared/utils/error.utils';
import { salvarArquivo } from '@/shared/utils/arquivo';
import type { ApiError } from '@/shared/types/axios.types';

import { fiscalService } from '../../services/fiscal.service';

const props = defineProps<{
  isOpen: boolean;
  /** Pré-seleciona o modelo da tela de origem; o operador pode trocar. */
  tipoInicial?: 'NFE' | 'NFCE';
}>();

const emit = defineEmits<{ close: [] }>();

const toast = useToast();

// ── Período ──────────────────────────────────────────────────────────────
const MESES = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];

function ultimoDia(ano: number, mes: number): string {
  const d = new Date(ano, mes, 0); // dia 0 do mês seguinte = último deste
  return `${ano}-${String(mes).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** Os 12 últimos meses, o anterior primeiro. */
const opcoesMes = computed(() => {
  const hoje = new Date();
  const lista: { value: string; label: string }[] = [];
  for (let i = 1; i <= 12; i++) {
    const d = new Date(hoje.getFullYear(), hoje.getMonth() - i + 1, 1);
    const ano = d.getFullYear();
    const mes = d.getMonth() + 1;
    lista.push({
      value: `${ano}-${String(mes).padStart(2, '0')}`,
      label: `${MESES[mes - 1]} de ${ano}`,
    });
  }
  return lista;
});

const modo = ref<'mes' | 'intervalo'>('mes');
const mesEscolhido = ref<string>('');
const dataInicio = ref('');
const dataFim = ref('');
const tipo = ref<'' | 'NFE' | 'NFCE'>(props.tipoInicial ?? '');

// O mês anterior é o padrão porque é o que se fecha; o atual ainda está aberto.
if (opcoesMes.value.length > 1) mesEscolhido.value = opcoesMes.value[1].value;

const periodo = computed<{ inicio: string; fim: string } | null>(() => {
  if (modo.value === 'mes') {
    if (!mesEscolhido.value) return null;
    const [ano, mes] = mesEscolhido.value.split('-').map(Number);
    return { inicio: `${mesEscolhido.value}-01`, fim: ultimoDia(ano, mes) };
  }
  if (!dataInicio.value || !dataFim.value || dataFim.value < dataInicio.value) return null;
  return { inicio: dataInicio.value, fim: dataFim.value };
});

const TIPO_OPTIONS = [
  { value: '', label: 'NF-e e NFC-e' },
  { value: 'NFE', label: 'Só NF-e (modelo 55)' },
  { value: 'NFCE', label: 'Só NFC-e (modelo 65)' },
];

// ── Download ─────────────────────────────────────────────────────────────
const isBaixando = ref(false);

async function baixar() {
  if (!periodo.value || isBaixando.value) return;
  isBaixando.value = true;
  try {
    const r = await fiscalService.exportarXmlPeriodo(
      periodo.value.inicio, periodo.value.fim, tipo.value || undefined,
    );
    if (r.documentos === 0) {
      toast.info('Nenhum documento no período', 'Não há nota autorizada ou cancelada nessas datas.');
      return;
    }
    const caminho = await salvarArquivo(r.nome, r.arquivo);
    const resumo = `${r.baixados} de ${r.documentos} XML${r.documentos === 1 ? '' : 's'}`
      + (r.naoBaixados > 0 ? ` — ${r.naoBaixados} não vieram da emissora (veja nao_baixados.txt)` : '');
    if (r.naoBaixados > 0) {
      toast.warning('Pacote gerado com faltas', resumo + (caminho ? `\nSalvo em ${caminho}` : ''));
    } else {
      toast.success('Pacote de XMLs pronto', resumo + (caminho ? `\nSalvo em ${caminho}` : ''));
    }
    emit('close');
  } catch (err) {
    toast.error('Não foi possível gerar o pacote', getErrorMessage(err as AxiosError<ApiError>));
  } finally {
    isBaixando.value = false;
  }
}
</script>

<template>
  <BaseModal :is-open="isOpen" title="XMLs do período" size="md" @close="emit('close')">
    <div class="space-y-5">
      <p class="text-sm text-zinc-600 leading-relaxed">
        Gera um arquivo <strong>.zip</strong> com o XML de cada nota autorizada ou cancelada
        no período, as inutilizações e uma relação em CSV — o pacote que o contador pede
        no fechamento do mês.
      </p>

      <!-- Modo -->
      <div class="flex items-center gap-2">
        <button
          type="button"
          :class="[
            'flex-1 rounded-lg border px-3 py-2 text-xs font-bold transition-colors cursor-pointer',
            modo === 'mes' ? 'border-brand-primary bg-brand-primary/5 text-brand-primary' : 'border-zinc-200 text-zinc-500 hover:bg-zinc-50',
          ]"
          @click="modo = 'mes'"
        >
          Mês fechado
        </button>
        <button
          type="button"
          :class="[
            'flex-1 rounded-lg border px-3 py-2 text-xs font-bold transition-colors cursor-pointer',
            modo === 'intervalo' ? 'border-brand-primary bg-brand-primary/5 text-brand-primary' : 'border-zinc-200 text-zinc-500 hover:bg-zinc-50',
          ]"
          @click="modo = 'intervalo'"
        >
          Intervalo de datas
        </button>
      </div>

      <BaseSelect
        v-if="modo === 'mes'"
        v-model="mesEscolhido"
        label="Mês"
        :options="opcoesMes"
        data-exportar-mes
      />
      <div v-else class="grid grid-cols-2 gap-3">
        <BaseDateInput v-model="dataInicio" label="De" />
        <BaseDateInput v-model="dataFim" label="Até" />
      </div>

      <BaseSelect v-model="tipo" label="Modelo" :options="TIPO_OPTIONS" />

      <p v-if="modo === 'intervalo' && dataInicio && dataFim && dataFim < dataInicio" class="text-xs text-rose-600">
        A data final é anterior à inicial.
      </p>
    </div>

    <template #footer>
      <div class="flex justify-end gap-3">
        <BaseButton variant="secondary" :disabled="isBaixando" @click="emit('close')">Cancelar</BaseButton>
        <BaseButton variant="primary" :disabled="!periodo || isBaixando" data-exportar-baixar @click="baixar">
          <Loader2 v-if="isBaixando" :size="16" class="mr-1.5 animate-spin" />
          <FolderArchive v-else :size="16" class="mr-1.5" />
          {{ isBaixando ? 'Gerando pacote...' : 'Gerar .zip' }}
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
