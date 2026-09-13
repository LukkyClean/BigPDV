<script setup lang="ts">
/**
 * @component BaseAjuda
 * @description O "?" ao lado do rótulo de um campo, com a explicação em
 * linguagem comum.
 *
 * Existe por causa dos campos fiscais: NCM, CSOSN e CFOP não significam nada
 * para quem vende no balcão, e mandar o lojista procurar fora do sistema é
 * como se perde um cadastro. Os formulários de referência do mercado põem um
 * "?" em TODO campo fiscal — é barato e resolve.
 *
 * Abre no hover (mouse) e no clique (toque), e fecha no Esc.
 */

import { ref, onBeforeUnmount } from 'vue';
import { HelpCircle } from 'lucide-vue-next';

interface Props {
  /** O texto da ajuda. Uma frase e um exemplo. */
  texto: string;
  /** Rótulo do campo, usado no aria-label ("Ajuda sobre NCM"). */
  campo?: string;
}

const props = defineProps<Props>();

const aberto = ref(false);
const fixado = ref(false);

function abrir() {
  aberto.value = true;
}

function fechar() {
  if (!fixado.value) aberto.value = false;
}

function alternarFixado() {
  fixado.value = !fixado.value;
  aberto.value = fixado.value;
}

function aoTeclar(evento: KeyboardEvent) {
  if (evento.key === 'Escape') {
    fixado.value = false;
    aberto.value = false;
  }
}

document.addEventListener('keydown', aoTeclar);
onBeforeUnmount(() => document.removeEventListener('keydown', aoTeclar));
</script>

<template>
  <span class="relative inline-flex align-middle">
    <button
      type="button"
      class="text-zinc-400 hover:text-brand-primary focus:text-brand-primary transition-colors cursor-help outline-none"
      :aria-label="campo ? `Ajuda sobre ${campo}` : 'Ajuda'"
      :title="props.texto"
      @mouseenter="abrir"
      @mouseleave="fechar"
      @focus="abrir"
      @blur="fechar"
      @click.stop.prevent="alternarFixado"
    >
      <HelpCircle :size="13" />
    </button>

    <Transition
      enter-active-class="transition ease-out duration-150"
      enter-from-class="opacity-0 translate-y-1"
      leave-active-class="transition ease-in duration-100"
      leave-to-class="opacity-0"
    >
      <span
        v-if="aberto"
        role="tooltip"
        class="absolute left-0 top-full z-50 mt-1.5 w-64 max-w-[min(16rem,70vw)] rounded-lg bg-zinc-800 px-3 py-2 text-[11px] font-normal leading-relaxed text-white shadow-lg"
      >
        {{ texto }}
      </span>
    </Transition>
  </span>
</template>
