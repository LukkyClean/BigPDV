<script setup lang="ts">
/**
 * @component ImageUploadSection
 * @description Beautiful image upload component with preview for product photos
 */

import { ref, computed } from 'vue';
import { X, Image as ImageIcon } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import { useProductForm } from '../../composables/useProductForm';
import { getBackendBaseUrl } from '@/api/backendUrl';

// =============================================
// Props
// =============================================

interface Props {
  disabled?: boolean;
}

defineProps<Props>();

// =============================================
// State
// =============================================

const { imageFile, image_url } = useProductForm();

const imagePreview = ref<string | null>(null);
const fileName = ref<string>('');
const isDragging = ref(false);

// =============================================
// Computed
// =============================================

const hasImage = computed(() => !!imagePreview.value || !!image_url.value);

const previewSource = computed(() => {
  if (imagePreview.value) {
    return imagePreview.value;
  } else if (image_url.value) {
    return `${getBackendBaseUrl()}/${image_url.value}`;
  }
  return '';
});

// =============================================
// Methods
// =============================================

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (file) {
    processFile(file);
  }
}

function handleDrop(event: DragEvent) {
  isDragging.value = false;
  const file = event.dataTransfer?.files[0];
  if (file && file.type.startsWith('image/')) {
    processFile(file);
  }
}

function processFile(file: File) {
  fileName.value = file.name;
  imageFile.value = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    imagePreview.value = e.target?.result as string;
  };
  reader.readAsDataURL(file);
}

function removeImage() {
  imagePreview.value = null;
  fileName.value = '';
  image_url.value = null;
}

function handleDragOver(event: DragEvent) {
  event.preventDefault();
  isDragging.value = true;
}

function handleDragLeave() {
  isDragging.value = false;
}
</script>

<template>
  <div>
    <!-- Upload Area -->
    <div
      class="relative w-full aspect-square max-w-70 rounded-2xl border-2 transition-all duration-300 ease-in-out overflow-hidden"
      :class="[
        hasImage
          ? 'border-solid border-slate-200 bg-white'
          : isDragging
            ? 'border-dashed border-brand-primary bg-linear-to-br from-brand-primary-light to-brand-primary-light scale-[1.02]'
            : 'border-dashed border-slate-300 bg-linear-to-br from-slate-50 to-slate-100 hover:border-brand-primary hover:bg-linear-to-br hover:from-blue-50 hover:to-brand-primary-light hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(59,130,246,0.12)]',
        disabled && 'opacity-60 cursor-not-allowed',
      ]"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop.prevent="handleDrop"
    >
      <!-- Preview State -->
      <div v-if="hasImage" class="relative w-full h-full flex flex-col">
        <img
          :src="previewSource"
          alt="Product preview"
          class="w-full h-full object-contain rounded-[14px]"
        />

        <!-- Overlay -->
        <div
          class="absolute inset-0 bg-linear-to-b from-black/40 via-transparent to-black/60 opacity-0 hover:opacity-100 transition-opacity duration-300 rounded-[14px] flex items-start justify-end p-3"
        >
          <button
            v-if="!disabled"
            type="button"
            class="flex items-center justify-center w-8 h-8 rounded-lg bg-red-500/95 text-white backdrop-blur-sm hover:bg-red-600 hover:scale-110 transition-all duration-200 cursor-pointer border-none"
            @click="removeImage"
            title="Remover imagem"
          >
            <LucideIcon :icon="X" size="md" />
          </button>
        </div>

        <!-- Image Info -->
        <div
          class="absolute bottom-0 left-0 right-0 p-3 bg-linear-to-t from-black/80 to-transparent rounded-b-[14px]"
        >
          <span class="text-xs text-white font-medium block truncate">{{ fileName }}</span>
        </div>
      </div>

      <!-- Upload State -->
      <label
        v-else
        class="flex items-center justify-center w-full h-full p-6 cursor-pointer"
        :class="{ 'cursor-not-allowed': disabled }"
      >
        <input
          type="file"
          accept="image/*"
          class="hidden"
          :disabled="disabled"
          @change="handleFileSelect"
        />
        <div class="flex flex-col items-center gap-4 text-center">
          <div
            class="flex items-center justify-center w-16 h-16 rounded-2xl bg-linear-to-br from-brand-primary to-brand-secondary text-white shadow-lg shadow-blue-500/30 transition-transform duration-300 group-hover:scale-110 group-hover:rotate-6"
          >
            <LucideIcon :icon="ImageIcon" size="lg" />
          </div>
          <div class="flex flex-col gap-1">
            <p class="text-sm font-semibold text-slate-800 m-0">Foto do Produto</p>
            <p class="text-xs text-slate-600 m-0">Clique ou arraste uma imagem</p>
            <p class="text-[10px] text-slate-500 m-0 mt-1">PNG, JPG até 5MB</p>
          </div>
        </div>
      </label>
    </div>
  </div>
</template>
