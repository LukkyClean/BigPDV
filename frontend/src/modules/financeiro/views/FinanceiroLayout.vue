<script setup lang="ts">
/**
 * Casca do módulo financeiro.
 *
 * Segura o que é comum às telas de dentro e nada além disso. Não decide acesso:
 * módulo e permissão já foram conferidos no `beforeEach` do router (que manda
 * para a home quem não tem) e no backend, que recusa a rota com 403. Repetir a
 * checagem aqui só criaria um terceiro lugar para a regra divergir.
 *
 * O seletor de período entra quando a primeira tela que depende dele existir —
 * hoje nenhuma existe, e um filtro que não filtra nada é ruído.
 */
</script>

<template>
  <div class="h-full flex flex-col p-4 md:p-6 lg:p-8 overflow-y-auto">
    <router-view />
  </div>
</template>
