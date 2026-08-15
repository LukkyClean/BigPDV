<script setup lang="ts">
/**
 * @fileoverview Formatos e Exibição.
 *
 * DATA E HORA é INFORMATIVO, não editável — e é uma decisão, não pendência. O
 * sistema formata data em 49 pontos espalhados por 34 arquivos (OS, relatórios,
 * vendas, cupom, ESC/POS) e não há formatador central. Tornar o formato
 * configurável significaria varrer tudo isso para atender uma troca que nenhuma
 * loja brasileira pede. Mostrar o padrão vigente informa; um select que salva e
 * não obedece geraria chamado de suporte.
 *
 * Esta tela já teve selects falsos de separador de milhar, casas decimais e
 * idioma — desenhos sem estado nenhum, que o botão "Salvar" nunca gravou. Foram
 * removidos em vez de implementados: casas decimais em dinheiro é convite a
 * recibo errado, e idioma exigiria i18n num código que assume português.
 *
 * TEMA é do master e só ele vê. A cor escolhida é a semente: a paleta inteira
 * sai dela em `shared/theme/paleta.ts`, com o contraste verificado — nenhuma
 * escolha produz texto ilegível. A prévia é o sistema inteiro recolorindo ao
 * vivo, por isso aplicamos a cada mudança e desfazemos ao sair sem salvar.
 */
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { CalendarDays, Clock, Palette, RotateCcw } from 'lucide-vue-next'

import { useUserQuery } from '@/shared/composables/useUser'
import { useEmpresaQuery } from '@/modules/enterprise/composables/useEmpresaQuery'
import BaseColorPicker from '@/shared/components/ui/BaseColorPicker/BaseColorPicker.vue'
import { aplicarCor, limparPaleta, guardarCorLocalmente } from '@/shared/theme/aplicar'
import { COR_PADRAO } from '@/shared/theme/paleta'

const FORMATOS = [
  { icone: CalendarDays, rotulo: 'Datas', valor: 'DD/MM/AAAA', exemplo: '04/08/2026' },
  { icone: Clock, rotulo: 'Horas', valor: '24 horas', exemplo: '14:30' },
]

const { data: userData } = useUserQuery()
const isMaster = computed(() => userData.value?.is_master === true)

const { data: empresa } = useEmpresaQuery()

/** Cor gravada hoje. `null` = paleta de fábrica. */
const corSalva = computed<string | null>(() => empresa.value?.cor_tema ?? null)

// `form` é o contrato que o ConfiguracoesModal espera de uma seção funcional
// (junto de `isDirty` e `resetar`). Guardar null e não COR_PADRAO é proposital:
// null diz "usar a paleta de fábrica", e é o que o backend grava ao restaurar.
const form = ref<{ cor_tema: string | null }>({ cor_tema: corSalva.value })

watch(corSalva, (valor) => { form.value.cor_tema = valor })

const isDirty = computed(() => form.value.cor_tema !== corSalva.value)

function resetar() {
  form.value.cor_tema = corSalva.value
}

defineExpose({ form, isDirty, resetar })

/** Cor mostrada no seletor: sem escolha, parte do azul de fábrica. */
const corNoSeletor = computed<string>({
  get: () => form.value.cor_tema ?? COR_PADRAO,
  set: (valor) => { form.value.cor_tema = valor },
})

const usandoPadrao = computed(() => form.value.cor_tema === null)

function restaurarPadrao() {
  form.value.cor_tema = null
}

// Prévia ao vivo: pinta a tela a cada mudança, sem gravar nada.
watch(() => form.value.cor_tema, (cor) => {
  if (!isMaster.value) return
  if (cor) aplicarCor(cor)
  else limparPaleta()
})

/**
 * Sair sem salvar tem de desfazer a prévia — senão o sistema fica com uma cor
 * que ninguém escolheu até o próximo boot. Quando salvou, `corSalva` já mudou e
 * a prévia coincide com o gravado, então reaplicar é inofensivo.
 */
onBeforeUnmount(() => {
  if (!isMaster.value) return
  if (corSalva.value) {
    aplicarCor(corSalva.value)
    guardarCorLocalmente(corSalva.value)
  } else {
    limparPaleta()
    guardarCorLocalmente(null)
  }
})
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h3 class="text-base font-bold text-zinc-900">Formatos e Exibição</h3>
      <p class="text-sm text-zinc-500 mt-0.5">Como o sistema exibe datas, horas e cores</p>
    </div>

    <!-- Data e hora: informativo -->
    <div class="flex flex-col gap-3">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Data e Hora</p>

      <div class="border border-zinc-200 rounded-lg divide-y divide-zinc-100">
        <div
          v-for="formato in FORMATOS"
          :key="formato.rotulo"
          class="flex items-center gap-3 px-3 py-3"
        >
          <component :is="formato.icone" :size="16" class="text-zinc-400 shrink-0" />
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-zinc-800">{{ formato.rotulo }}</p>
            <p class="text-xs text-zinc-500 mt-0.5">Exemplo: {{ formato.exemplo }}</p>
          </div>
          <span class="text-sm font-semibold text-zinc-700 tabular-nums shrink-0">
            {{ formato.valor }}
          </span>
        </div>
      </div>

      <p class="text-xs text-zinc-500">
        Padrão brasileiro, aplicado em todas as telas e também nos documentos impressos.
      </p>
    </div>

    <!-- Tema: exclusivo do master -->
    <div v-if="isMaster" class="flex flex-col gap-3">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Tema do Sistema</p>

      <div class="border border-zinc-200 rounded-lg p-4 flex flex-col gap-4">
        <div class="flex items-start gap-2">
          <Palette :size="16" class="text-zinc-400 shrink-0 mt-0.5" />
          <p class="text-xs text-zinc-500">
            Escolha a cor da sua empresa. O restante da paleta é gerado a partir dela,
            sempre com contraste suficiente para o texto continuar legível.
          </p>
        </div>

        <BaseColorPicker v-model="corNoSeletor" />

        <!-- Prévia: os elementos que de fato mudam de cor -->
        <div class="flex flex-col gap-2">
          <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Prévia</p>
          <div class="flex flex-wrap items-center gap-2">
            <span class="px-3 py-1.5 rounded-lg bg-brand-primary text-white text-xs font-semibold">
              Botão
            </span>
            <span class="px-3 py-1.5 rounded-lg bg-brand-primary-light text-brand-primary text-xs font-semibold">
              Item ativo
            </span>
            <span class="text-xs font-semibold text-brand-primary">Link de exemplo</span>
            <span class="px-3 py-1.5 rounded-lg bg-brand-secondary text-white text-xs font-semibold">
              Apoio
            </span>
          </div>
          <p class="text-[11px] text-zinc-400">
            O menu lateral, o fundo das telas e os documentos impressos não seguem o tema.
          </p>
        </div>

        <div class="flex items-center justify-between border-t border-zinc-100 pt-3">
          <span class="text-xs text-zinc-500">
            {{ usandoPadrao ? 'Usando a cor padrão do StartBig' : `Cor personalizada: ${form.cor_tema}` }}
          </span>
          <button
            type="button"
            :disabled="usandoPadrao"
            class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-zinc-200 text-xs font-semibold text-zinc-600 hover:border-brand-primary hover:text-brand-primary transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            @click="restaurarPadrao"
          >
            <RotateCcw :size="13" /> Restaurar padrão
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
