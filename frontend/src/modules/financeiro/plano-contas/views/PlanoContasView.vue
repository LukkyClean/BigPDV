<script setup lang="ts">
/**
 * As categorias que classificam cada despesa.
 *
 * NÃO existe excluir, só desativar — e isso é regra, não limitação da tela: a
 * categoria pode estar amarrada a contas antigas, e apagá-la faria o relatório
 * do ano passado mostrar "sem categoria" onde sempre houve uma.
 */
import { ref } from 'vue';
import { Plus, Check, X } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import { useToast } from '@/shared/composables/useToast';

import {
  useAtualizarPlanoConta,
  useCriarPlanoConta,
  usePlanoContasQuery,
} from '../../shared/composables/useFinanceiro';

const toast = useToast();
const { data: categorias, isLoading } = usePlanoContasQuery(false);
const criar = useCriarPlanoConta();
const atualizar = useAtualizarPlanoConta();

const novoNome = ref('');
const editandoId = ref<number | null>(null);
const nomeEditado = ref('');

function adicionar() {
  const nome = novoNome.value.trim();
  if (!nome) return;
  criar.mutate(nome, {
    onSuccess: () => (novoNome.value = ''),
    // O backend recusa nome repetido com 400 e uma mensagem pronta. Mostrar a
    // dele em vez de uma genérica é o que diz ao usuário QUAL nome colidiu.
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail ?? 'Não foi possível criar a categoria'),
  });
}

function abrirEdicao(id: number, nome: string) {
  editandoId.value = id;
  nomeEditado.value = nome;
}

function salvarEdicao(id: number) {
  const nome = nomeEditado.value.trim();
  if (!nome) return;
  atualizar.mutate({ id, dados: { nome } }, { onSuccess: () => (editandoId.value = null) });
}

function alternarAtivo(id: number, ativo: boolean) {
  atualizar.mutate({ id, dados: { ativo: !ativo } });
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <p class="max-w-2xl text-sm text-gray-500">
      As categorias classificam cada conta que você lança. É o que faz o resultado do mês
      dizer <strong class="text-gray-700">onde</strong> o dinheiro foi, e não só quanto saiu.
    </p>

    <!-- Nova categoria -->
    <form class="flex flex-wrap items-end gap-3" @submit.prevent="adicionar">
      <div class="w-full sm:w-72">
        <BaseInput v-model="novoNome" label="Nova categoria" placeholder="Ex.: Contador" />
      </div>
      <BaseButton type="submit" variant="primary" :disabled="!novoNome.trim() || criar.isPending.value">
        <Plus :size="16" class="mr-1.5" /> Adicionar
      </BaseButton>
    </form>

    <div v-if="isLoading" class="text-sm text-gray-500">Carregando…</div>

    <div v-else class="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
      <ul class="divide-y divide-gray-100">
        <li
          v-for="c in categorias" :key="c.id"
          class="flex flex-wrap items-center gap-3 px-5 py-3.5"
          :class="!c.ativo && 'bg-gray-50'"
        >
          <!-- Modo edição -->
          <template v-if="editandoId === c.id">
            <div class="w-full sm:w-64">
              <BaseInput v-model="nomeEditado" @keyup.enter="salvarEdicao(c.id)" />
            </div>
            <button type="button" class="p-1.5 text-emerald-600 cursor-pointer" @click="salvarEdicao(c.id)" aria-label="Salvar">
              <Check :size="18" />
            </button>
            <button type="button" class="p-1.5 text-gray-400 cursor-pointer" @click="editandoId = null" aria-label="Cancelar">
              <X :size="18" />
            </button>
          </template>

          <!-- Modo leitura -->
          <template v-else>
            <button
              type="button"
              class="flex-1 min-w-0 text-left cursor-pointer"
              @click="abrirEdicao(c.id, c.nome)"
            >
              <span class="text-sm font-medium" :class="c.ativo ? 'text-gray-800' : 'text-gray-400 line-through'">
                {{ c.nome }}
              </span>
            </button>

            <span v-if="c.em_uso" class="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-600">
              em uso
            </span>

            <button
              type="button"
              class="text-xs font-semibold cursor-pointer"
              :class="c.ativo ? 'text-gray-500 hover:text-gray-700' : 'text-brand-primary'"
              @click="alternarAtivo(c.id, c.ativo)"
            >
              {{ c.ativo ? 'Desativar' : 'Reativar' }}
            </button>
          </template>
        </li>
      </ul>
    </div>

    <p class="text-xs text-gray-400">
      Categorias desativadas somem dos novos lançamentos, mas continuam valendo nas contas
      antigas — por isso não existe excluir.
    </p>
  </div>
</template>
