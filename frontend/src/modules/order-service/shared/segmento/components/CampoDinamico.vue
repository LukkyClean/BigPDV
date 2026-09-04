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
import { computed, ref } from 'vue';
import { Plus, X } from 'lucide-vue-next';

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

/**
 * Opções do contrato MAIS o valor já gravado, quando ele não está entre elas.
 *
 * Lista de opções muda com o tempo (a serigrafia trocou as famílias de sacola
 * pelas da tabela do dono). Sem este acréscimo, uma OS gravada com o valor
 * antigo abriria com o select em branco — e o primeiro save apagaria em
 * silêncio o que estava lá, que é o tipo de perda que só aparece na loja.
 */
const opcoes = computed<SelectOption[]>(() => {
  const doContrato = props.campo.opcoes ?? [];
  const salvo = valorTexto.value;

  const legado =
    salvo && !doContrato.includes(salvo)
      ? [{ value: salvo, label: `${salvo} (cadastro anterior)` }]
      : [];

  return [...doContrato.map((opcao) => ({ value: opcao, label: opcao })), ...legado];
});

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

    case 'lista':
      // Não passa por aqui: a lista tem UI própria (campo + chips) e o
      // BaseInput de texto só é desenhado para os tipos de valor único.
      return undefined;

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

// ─── Campo repetível (tipo `lista`) ──────────────────────────────────────────
// O valor é `string[]`. Nasceu da serigrafia, onde uma OS produz sacolas de
// vários tamanhos e o dono trabalha por referência ("20.1", "22", "Bolo") —
// uma linha de texto só não comporta a lista.

/** Tolera valor legado ou sujo: só entra no array o que for texto de verdade. */
const valorLista = computed<string[]>(() =>
  Array.isArray(props.modelValue)
    ? props.modelValue.filter((item): item is string => typeof item === 'string')
    : [],
);

const novaEntrada = ref('');

function emitirLista(itens: string[]) {
  // Lista vazia vira `undefined`: em `dados_adicionais` a ausência da chave é o
  // jeito de dizer "não preenchido", e um `[]` apareceria como seção vazia na
  // via do cliente.
  emit('update:modelValue', itens.length ? itens : undefined);
}

function adicionarItem() {
  const item = novaEntrada.value.trim();
  if (!item) return;

  // Repetir a mesma referência não descreve nada — a lista é o conjunto de
  // tamanhos daquela produção. Comparação sem caixa evita "20.1" e "20.1 ".
  const jaExiste = valorLista.value.some(
    (existente) => existente.toLowerCase() === item.toLowerCase(),
  );
  if (!jaExiste) emitirLista([...valorLista.value, item]);

  novaEntrada.value = '';
}

function removerItem(indice: number) {
  emitirLista(valorLista.value.filter((_, i) => i !== indice));
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

  <div v-else-if="campo.tipo === 'lista'">
    <label class="block select-none text-xs font-medium text-gray-700 mb-1">
      {{ campo.label }}
      <span v-if="campo.obrigatorio" class="text-red-600"> *</span>
    </label>

    <div class="flex gap-2">
      <input
        v-model="novaEntrada"
        type="text"
        :placeholder="`Digite e tecle Enter (ex: 20.1)`"
        :disabled="disabled"
        class="flex-1 px-3 py-2 border rounded-md transition-colors duration-200 outline-none text-sm placeholder:text-gray-400 text-gray-700 border-gray-300 focus:border-brand-primary focus:ring-1 focus:ring-brand-primary disabled:bg-gray-100 disabled:cursor-not-allowed"
        @keydown.enter.prevent="adicionarItem"
      />
      <button
        type="button"
        :disabled="disabled || !novaEntrada.trim()"
        class="px-3 rounded-md border border-brand-primary text-brand-primary hover:bg-brand-primary/5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        @click="adicionarItem"
      >
        <Plus :size="16" />
      </button>
    </div>

    <div v-if="valorLista.length" class="flex flex-wrap gap-1.5 mt-2">
      <span
        v-for="(item, indice) in valorLista"
        :key="`${item}-${indice}`"
        class="inline-flex items-center gap-1 pl-2.5 pr-1 py-1 rounded-full bg-brand-primary/10 text-brand-primary text-xs font-semibold"
      >
        {{ item }}
        <button
          v-if="!disabled"
          type="button"
          class="rounded-full hover:bg-brand-primary/20 p-0.5 transition-colors cursor-pointer"
          :aria-label="`Remover ${item}`"
          @click="removerItem(indice)"
        >
          <X :size="12" />
        </button>
      </span>
    </div>

    <p v-if="error" class="select-none mt-0.5 text-xs text-red-500">{{ error }}</p>
  </div>

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
