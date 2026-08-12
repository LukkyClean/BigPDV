<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ChevronDown, HardDrive, CheckCircle, Clock, Loader2 } from 'lucide-vue-next'
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue'
import BaseConfirmModal from '@/shared/components/commons/BaseConfirmModal/BaseConfirmModal.vue'
import { useUltimoBackupQuery } from '@/modules/configuracoes/composables/queries/useUltimoBackupQuery'
import { useConfiguracaoBackupQuery } from '@/modules/configuracoes/composables/queries/useConfiguracaoBackupQuery'
import { useListarBackupsQuery } from '@/modules/configuracoes/composables/queries/useListarBackupsQuery'
import { useCriarBackupMutation } from '@/modules/configuracoes/composables/mutates/useCriarBackupMutation'
import { useConfirmacao } from '@/shared/composables/useConfirmacao'
import BackupHistoricoModal from './BackupHistoricoModal.vue'
import BackupRestaurarModal from './BackupRestaurarModal.vue'

const confirmacao = useConfirmacao()

const { data: ultimoBackup, isLoading: isLoadingUltimo } = useUltimoBackupQuery()
const { data: configBackup } = useConfiguracaoBackupQuery()
const { mutate: criarBackup, isPending: isCriando } = useCriarBackupMutation()

const historicoAberto = ref(false)
const restaurarAberto = ref(false)

// Busca lista de backups para calcular cota do dia
const listaEnabled = ref(true)
const { data: listaBackups } = useListarBackupsQuery(listaEnabled)

const backupsHoje = computed(() => {
  if (!listaBackups.value) return 0
  const hoje = new Date().toISOString().slice(0, 10)
  return listaBackups.value.filter((b) => b.criado_em.startsWith(hoje)).length
})

const backupsRestantes = computed(() => Math.max(0, 2 - backupsHoje.value))

// Form de configuração de backup automático
const form = reactive({
  backup_automatico_ativo: false,
  frequencia: 'diario' as 'diario' | '8horas' | '12horas',
  horario: '02:00',
})

function valoresDoStore() {
  return {
    backup_automatico_ativo: configBackup.value?.backup_automatico_ativo ?? true,
    frequencia: configBackup.value?.frequencia ?? '8horas',
    horario: configBackup.value?.horario ?? '02:00',
  }
}

watch(() => configBackup.value, () => {
  Object.assign(form, valoresDoStore())
}, { immediate: true })

function resetar() {
  Object.assign(form, valoresDoStore())
}

const isDirty = computed(() => JSON.stringify({ ...form }) !== JSON.stringify(valoresDoStore()))

