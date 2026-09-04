<script setup lang="ts">
/**
 * @component IdentificationSection
 * @description Seção de identificação da empresa (logo, razão social, CNPJ, etc.)
 * Refatorado para usar inject pattern
 */

import { ref, computed, watch } from 'vue';
import { Building2, Camera, Image as ImageIcon, Search } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import CropperImagemModal from '@/shared/components/commons/CropperImagemModal/CropperImagemModal.vue';
import { SECTION_LABELS } from '../../constants/empresa.constants';
import { useEmpresaForm } from '../../composables/useEmpresaFormProvider';
import { getImageUrl } from '@/shared/utils/print.utils';

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
  razao_social,
  nome_fantasia,
  documento,
  is_cnpj,
  cnae_principal,
  cnaes_secundarios,
  data_abertura,
  website,
  url_logo,
  handleLogoUpload,
  isUploadingLogo,
  temAlteracoesPendentes,
  cnpjSalvo,
  isConsultingCNPJ,
  consultarCNPJ,
  setTipoPessoa,
  errors,
  submitCount,
} = useEmpresaForm();

// =============================================
// Tipo de Pessoa (PF/PJ)
// =============================================
// A empresa pode ser um CPF (autônomo, profissional liberal) ou um CNPJ.
// O tipo vem do cadastro inicial em `is_cnpj` e define rótulo, máscara e
// quais campos existem — CNAE e data de abertura são só de PJ.

const rotuloDocumento = computed(() => (is_cnpj.value ? 'CNPJ' : 'CPF'));

const mascaraDocumento = computed(() =>
  is_cnpj.value ? '##.###.###/####-##' : '###.###.###-##',
);

const placeholderDocumento = computed(() =>
  is_cnpj.value ? '00.000.000/0000-00' : '000.000.000-00',
);

const rotuloNome = computed(() => (is_cnpj.value ? 'Razão Social' : 'Nome Completo'));

// A mensagem do Zod é escrita para PJ ("Razão Social é obrigatória"); em PF o
// campo tem outro nome na tela e o erro precisa acompanhar.
const erroNome = computed(() => {
  const erro = submitCount.value > 0 ? errors.value.razao_social : '';
  if (!erro) return '';
  return is_cnpj.value ? erro : 'Nome completo é obrigatório';
});

// =============================================
// CNPJ Auto-lookup
// =============================================

const documentoDigits = computed(() => documento.value.replace(/\D/g, ''));

watch(documentoDigits, (digits) => {
  if (!is_cnpj.value || digits.length !== 14) return;
  // Só consulta se o CNPJ for diferente do que já está salvo no servidor
  // Isso evita disparar o lookup no carregamento inicial da página
  if (digits === cnpjSalvo.value) return;
  consultarCNPJ(digits);
});

// =============================================
// Refs
// =============================================

const logoInput = ref<HTMLInputElement | null>(null);

// =============================================
// Computed
// =============================================

const logoUrl = computed(() => getImageUrl(url_logo.value) ?? '');

// =============================================
// Upload da logo (mesmo fluxo da foto de perfil)
// =============================================
// O arquivo escolhido passa pelo cropper antes de subir. O recorte é livre —
// travar em 1:1 obrigaria uma logo horizontal a perder pedaço — e a saída é PNG
// para não achatar a transparência, que o backend preserva só para a logo.

const cropperAberto = ref(false);
const imagemParaCropar = ref('');

function triggerLogoUpload() {
  logoInput.value?.click();
}

function onLogoFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  imagemParaCropar.value = URL.createObjectURL(file);
  cropperAberto.value = true;
  input.value = '';
}

function onCropConfirmado(arquivo: File) {
  cropperAberto.value = false;
  URL.revokeObjectURL(imagemParaCropar.value);
  handleLogoUpload(arquivo);
}

function onCropCancelado() {
  cropperAberto.value = false;
  URL.revokeObjectURL(imagemParaCropar.value);
}
</script>

