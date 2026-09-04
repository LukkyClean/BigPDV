<script setup lang="ts">
/**
 * @component GrupoDeCampos
 * @description Desenha uma seção do formulário a partir do contrato: cabeçalho
 * + os campos daquele `grupo`, na grade de 2 colunas.
 *
 * Separado de `CampoDinamico` porque o que muda entre segmentos é o LAYOUT (que
 * campos, em que seção, com que largura) — o campo em si é sempre o mesmo. É
 * essa separação que permite reproduzir o desenho de uma tela curada sem
 * programar tela nenhuma.
 *
 * O cabeçalho repete a classe usada em `OSObjetoTab.vue` de propósito: a tela
 * dirigida por contrato tem que parecer parte do sistema, não um formulário
 * genérico colado ao lado.
 */
import CampoDinamico from './CampoDinamico.vue';

import type { SegmentField } from '../segmentDefinition.type';

interface Props {
  /** Cabeçalho da seção. Vazio/nulo desenha os campos sem título. */
  titulo?: string | null;
  campos: SegmentField[];
  /** Valores atuais, indexados por `campo.nome`. */
  valores: Record<string, unknown>;
  /** Erros de validação, indexados por `campo.nome`. */
  erros?: Record<string, string>;
  disabled?: boolean;
}

defineProps<Props>();
const emit = defineEmits<{ 'update:campo': [nome: string, valor: unknown] }>();
</script>

<template>
  <div v-if="campos.length > 0" class="space-y-4">
    <h5
      v-if="titulo"
      class="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase border-b border-slate-100 pb-2"
    >
      {{ titulo }}
    </h5>

    <div class="grid grid-cols-2 gap-3">
      <CampoDinamico
        v-for="campo in campos"
        :key="campo.nome"
        :campo="campo"
        :model-value="valores[campo.nome]"
        :error="erros?.[campo.nome]"
        :disabled="disabled"
        :class="campo.largura === 'inteira' ? 'col-span-2' : ''"
        @update:model-value="emit('update:campo', campo.nome, $event)"
      />
    </div>
  </div>
</template>
