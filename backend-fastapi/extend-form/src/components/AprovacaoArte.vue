<script setup lang="ts">
/**
 * @component AprovacaoArte
 * @description Cliente vê o mockup no celular e libera (ou pede ajuste da) arte.
 *
 * Existe ao lado do ChecklistForm, escolhido pela capacidade `aprovacao_arte`
 * do segmento — nenhuma tela de vistoria muda por causa deste arquivo.
 *
 * É o momento mais barato do processo para descobrir que a cor está errada:
 * depois de gravar a tela e estampar 200 peças, o erro custa as 200 peças.
 * Por isso a resposta é gravada com NOME e HORA — numa discussão sobre quem
 * aprovou o quê, "o cliente disse que podia" não é prova.
 */
import { computed, ref } from 'vue'

import { urlDaLogo } from '../theme/aplicarTema'

interface Props {
  /** Fotos da OS: o mockup que o cliente precisa ver. */
  fotos: string[]
  dadosAdicionais: Record<string, unknown>
  isSubmitting: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:dadosAdicionais': [valor: Record<string, unknown>]
  submit: []
}>()

/** Chaves gravadas em dados_adicionais da OS. */
const CHAVE_STATUS = 'arte_status'
const CHAVE_QUEM = 'arte_respondido_por'
const CHAVE_QUANDO = 'arte_respondido_em'
const CHAVE_OBSERVACAO = 'arte_observacao'

const nome = ref((props.dadosAdicionais[CHAVE_QUEM] as string) ?? '')
const observacao = ref((props.dadosAdicionais[CHAVE_OBSERVACAO] as string) ?? '')
const pedindoAjuste = ref(false)
const erro = ref('')

/** Resposta anterior, quando a arte já foi respondida uma vez. */
const statusAnterior = computed(() => props.dadosAdicionais[CHAVE_STATUS] as string | undefined)

// As fotos vêm como caminho salvo no banco; o celular precisa da URL completa,
// pela mesma regra da logo.
const imagens = computed(() => props.fotos.map((foto) => urlDaLogo(foto)).filter(Boolean) as string[])

function responder(status: 'APROVADA' | 'AJUSTE_SOLICITADO') {
  erro.value = ''

  if (!nome.value.trim()) {
    erro.value = 'Escreva seu nome para registrar a resposta.'
    return
  }
  if (status === 'AJUSTE_SOLICITADO' && !observacao.value.trim()) {
    erro.value = 'Diga o que precisa mudar para a loja saber o que corrigir.'
    return
  }

  emit('update:dadosAdicionais', {
    ...props.dadosAdicionais,
    [CHAVE_STATUS]: status,
    [CHAVE_QUEM]: nome.value.trim(),
    // ISO em UTC: o backend guarda tudo em UTC e quem converte é a exibição.
    [CHAVE_QUANDO]: new Date().toISOString(),
    [CHAVE_OBSERVACAO]: status === 'AJUSTE_SOLICITADO' ? observacao.value.trim() : '',
  })
  emit('submit')
}
</script>

<template>
  <div class="space-y-5">
    <!-- Já respondida antes: a loja pode ter mandado um mockup novo, então a
         resposta continua aberta — mas o cliente precisa saber o que consta. -->
    <div
      v-if="statusAnterior"
      class="rounded-xl border p-3 text-sm"
      :class="statusAnterior === 'APROVADA'
        ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
        : 'border-amber-200 bg-amber-50 text-amber-800'"
    >
      <p class="font-semibold">
        {{ statusAnterior === 'APROVADA' ? 'Arte já aprovada' : 'Ajuste já solicitado' }}
      </p>
      <p class="text-xs mt-0.5">
        por {{ dadosAdicionais[CHAVE_QUEM] || 'não informado' }}. Respondendo de novo, esta
        resposta substitui a anterior.
      </p>
    </div>

    <section class="space-y-3">
      <h2 class="text-sm font-bold text-slate-700">Confira a arte</h2>

      <div v-if="imagens.length > 0" class="space-y-3">
        <img
          v-for="(imagem, indice) in imagens"
          :key="indice"
          :src="imagem"
          :alt="`Arte ${indice + 1}`"
          class="w-full rounded-xl border border-slate-200 bg-white"
        />
      </div>

      <!-- Sem foto não há o que aprovar; dizer isso é melhor que mostrar um
           quadro vazio e deixar o cliente achar que o celular falhou. -->
      <p v-else class="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
        A loja ainda não anexou a imagem da arte. Peça o envio antes de aprovar.
      </p>
    </section>

    <section class="space-y-3">
      <label class="block">
        <span class="text-sm font-semibold text-slate-700">Seu nome</span>
        <input
          v-model="nome"
          type="text"
          placeholder="Quem está aprovando"
          class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2.5 text-base focus:border-brand-primary focus:outline-none"
        />
      </label>

      <label v-if="pedindoAjuste" class="block">
        <span class="text-sm font-semibold text-slate-700">O que precisa mudar?</span>
        <textarea
          v-model="observacao"
          rows="3"
          placeholder="Ex: o verde está mais escuro que o da logo"
          class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2.5 text-base focus:border-brand-primary focus:outline-none"
        />
      </label>

      <p v-if="erro" class="text-sm text-red-600">{{ erro }}</p>
    </section>

    <section class="space-y-2 pb-4">
      <button
        type="button"
        :disabled="isSubmitting || imagens.length === 0"
        class="w-full rounded-xl bg-emerald-600 py-3.5 text-base font-bold text-white disabled:opacity-50"
        @click="pedindoAjuste = false; responder('APROVADA')"
      >
        {{ isSubmitting ? 'Enviando...' : 'Aprovar e liberar produção' }}
      </button>

      <button
        v-if="!pedindoAjuste"
        type="button"
        :disabled="isSubmitting"
        class="w-full rounded-xl border-2 border-amber-500 py-3 text-base font-bold text-amber-700 disabled:opacity-50"
        @click="pedindoAjuste = true"
      >
        Pedir ajuste
      </button>

      <button
        v-else
        type="button"
        :disabled="isSubmitting"
        class="w-full rounded-xl bg-amber-500 py-3.5 text-base font-bold text-white disabled:opacity-50"
        @click="responder('AJUSTE_SOLICITADO')"
      >
        {{ isSubmitting ? 'Enviando...' : 'Enviar pedido de ajuste' }}
      </button>
    </section>
  </div>
</template>
