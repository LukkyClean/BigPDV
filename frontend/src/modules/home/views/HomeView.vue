<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';

import DashboardFuncionario from '../components/dashboard/DashboardFuncionario.vue';
import DashboardMaster from '../components/dashboard/DashboardMaster.vue';
import { useAuthStore } from '@/shared/stores/auth.store';

const authStore = useAuthStore();
const { userData } = storeToRefs(authStore);

// A visão geral da loja é EXCLUSIVA do Master (is_master setado pelo dono).
// Alinha com o backend (get_current_master_user): quem não é master vê o
// dashboard pessoal. Antes o gate incluía cargos por nome ("gerente"/
// "administrador"), o que era frágil e não batia com a trava do servidor.
const isMaster = computed(() => userData.value?.is_master === true);
</script>

<template>
  <DashboardFuncionario v-if="!isMaster" />
  <DashboardMaster v-else />
</template>
