<script setup lang="ts">
/**
 * @view LicenseErrorView
 * @description Tela de bloqueio exibida quando a licença é inválida.
 * Mostra título contextual baseado no código de erro e permite tentar novamente.
 */

import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { openUrl } from '@tauri-apps/plugin-opener';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseFooter from '@/shared/components/layout/BaseFooter.vue';
import { verificarLicenca } from '@/shared/services/licenca.service';
import { LINKS } from '@/shared/config/links';

import AppLogo from '@/shared/components/AppLogo.vue';

const props = defineProps<{
  codigo: string;
  mensagem: string;
}>();

const router = useRouter();
const isRetrying = ref(false);
const retryError = ref('');

const titulo = computed(() => {
  switch (props.codigo) {
    case 'CLONAGEM_DETECTADA':
      return 'Licença Inválida';
    case 'REQUISITA_CONEXAO_INTERNET':
      return 'Conexão com Internet Necessária';
    case 'LICENCA_EXPIRADA':
      return 'Licença Expirada';
    case 'LICENCA_NAO_ENCONTRADA':
      return 'Licença Não Encontrada';
    case 'LICENCA_RECUSADA':
      return 'Licença Recusada';
    case 'LICENCA_BLOQUEADA':
      return 'Licença Bloqueada';
    default:
      return 'Erro de Licença';
  }
});

const icone = computed(() => {
  switch (props.codigo) {
    case 'CLONAGEM_DETECTADA':
      return '🔒';
    case 'REQUISITA_CONEXAO_INTERNET':
      return '🌐';
    case 'LICENCA_EXPIRADA':
      return '⏰';
    case 'LICENCA_NAO_ENCONTRADA':
      return '🔍';
    case 'LICENCA_BLOQUEADA':
      return '🚫';
    default:
      return '⚠️';
  }
});

/**
 * Códigos em que o caminho de saída é comercial (pagar), não técnico.
 *
 * Os demais (clonagem, falta de internet, bloqueio administrativo) ficam de
 * fora de propósito: mandar para pagamento quem só está sem conexão, ou quem
 * já pagou e foi bloqueado, joga a pessoa no lugar errado.
 *
 * Todos vão para a página de planos por enquanto — ela já está no ar e resolve
 * tanto quem nunca assinou quanto quem precisa renovar.
 *
 * TODO(renovacao): esta tela NÃO consegue separar trial de licença paga — o
 * erro 403 carrega só `codigo` e `mensagem`, e o flag `trial` existe apenas no
 * GET /licenca/status (e ainda não é preenchido pela API StartBig). Quando der
 * para distinguir, o cliente pagante deve pular a tabela de planos e ir direto
 * ao link de pagamento (Stripe) gerado na hora.
 */
const CODIGOS_COMERCIAIS = ['LICENCA_EXPIRADA', 'LICENCA_NAO_ENCONTRADA'];

const casoComercial = computed(() => CODIGOS_COMERCIAIS.includes(props.codigo));

function verPlanos() {
  openUrl(LINKS.planos);
}

function falarComSuporte() {
  openUrl(LINKS.whatsapp);
}

async function tentarNovamente() {
  isRetrying.value = true;
  retryError.value = '';

  try {
    await verificarLicenca();
    // Licença válida — redirecionar para login
    router.push({ name: 'auth.user' });
  } catch {
    retryError.value = 'A verificação falhou novamente. Verifique sua conexão e tente mais tarde.';
  } finally {
    isRetrying.value = false;
  }
}
</script>

<template>
  <div class="h-screen flex flex-col items-center justify-between bg-white px-6 py-8">
    <div class="flex flex-col items-center flex-1 justify-center max-w-md w-full">
      <!-- Logo -->
      <div class="flex justify-center mb-6">
        <AppLogo class="h-16 w-auto" />
      </div>

      <!-- Ícone e Título -->
      <div class="text-center mb-6">
        <span class="text-5xl mb-4 block">{{ icone }}</span>
        <h1 class="text-2xl font-bold text-gray-800 mb-2">{{ titulo }}</h1>
      </div>

      <!-- Mensagem de Erro -->
      <div
        class="w-full bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm text-center mb-6"
      >
        {{ mensagem || 'Ocorreu um erro na verificação da licença.' }}
      </div>

      <!-- Erro do retry -->
      <div
        v-if="retryError"
        class="w-full bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-lg text-sm text-center mb-4"
      >
        {{ retryError }}
      </div>

      <!-- Ação principal quando o que falta é pagar -->
      <BaseButton
        v-if="casoComercial"
        type="button"
        variant="primary"
        class="w-full mb-2"
        @click="verPlanos"
      >
        Ver planos e renovar
      </BaseButton>

      <!-- Revalidação.
           Esta tela NÃO revalida sozinha: a rota tem skipLicenseCheck, senão
           o guard do router a recarregaria em laço. Para quem acabou de pagar
           este botão é a ÚNICA saída — esperar não adianta —, então o rótulo
           precisa dizer isso com todas as letras. -->
      <BaseButton
        type="button"
        :variant="casoComercial ? 'secondary' : 'primary'"
        class="w-full"
        :disabled="isRetrying"
        @click="tentarNovamente"
      >
        {{ isRetrying ? 'Verificando...' : (casoComercial ? 'Já paguei — liberar acesso' : 'Tentar Novamente') }}
      </BaseButton>

      <!-- Orientação -->
      <p v-if="casoComercial" class="text-xs text-gray-500 text-center mt-4">
        Depois de pagar, a liberação é automática: basta estar conectado à
        internet e clicar em <strong>Já paguei — liberar acesso</strong>.
      </p>

      <button
        type="button"
        class="text-xs text-gray-400 hover:text-gray-600 underline text-center mt-4 cursor-pointer"
        @click="falarComSuporte"
      >
        {{ casoComercial ? 'Precisa de ajuda? Falar com o suporte' : 'Se o problema persistir, fale com o suporte técnico' }}
      </button>
    </div>

    <BaseFooter />
  </div>
</template>
