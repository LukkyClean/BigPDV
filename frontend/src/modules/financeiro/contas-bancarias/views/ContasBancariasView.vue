<script setup lang="ts">
/**
 * Onde o dinheiro da loja fica.
 *
 * Antes desta tela o sistema só tinha a "Caixa da loja" que ele mesmo semeia no
 * primeiro acesso — para o lojista que só trabalha com dinheiro conseguir dar
 * baixa no primeiro dia. Não havia como cadastrar banco nem cartão, o que
 * deixava o tipo CARTAO_CREDITO inalcançável e o "Entrou em" da baixa com uma
 * opção só.
 *
 * NÃO é integração bancária: ninguém se conecta a banco nenhum. É só o nome do
 * lugar, para o dinheiro ter endereço.
 */
import { computed, ref } from 'vue';
import { Banknote, CreditCard, Landmark, Plus, Star } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import { useToast } from '@/shared/composables/useToast';

import {
  useAtualizarContaBancaria,
  useContasBancariasQuery,
  useCriarContaBancaria,
} from '../../shared/composables/useFinanceiro';
import type { ContaBancaria } from '../../shared/schemas/financeiro.schema';

const toast = useToast();
const { data: contas, isLoading } = useContasBancariasQuery();
const criar = useCriarContaBancaria();
const atualizar = useAtualizarContaBancaria();

const TIPOS = [
  {
    valor: 'CAIXA',
    titulo: 'Caixa',
    ajuda: 'Dinheiro em espécie na loja',
    icone: Banknote,
  },
  {
    valor: 'BANCO',
    titulo: 'Banco',
    ajuda: 'Conta corrente, poupança ou digital',
    icone: Landmark,
  },
  {
    valor: 'CARTAO_CREDITO',
    titulo: 'Cartão',
    ajuda: 'O que a operadora tem para repassar',
    icone: CreditCard,
  },
];

function iconeDoTipo(tipo: string) {
  return TIPOS.find((t) => t.valor === tipo)?.icone ?? Landmark;
}

function rotuloDoTipo(tipo: string): string {
  return TIPOS.find((t) => t.valor === tipo)?.titulo ?? tipo;
}

// --- Formulário ---
const aberto = ref(false);
const emEdicao = ref<ContaBancaria | null>(null);
const nome = ref('');
const tipo = ref('BANCO');
const principal = ref(false);

function abrirNova() {
  emEdicao.value = null;
  nome.value = '';
  tipo.value = 'BANCO';
  principal.value = false;
  aberto.value = true;
}

function abrirEdicao(conta: ContaBancaria) {
  emEdicao.value = conta;
  nome.value = conta.nome;
  tipo.value = conta.tipo;
  principal.value = conta.principal;
  aberto.value = true;
}

const salvando = computed(() => criar.isPending.value || atualizar.isPending.value);
const podeSalvar = computed(() => !!nome.value.trim());

function salvar() {
  if (!podeSalvar.value) return;
  const aoErrar = (e: any) =>
    toast.error(e?.response?.data?.detail ?? 'Não foi possível salvar a conta');
  const fechar = () => (aberto.value = false);

  if (emEdicao.value) {
    atualizar.mutate(
      {
        id: emEdicao.value.id,
        dados: { nome: nome.value.trim(), tipo: tipo.value, principal: principal.value },
      },
      { onSuccess: fechar, onError: aoErrar },
    );
  } else {
    criar.mutate(
      { nome: nome.value.trim(), tipo: tipo.value, principal: principal.value },
      { onSuccess: fechar, onError: aoErrar },
    );
  }
}

// Só uma conta pode ser a sugerida; o backend limpa as outras sozinho.
function tornarPrincipal(conta: ContaBancaria) {
  atualizar.mutate({ id: conta.id, dados: { principal: true } });
}

