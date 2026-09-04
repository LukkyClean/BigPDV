<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { User, Camera } from 'lucide-vue-next';
import { storeToRefs } from 'pinia';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseConfirmModal from '@/shared/components/commons/BaseConfirmModal/BaseConfirmModal.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import CropperImagemModal from '@/shared/components/commons/CropperImagemModal/CropperImagemModal.vue';

import { useAuthStore } from '@/shared/stores/auth.store';
import { useConfirmacao } from '@/shared/composables/useConfirmacao';
import { useAtualizarContaMutation } from '../composables/mutates/useAtualizarContaMutation';
import { useAlterarSenhaMutation } from '../composables/mutates/useAlterarSenhaMutation';
import { useUploadFotoPerfilMutation } from '../composables/mutates/useUploadFotoPerfilMutation';
import { AtualizarContaSchema, AlterarSenhaSchema } from '../schemas/minhaConta.schema';
import { getImageUrl } from '@/shared/utils/print.utils';

const props = defineProps<{ isOpen: boolean }>();
const emit = defineEmits<{ close: [] }>();

const authStore = useAuthStore();
const { userData } = storeToRefs(authStore);
const confirmacao = useConfirmacao();

// =============================================
// Upload de Foto
// =============================================

const fileInputRef = ref<HTMLInputElement | null>(null);
const cropperAberto = ref(false);
const imagemParaCropar = ref('');
const { mutate: uploadFoto, isPending: isUploadando } = useUploadFotoPerfilMutation();

function abrirSeletorFoto() {
  fileInputRef.value?.click();
}

function onFotoSelecionada(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  imagemParaCropar.value = URL.createObjectURL(file);
  cropperAberto.value = true;
  (event.target as HTMLInputElement).value = '';
}

function onCropConfirmado(arquivo: File) {
  cropperAberto.value = false;
  URL.revokeObjectURL(imagemParaCropar.value);
  uploadFoto(arquivo);
}

function onCropCancelado() {
  cropperAberto.value = false;
  URL.revokeObjectURL(imagemParaCropar.value);
}

// =============================================
// Dados da Conta
// =============================================

const nome = ref('');
const email = ref('');
const contaErrors = ref<Record<string, string>>({});

watch(
  userData,
  (user) => {
    if (user) {
      nome.value = user.nome;
      email.value = user.email;
    }
  },
  { immediate: true },
);

const temAlteracoesPendentes = computed(
  () => nome.value !== (userData.value?.nome ?? '') || email.value !== (userData.value?.email ?? ''),
);

const { mutateAsync: atualizarConta, isPending: isAtualizando } = useAtualizarContaMutation();

async function salvarDados() {
  const resultado = AtualizarContaSchema.safeParse({ nome: nome.value, email: email.value });
  if (!resultado.success) {
    const erros: Record<string, string> = {};
    resultado.error.errors.forEach((e) => {
      if (e.path[0]) erros[String(e.path[0])] = e.message;
    });
    contaErrors.value = erros;
    return;
  }
  contaErrors.value = {};
  try {
    await atualizarConta({ nome: nome.value, email: email.value });
    emit('close');
  } catch {
    // erro já tratado pelo onError da mutation
  }
}

async function handleClose() {
  if (!temAlteracoesPendentes.value) {
    emit('close');
    return;
  }

  const ok = await confirmacao.pedirConfirmacao({
    titulo: 'Sair sem salvar?',
    descricao: 'Você tem <strong>alterações não salvas</strong>. Se sair agora, as alterações serão perdidas.',
    confirmLabel: 'Sair sem salvar',
    cancelLabel: 'Continuar editando',
    variant: 'danger',
  });

  if (ok) emit('close');
}

// =============================================
// Alterar Senha
// =============================================

const senhaAtual = ref('');
const novaSenha = ref('');
const confirmarNovaSenha = ref('');
const senhaErrors = ref<Record<string, string>>({});

const { mutate: alterarSenha, isPending: isAlterando } = useAlterarSenhaMutation();

function salvarSenha() {
  const resultado = AlterarSenhaSchema.safeParse({
    senha_atual: senhaAtual.value,
    nova_senha: novaSenha.value,
    confirmar_nova_senha: confirmarNovaSenha.value,
  });
  if (!resultado.success) {
    const erros: Record<string, string> = {};
    resultado.error.errors.forEach((e) => {
      if (e.path[0]) erros[String(e.path[0])] = e.message;
    });
    senhaErrors.value = erros;
    return;
  }
  senhaErrors.value = {};
  alterarSenha(
    { senha_atual: senhaAtual.value, nova_senha: novaSenha.value },
    {
      onSuccess: () => {
        senhaAtual.value = '';
        novaSenha.value = '';
        confirmarNovaSenha.value = '';
      },
    },
  );
}
</script>

