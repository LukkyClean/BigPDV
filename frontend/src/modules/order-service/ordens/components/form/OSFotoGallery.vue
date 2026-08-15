<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { Trash2, Plus, Image as ImageIcon, ChevronLeft, ChevronRight, X, Clock } from 'lucide-vue-next';
import { useToast } from '@/shared/composables/useToast';
import { useDeleteFotoOSMutation } from '../../composables/request/relationship/useOSPhotoMutate.mutate';
import type { OsImageReadDataType } from '../../schemas/relationship/osPhoto.schema';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import ConfirmationTemplate from '@/shared/components/templates/ConfirmationTemplate.vue';
import { getBackendBaseUrl } from '@/api/backendUrl';

export interface PendingPhoto {
  file: File;
  previewUrl: string;
  nome_arquivo: string;
}

interface Props {
  osNumero: string;
  fotos: OsImageReadDataType[];
  pendingPhotos?: PendingPhoto[];
  readOnly?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  fotos: () => [],
  pendingPhotos: () => [],
  readOnly: false,
});

const emit = defineEmits<{
  'add-photo': [file: File];
  'remove-pending': [index: number];
  deleted: [];
}>();

const toast = useToast();
const fileInput = ref<HTMLInputElement | null>(null);

const deleteMutation = useDeleteFotoOSMutation();

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  if (!target.files || target.files.length === 0) return;
  const file = target.files[0];
  if (!file.type.startsWith('image/')) {
    toast.error('Selecione apenas arquivos de imagem.');
    return;
  }
  emit('add-photo', file);
  if (fileInput.value) fileInput.value.value = '';
}

function triggerFileInput() { fileInput.value?.click(); }

// ─── Slideshow ─────────────────────────────────────────────────────────────
const allPhotos = computed(() => [
  ...props.fotos.map(f => ({ id: f.id, nome_arquivo: f.nome_arquivo, url: f.url, isPending: false })),
  ...props.pendingPhotos.map((p, i) => ({ id: -(i + 1), nome_arquivo: p.nome_arquivo, url: p.previewUrl, isPending: true })),
]);

const totalCount = computed(() => allPhotos.value.length);

const slideshow = ref({ isOpen: false, currentIndex: 0 });

const currentPhoto = computed(() => {
  if (!allPhotos.value.length || slideshow.value.currentIndex < 0) return null;
  return allPhotos.value[slideshow.value.currentIndex];
});

function openSlideshow(index: number) {
  slideshow.value.currentIndex = index;
  slideshow.value.isOpen = true;
}

function closeSlideshow() { slideshow.value.isOpen = false; }

function nextPhoto() {
  slideshow.value.currentIndex = slideshow.value.currentIndex < allPhotos.value.length - 1
    ? slideshow.value.currentIndex + 1 : 0;
}

function prevPhoto() {
  slideshow.value.currentIndex = slideshow.value.currentIndex > 0
    ? slideshow.value.currentIndex - 1 : allPhotos.value.length - 1;
}

function handleKeydown(e: KeyboardEvent) {
  if (!slideshow.value.isOpen) return;
  if (e.key === 'Escape') closeSlideshow();
  if (e.key === 'ArrowRight') nextPhoto();
  if (e.key === 'ArrowLeft') prevPhoto();
}

onMounted(() => window.addEventListener('keydown', handleKeydown));
onUnmounted(() => window.removeEventListener('keydown', handleKeydown));

// ─── Delete (apenas fotos salvas) ──────────────────────────────────────────
const confirmDeleteModal = ref({ isOpen: false, fotoId: null as number | null });

function openDeleteModal(fotoId: number) {
  confirmDeleteModal.value.fotoId = fotoId;
  confirmDeleteModal.value.isOpen = true;
}

function closeDeleteModal() {
  confirmDeleteModal.value.isOpen = false;
  confirmDeleteModal.value.fotoId = null;
}

function confirmDelete() {
  if (confirmDeleteModal.value.fotoId) {
    deleteMutation.mutate(
      { osNumber: props.osNumero, fotoId: confirmDeleteModal.value.fotoId },
      { onSuccess: () => emit('deleted') },
    );
    closeDeleteModal();
  }
}

// ─── Ações por tipo de foto ────────────────────────────────────────────────
function handleRemovePhoto(photo: { id: number; isPending: boolean }, index: number) {
  if (photo.isPending) {
    emit('remove-pending', index - props.fotos.length);
  } else {
    openDeleteModal(photo.id);
  }
}

function getImageUrlFromBackend(url: string) {
  const normalizedUrl = url.startsWith('/') ? url : `/${url}`;
  return `${getBackendBaseUrl()}${normalizedUrl}`;
}