function alternarAtivo(conta: ContaBancaria) {
  atualizar.mutate({ id: conta.id, dados: { ativo: !conta.ativo } });
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <p class="max-w-2xl text-sm text-gray-500">
        Cadastre onde o dinheiro entra e sai: a gaveta da loja, as contas de banco e os
        cartões. É o que aparece no “Entrou em” e no “Saiu de” quando você dá baixa numa conta.
      </p>
      <BaseButton variant="primary" @click="abrirNova">
        <Plus :size="16" class="mr-1.5" /> Nova conta
      </BaseButton>
    </div>

    <div v-if="isLoading" class="text-sm text-gray-500">Carregando…</div>

    <div v-else class="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
      <ul class="divide-y divide-gray-100">
        <li
          v-for="conta in contas" :key="conta.id"
          class="flex flex-wrap items-center gap-3 px-5 py-3.5"
          :class="!conta.ativo && 'bg-gray-50'"
        >
          <component :is="iconeDoTipo(conta.tipo)" :size="18" class="shrink-0 text-gray-400" />

          <button type="button" class="min-w-0 flex-1 text-left cursor-pointer" @click="abrirEdicao(conta)">
            <span class="text-sm font-medium" :class="conta.ativo ? 'text-gray-800' : 'text-gray-400 line-through'">
              {{ conta.nome }}
            </span>
            <span class="ml-2 text-xs text-gray-400">{{ rotuloDoTipo(conta.tipo) }}</span>
          </button>

          <span
            v-if="conta.principal"
            class="flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700"
          >
            <Star :size="11" /> padrão
          </span>
          <button
            v-else-if="conta.ativo"
            type="button"
            class="text-xs font-medium text-gray-600 hover:text-gray-900 cursor-pointer"
            @click="tornarPrincipal(conta)"
          >
            Tornar padrão
          </button>

          <button
            type="button"
            class="text-xs font-semibold cursor-pointer"
            :class="conta.ativo ? 'text-gray-500 hover:text-gray-700' : 'text-brand-primary'"
            @click="alternarAtivo(conta)"
          >
            {{ conta.ativo ? 'Desativar' : 'Reativar' }}
          </button>
        </li>
      </ul>
    </div>

    <p class="text-xs text-gray-400">
      Contas desativadas somem dos novos lançamentos, mas continuam valendo nos antigos — por
      isso não existe excluir. A conta marcada como padrão vem pré-selecionada nas baixas.
    </p>

    <BaseModal
      :is-open="aberto"
      :title="emEdicao ? 'Editar conta' : 'Nova conta'"
      size="sm"
      overlay
      @close="aberto = false"
    >
      <div class="flex flex-col gap-4">
        <BaseInput v-model="nome" label="Nome" placeholder="Ex.: Nubank, Itaú c/c, Caixa da loja" required />

        <fieldset class="flex flex-col gap-2">
          <legend class="mb-1.5 block text-sm font-medium text-gray-700">Tipo</legend>
          <div class="grid gap-2 sm:grid-cols-3">
            <label
              v-for="opcao in TIPOS" :key="opcao.valor"
              class="cursor-pointer rounded-xl border px-3 py-2.5 transition"
              :class="tipo === opcao.valor
                ? 'border-brand-primary bg-brand-primary/5 ring-1 ring-brand-primary'
                : 'border-gray-200 hover:border-gray-300'"
            >
              <input v-model="tipo" type="radio" :value="opcao.valor" class="sr-only" />
              <span class="flex items-center gap-1.5 text-sm font-medium text-gray-800">
                <component :is="opcao.icone" :size="14" /> {{ opcao.titulo }}
              </span>
              <span class="mt-0.5 block text-[11px] text-gray-400">{{ opcao.ajuda }}</span>
            </label>
          </div>
        </fieldset>

        <label class="flex items-center gap-2 text-sm text-gray-700">
          <input v-model="principal" type="checkbox" class="h-3.5 w-3.5 rounded border-gray-300 accent-brand-primary" />
          Usar como padrão nas baixas
        </label>
      </div>

      <template #footer>
        <div class="flex w-full justify-end gap-2">
          <BaseButton variant="secondary" class="px-5" @click="aberto = false">Cancelar</BaseButton>
          <BaseButton
            variant="primary" class="px-5"
            :disabled="!podeSalvar" :is-loading="salvando"
            @click="salvar"
          >
            Salvar
          </BaseButton>
        </div>
      </template>
    </BaseModal>
  </div>
</template>