<template>
  <BaseModal
    :isOpen="props.isOpen"
    title="Minha Conta"
    subtitle="Gerencie seus dados de acesso ao sistema"
    size="md"
    @close="handleClose"
  >
    <div class="flex flex-col gap-6">

      <!-- Avatar centralizado -->
      <div class="flex flex-col items-center gap-2 pt-1">
        <input
          ref="fileInputRef"
          type="file"
          accept="image/jpeg,image/png"
          class="hidden"
          @change="onFotoSelecionada"
        />

        <div class="relative group cursor-pointer" @click="abrirSeletorFoto">
          <div
            class="w-24 h-24 rounded-full bg-brand-primary flex items-end justify-center overflow-hidden ring-4 ring-white shadow-md"
          >
            <img
              v-if="userData?.url_perfil"
              :src="getImageUrl(userData.url_perfil) ?? ''"
              alt="Foto de perfil"
              class="w-full h-full object-cover"
            />
            <User v-else :size="60" class="text-white" />
          </div>

          <!-- Overlay câmera ao hover -->
          <div
            class="absolute inset-0 rounded-full bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
            :class="{ 'opacity-100': isUploadando }"
          >
            <Camera v-if="!isUploadando" :size="22" class="text-white" />
            <svg
              v-else
              class="animate-spin w-5 h-5 text-white"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
        </div>

        <div class="text-center">
          <p class="text-base font-semibold text-zinc-800">{{ userData?.nome }}</p>
          <p class="text-xs text-zinc-400 mt-0.5">{{ userData?.cargo?.nome }}</p>
          <button
            class="text-xs text-brand-primary hover:underline mt-1 cursor-pointer"
            @click="abrirSeletorFoto"
          >
            Alterar foto
          </button>
        </div>
      </div>

      <div class="border-t border-zinc-100" />

      <!-- Dados da Conta -->
      <div>
        <p class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">
          Dados da Conta
        </p>
        <div class="flex flex-col gap-3">
          <BaseInput
            v-model="nome"
            label="Nome"
            placeholder="Seu nome completo"
            :error="contaErrors.nome"
          />
          <BaseInput
            v-model="email"
            type="email"
            label="E-mail"
            placeholder="seu@email.com"
            :error="contaErrors.email"
          />
          <div class="flex justify-end">
            <BaseButton variant="primary" size="sm" :isLoading="isAtualizando" @click="salvarDados">
              Salvar Dados
            </BaseButton>
          </div>
        </div>
      </div>

      <div class="border-t border-zinc-100" />

      <!-- Alterar Senha -->
      <div>
        <p class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">
          Alterar Senha
        </p>
        <div class="flex flex-col gap-3">
          <BaseInput
            v-model="senhaAtual"
            type="password"
            label="Senha Atual"
            placeholder="••••••••"
            :error="senhaErrors.senha_atual"
          />
          <BaseInput
            v-model="novaSenha"
            type="password"
            label="Nova Senha"
            placeholder="••••••••"
            :error="senhaErrors.nova_senha"
          />
          <BaseInput
            v-model="confirmarNovaSenha"
            type="password"
            label="Confirmar Nova Senha"
            placeholder="••••••••"
            :error="senhaErrors.confirmar_nova_senha"
          />
          <div class="flex justify-end">
            <BaseButton variant="primary" size="sm" :isLoading="isAlterando" @click="salvarSenha">
              Alterar Senha
            </BaseButton>
          </div>
        </div>
      </div>

    </div>
  </BaseModal>

  <BaseConfirmModal
    :is-open="confirmacao.isOpen.value"
    :title="confirmacao.opcoes.value.titulo"
    :description="confirmacao.opcoes.value.descricao"
    :confirm-label="confirmacao.opcoes.value.confirmLabel"
    :cancel-label="confirmacao.opcoes.value.cancelLabel"
    :variant="confirmacao.opcoes.value.variant"
    @confirm="confirmacao.confirmar"
    @close="confirmacao.cancelar"
  />

  <CropperImagemModal
    :is-open="cropperAberto"
    :image-src="imagemParaCropar"
    titulo="Ajustar foto de perfil"
    formato="circulo"
    tipo-saida="image/jpeg"
    nome-arquivo="foto-perfil.jpg"
    label-confirmar="Usar esta foto"
    @confirm="onCropConfirmado"
    @close="onCropCancelado"
  />
</template>
