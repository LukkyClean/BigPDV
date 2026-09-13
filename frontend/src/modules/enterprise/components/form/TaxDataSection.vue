<script setup lang="ts">
/**
 * @component TaxDataSection
 * @description Seção de dados fiscais (IE, IM, Regime Tributário)
 * Refatorado para usar inject pattern
 */

import { Landmark } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { SECTION_LABELS, REGIME_TRIBUTARIO_OPTIONS, INDICADOR_IE_OPTIONS, NATUREZA_JURIDICA_OPTIONS, TIPO_ATIVIDADE_OPTIONS } from '../../constants/empresa.constants';
import { useEmpresaForm } from '../../composables/useEmpresaFormProvider';

// =============================================
// Props
// =============================================

interface Props {
  disabled?: boolean;
}

withDefaults(defineProps<Props>(), {
  disabled: false,
});

// =============================================
// Inject Context
// =============================================

const {
  inscricao_estadual,
  inscricao_municipal,
  regime_tributario,
  indicador_ie,
  natureza_juridica,
  tipo_atividade,
  errors,
  submitCount,
} = useEmpresaForm();
</script>

<template>
  <section class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <div
        class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary"
      >
        <LucideIcon :icon="Landmark"/>
      </div>
      <h3 class="text-lg font-semibold text-zinc-800">{{ SECTION_LABELS.dadosFiscais }}</h3>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Inscrição Estadual -->
      <!-- "Inscrição Estadual" e "Indicador de IE" sao campos DIFERENTES com
           nomes quase iguais. Quem nao e contador preenche um achando que
           preencheu o outro, e a pendencia continua aparecendo sem explicacao.
           A linha de ajuda existe para desfazer essa confusao no lugar onde ela
           acontece. -->
      <div>
        <BaseInput
          v-model="inscricao_estadual"
          label="Inscrição Estadual (IE)"
          type="text"
          placeholder="Ex: Isento"
          :disabled="disabled"
          :error="submitCount > 0 ? errors.inscricao_estadual : ''"
        />
        <p class="text-xs text-zinc-500 mt-1.5">
          O número da inscrição na Secretaria da Fazenda do seu estado. Não confundir
          com o "Indicador de IE" abaixo.
        </p>
      </div>

      <!-- Inscrição Municipal -->
      <BaseInput
        v-model="inscricao_municipal"
        label="Inscrição Municipal (IM)"
        type="text"
        :disabled="disabled"
        :error="submitCount > 0 ? errors.inscricao_municipal : ''"
      />

      <!-- Regime Tributário -->
      <div class="md:col-span-2">
        <BaseSelect
          v-model="regime_tributario"
          label="Regime Tributário"
          :options="REGIME_TRIBUTARIO_OPTIONS"
          placeholder="Selecione o regime..."
          :disabled="disabled"
          :error="submitCount > 0 ? errors.regime_tributario : ''"
        />
      </div>

      <!-- Indicador de IE -->
      <div>
        <BaseSelect
          v-model="indicador_ie"
          label="Indicador de IE"
          :options="INDICADOR_IE_OPTIONS"
          placeholder="Selecione..."
          :disabled="disabled"
        />
        <!--
          O texto dizia "Diz à SEFAZ a sua situação perante o ICMS", e isso é
          falso: no layout da NF-e o indicador de IE existe só para o
          DESTINATÁRIO. No emitente vão a Inscrição Estadual e o CRT. Este
          campo é a declaração da loja sobre si mesma, usada pelo sistema para
          conferir o cadastro antes de emitir.
        -->
        <p class="text-xs text-zinc-500 mt-1.5">
          Sua situação perante o ICMS:
          <strong>1</strong> se você tem Inscrição Estadual,
          <strong>2</strong> se é isento e
          <strong>9</strong> se não é contribuinte.
          Tem IE e vende mercadoria? Então é <strong>1</strong> — o sistema avisa se
          os dois se contradisserem.
        </p>
      </div>

      <!-- Natureza Jurídica -->
      <BaseSelect
        v-model="natureza_juridica"
        label="Natureza Jurídica"
        :options="NATUREZA_JURIDICA_OPTIONS"
        placeholder="Selecione..."
        :disabled="disabled"
      />

      <!-- Tipo de Atividade -->
      <div class="md:col-span-2">
        <BaseSelect
          v-model="tipo_atividade"
          label="Tipo de Atividade"
          :options="TIPO_ATIVIDADE_OPTIONS"
          placeholder="Selecione..."
          :disabled="disabled"
        />
      </div>
    </div>
  </section>
</template>
