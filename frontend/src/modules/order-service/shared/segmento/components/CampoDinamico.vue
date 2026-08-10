<script setup lang="ts">
/**
 * @component CampoDinamico
 * @description Desenha UM campo a partir do metadado do contrato de segmento.
 *
 * É o componente que torna a regra do projeto verdadeira: *segmento novo só
 * acrescenta declaração no registry*. Enquanto a tela souber desenhar um campo
 * a partir de `{ nome, label, tipo, opcoes }`, acrescentar um segmento deixa de
 * exigir Vue — e por isso deixa de poder quebrar os segmentos que já rodam em
 * produção.
 *
 * O `switch` de `normalizar()` é EXAUSTIVO sobre `SegmentFieldType`: se alguém
 * acrescentar um tipo de campo no contrato e esquecer de desenhá-lo aqui, o
 * `vue-tsc` não compila. É a metade de frontend do guard que
 * `test/core/test_registry_segmentos.py` faz no backend.
 */
import { computed } from 'vue';

import BaseCheckbox from '@/shared/components/ui/BaseCheckbox/BaseCheckbox.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseSelect, { type SelectOption } from '@/shared/components/ui/BaseSelect/BaseSelect.vue';

import type { SegmentField, SegmentFieldType } from '../segmentDefinition.type';

interface Props {
  campo: SegmentField;
  /** Valor atual — vem do JSON de `dados_adicionais`, então é `unknown`. */
  modelValue: unknown;
  error?: string;
  disabled?: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{ 'update:modelValue': [unknown] }>();

/**
 * Texto puro do valor para os inputs. `null`/`undefined` viram string vazia —
 * um input com "undefined" escrito dentro é o tipo de coisa que chega até a
 * loja.
 */
const valorTexto = computed(() =>
  props.modelValue === null || props.modelValue === undefined ? '' : String(props.modelValue),
);

const valorBooleano = computed(() => props.modelValue === true);

const opcoes = computed<SelectOption[]>(() =>
  (props.campo.opcoes ?? []).map((opcao) => ({ value: opcao, label: opcao })),
);

/**
 * Teclado sugerido no celular. Nunca `type="number"`: ele só aceita o separador
 * decimal do locale do navegador, e num campo em português a vírgula some.
 */
const inputmode = computed<'text' | 'decimal' | 'numeric'>(() => {
  if (props.campo.tipo === 'numero') return 'decimal';
  if (props.campo.tipo === 'inteiro') return 'numeric';
  return 'text';
});

/**
 * Converte o texto digitado para o tipo que o contrato declarou.
 *
 * Campo vazio vira `undefined`, e não `0` nem `''`: em `dados_adicionais` a
 * ausência da chave é o jeito de dizer "não preenchido", e um zero fantasma
 * apareceria impresso na via do cliente.
 */
function normalizar(tipo: SegmentFieldType, bruto: string): unknown {
  switch (tipo) {
    case 'texto':
    case 'opcao':
      return bruto === '' ? undefined : bruto;

    case 'inteiro': {
      const digitos = bruto.replace(/\D/g, '');
      return digitos === '' ? undefined : Number(digitos);
    }

    case 'numero': {
      const limpo = bruto.replace(/[^\d,.-]/g, '').replace(',', '.');
      const numero = Number(limpo);
      return limpo === '' || Number.isNaN(numero) ? undefined : numero;
    }

    case 'booleano':
      return bruto === 'true';

    default: {
      // Exaustividade: acrescentar um tipo em SegmentFieldType sem tratá-lo
      // aqui quebra o build, em vez de virar campo mudo na tela da loja.
      const _exaustivo: never = tipo;
      return _exaustivo;
    }
  }
}

function aoDigitar(bruto: string) {
  emit('update:modelValue', normalizar(props.campo.tipo, bruto));
}
</script>

<template>
  <BaseSelect
    v-if="campo.tipo === 'opcao'"
    :model-value="valorTexto"
    :label="campo.label"
    :options="opcoes"
    :required="campo.obrigatorio"
    :error="error"
    :disabled="disabled"
    @update:model-value="emit('update:modelValue', $event === '' ? undefined : $event)"
  />

  <BaseCheckbox
    v-else-if="campo.tipo === 'booleano'"
    :model-value="valorBooleano"
    :label="campo.label"
    :disabled="disabled"
    @update:model-value="emit('update:modelValue', $event)"
  />

  <BaseInput
    v-else
    :model-value="valorTexto"
    :label="campo.label"
    :placeholder="campo.label"
    :required="campo.obrigatorio"
    :error="error"
    :disabled="disabled"
    :inputmode="inputmode"
    @update:model-value="aoDigitar"
  />
</template>
