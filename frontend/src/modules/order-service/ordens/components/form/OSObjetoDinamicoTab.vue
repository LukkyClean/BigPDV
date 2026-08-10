<script setup lang="ts">
/**
 * @component OSObjetoDinamicoTab
 * @description Aba de objeto desenhada 100% a partir do contrato do segmento.
 *
 * Existe AO LADO da `OSObjetoTab.vue`, não no lugar dela. A tab curada atende
 * informática e oficina, que estão em produção; esta atende segmentos que
 * declaram `tipos` de trabalho no registry. Segmento que não declara tipos
 * nunca chega aqui — é o que garante que este arquivo não pode quebrar as duas
 * lojas que já rodam.
 *
 * O que ela sabe fazer, e a tab curada não: montar o formulário a partir de
 * campos que ninguém programou. É o que faz um segmento novo custar declaração
 * em vez de Vue.
 */
import { computed } from 'vue';

import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import GrupoDeCampos from '@/modules/order-service/shared/segmento/components/GrupoDeCampos.vue';
import { useTiposDeTrabalho } from '@/modules/order-service/shared/segmento/useTiposDeTrabalho';
import type { SegmentField } from '@/modules/order-service/shared/segmento/segmentDefinition.type';

import type { ObjetoFormData } from '../../composables/modal/useOSFormAdapter';

/** Chave da OS em que o tipo de trabalho escolhido fica gravado. */
const CHAVE_TIPO = 'tipo_trabalho';

interface Props {
  modelValue: ObjetoFormData;
  /** dados_adicionais do objeto. */
  objetoDados?: Record<string, unknown>;
  /** dados_adicionais da OS. */
  osDados?: Record<string, unknown>;
  errors?: Record<string, string | undefined>;
  isLocked?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  objetoDados: () => ({}),
  osDados: () => ({}),
  errors: () => ({}),
  isLocked: false,
});

const emit = defineEmits<{
  'update:modelValue': [value: ObjetoFormData];
  'update:objetoDados': [value: Record<string, unknown>];
  'update:osDados': [value: Record<string, unknown>];
}>();

const { opcoes, tipoPadrao, gruposDoTipo } = useTiposDeTrabalho();

/**
 * O tipo escolhido mora em `dados_adicionais` da OS — não precisa de coluna
 * nova, e acompanha a OS para a impressão e para a reabertura.
 */
const tipoAtual = computed<string>(
  () => (props.osDados[CHAVE_TIPO] as string) ?? tipoPadrao.value ?? '',
);

const grupos = computed(() => gruposDoTipo(tipoAtual.value));

function trocarTipo(valor: string) {
  // Só o tipo muda. Os valores já digitados ficam onde estão: trocar de tipo
  // por engano e perder o que foi preenchido seria pior que um campo órfão no
  // JSON, que ninguém lê porque não está no contrato do tipo atual.
  emit('update:osDados', { ...props.osDados, [CHAVE_TIPO]: valor });
}

/** Mesma resolução de erro da tab curada (`objeto.campo` ou `campo`). */
function erroDoCampo(nome: string): string | undefined {
  return props.errors?.[`objeto.${nome}`] ?? props.errors?.[nome];
}

const erros = computed<Record<string, string>>(() => {
  const mapa: Record<string, string> = {};
  for (const grupo of grupos.value) {
    for (const campo of grupo.campos) {
      const erro = erroDoCampo(campo.nome);
      if (erro) mapa[campo.nome] = erro;
    }
  }
  return mapa;
});

/**
 * Onde cada campo mora, decidido pelo contrato e não por `if segmento`.
 *
 * `origem: 'coluna'` aponta para uma coluna real de objetos_servico, e o nome
 * do campo pode diferir do nome da coluna (a placa da oficina é `numero_serie`).
 * Errar isso gravaria o valor num JSON que ninguém lê, e o objeto sumiria da
 * busca — em silêncio.
 */
function chaveDeColuna(campo: SegmentField): keyof ObjetoFormData {
  return (campo.coluna ?? campo.nome) as keyof ObjetoFormData;
}

function valoresDoGrupo(campos: SegmentField[]): Record<string, unknown> {
  const valores: Record<string, unknown> = {};
  for (const campo of campos) {
    if (campo.origem === 'coluna') {
      valores[campo.nome] = props.modelValue[chaveDeColuna(campo)];
    } else if (campo.escopo === 'os') {
      valores[campo.nome] = props.osDados[campo.nome];
    } else {
      valores[campo.nome] = props.objetoDados[campo.nome];
    }
  }
  return valores;
}

function gravarCampo(campos: SegmentField[], nome: string, valor: unknown) {
  const campo = campos.find((c) => c.nome === nome);
  if (!campo) return;

  if (campo.origem === 'coluna') {
    // Colunas de objetos_servico são NOT NULL: vazio é string vazia, nunca
    // `undefined`, senão o payload chega sem a chave e o backend recusa.
    emit('update:modelValue', {
      ...props.modelValue,
      [chaveDeColuna(campo)]: valor === undefined || valor === null ? '' : String(valor),
    });
    return;
  }

  if (campo.escopo === 'os') {
    emit('update:osDados', { ...props.osDados, [campo.nome]: valor });
  } else {
    emit('update:objetoDados', { ...props.objetoDados, [campo.nome]: valor });
  }
}
</script>

<template>
  <div class="space-y-5 animate-fadeIn">
    <!-- Seletor do tipo de trabalho. Some sozinho quando o segmento declara um
         tipo só — perguntar "camisa ou camisa?" seria ruído. -->
    <BaseSelect
      v-if="opcoes.length > 1"
      :model-value="tipoAtual"
      label="Tipo de trabalho"
      :options="opcoes"
      required
      :disabled="isLocked"
      @update:model-value="trocarTipo(String($event))"
    />

    <GrupoDeCampos
      v-for="(grupo, indice) in grupos"
      :key="`${tipoAtual}-${grupo.titulo ?? indice}`"
      :titulo="grupo.titulo"
      :campos="grupo.campos"
      :valores="valoresDoGrupo(grupo.campos)"
      :erros="erros"
      :disabled="isLocked"
      @update:campo="(nome, valor) => gravarCampo(grupo.campos, nome, valor)"
    />
  </div>
</template>
