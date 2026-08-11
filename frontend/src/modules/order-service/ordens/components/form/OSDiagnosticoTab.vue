<script setup lang="ts">
import { ClipboardList, Image } from 'lucide-vue-next';
import BaseTextarea from '@/shared/components/ui/BaseInput/BaseTextarea.vue';
import { useCapacidades } from '@/modules/order-service/shared/segmento/useCapacidades';
import OSFotoGallery from './OSFotoGallery.vue';
import type { OsImageReadDataType } from '../../schemas/relationship/osPhoto.schema';
import type { PendingPhoto } from './OSFotoGallery.vue';

interface Props {
  diagnostico: string;
  osNumero?: string;
  fotos: OsImageReadDataType[];
  pendingPhotos: PendingPhoto[];
  isLocked: boolean;
}

defineProps<Props>();

/**
 * O laudo técnico só faz sentido em negócio que DIAGNOSTICA: recebe algo com
 * problema, investiga, emite parecer. Serigrafia não diagnostica nada — o
 * cliente chega dizendo o que quer e a loja produz.
 *
 * A aba continua existindo mesmo sem laudo, e de propósito: é aqui que mora a
 * galeria de fotos, e em serigrafia a foto É a arte — é ela que o cliente
 * aprova pelo celular. Tirar a aba inteira tiraria o lugar de anexar o mockup.
 */
const { temDiagnostico } = useCapacidades();

const emit = defineEmits<{
  'update:diagnostico': [value: string];
  'add-photo': [file: File];
  'remove-pending': [index: number];
  photoChange: [];
}>();
</script>

<template>
  <div class="space-y-4 animate-fadeIn">
    <div class="bg-brand-primary-light border-l-4 border-brand-primary p-4 rounded-r-xl mb-4">
      <h5 class="text-sm font-bold text-brand-primary flex items-center gap-2">
        <component :is="temDiagnostico ? ClipboardList : Image" :size="16" />
        {{ temDiagnostico ? 'Área Técnica' : 'Imagens' }}
      </h5>
      <p class="text-xs text-brand-primary mt-1">
        {{ temDiagnostico
          ? 'Espaço reservado para o laudo técnico.'
          : 'Anexe a arte aprovada e as fotos do pedido.' }}
      </p>
    </div>

    <div v-if="temDiagnostico">
      <BaseTextarea
        :model-value="diagnostico"
        label="Laudo Técnico / Diagnóstico"
        :rows="12"
        placeholder="Descreva os testes realizados, componentes analisados e o diagnóstico final..."
        :disabled="isLocked"
        @update:model-value="emit('update:diagnostico', $event as string)"
      />
    </div>

    <div :class="temDiagnostico ? 'pt-4 border-t border-slate-200' : ''">
      <OSFotoGallery
        v-if="osNumero"
        :os-numero="osNumero"
        :fotos="fotos"
        :pending-photos="pendingPhotos"
        :read-only="isLocked"
        @add-photo="emit('add-photo', $event)"
        @remove-pending="emit('remove-pending', $event)"
        @deleted="emit('photoChange')"
      />
      <div
        v-else
        class="text-center py-4 bg-slate-50 border border-dashed border-slate-200 rounded-lg text-slate-500 text-sm"
      >
        Salve a OS antes de adicionar fotos.
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-fadeIn {
  animation: fadeIn 0.3s ease-in-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
