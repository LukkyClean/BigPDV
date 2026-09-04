<script setup lang="ts">
/**
 * @component CropperImagemModal
 * @description Modal de recorte de imagem antes do upload.
 *
 * Nasceu como o cropper da foto de perfil e foi generalizado para servir também
 * à logo da empresa. As duas diferenças que importam entre os dois usos:
 *
 * - **Formato**: foto de perfil é círculo travado em 1:1; logo é recorte livre,
 *   porque logo de loja raramente é quadrada e forçar 1:1 obrigaria o dono a
 *   cortar pedaço da própria marca.
 * - **Tipo de saída**: perfil sai em JPEG (menor), mas a logo PRECISA sair em
 *   PNG. O backend preserva o canal alfa só no contexto `empresa_logo`
 *   (core/imagem.py) e achatar em JPEG poria fundo preto atrás de uma logo
 *   transparente — direto no cabeçalho do cupom.
 */

import { computed, ref } from 'vue';
import { Cropper, CircleStencil } from 'vue-advanced-cropper';
import 'vue-advanced-cropper/dist/style.css';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

const props = withDefaults(
  defineProps<{
    isOpen: boolean;
    imageSrc: string;
    titulo?: string;
    descricao?: string;
    /** `circulo` trava em 1:1 (avatar); `livre` deixa o usuário recortar como quiser. */
    formato?: 'circulo' | 'livre';
    tipoSaida?: 'image/jpeg' | 'image/png';
    nomeArquivo?: string;
    labelConfirmar?: string;
  }>(),
  {
    titulo: 'Ajustar imagem',
    descricao: 'Arraste e use o scroll para ajustar o recorte',
    formato: 'circulo',
    tipoSaida: 'image/jpeg',
    nomeArquivo: 'imagem.jpg',
    labelConfirmar: 'Usar esta imagem',
  },
);

const emit = defineEmits<{ confirm: [file: File]; close: [] }>();

const cropperRef = ref<InstanceType<typeof Cropper> | null>(null);
const isProcessing = ref(false);

const ehCirculo = computed(() => props.formato === 'circulo');

const stencilComponent = computed(() => (ehCirculo.value ? CircleStencil : undefined));

const stencilProps = computed(() => (ehCirculo.value ? { aspectRatio: 1 } : {}));

/**
 * No círculo, o recorte abre em 280x280 no centro — é o enquadramento que o
 * avatar sempre teve. No modo livre ele abre cobrindo a imagem inteira: quem
 * escolhe um arquivo já pronto e confirma sem mexer precisa receber a imagem
 * como ela era, não um quadrado recortado do meio dela.
 */
const defaultSize = computed(() =>
  ehCirculo.value
    ? { width: 280, height: 280 }
    : ({ imageSize }: { imageSize: { width: number; height: number } }) => ({
        width: imageSize.width,
        height: imageSize.height,
      }),
);

function confirmar() {
  const resultado = cropperRef.value?.getResult();
  if (!resultado?.canvas) return;

  isProcessing.value = true;
  resultado.canvas.toBlob(
    (blob) => {
      isProcessing.value = false;
      if (!blob) return;
      const arquivo = new File([blob], props.nomeArquivo, { type: props.tipoSaida });
      emit('confirm', arquivo);
    },
    props.tipoSaida,
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
            <h3 class="text-sm font-bold text-zinc-800">{{ titulo }}</h3>
            <p class="text-xs text-zinc-400 mt-0.5">{{ descricao }}</p>
          </div>

          <!-- Cropper -->
          <div class="bg-zinc-900 flex items-center justify-center" style="height: 360px;">
            <Cropper
              ref="cropperRef"
              :src="imageSrc"
              :stencil-component="stencilComponent"
              :stencil-props="stencilProps"
              :default-size="defaultSize"
              background-class="bg-zinc-900"
              class="w-full h-full"
            />
          </div>

          <!-- Ações -->
          <div class="px-6 py-4 flex justify-end gap-2 border-t border-zinc-100">
            <BaseButton variant="ghost" size="sm" @click="emit('close')">
              Cancelar
            </BaseButton>
            <BaseButton
              variant="primary"
              size="sm"
              :isLoading="isProcessing"
              @click="confirmar"
            >
              {{ labelConfirmar }}
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
