<script setup lang="ts">
import { ref } from 'vue';
import { Cropper, CircleStencil } from 'vue-advanced-cropper';
import 'vue-advanced-cropper/dist/style.css';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

defineProps<{ isOpen: boolean; imageSrc: string }>();
const emit = defineEmits<{ confirm: [file: File]; close: [] }>();

const cropperRef = ref<InstanceType<typeof Cropper> | null>(null);
const isProcessing = ref(false);

function confirmar() {
  const resultado = cropperRef.value?.getResult();
  if (!resultado?.canvas) return;

  isProcessing.value = true;
  resultado.canvas.toBlob(
    (blob) => {
      isProcessing.value = false;
      if (!blob) return;
      const arquivo = new File([blob], 'foto-perfil.jpg', { type: 'image/jpeg' });
      emit('confirm', arquivo);
    },
    'image/jpeg',
    0.92,
  );
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-200 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @click.self="emit('close')"
      >
        <div class="bg-white rounded-2xl shadow-2xl w-420px flex flex-col overflow-hidden">
          <!-- Header -->
          <div class="px-6 py-4 border-b border-zinc-100">
            <h3 class="text-sm font-bold text-zinc-800">Ajustar foto de perfil</h3>
            <p class="text-xs text-zinc-400 mt-0.5">Arraste e use o scroll para ajustar o recorte</p>
          </div>

          <!-- Cropper -->
          <div class="bg-zinc-900 flex items-center justify-center" style="height: 360px;">
            <Cropper
              ref="cropperRef"
              :src="imageSrc"
              :stencil-component="CircleStencil"
              :stencil-props="{ aspectRatio: 1 }"
              :default-size="{ width: 280, height: 280 }"
              background-class="bg-zinc-900"
              class="w-full h-full"
            />
          </div>

          <!-- Ações -->
          <div class="px-6 py-4 flex justify-end gap-2 border-t border-zinc-100">
            <BaseButton variant="ghost" size="sm" @click="emit('close')">
              Cancelar
            </BaseButton>
            <BaseButton variant="primary" size="sm" :isLoading="isProcessing" @click="confirmar">
              Usar esta foto
            </BaseButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
