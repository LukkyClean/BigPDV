<script setup lang="ts">
/**
 * @component CertificadoSection
 * @description Seção de certificado digital do formulário de empresa
 *
 * IMPORTANTE - Segurança:
 * - A senha do certificado A1 é usada apenas para validação no momento do upload
 * - A senha NÃO é persistida no banco de dados
 * - Usa uma ref local para a senha (não faz parte do form state)
 */

import { ref, computed, watch } from 'vue';
import { Shield, Upload, Key, CheckCircle, AlertCircle, RefreshCw } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { useToast } from '@/shared/composables/useToast';
import { SECTION_LABELS, UPLOAD_CONFIG } from '../../constants/empresa.constants';
import { useEmpresaForm } from '../../composables/useEmpresaFormProvider';
import { useVincularCertificadoWindowsMutation } from '../../composables/useEmpresaQuery';
import type { FiscalSettings } from '../../types/empresa.types';

// =============================================
// Props
// =============================================

interface Props {
  disabled?: boolean;
}

withDefaults(defineProps<Props>(), {
  disabled: false,
});

// =============================================
// Inject Context
// =============================================

const {
  fiscal_settings,
  windowsCertificates,
  isUploadingCert,
  isLoadingCertificates,
  handleCertUpload,
  refetchWindowsCerts,
} = useEmpresaForm();

// Mutation para vincular certificado Windows
const vincularWindowsMutation = useVincularCertificadoWindowsMutation();
const toast = useToast();

// =============================================
// Refs
// =============================================

const certInput = ref<HTMLInputElement | null>(null);

/**
 * Senha do certificado A1 - ref LOCAL (não persiste no form state)
 * Usada apenas no momento do upload para validação
 */
const senhaLocal = ref('');

// =============================================
// Computed
// =============================================

const tipoCertificado = computed({
  get: () => fiscal_settings.value.tipo_certificado || 'ARQUIVO',
  set: (value) => updateFiscalSetting('tipo_certificado', value),
});

const isArquivo = computed(() => tipoCertificado.value === 'ARQUIVO');

const hasCertificadoPath = computed(() => Boolean(fiscal_settings.value.certificado_digital_path));

const hasCertificadoWindows = computed(() => Boolean(fiscal_settings.value.certificado_thumbprint));

const certificadoValidade = computed(() => {
  if (!fiscal_settings.value.certificado_validade) return null;
  return new Date(fiscal_settings.value.certificado_validade).toLocaleDateString('pt-BR');
});

const certificadoSubject = computed(() => fiscal_settings.value.certificado_subject || null);

// =============================================
// Watchers
// =============================================

// Carregar certificados Windows automaticamente ao mudar para modo Windows
watch(
  () => tipoCertificado.value,
  (newType) => {
    if (newType === 'WINDOWS' && windowsCertificates.length === 0) {
      refetchWindowsCerts();
    }
  }
);

// =============================================
// Methods
// =============================================

function updateFiscalSetting<K extends keyof FiscalSettings>(field: K, value: FiscalSettings[K]) {
  fiscal_settings.value = { ...fiscal_settings.value, [field]: value };
}

function onCertFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  if (input.files && input.files[0]) {
    const file = input.files[0];
    const extension = file.name.toLowerCase();

    // Validar extensão
    const isValid = UPLOAD_CONFIG.certificado.extensions.some(ext => extension.endsWith(ext));
    if (!isValid) {
      toast.warning('Arquivo inválido. Selecione um arquivo .pfx ou .p12');
      return;
    }

    // Validar se a senha foi preenchida
    if (!senhaLocal.value.trim()) {
      toast.warning('Digite a senha do certificado antes de enviar o arquivo');
      input.value = '';
      return;
    }

    // Upload com senha local (não persiste no form)
    handleCertUpload(file, senhaLocal.value);

    // Limpar senha e input após envio
    senhaLocal.value = '';
    input.value = '';
  }
}

/**
 * Vincula certificado Windows selecionado
 */