function getPhotoSrc(photo: { url: string; isPending: boolean }) {
  return photo.isPending ? photo.url : getImageUrlFromBackend(photo.url);
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-semibold text-slate-700 flex items-center gap-2">
        <ImageIcon :size="16" class="text-slate-500" />
        Fotos do Diagnóstico
        <span class="text-xs font-normal text-slate-400">({{ totalCount }})</span>
      </h3>

      <BaseButton v-if="!readOnly" @click="triggerFileInput" size="sm" variant="primary">
        <Plus :size="16" class="mr-2" />
        Adicionar Foto
      </BaseButton>

      <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="handleFileSelect" />
    </div>

    <div v-if="allPhotos.length > 0" class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
      <div
        v-for="(foto, index) in allPhotos"
        :key="foto.id"
        class="group relative aspect-square bg-slate-100 rounded-xl overflow-hidden border border-slate-200"
        :class="{ 'border-amber-300 border-2': foto.isPending }"
      >
        <img :src="getPhotoSrc(foto)" :alt="foto.nome_arquivo" class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105" />

        <!-- Badge pendente -->
        <span
          v-if="foto.isPending"
          class="absolute top-2 left-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700 shadow-sm"
        >
          <Clock :size="10" />
          Pendente
        </span>

        <div class="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
          <div class="absolute top-2 right-2 flex gap-2">
            <button type="button" @click="openSlideshow(index)" class="bg-white/90 p-1.5 rounded-lg text-slate-600 hover:text-brand-primary hover:bg-white shadow-sm transition-all" title="Visualizar">
              <ImageIcon :size="16" />
            </button>
            <button type="button" v-if="!readOnly" @click="handleRemovePhoto(foto, index)" class="bg-white/90 p-1.5 rounded-lg text-slate-600 hover:text-red-600 hover:bg-white shadow-sm transition-all" title="Excluir">
              <Trash2 :size="16" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-8 bg-slate-50 rounded-xl border border-dashed border-slate-200">
      <div class="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-3">
        <ImageIcon :size="24" class="text-slate-400" />
      </div>
      <p class="text-sm text-slate-500 font-medium">Nenhuma foto adicionada</p>
      <p class="text-xs text-slate-400 mt-1">Fotos do objeto e diagnóstico aparecerão aqui.</p>
    </div>

    <!-- Slideshow -->
    <div v-if="slideshow.isOpen" class="fixed inset-0 z-9999 bg-black/90 flex flex-col items-center justify-center p-4 backdrop-blur-sm animate-fadeIn">
      <button type="button" class="absolute top-4 right-4 text-white/70 hover:text-white bg-white/10 hover:bg-white/20 p-2 rounded-full transition-all" @click="closeSlideshow">
        <X :size="24" />
      </button>
      <div class="relative w-full max-w-5xl h-full max-h-[85vh] flex items-center justify-center">
        <button v-if="allPhotos.length > 1" type="button" class="absolute left-0 md:-left-12 z-10 text-white/70 hover:text-white bg-black/20 hover:bg-black/40 p-3 rounded-full transition-all" @click.stop="prevPhoto">
          <ChevronLeft :size="32" />
        </button>
        <img v-if="currentPhoto" :src="getPhotoSrc(currentPhoto)" :alt="currentPhoto.nome_arquivo" class="max-w-full max-h-full object-contain rounded-lg shadow-2xl" />
        <button v-if="allPhotos.length > 1" type="button" class="absolute right-0 md:-right-12 z-10 text-white/70 hover:text-white bg-black/20 hover:bg-black/40 p-3 rounded-full transition-all" @click.stop="nextPhoto">
          <ChevronRight :size="32" />
        </button>
      </div>
      <div class="absolute bottom-6 left-0 right-0 text-center">
        <p class="text-white/90 font-medium text-lg drop-shadow-md">{{ currentPhoto?.nome_arquivo }}</p>
        <p class="text-white/60 text-sm mt-1">{{ slideshow.currentIndex + 1 }} de {{ allPhotos.length }}</p>
      </div>
    </div>

    <!-- Modal de confirmação de exclusão -->
    <BaseModal :is-open="confirmDeleteModal.isOpen" title="Excluir Foto?" size="sm" @close="closeDeleteModal">
      <ConfirmationTemplate :icon="Trash2" icon-bg-class="bg-brand-primary-light" icon-color-class="text-brand-primary">
        <template #description>
          <p class="text-sm text-slate-500 leading-relaxed">
            Deseja realmente remover esta foto do diagnóstico? <br>
            <span class="text-xs text-red-500 font-semibold">Esta ação não poderá ser desfeita.</span>
          </p>
        </template>
        <template #footer>
          <div class="flex gap-3 w-full">
            <BaseButton variant="secondary" class="flex-1" @click="closeDeleteModal">Cancelar</BaseButton>
            <BaseButton variant="primary" class="flex-1" @click="confirmDelete">Excluir</BaseButton>
          </div>
        </template>
      </ConfirmationTemplate>
    </BaseModal>
  </div>
</template>
