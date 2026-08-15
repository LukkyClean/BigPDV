<script setup lang="ts">
/**
 * @view LoginView
 * @description Página de login do sistema Start Big.
 * Apresenta um layout dividido com background decorativo à esquerda
 * e formulário de autenticação à direita.
 */

import { onMounted } from 'vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseCheckbox from '@/shared/components/ui/BaseCheckbox/BaseCheckbox.vue';
import BaseFooter from '@/shared/components/layout/BaseFooter.vue';

import { useLogin } from '../composables/useLogin';

import backgroundImage from '@/shared/assets/images/login/background.png';
import AppLogo from '@/shared/components/AppLogo.vue';

const {
  loginData,
  savedEmail,
  rememberMe,
  errors: loginErrors,
  apiError: loginApiError,
  isLoading: loginIsLoading,
  loginSubmit,
  submitCount: loginSubmitCount,
} = useLogin();

onMounted(() => {
  if (savedEmail.value) {
    loginData.email = savedEmail.value;
  }
});
</script>

<template>
  <div class="h-screen flex overflow-hidden">
    <!-- Lado esquerdo - Background decorativo -->
    <div class="hidden lg:flex lg:w-full relative overflow-hidden select-none">
      <img
        :src="backgroundImage"
        alt="Background decorativo"
        class="absolute inset-0 w-full h-full object-cover"
      />
    </div>

    <!-- Lado direito - Formulário de Login -->
    <div
      class="w-full lg:w-5/10 flex flex-col items-center justify-between px-6 py-8 bg-white drop-shadow-xl shadow-brand-action overflow-y-scroll"
    >
      <div class="w-full max-w-xs flex flex-col items-center flex-1">
        <!-- Logo -->
        <div class="flex justify-center mb-8">
          <AppLogo class="h-20 w-auto" />
        </div>

        <!-- Título -->
        <div class="mb-8 mr-auto">
          <h2 class="text-2xl font-bold text-brand-action">Entrar</h2>
        </div>

        <!-- Formulário de Login -->
        <form @submit.prevent="loginSubmit" class="w-full space-y-1">
          <!-- Erro da API -->
          <div
            v-if="loginApiError"
            class="bg-red-50 border border-red-200 text-red-700 px-3 py-2 mb-4 rounded-lg text-xs"
          >
            {{ loginApiError }}
          </div>

          <div class="flex flex-col gap-5">
            <!-- Campo Email -->
            <BaseInput
              v-model="loginData.email"
              type="email"
              label="Email"
              placeholder="Digite seu email"
              :error="loginSubmitCount > 0 ? loginErrors.email : ''"
            />

            <!-- Campo Senha -->
            <BaseInput
              v-model="loginData.senha"
              type="password"
              label="Senha"
              placeholder="Digite sua senha"
              :error="loginSubmitCount > 0 ? loginErrors.senha : ''"
            />

            <!-- Lembre-se de mim -->
            <BaseCheckbox v-model="rememberMe" label="Lembre-se de mim" />

            <!-- Botão de Login -->
            <div class="pt-2">
              <BaseButton type="submit" size="md" :is-loading="loginIsLoading" class="w-full">
                Entrar
              </BaseButton>
            </div>
          </div>

          <!-- Link Esqueceu a senha -->
          <div class="text-center pt-1">
            <a href="#" class="text-xs text-brand-primary hover:underline"> Esqueceu a senha? </a>
          </div>
        </form>
      </div>

      <!-- Footer -->
      <footer class="mt-2">
        <BaseFooter />
      </footer>
    </div>
  </div>
</template>
