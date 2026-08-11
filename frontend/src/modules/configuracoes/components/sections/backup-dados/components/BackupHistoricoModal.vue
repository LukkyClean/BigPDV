<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { HardDrive, X, Archive, Layers } from 'lucide-vue-next'
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue'
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue'
import { useListarBackupsQuery } from '@/modules/configuracoes/composables/queries/useListarBackupsQuery'
import type { BackupInfoType } from '@/modules/configuracoes/types/backup.types'

const props = defineProps<{ isOpen: boolean }>()
const emit = defineEmits<{ close: [] }>()

const enabled = ref(false)
watch(() => props.isOpen, (aberto) => { if (aberto) enabled.value = true })

const { data: backups, isLoading } = useListarBackupsQuery(enabled)

interface CadeiaBackup {
  anchor: BackupInfoType
  incrementais: BackupInfoType[]
}

const cadeias = computed<CadeiaBackup[]>(() => {
  if (!backups.value?.length) return []

  const resultado: CadeiaBackup[] = []
  let cadeiaAtual: CadeiaBackup | null = null

  for (const b of backups.value) {
    if (b.completo) {
      cadeiaAtual = { anchor: b, incrementais: [] }
      resultado.push(cadeiaAtual)
    } else if (cadeiaAtual) {
      cadeiaAtual.incrementais.push(b)
    } else {
      // Incremental órfão (sem full anterior) — cria grupo isolado
      resultado.push({ anchor: b, incrementais: [] })
    }
  }

  return resultado
})

function formatarData(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }) +
    ' ' +
    d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function formatarTamanho(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<template>
  <BaseModal :is-open="isOpen" title="Histórico de Backups" size="md" @close="emit('close')">
    <template #header>
      <div class="flex items-center justify-between px-6 py-4 border-b border-zinc-100 shrink-0">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 bg-zinc-100 rounded-lg flex items-center justify-center">
            <HardDrive :size="16" class="text-zinc-600" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-zinc-900">Histórico de Backups</h2>
            <p class="text-[11px] text-zinc-400 leading-tight">
              {{ backups?.length ?? 0 }} backup(s) encontrado(s)
            </p>
          </div>
        </div>
        <button
          type="button"
          class="p-1.5 text-zinc-400 hover:text-red-500 hover:bg-zinc-100 rounded-lg transition-colors cursor-pointer"
          @click="emit('close')"
        >
          <X :size="18" />
        </button>
      </div>
    </template>

    <div class="min-h-[300px] max-h-[400px] overflow-y-auto">
      <!-- Loading -->
      <div v-if="isLoading" class="flex items-center justify-center h-[300px] text-sm text-zinc-500">
        Carregando backups...
      </div>

      <!-- Vazio -->
      <div v-else-if="!cadeias.length" class="flex flex-col items-center justify-center h-[300px] text-zinc-400">
        <HardDrive :size="32" class="mb-2" />
        <p class="text-sm">Nenhum backup encontrado</p>
      </div>

      <!-- Lista agrupada -->
      <div v-else class="flex flex-col gap-1 p-2">
        <div v-for="(cadeia, i) in cadeias" :key="i" class="rounded-lg overflow-hidden">
          <!-- Anchor (Full ou órfão) -->
          <div class="flex items-center gap-3 px-3 py-2.5 bg-zinc-50 border border-zinc-100 rounded-lg">
            <div class="w-6 h-6 rounded flex items-center justify-center shrink-0"
              :class="cadeia.anchor.completo ? 'bg-blue-100' : 'bg-zinc-200'">
              <Archive v-if="cadeia.anchor.completo" :size="12" class="text-blue-600" />
              <Layers v-else :size="12" class="text-zinc-500" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-xs font-medium text-zinc-800 truncate">{{ cadeia.anchor.arquivo }}</p>
              <p class="text-[11px] text-zinc-500">
                {{ formatarData(cadeia.anchor.criado_em) }}
                <span class="text-zinc-300 mx-1">|</span>
                {{ formatarTamanho(cadeia.anchor.tamanho_bytes) }}
              </p>
            </div>
            <span
              :class="[
                'text-[10px] font-bold uppercase px-1.5 py-0.5 rounded',
                cadeia.anchor.completo
                  ? 'bg-blue-50 text-blue-600'
                  : 'bg-zinc-100 text-zinc-500',
              ]"
            >
              {{ cadeia.anchor.completo ? 'Completo' : 'Incremental' }}
            </span>
          </div>

          <!-- Incrementais -->
          <div v-for="incr in cadeia.incrementais" :key="incr.arquivo"
            class="flex items-center gap-3 px-3 py-2 ml-5 border-l-2 border-zinc-200">
            <Layers :size="12" class="text-zinc-400 shrink-0" />
            <div class="flex-1 min-w-0">
              <p class="text-[11px] text-zinc-700 truncate">{{ incr.arquivo }}</p>
              <p class="text-[10px] text-zinc-400">
                {{ formatarData(incr.criado_em) }}
                <span class="text-zinc-300 mx-1">|</span>
                {{ formatarTamanho(incr.tamanho_bytes) }}
              </p>
            </div>
            <span class="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-500">
              Incremental
            </span>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end">
        <BaseButton variant="ghost" size="sm" @click="emit('close')">
          Fechar
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
