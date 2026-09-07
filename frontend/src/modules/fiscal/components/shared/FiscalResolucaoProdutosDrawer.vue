<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { X, Save, Loader2, CheckCircle, Package } from 'lucide-vue-next';
import { useQueryClient } from '@tanstack/vue-query';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import { useToast } from '@/shared/composables/useToast';
import { upsertProdutoFiscal } from '@/modules/products/inventory/services/product.service';
import { useFiscalPendenciasQuery } from '../../composables/useFiscalPendenciasQuery';
import { fiscalKeys } from '../../constants/fiscal.constants';

defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:isOpen', value: boolean): void;
}>();

const close = () => emit('update:isOpen', false);

const toast = useToast();
const queryClient = useQueryClient();
const { data: pendencias, isLoading } = useFiscalPendenciasQuery();

const produtos = computed(() => pendencias.value?.produtos_sem_ncm ?? []);

// Estado editável por produto
interface ProdutoEdit {
  ncm: string;
  cfop_padrao: string;
  salvando: boolean;
  salvo: boolean;
}

const editMap = ref<Map<number, ProdutoEdit>>(new Map());

watch(produtos, (lista) => {
  for (const p of lista) {
    if (!editMap.value.has(p.id)) {
      editMap.value.set(p.id, { ncm: '', cfop_padrao: '', salvando: false, salvo: false });
    }
  }
}, { immediate: true });

function getEdit(id: number): ProdutoEdit {
  if (!editMap.value.has(id)) {
    editMap.value.set(id, { ncm: '', cfop_padrao: '', salvando: false, salvo: false });
  }
  return editMap.value.get(id)!;
}

function podesSalvar(id: number): boolean {
  const e = getEdit(id);
  return e.ncm.length === 8 && !e.salvando;
}

async function salvarProduto(produtoId: number) {
  const edit = getEdit(produtoId);
  if (edit.ncm.length !== 8) {
    toast.warning('NCM inválido', 'NCM deve ter exatamente 8 dígitos.');
    return;
  }

  edit.salvando = true;
  try {
    const dados: Record<string, string> = { ncm: edit.ncm };
    if (edit.cfop_padrao.length === 4) {
      dados.cfop_padrao = edit.cfop_padrao;
    }
    await upsertProdutoFiscal(produtoId, dados);
    edit.salvo = true;
    toast.success('Dados fiscais atualizados');
    queryClient.invalidateQueries({ queryKey: fiscalKeys.pendencias() });
    queryClient.invalidateQueries({ queryKey: fiscalKeys.resumo() });
  } catch {
    toast.error('Erro ao salvar dados fiscais');
  } finally {
    edit.salvando = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex justify-end"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/30" @click="close" />

        <!-- Drawer -->
        <div class="relative w-full max-w-lg bg-white shadow-2xl flex flex-col h-full">
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-zinc-100">
            <div>
              <h2 class="text-base font-bold text-zinc-900 flex items-center gap-2">
                <Package :size="18" class="text-brand-primary" />
                Resolver Pendências de Produtos
              </h2>
              <p class="text-xs text-zinc-400 mt-0.5">
                Preencha o NCM dos produtos para habilitar a emissão fiscal.
              </p>
            </div>
            <button
              type="button"
              class="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 transition-colors"
              @click="close"
            >
              <X :size="18" />
            </button>
          </div>

          <!-- Content -->
          <div class="flex-1 overflow-y-auto p-6">
            <div v-if="isLoading" class="flex items-center justify-center py-12">
              <Loader2 class="w-6 h-6 animate-spin text-zinc-400" />
            </div>

            <div v-else-if="produtos.length === 0" class="flex flex-col items-center justify-center py-12 text-center">
              <CheckCircle class="w-10 h-10 text-emerald-500 mb-3" />
              <p class="text-sm font-semibold text-zinc-800">Todos os produtos estão completos!</p>
              <p class="text-xs text-zinc-400 mt-1">Nenhuma pendência fiscal de produto encontrada.</p>
            </div>

            <div v-else class="space-y-4">
              <div
                v-for="produto in produtos"
                :key="produto.id"
                class="rounded-xl border border-zinc-200 p-4 transition-colors"
                :class="{ 'bg-emerald-50/50 border-emerald-200': getEdit(produto.id).salvo }"
              >
                <div class="flex items-center justify-between mb-3">
                  <p class="text-sm font-semibold text-zinc-800 truncate" :title="produto.nome">
                    {{ produto.nome }}
                  </p>
                  <CheckCircle v-if="getEdit(produto.id).salvo" :size="16" class="text-emerald-500 shrink-0" />
                </div>

                <div class="grid grid-cols-2 gap-3">
                  <BaseInput
                    v-model="getEdit(produto.id).ncm"
                    label="NCM"
                    placeholder="00000000"
                    maxlength="8"
                    :disabled="getEdit(produto.id).salvo"
                  />
                  <BaseInput
                    v-model="getEdit(produto.id).cfop_padrao"
                    label="CFOP (opcional)"
                    placeholder="5102"
                    maxlength="4"
                    :disabled="getEdit(produto.id).salvo"
                  />
                </div>

                <div class="mt-3 flex justify-end">
                  <BaseButton
                    v-if="!getEdit(produto.id).salvo"
                    variant="primary"
                    size="sm"
                    :disabled="!podesSalvar(produto.id)"
                    :is-loading="getEdit(produto.id).salvando"
                    @click="salvarProduto(produto.id)"
                  >
                    <Save :size="14" class="mr-1" />
                    Salvar
                  </BaseButton>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.drawer-enter-active,
.drawer-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from > div:last-child,
.drawer-leave-to > div:last-child {
  transform: translateX(100%);
}
</style>
