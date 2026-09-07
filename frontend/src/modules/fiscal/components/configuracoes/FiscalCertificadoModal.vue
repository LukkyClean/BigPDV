<script setup lang="ts">
import { ref } from 'vue';
import { UploadCloud, File, AlertCircle } from 'lucide-vue-next';
import { api } from '@/api/axios';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';

defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  'update:isOpen': [value: boolean];
  'uploaded': [];
}>();

const file = ref<File | null>(null);
const password = ref('');
const loading = ref(false);
const error = ref('');
const success = ref(false);

function close() {
  emit('update:isOpen', false);
  // Reset state
  setTimeout(() => {
    file.value = null;
    password.value = '';
    error.value = '';
    success.value = false;
  }, 300);
}

function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    file.value = target.files[0];
    error.value = '';
  }
}

async function uploadCertificate() {
  if (!file.value || !password.value) {
    error.value = 'Arquivo e senha são obrigatórios.';
    return;
  }

  loading.value = true;
  error.value = '';
  success.value = false;

  try {
    const formData = new FormData();
    formData.append('file', file.value);
    // O backend recebe `senha` (Form(...)), não `password` — o nome errado
    // devolvia 422 antes mesmo de o arquivo ser lido.
    formData.append('senha', password.value);

    // O baseURL do axios JÁ é .../api/v1: repetir o prefixo aqui gerava
    // .../api/v1/api/v1/fiscal/... e um 404 silencioso.
    await api.post('/fiscal/certificado/upload-focus', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });

    success.value = true;
    emit('uploaded');
    setTimeout(() => {
      close();
    }, 2000);
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Erro ao enviar o certificado. Verifique a senha e o arquivo.';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    title="Upload de Certificado A1"
    size="sm"
    @close="close"
  >
    <div class="space-y-6">
      <div v-if="error" class="p-4 rounded-lg bg-red-50 border border-red-200 flex items-start gap-3">
        <LucideIcon :icon="AlertCircle" class="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
        <p class="text-sm text-red-600">{{ error }}</p>
      </div>

      <div v-if="success" class="p-4 rounded-lg bg-emerald-50 border border-emerald-200 flex items-start gap-3">
        <svg class="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <p class="text-sm text-emerald-700">Certificado enviado com sucesso!</p>
      </div>

      <!-- File Upload Area -->
      <div 
        class="border-2 border-dashed rounded-xl p-8 text-center transition-colors"
        :class="file ? 'border-brand-primary bg-brand-primary-light/10' : 'border-gray-200 hover:border-brand-primary/50 bg-gray-50/50'"
      >
        <input 
          type="file" 
          id="certificado-file" 
          class="hidden" 
          accept=".pfx,.p12" 
          @change="handleFileChange"
        />
        <label for="certificado-file" class="cursor-pointer flex flex-col items-center gap-3">
          <div 
            class="w-12 h-12 rounded-full flex items-center justify-center transition-colors"
            :class="file ? 'bg-brand-primary text-white' : 'bg-gray-100 text-gray-400'"
          >
            <LucideIcon :icon="file ? File : UploadCloud" class="w-6 h-6" />
          </div>
          
          <div v-if="file">
            <p class="text-sm font-medium text-gray-800">{{ file.name }}</p>
            <p class="text-xs text-gray-500 mt-1">{{ (file.size / 1024).toFixed(1) }} KB</p>
          </div>
          <div v-else>
            <p class="text-sm font-medium text-gray-800">Clique para selecionar</p>
            <p class="text-xs text-gray-500 mt-1">Apenas arquivos .pfx ou .p12</p>
          </div>
        </label>
      </div>

      <!-- Password Input -->
      <div>
        <BaseInput 
          v-model="password" 
          label="Senha do Certificado" 
          type="password" 
          placeholder="Digite a senha..." 
          :disabled="loading || success"
        />
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end gap-3 w-full">
        <BaseButton 
          variant="secondary" 
          @click="close"
          :disabled="loading"
        >
          Cancelar
        </BaseButton>
        <BaseButton 
          variant="primary" 
          @click="uploadCertificate"
          :is-loading="loading"
          :disabled="!file || !password || success"
        >
          Enviar Certificado
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
