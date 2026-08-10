<script setup lang="ts">
import { computed, ref } from 'vue';
import { ClipboardList, Image, QrCode, CheckCircle2, AlertCircle } from 'lucide-vue-next';
import OSQrCodeModal from '../OSQrCodeModal.vue';
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
  /** dados_adicionais da OS — carrega a resposta do cliente sobre a arte. */
  osDados?: Record<string, unknown>;
}

const props = withDefaults(defineProps<Props>(), {
  osDados: () => ({}),
});

/**
 * O laudo técnico só faz sentido em negócio que DIAGNOSTICA: recebe algo com
 * problema, investiga, emite parecer. Serigrafia não diagnostica nada — o
 * cliente chega dizendo o que quer e a loja produz.
 *
 * A aba continua existindo mesmo sem laudo, e de propósito: é aqui que mora a
 * galeria de fotos, e em serigrafia a foto É a arte — é ela que o cliente
 * aprova pelo celular. Tirar a aba inteira tiraria o lugar de anexar o mockup.
 */
const { temDiagnostico, temAprovacaoArte } = useCapacidades();

/**
 * A porta de entrada da aprovação de arte.
 *
 * O QR já era gerado pela aba de Vistoria — que só existe em oficina. Sem este
 * botão, o segmento de serigrafia tinha a página do celular, o endpoint e a
 * capacidade, e NENHUM jeito de chegar até eles: a funcionalidade inteira era
 * inalcançável pelo usuário.
 *
 * Fica aqui, ao lado da galeria, porque o fluxo é este: anexa o mockup, manda
 * para o cliente ver, ele aprova. Sem foto anexada não há o que aprovar, e a
 * própria página do celular avisa isso.
 */
const showQrModal = ref(false);

/** Resposta do cliente, gravada pela página do celular. */
const arteStatus = computed(() => props.osDados.arte_status as string | undefined);
const arteQuem = computed(() => props.osDados.arte_respondido_por as string | undefined);
const arteObservacao = computed(() => props.osDados.arte_observacao as string | undefined);

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

    <!-- Aprovação de arte: a porta de entrada do QR para o celular do cliente. -->
    <div
      v-if="temAprovacaoArte"
      class="rounded-xl border border-slate-200 p-4 space-y-3"
    >
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <p class="text-sm font-bold text-slate-700">Aprovação do cliente</p>
          <p class="text-xs text-slate-500 mt-0.5">
            Anexe a arte abaixo e envie o QR code para o cliente conferir e liberar a produção.
          </p>
        </div>
        <button
          type="button"
          :disabled="!osNumero"
          class="shrink-0 flex items-center gap-2 px-3 py-2 rounded-lg bg-brand-primary text-white text-xs font-bold disabled:opacity-50"
          @click="showQrModal = true"
        >
          <QrCode :size="14" />
          Enviar para aprovação
        </button>
      </div>

      <!-- O que o cliente respondeu. Sem isto a loja não tem como saber se pode
           gravar a tela — a resposta ficaria só dentro do celular dele. -->
      <div
        v-if="arteStatus"
        class="flex items-start gap-2 rounded-lg p-3 text-xs"
        :class="arteStatus === 'APROVADA'
          ? 'bg-emerald-50 text-emerald-800'
          : 'bg-amber-50 text-amber-800'"
      >
        <component
          :is="arteStatus === 'APROVADA' ? CheckCircle2 : AlertCircle"
          :size="16"
          class="mt-0.5 shrink-0"
        />
        <div class="min-w-0">
          <p class="font-bold">
            {{ arteStatus === 'APROVADA' ? 'Arte aprovada' : 'Cliente pediu ajuste' }}
            <span v-if="arteQuem" class="font-normal">— por {{ arteQuem }}</span>
          </p>
          <p v-if="arteObservacao" class="mt-0.5">{{ arteObservacao }}</p>
        </div>
      </div>

      <p v-else-if="osNumero" class="text-xs text-slate-400">
        Aguardando resposta do cliente.
      </p>
      <p v-else class="text-xs text-slate-400">
        Salve a OS para poder enviar a arte.
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

    <OSQrCodeModal
      v-if="osNumero"
      :is-open="showQrModal"
      :os-number="osNumero"
      @close="showQrModal = false"
    />
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