function onSelectWindowsCert(event: Event) {
  const select = event.target as HTMLSelectElement;
  const thumbprint = select.value;

  if (!thumbprint) return;

  // Chamar mutation para vincular no backend
  vincularWindowsMutation.mutate(thumbprint, {
    onSuccess: (updatedEmpresa) => {
      if (updatedEmpresa.fiscal_settings) {
        fiscal_settings.value = {
          ...fiscal_settings.value,
          tipo_certificado: updatedEmpresa.fiscal_settings.tipo_certificado,
          certificado_thumbprint: updatedEmpresa.fiscal_settings.certificado_thumbprint,
          certificado_validade: updatedEmpresa.fiscal_settings.certificado_validade,
          certificado_subject: updatedEmpresa.fiscal_settings.certificado_subject,
          certificado_digital_path: undefined, // Limpar arquivo
        };
      }
    },
  });
}
</script>

<template>
  <section class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <div
        class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary"
      >
        <LucideIcon :icon="Shield"/>
      </div>
      <h3 class="text-lg font-semibold text-zinc-800">{{ SECTION_LABELS.certificado }}</h3>
    </div>

    <div class="space-y-6">
      <!-- Tipo de Certificado -->
      <div class="flex gap-6">
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            v-model="tipoCertificado"
            type="radio"
            value="ARQUIVO"
            :disabled="disabled"
            class="radio radio-primary radio-sm accent-brand-primary"
          />
          <span class="text-sm font-medium text-gray-700">Arquivo (A1)</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            v-model="tipoCertificado"
            type="radio"
            value="WINDOWS"
            :disabled="disabled"
            class="radio radio-primary radio-sm accent-brand-primary"
          />
          <span class="text-sm font-medium text-gray-700">Instalado no Windows (A1 ou A3)</span>
        </label>
      </div>

      <!-- OPÇÃO 1: ARQUIVO A1 -->
      <div v-if="isArquivo" class="space-y-6 animate-in fade-in zoom-in duration-300">
        <!-- Status Banner -->
        <div
          v-if="hasCertificadoPath"
          class="flex items-center gap-3 p-4 bg-green-50 border border-green-100 rounded-lg text-green-800"
        >
          <CheckCircle class="text-green-600 shrink-0" :size="24" />
          <div class="flex-1 min-w-0">
            <p class="font-bold text-sm">Certificado A1 Configurado</p>
            <p v-if="certificadoSubject" class="text-xs text-green-700 mt-0.5 truncate">
              {{ certificadoSubject }}
            </p>
            <p v-if="certificadoValidade" class="text-xs text-green-600 font-medium mt-0.5">
              Válido até: {{ certificadoValidade }}
            </p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
          <!-- Senha do Certificado (PRIMEIRO - usuário precisa digitar antes) -->
          <div class="space-y-2">
            <label class="text-sm font-medium text-gray-700">
              Senha do Certificado
              <span class="text-red-500">*</span>
            </label>
            <div class="relative">
              <div
                class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400"
              >
                <Key :size="18" />
              </div>
              <input
                v-model="senhaLocal"
                type="password"
                placeholder="Digite a senha antes de enviar"
                :disabled="disabled || isUploadingCert"
                class="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:bg-white focus:ring-2 focus:ring-brand-primary-light focus:border-brand-primary outline-none transition-all text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
            <p class="text-xs text-gray-500">
              A senha é usada apenas para validar o certificado. Não é armazenada.
            </p>
          </div>

          <!-- Upload (SEGUNDO - só após senha) -->
          <div class="space-y-2">
            <label class="text-sm font-medium text-gray-700">Arquivo (.pfx / .p12)</label>
            <div class="relative">
              <input
                ref="certInput"
                type="file"
                :accept="UPLOAD_CONFIG.certificado.accept"
                :disabled="isUploadingCert || disabled || !senhaLocal.trim()"
                class="hidden"
                @change="onCertFileChange"
              />
              <button
                type="button"
                :disabled="isUploadingCert || disabled || !senhaLocal.trim()"
                class="flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-gray-50 border border-dashed border-gray-300 rounded-lg text-sm text-gray-600 cursor-pointer hover:bg-gray-100 hover:border-gray-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                :class="{ 'border-brand-primary bg-brand-primary-light/30': senhaLocal.trim() }"
                @click="certInput?.click()"
              >
                <span v-if="isUploadingCert" class="loading loading-spinner loading-sm"></span>
                <Upload v-else :size="16" />
                {{ isUploadingCert ? 'Validando e enviando...' : 'Selecionar Arquivo' }}
              </button>
            </div>
            <p v-if="!senhaLocal.trim()" class="text-xs text-amber-600">
              Digite a senha primeiro para habilitar o upload.
            </p>
            <p v-else class="text-xs text-green-600">
              Pronto! Selecione o arquivo do certificado.
            </p>
          </div>
        </div>
      </div>

      <!-- OPÇÃO 2: WINDOWS KEYSTORE -->
      <div v-else class="space-y-6 animate-in fade-in zoom-in duration-300">
        <!-- Status Banner (se já tem certificado Windows) -->
        <div
          v-if="hasCertificadoWindows"
          class="flex items-center gap-3 p-4 bg-green-50 border border-green-100 rounded-lg text-green-800"
        >
          <CheckCircle class="text-green-600 shrink-0" :size="24" />
          <div class="flex-1 min-w-0">
            <p class="font-bold text-sm">Certificado Windows Vinculado</p>
            <p v-if="certificadoSubject" class="text-xs text-green-700 mt-0.5 truncate">
              {{ certificadoSubject }}
            </p>
            <p v-if="certificadoValidade" class="text-xs text-green-600 font-medium mt-0.5">
              Válido até: {{ certificadoValidade }}
            </p>
            <p class="text-xs text-gray-500 mt-1 font-mono truncate">
              {{ fiscal_settings.certificado_thumbprint }}
            </p>
          </div>
        </div>

        <!-- Info Banner -->
        <div
          class="bg-brand-primary-light border border-brand-primary/20 p-4 rounded-lg flex items-start gap-3"
        >
          <AlertCircle class="text-brand-primary shrink-0 mt-0.5" :size="20" />
          <div class="space-y-1">
            <p class="text-sm text-brand-primary font-bold">Certificado A3 ou Integrado</p>
            <p class="text-xs text-brand-primary">
              Esta opção utiliza os certificados instalados no Windows (Token, Cartão ou Arquivo
              instalado). O Backend deve estar rodando na mesma máquina onde o certificado está
              conectado.
            </p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-end">
          <!-- Select de Certificados -->
          <div class="space-y-2">
            <label class="text-sm font-medium text-gray-700">Selecione o Certificado</label>
            <select
              :value="fiscal_settings.certificado_thumbprint || ''"
              :disabled="disabled || vincularWindowsMutation.isPending.value || windowsCertificates.length === 0"
              class="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:bg-white focus:ring-2 focus:ring-brand-primary-light focus:border-brand-primary outline-none transition-all text-sm text-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
              @change="onSelectWindowsCert"
            >
              <option value="" disabled>
                {{ windowsCertificates.length === 0 ? 'Carregue a lista primeiro...' : 'Selecione...' }}
              </option>
              <option
                v-for="cert in windowsCertificates"
                :key="cert.thumbprint"
                :value="cert.thumbprint"
              >
                {{ cert.friendly_name || cert.subject }}
                <template v-if="cert.valid_until">
                  (até {{ new Date(cert.valid_until).toLocaleDateString('pt-BR') }})
                </template>
              </option>
            </select>
            <p v-if="vincularWindowsMutation.isPending.value" class="text-xs text-brand-primary">
              Vinculando certificado...
            </p>
          </div>

          <!-- Botão Carregar Lista -->
          <BaseButton
            type="button"
            variant="secondary"
            :loading="isLoadingCertificates"
            :disabled="disabled"
            class="w-full justify-center md:w-auto"
            @click="refetchWindowsCerts"
          >
            <RefreshCw :size="16" class="mr-2" />
            {{ windowsCertificates.length > 0 ? 'Atualizar Lista' : 'Carregar Certificados' }}
          </BaseButton>
        </div>
      </div>
    </div>
  </section>
</template>
