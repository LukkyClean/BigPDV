<script setup lang="ts">
/**
 * Marcador das telas do financeiro que ainda não foram construídas.
 *
 * Existe para que o menu inteiro seja navegável desde a primeira onda: o item
 * aparece, clica e leva a algum lugar. A alternativa — declarar só os itens
 * prontos — faria o menu mudar de tamanho a cada entrega, e o usuário reaprende
 * onde as coisas estão toda vez.
 *
 * Cada onda substitui um destes por uma tela de verdade.
 */
import { Hammer } from 'lucide-vue-next';

defineProps<{ titulo: string; descricao: string }>();
</script>

<template>
  <div class="flex-1 flex items-start justify-center pt-10">
    <div class="w-full max-w-md text-center">
      <div
        class="w-14 h-14 mx-auto rounded-2xl bg-zinc-100 flex items-center justify-center mb-4"
      >
        <Hammer :size="24" class="text-zinc-400" />
      </div>
      <h2 class="text-lg font-bold text-zinc-800">{{ titulo }}</h2>
      <p class="text-sm text-zinc-500 mt-2 leading-relaxed">{{ descricao }}</p>
    </div>
  </div>
</template>
