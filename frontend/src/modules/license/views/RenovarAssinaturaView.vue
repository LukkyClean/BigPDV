<script setup lang="ts">
/**
 * @view RenovarAssinaturaView
 * @description A parede que a licença vencida levanta — e a porta ao lado dela.
 *
 * Diferente da `LicenseErrorView`, aqui a pessoa JÁ ESTÁ DENTRO: logou, o
 * sistema reconhece quem ela é, e o que falta é só o pagamento. Por isso esta
 * tela fala de assinatura, não de erro — e por isso o caminho de saída é um
 * botão que cobra, não um link para uma página de planos no navegador.
 *
 * Quem não é master cai aqui do mesmo jeito (o sistema está inativo para todo
 * mundo), mas não vê o botão de pagar: a conta é do dono. Para o funcionário a
 * tela vira um recado — "avise o responsável" —, que é exatamente o que ele
 * pode fazer.
 */
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { openUrl } from '@tauri-apps/plugin-opener';
import { LockKeyhole } from 'lucide-vue-next';

import AppLogo from '@/shared/components/AppLogo.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { useAuthStore } from '@/shared/stores/auth.store';
import { useLicencaStore } from '@/shared/stores/licenca.store';
import { useAppNavigation } from '@/shared/composables/useAppNavigation';
import { verificarLicenca } from '@/shared/services/licenca.service';
import { LINKS } from '@/shared/config/links';

import RenovarAssinaturaModal from '../components/RenovarAssinaturaModal.vue';

const router = useRouter();
const authStore = useAuthStore();
const licencaStore = useLicencaStore();
const { logoutAndRedirect } = useAppNavigation();

const { userData } = storeToRefs(authStore);
const { mensagem } = storeToRefs(licencaStore);

const isMaster = computed(() => userData.value?.is_master === true);
const modalAberto = ref(false);
const conferindo = ref(false);

/**
 * Ao fechar a cobrança, pergunta ao servidor se a licença voltou.
 *
 * É o caminho normal de saída daqui: quem pagou fecha o modal e cai direto no
 * sistema. Também cobre quem pagou por fora (transferência, suporte) e só
 * queria conferir — sem precisar reiniciar o programa.
 */
async function aoFecharCobranca() {
  modalAberto.value = false;
  conferindo.value = true;

  try {
    await verificarLicenca();
    licencaStore.limpar();
    router.replace({ name: 'home' });
  } catch {
    // Continua vencida — a parede permanece, sem alarme extra: a própria tela
    // já está dizendo o que está acontecendo.
  } finally {
    conferindo.value = false;
  }
}

function falarComSuporte() {
  openUrl(LINKS.whatsapp);
}
</script>

<template>
  <div class="h-screen flex flex-col items-center justify-center bg-white px-6">
    <div class="w-full max-w-md flex flex-col items-center text-center">
      <AppLogo class="h-14 w-auto mb-8" />

      <div class="w-12 h-12 rounded-2xl bg-amber-50 flex items-center justify-center mb-5">
        <LockKeyhole :size="22" class="text-amber-500" />
      </div>

      <h1 class="text-2xl font-bold text-zinc-900 mb-2">
        Assinatura expirada
      </h1>

      <p class="text-sm text-zinc-500 mb-1">
        {{ mensagem || 'Sua assinatura expirou.' }}
      </p>
      <p class="text-sm text-zinc-500 mb-8">
        O sistema fica indisponível até a renovação. Seus dados continuam aqui,
        intactos.
      </p>

      <!-- Master: pode resolver agora -->
      <template v-if="isMaster">
        <BaseButton
          variant="primary"
          size="lg"
          class="w-full"
          :disabled="conferindo"
          @click="modalAberto = true"
        >
          {{ conferindo ? 'Conferindo…' : 'Renovar assinatura' }}
        </BaseButton>
      </template>

      <!-- Funcionário: o recado que ele pode agir sobre -->
      <template v-else>
        <div class="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3.5">
          <p class="text-sm text-zinc-600">
            Avise o responsável pela loja para renovar a assinatura.
          </p>
        </div>
      </template>

      <div class="w-full flex gap-2 mt-3">
        <BaseButton variant="ghost" size="md" class="flex-1" @click="falarComSuporte">
          Falar com o suporte
        </BaseButton>
        <BaseButton variant="ghost" size="md" class="flex-1" @click="logoutAndRedirect">
          Sair do sistema
        </BaseButton>
      </div>
    </div>

    <RenovarAssinaturaModal
      :is-open="modalAberto"
      @close="aoFecharCobranca"
    />
  </div>
</template>