<template>
  <section class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
    <div class="flex items-center gap-3 mb-6">
      <div
        class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary"
      >
        <LucideIcon :icon="Building2"/>
      </div>
      <h3 class="text-lg font-semibold text-zinc-800">{{ SECTION_LABELS.identificacao }}</h3>
    </div>
    <!-- Header -->

    <div class="space-y-6">
      <!-- Logo Upload -->
      <div
        class="flex items-center gap-6 p-4 bg-gray-50 rounded-lg border border-gray-100 mb-6"
      >
        <input
          ref="logoInput"
          type="file"
          accept="image/png, image/jpeg, image/jpg, image/webp"
          class="hidden"
          :disabled="isUploadingLogo || disabled"
          @change="onLogoFileChange"
        />

        <!-- A miniatura inteira é o botão, como no avatar de Minha Conta -->
        <div
          class="relative shrink-0 group"
          :class="disabled ? 'cursor-not-allowed' : 'cursor-pointer'"
          @click="!disabled && triggerLogoUpload()"
        >
          <div
            class="w-24 h-24 rounded-lg bg-white border border-gray-200 flex items-center justify-center overflow-hidden shadow-sm"
          >
            <img
              v-if="logoUrl"
              :src="logoUrl"
              alt="Logo da empresa"
              class="w-full h-full object-contain p-1"
            />
            <div v-else class="text-gray-300">
              <ImageIcon :size="32" stroke-width="1.5" />
            </div>
          </div>

          <!-- Overlay câmera ao hover (e spinner durante o envio) -->
          <div
            class="absolute inset-0 rounded-lg bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
            :class="{ 'opacity-100': isUploadingLogo }"
          >
            <Camera v-if="!isUploadingLogo" :size="22" class="text-white" />
            <span v-else class="loading loading-spinner loading-sm text-white"></span>
          </div>
        </div>

        <div class="flex-1">
          <h4 class="font-medium text-gray-800 text-sm mb-1">Logomarca</h4>
          <p class="text-xs text-gray-500">
            Exibida em orçamentos, pedidos e no cabeçalho do sistema. Recomendado:
            200x200px (PNG ou JPG).
          </p>
          <button
            type="button"
            class="text-xs text-brand-primary hover:underline mt-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed disabled:no-underline"
            :disabled="isUploadingLogo || disabled"
            @click="triggerLogoUpload"
          >
            {{ isUploadingLogo ? 'Enviando...' : logoUrl ? 'Alterar logo' : 'Adicionar logo' }}
          </button>
        </div>
      </div>

      <!-- Tipo de Pessoa (PF/PJ) -->
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-2">Tipo de Cadastro</label>
        <div class="flex gap-2 max-w-md">
          <button
            type="button"
            class="flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all border disabled:opacity-60 disabled:cursor-not-allowed"
            :class="
              !is_cnpj
                ? 'bg-brand-primary text-white border-brand-primary'
                : 'bg-white text-gray-600 border-gray-200 hover:border-brand-primary'
            "
            :disabled="disabled"
            @click="setTipoPessoa(false)"
          >
            Pessoa Física (CPF)
          </button>
          <button
            type="button"
            class="flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all border disabled:opacity-60 disabled:cursor-not-allowed"
            :class="
              is_cnpj
                ? 'bg-brand-primary text-white border-brand-primary'
                : 'bg-white text-gray-600 border-gray-200 hover:border-brand-primary'
            "
            :disabled="disabled"
            @click="setTipoPessoa(true)"
          >
            Pessoa Jurídica (CNPJ)
          </button>
        </div>
        <p class="mt-1.5 text-xs text-gray-400">
          Ao trocar o tipo, o documento é limpo e você precisa informá-lo novamente.
        </p>
      </div>

      <!-- Razão Social (PJ) / Nome Completo (PF) + Nome Fantasia -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <BaseInput
          v-model="razao_social"
          :label="rotuloNome"
          type="text"
          required
          :disabled="disabled"
          :error="erroNome"
        />
        <BaseInput
          v-model="nome_fantasia"
          :label="is_cnpj ? 'Nome Fantasia' : 'Nome do Negócio'"
          type="text"
          :disabled="disabled"
          :error="submitCount > 0 ? errors.nome_fantasia : ''"
        />
      </div>

      <!-- Documento (CPF/CNPJ) / CNAE -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <BaseInput
            :key="rotuloDocumento"
            v-model="documento"
            :label="rotuloDocumento"
            :mask="mascaraDocumento"
            :placeholder="placeholderDocumento"
            :required="true"
            :disabled="disabled || isConsultingCNPJ"
            :error="submitCount > 0 ? errors.documento : ''"
          />
          <div
            v-if="isConsultingCNPJ"
            class="mt-1.5 flex items-center gap-1.5 text-xs text-brand-primary animate-pulse"
          >
            <span class="loading loading-spinner loading-xs"></span>
            Consultando Receita Federal...
          </div>
          <div
            v-else-if="is_cnpj && documentoDigits.length === 14 && temAlteracoesPendentes"
            class="mt-1.5 flex items-center gap-1 text-xs text-gray-400"
          >
            <Search :size="11" />
            Dados preenchidos automaticamente pela Receita Federal
          </div>
        </div>
        <BaseInput
          v-if="is_cnpj"
          v-model="cnae_principal"
          label="CNAE Principal"
          type="text"
          :disabled="disabled || isConsultingCNPJ"
          :error="submitCount > 0 ? errors.cnae_principal : ''"
        />
      </div>

      <!-- CNAE Secundários / Data de Abertura (só PJ) -->
      <div v-if="is_cnpj" class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <BaseInput
          v-model="cnaes_secundarios"
          label="CNAEs Secundários"
          type="text"
          placeholder="Ex: 4751-2/01, 4753-9/00"
          :disabled="disabled"
        />
        <BaseInput
          v-model="data_abertura"
          label="Data de Abertura"
          type="date"
          :disabled="disabled"
        />
      </div>

      <!-- Website -->
      <BaseInput
        v-model="website"
        label="Website"
        type="text"
        placeholder="https://www.suaempresa.com.br"
        :disabled="disabled"
      />
    </div>
  </section>

  <CropperImagemModal
    :is-open="cropperAberto"
    :image-src="imagemParaCropar"
    titulo="Ajustar logo da empresa"
    descricao="Arraste e use o scroll para enquadrar. Use o recorte para tirar sobras em volta da marca."
    formato="livre"
    tipo-saida="image/png"
    nome-arquivo="logo.png"
    label-confirmar="Usar esta logo"
    @confirm="onCropConfirmado"
    @close="onCropCancelado"
  />
</template>