// Formatações
function formatarData(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }) +
    ' às ' +
    d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function formatarTamanho(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const frequenciaOpcoes = [
  { value: 'diario', label: 'Diário' },
  { value: '8horas', label: 'A cada 8 horas' },
  { value: '12horas', label: 'A cada 12 horas' },
]

const frequenciaSelecionada = computed(() => {
  return frequenciaOpcoes.find((o) => o.value === form.frequencia)?.label ?? 'Diário'
})

const selectAberto = ref(false)

function selecionarFrequencia(valor: string) {
  form.frequencia = valor as typeof form.frequencia
  selectAberto.value = false
}

async function onCriarBackup() {
  const ok = await confirmacao.pedirConfirmacao({
    titulo: 'Criar backup agora?',
    descricao: 'Um backup manual do banco de dados será criado. Isso pode levar alguns segundos.',
    confirmLabel: 'Criar Backup',
    variant: 'warning',
  })
  if (!ok) return
  criarBackup()
}

defineExpose({
  get form() {
    return {
      backup_automatico_ativo: form.backup_automatico_ativo,
      frequencia: form.frequencia,
      horario: form.horario,
    }
  },
  isDirty,
  resetar,
})
</script>

<template>
  <BaseConfirmModal
    :is-open="confirmacao.isOpen.value"
    :title="confirmacao.opcoes.value.titulo"
    :description="confirmacao.opcoes.value.descricao"
    :confirm-label="confirmacao.opcoes.value.confirmLabel"
    :cancel-label="confirmacao.opcoes.value.cancelLabel"
    :variant="confirmacao.opcoes.value.variant"
    overlay
    @confirm="confirmacao.confirmar"
    @close="confirmacao.cancelar"
  />
  <BackupHistoricoModal :is-open="historicoAberto" @close="historicoAberto = false" />
  <BackupRestaurarModal :is-open="restaurarAberto" @close="restaurarAberto = false" />

  <div class="flex flex-col gap-6">
    <div>
      <h3 class="text-base font-bold text-zinc-900">Backup dos Dados</h3>
      <p class="text-sm text-zinc-500 mt-0.5">Configure e gerencie os backups do banco de dados do sistema</p>
    </div>

    <!-- Status do Último Backup -->
    <div class="bg-zinc-50 border border-zinc-100 rounded-lg p-4">
      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
          :class="ultimoBackup ? 'bg-emerald-100' : 'bg-zinc-200'">
          <CheckCircle v-if="ultimoBackup" :size="16" class="text-emerald-600" />
          <HardDrive v-else :size="16" class="text-zinc-400" />
        </div>
        <div v-if="isLoadingUltimo" class="flex items-center gap-2 text-sm text-zinc-500">
          <Loader2 :size="14" class="animate-spin" />
          Carregando...
        </div>
        <div v-else-if="ultimoBackup" class="flex-1 min-w-0">
          <p class="text-sm font-medium text-zinc-800">Último backup realizado</p>
          <p class="text-xs text-zinc-500 mt-0.5">
            {{ formatarData(ultimoBackup.criado_em) }}
            <span class="text-zinc-300 mx-1">|</span>
            {{ ultimoBackup.completo ? 'Completo' : 'Incremental' }}
            <span class="text-zinc-300 mx-1">|</span>
            {{ formatarTamanho(ultimoBackup.tamanho_bytes) }}
          </p>
        </div>
        <div v-else>
          <p class="text-sm font-medium text-zinc-800">Nenhum backup encontrado</p>
          <p class="text-xs text-zinc-500 mt-0.5">Crie o primeiro backup para proteger seus dados</p>
        </div>
      </div>
    </div>

    <!-- Backup Automático -->
    <div class="flex flex-col gap-3">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Backup Automático</p>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Ativar backup automático</p>
          <p class="text-xs text-zinc-500 mt-0.5">Realiza backup nos horários configurados</p>
        </div>
        <button
          type="button"
          :class="['relative w-9 h-4.5 rounded-full transition-colors duration-200 cursor-pointer shrink-0', form.backup_automatico_ativo ? 'bg-brand-primary' : 'bg-zinc-200']"
          @click="form.backup_automatico_ativo = !form.backup_automatico_ativo"
        >
          <span :class="['absolute left-0 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200', form.backup_automatico_ativo ? 'translate-x-5' : 'translate-x-0.5']" />
        </button>
      </div>

      <div v-if="form.backup_automatico_ativo" class="flex flex-col gap-3">
        <div class="flex flex-col gap-1.5 relative">
          <label class="text-xs font-medium text-zinc-600">Frequência de backup</label>
          <button
            type="button"
            class="flex items-center justify-between border border-zinc-200 rounded-lg px-3 py-2.5 bg-zinc-50 cursor-pointer hover:border-zinc-300 transition-colors"
            @click="selectAberto = !selectAberto"
          >
            <span class="text-sm text-zinc-700">{{ frequenciaSelecionada }}</span>
            <ChevronDown :size="14" class="text-zinc-400 shrink-0" />
          </button>
          <div
            v-if="selectAberto"
            class="absolute top-full left-0 right-0 mt-1 bg-white border border-zinc-200 rounded-lg shadow-lg z-10 overflow-hidden"
          >
            <button
              v-for="opcao in frequenciaOpcoes"
              :key="opcao.value"
              type="button"
              :class="[
                'w-full text-left px-3 py-2 text-sm cursor-pointer transition-colors',
                form.frequencia === opcao.value
                  ? 'bg-brand-primary/8 text-brand-primary font-medium'
                  : 'text-zinc-700 hover:bg-zinc-50',
              ]"
              @click="selecionarFrequencia(opcao.value)"
            >
              {{ opcao.label }}
            </button>
          </div>
        </div>

        <div v-if="form.frequencia === 'diario'" class="flex flex-col gap-1.5">
          <label class="text-xs font-medium text-zinc-600">Horário do backup</label>
          <input
            v-model="form.horario"
            type="time"
            class="border border-zinc-200 rounded-lg px-3 py-2.5 bg-zinc-50 text-sm text-zinc-700 outline-none focus:border-brand-primary transition-colors"
          />
        </div>
      </div>
    </div>

    <!-- Backup Manual -->
    <div class="flex flex-col gap-3">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Backup Manual</p>

      <div class="flex flex-col gap-2">
        <BaseButton
          variant="primary"
          size="sm"
          :disabled="isCriando || backupsRestantes === 0"
          :isLoading="isCriando"
          @click="onCriarBackup"
        >
          Fazer Backup Agora
        </BaseButton>
        <p class="text-xs text-zinc-500 flex items-center gap-1">
          <Clock :size="12" />
          {{ backupsRestantes }} de 2 backups manuais restantes hoje
        </p>
        <BaseButton variant="ghost" size="sm" @click="historicoAberto = true">
          Histórico de Backups
        </BaseButton>
      </div>
    </div>

    <!-- Restauração -->
    <div class="flex flex-col gap-3">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Restauração</p>

      <BaseButton variant="danger" size="sm" @click="restaurarAberto = true">
        Restaurar Backup
      </BaseButton>
    </div>
  </div>
</template>
