<script setup lang="ts">
/**
 * @component NcmBuscaInput
 * @description O campo de NCM: digita "caneta", escolhe 9608.10.00.
 *
 * POR QUE NÃO É UM BaseSelect
 * ---------------------------
 * Porque o BaseSelect FILTRA LOCALMENTE a lista que recebe
 * (`option.label.toLowerCase().includes(query)`), e aqui quem filtra é o
 * servidor — com acentos, palavras soltas e tolerância a erro de digitação.
 * O refiltro local descartaria justamente o que o motor achou: procurar
 * "pneumaticos" sem acento devolveria resultado do servidor e a tela jogaria
 * fora, porque a descrição gravada tem "Pneumáticos".
 *
 * Essa armadilha já mordeu este projeto antes, na busca de produtos.
 *
 * O CAMPO CONTINUA ACEITANDO DIGITAÇÃO DIRETA
 * -------------------------------------------
 * Quem já sabe o código digita os 8 dígitos e segue. A busca é ajuda, não
 * obrigação — e se a tabela não tiver sido carregada (instalação antiga, ou
 * arquivo ausente no pacote), o campo se comporta como sempre se comportou.
 */

import { ref, computed, watch, onBeforeUnmount } from 'vue';
import { Search, Check } from 'lucide-vue-next';

import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import { fiscalService } from '../../services/fiscal.service';
import type { NcmItem } from '../../types/fiscal.types';

const props = defineProps<{
  modelValue: string;
  label?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  ajuda?: string;
}>();

const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>();

const termo = ref('');
const resultados = ref<NcmItem[]>([]);
const aberto = ref(false);
const buscando = ref(false);
/** A descrição do código já escolhido, para o lojista conferir sem reabrir. */
const descricaoAtual = ref('');

let timer: ReturnType<typeof setTimeout> | undefined;

/**
 * Espera a digitação parar antes de perguntar ao servidor.
 *
 * 300ms porque a busca custa de 25ms (caso comum) a ~500ms (quando nada casa
 * na descrição própria e é preciso varrer a hierarquia). Sem a espera, digitar
 * "caneta" dispararia seis consultas.
 */
function agendarBusca(valor: string) {
  if (timer) clearTimeout(timer);
  if (valor.trim().length < 2) {
    resultados.value = [];
    aberto.value = false;
    return;
  }
  timer = setTimeout(() => buscar(valor), 300);
}

async function buscar(valor: string) {
  buscando.value = true;
  try {
    const { resultados: achados } = await fiscalService.buscarNcm(valor.trim());
    resultados.value = achados;
    aberto.value = achados.length > 0;
  } catch {
    // Sem tabela carregada ou sem módulo fiscal: o campo volta a ser digitação
    // livre, que é como funcionou até aqui. Não vale um erro na tela.
    resultados.value = [];
    aberto.value = false;
  } finally {
    buscando.value = false;
  }
}

onBeforeUnmount(() => timer && clearTimeout(timer));

/** O que o usuário digitou: código direto ou termo de busca. */
function aoDigitar(valor: string) {
  termo.value = valor;
  const digitos = valor.replace(/\D/g, '');

  // Oito dígitos é o código completo — grava e não oferece lista.
  if (digitos.length === 8 && digitos === valor.replace(/[.\s]/g, '')) {
    emit('update:modelValue', digitos);
    aberto.value = false;
    return;
  }

  emit('update:modelValue', digitos.length === 8 ? digitos : '');
  agendarBusca(valor);
}

function escolher(item: NcmItem) {
  emit('update:modelValue', item.codigo);
  descricaoAtual.value = item.descricao;
  termo.value = item.codigo;
  aberto.value = false;
}

// Código que chega de fora (edição de produto) aparece no campo.
watch(
  () => props.modelValue,
  (codigo) => {
    if (codigo && codigo !== termo.value.replace(/\D/g, '')) {
      termo.value = codigo;
    }
  },
  { immediate: true },
);

const rotulo = computed(() => props.label ?? 'NCM');
</script>

<template>
  <div class="relative">
    <BaseInput
      :model-value="termo"
      :label="rotulo"
      placeholder="Digite o código ou o que o produto é (ex: caneta)"
      :required="required"
      :disabled="disabled"
      :error="error"
      :ajuda="ajuda"
      @update:model-value="aoDigitar"
      @focus="resultados.length && (aberto = true)"
    />

    <!-- A descrição do escolhido, para conferir sem reabrir a lista -->
    <p v-if="descricaoAtual && !aberto" class="mt-1 text-xs text-emerald-600 flex items-center gap-1">
      <Check :size="12" class="shrink-0" />
      {{ descricaoAtual }}
    </p>

    <p v-else-if="buscando" class="mt-1 text-xs text-zinc-400 flex items-center gap-1">
      <Search :size="12" class="shrink-0" /> procurando…
    </p>

    <!-- Resultados. Sem refiltro local: quem filtrou foi o servidor. -->
    <ul
      v-if="aberto"
      class="absolute z-50 mt-1 w-full max-h-64 overflow-auto rounded-xl border border-zinc-200 bg-white shadow-lg"
    >
      <li
        v-for="item in resultados"
        :key="item.codigo"
        class="cursor-pointer px-3 py-2 hover:bg-brand-primary-light transition-colors"
        @mousedown.prevent="escolher(item)"
      >
        <p class="text-sm font-medium text-zinc-800">
          {{ item.codigo }} · {{ item.descricao }}
        </p>
        <p v-if="item.descricao_completa" class="text-[11px] text-zinc-400 truncate">
          {{ item.descricao_completa }}
        </p>
      </li>
    </ul>
  </div>
</template>
