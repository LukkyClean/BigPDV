<script setup lang="ts">
/**
 * @component PositionModal
 * @description Modal for creating/editing cargos with permission matrix
 */

import { computed, ref, onMounted, onUnmounted, watch } from 'vue';
import { Check, X, XCircle, ShieldCheck } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';

import { usePositionModal } from '../composables/usePositionModal';
import { usePositionFormProvider } from '../composables/usePositionForm';
import { useDeletePositionMutation } from '../composables/usePositionsQuery';
import {
  PERMISSION_KEYS,
  PERMISSION_MATRIX,
  getAccessLevel,
  getPermissionStats,
} from '../constants/positions.constants';

const {
  isOpen,
  isCreateMode,
  isViewMode,
  modalTitle,
  closeModal,
  selectedPosition,
} = usePositionModal();

const {
  nome,
  permissoes,
  comissaoVenda,
  comissaoServico,
  metaMensal,
  comissaoModo,
  errors,
  submitCount,
  apiError,
  isPending,
  setPermission,
  setAllPermissions,
  onSubmit,
} = usePositionFormProvider();

const deleteMutation = useDeletePositionMutation();

// Conversão só na exibição: form guarda basis points (500=5%) e centavos.
function bpParaStr(bp: number | null | undefined): string {
  return bp != null ? String(bp / 100) : '';
}
function strParaBp(v: string): number | null {
  const n = parseFloat(String(v).replace(',', '.'));
  return isNaN(n) ? null : Math.round(n * 100);
}
const comissaoVendaPct = computed<string>({
  get: () => bpParaStr(comissaoVenda.value),
  set: (v) => { comissaoVenda.value = strParaBp(v); },
});
const comissaoServicoPct = computed<string>({
  get: () => bpParaStr(comissaoServico.value),
  set: (v) => { comissaoServico.value = strParaBp(v); },
});
const metaReais = computed<number>({
  get: () => (metaMensal.value != null ? metaMensal.value / 100 : 0),
  set: (v) => { metaMensal.value = v ? Math.round(Number(v) * 100) : null; },
});

// Modo de comissão: null é tratado como 'direto' na UI (retrocompatível).
const modoAtual = computed<'direto' | 'meta'>(() =>
  comissaoModo.value === 'meta' ? 'meta' : 'direto',
);
function setModo(modo: 'direto' | 'meta') {
  comissaoModo.value = modo;
}
// Aviso: modo 'meta' sem meta definida não trava nada (cai em 'direto' no cálculo).
const metaExigidaSemvalor = computed(
  () => modoAtual.value === 'meta' && !metaMensal.value,
);

const totalPermissions = computed(() => PERMISSION_KEYS.length);
const permissionStats = computed(() => getPermissionStats(permissoes.value));
const enabledPermissions = computed(() => permissionStats.value.enabled);
const accessLevel = computed(() => getAccessLevel(permissoes.value));

const isAllSelected = computed(
  () => enabledPermissions.value === totalPermissions.value && totalPermissions.value > 0,
);

// Cargo Master / de acesso total (permissão 'all'): a matriz é PROTEGIDA — não dá
// para desmarcar nada, senão o acesso quebraria (o backend concede tudo via 'all',
// ver depends.py). Detecta pela permissão 'all' ou pelo nome "master".
const cargoAcessoTotal = computed(
  () =>
    permissoes.value?.all === true ||
    selectedPosition.value?.nome?.toLowerCase() === 'master',
);
// Matriz somente-leitura: no modo visualização OU quando é cargo de acesso total.
const matrizBloqueada = computed(() => isViewMode.value || cargoAcessoTotal.value);

function togglePermission(key: string) {
  if (matrizBloqueada.value) return;
  const currentValue = !!permissoes.value?.[key];
  setPermission(key, !currentValue);
}

/**
 * A célula deve aparecer marcada quando a permissão específica está ligada OU
 * quando o cargo tem acesso total (`all`) — é como o backend concede acesso
 * (depends.py: `permissoes.get("all")`). Sem isso, um cargo com `{all:true}`
 * (ex.: Master/admin) mostrava a matriz inteira em branco, mesmo com acesso total.
 */
function permissaoMarcada(key?: string): boolean {
  if (!key) return false;
  return !!(permissoes.value?.[key] || permissoes.value?.all);
}

function toggleAllPermissions() {
  if (matrizBloqueada.value) return;
  setAllPermissions(!isAllSelected.value);
}

function handleDelete() {
  if (!selectedPosition.value) return;
  const confirmed = window.confirm(
    `Tem certeza que deseja excluir o cargo "${selectedPosition.value.nome}"?`,
  );
  if (!confirmed) return;

  deleteMutation.mutate(selectedPosition.value.id, {
    onSuccess: () => {
      closeModal();
    },
  });
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && isOpen.value) {
    closeModal();
  }
}

const gestoComecouNoFundo = ref(false);

function handleBackdropMousedown(event: MouseEvent) {
  gestoComecouNoFundo.value = (event.target as HTMLElement).classList.contains('modal-backdrop');
}

/**
 * Fecha ao clicar no fundo — mas só quando o clique COMEÇOU no fundo.
 *
 * Decidir pelo `click` fechava o modal no meio da edição: ao arrastar o mouse
 * para selecionar o texto de um campo e soltar fora dele, o navegador dispara o
 * `click` no ancestral comum entre onde apertou e onde soltou — o próprio
 * backdrop. Só acontecia com o mouse; com teclado nunca.
 */
function handleBackdropClick(event: MouseEvent) {
  const terminouNoFundo = (event.target as HTMLElement).classList.contains('modal-backdrop');
  if (gestoComecouNoFundo.value && terminouNoFundo) {
    closeModal();
  }
  gestoComecouNoFundo.value = false;
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown);
});

watch(isOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : '';
});
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition ease-out duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition ease-in duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen"
        class="modal-backdrop fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        @mousedown="handleBackdropMousedown"
        @click="handleBackdropClick"
      >
        <Transition
          enter-active-class="transition ease-out duration-300"
          enter-from-class="opacity-0 scale-95 translate-y-4"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="transition ease-in duration-200"
          leave-from-class="opacity-100 scale-100 translate-y-0"
          leave-to-class="opacity-0 scale-95 translate-y-4"
        >
          <div
            v-if="isOpen"
            class="flex w-full max-w-6xl max-h-[90vh] flex-col overflow-hidden rounded-2xl bg-white shadow-2xl mx-4"
          >
            <div class="flex items-center justify-between border-b border-zinc-200 px-6 py-4">
              <div>
                <h2 class="text-xl font-bold text-zinc-800">{{ modalTitle }}</h2>
              </div>
              <button
                type="button"
                class="rounded-lg p-2 text-zinc-400 transition-colors hover:bg-red-50 hover:text-red-600 cursor-pointer"
                @click="closeModal"
              >
                <X :size="20" />
              </button>
            </div>

            <div class="flex-1 overflow-y-auto px-6 py-6">
              <div
                v-if="apiError"
                class="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
              >
                {{ apiError }}
              </div>

              <form id="position-form" class="grid grid-cols-1 gap-6 lg:grid-cols-[320px_1fr]" @submit.prevent="onSubmit">
                <div class="space-y-6">
                  <div class="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
                    <h3 class="text-sm font-semibold text-zinc-800">Informacoes Gerais</h3>
                    <p class="mt-1 text-xs text-zinc-400">
                      Defina o nome do cargo e o escopo principal.
                    </p>
                    <div class="mt-5">
                      <BaseInput
                        v-model="nome"
                        label="Nome do cargo"
                        placeholder="Ex: Gerente de Vendas"
                        :required="true"
                        :error="submitCount > 0 ? errors.nome : ''"
                        :disabled="isViewMode"
                      />
                    </div>
                    <div class="mt-4 rounded-xl border border-dashed border-zinc-200 bg-zinc-50 p-3">
                      <p class="text-[10px] font-semibold uppercase text-zinc-400">Resumo</p>
                      <div class="mt-2 text-xs text-zinc-600">
                        {{ enabledPermissions }} de {{ totalPermissions }} permissoes habilitadas
                      </div>
                    </div>
                  </div>

                  <div class="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
                    <h3 class="text-sm font-semibold text-zinc-800">Comissão</h3>
                    <p class="mt-1 text-xs text-zinc-400">
                      Padrão deste cargo. Deixe vazio para "sem comissão".
                    </p>
                    <div class="mt-5 grid grid-cols-2 gap-3">
                      <div>
                        <label class="mb-1 block text-xs font-medium text-zinc-600">% sobre vendas</label>
                        <div class="flex items-center gap-1.5">
                          <BaseInput v-model="comissaoVendaPct" type="number" placeholder="0" :disabled="isViewMode" />
                          <span class="text-sm font-medium text-zinc-400">%</span>
                        </div>
                      </div>
                      <div>
                        <label class="mb-1 block text-xs font-medium text-zinc-600">% sobre serviços</label>
                        <div class="flex items-center gap-1.5">
                          <BaseInput v-model="comissaoServicoPct" type="number" placeholder="0" :disabled="isViewMode" />
                          <span class="text-sm font-medium text-zinc-400">%</span>
                        </div>
                      </div>
                    </div>
                    <div class="mt-5">
                      <label class="mb-1.5 block text-xs font-medium text-zinc-600">Quando pagar a comissão</label>
                      <div class="grid grid-cols-2 gap-2">
                        <button
                          type="button"
                          :disabled="isViewMode"
                          class="rounded-xl border px-3 py-2.5 text-left transition disabled:opacity-60"
                          :class="modoAtual === 'direto'
                            ? 'border-indigo-500 bg-indigo-50 ring-1 ring-indigo-500'
                            : 'border-zinc-200 bg-white hover:border-zinc-300'"
                          @click="setModo('direto')"
                        >
                          <span class="block text-xs font-semibold text-zinc-800">Direto</span>
                          <span class="mt-0.5 block text-[11px] leading-tight text-zinc-500">Paga em toda venda/serviço</span>
                        </button>
                        <button
                          type="button"
                          :disabled="isViewMode"
                          class="rounded-xl border px-3 py-2.5 text-left transition disabled:opacity-60"
                          :class="modoAtual === 'meta'
                            ? 'border-indigo-500 bg-indigo-50 ring-1 ring-indigo-500'
                            : 'border-zinc-200 bg-white hover:border-zinc-300'"
                          @click="setModo('meta')"
                        >
                          <span class="block text-xs font-semibold text-zinc-800">Só ao bater a meta</span>
                          <span class="mt-0.5 block text-[11px] leading-tight text-zinc-500">Trava até atingir a meta</span>
                        </button>
                      </div>
                    </div>
                    <div class="mt-4">
                      <label class="mb-1 block text-xs font-medium text-zinc-600">
                        Meta mensal
                        <span v-if="modoAtual === 'meta'" class="text-indigo-600">(usada como gatilho)</span>
                        <span v-else>(opcional)</span>
                      </label>
                      <BaseMoneyInput v-model="metaReais" :disabled="isViewMode" />
                      <p v-if="metaExigidaSemvalor" class="mt-1.5 text-[11px] leading-tight text-amber-600">
                        Sem meta definida, o modo "Só ao bater a meta" não trava nada — a comissão sai como no modo direto.
                      </p>
                    </div>
                  </div>

                  <div
                    class="rounded-2xl bg-linear-to-br p-5 text-white shadow-lg"
                    :class="accessLevel.gradient"
                  >
                    <div class="flex items-center justify-between">
                      <div class="text-sm font-semibold">Nivel de Acesso</div>
                      <span class="rounded-full bg-white/20 px-3 py-1 text-[10px] font-semibold uppercase tracking-widest">
                        {{ accessLevel.badge }}
                      </span>
                    </div>
                    <h4 class="mt-3 text-xl font-bold">{{ accessLevel.label }}</h4>
                    <p class="mt-2 text-sm text-white/80">
                      {{ accessLevel.description }}
                    </p>
                    <div class="mt-4 text-xs text-white/70">
                      Cobertura geral: {{ enabledPermissions }} / {{ totalPermissions }}
                    </div>
                  </div>
                </div>

                <div class="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
                  <div class="flex items-center justify-between">
                    <div>
                      <h3 class="text-sm font-semibold text-zinc-800">Matriz de Permissoes</h3>
                      <p class="mt-1 text-xs text-zinc-400">
                        Defina o que este cargo pode visualizar, editar e excluir.
                      </p>
                    </div>
                    <button
                      v-if="!cargoAcessoTotal"
                      type="button"
                      class="text-xs font-semibold text-brand-primary hover:text-brand-primary/80"
                      :disabled="isViewMode"
                      :class="isViewMode ? 'cursor-not-allowed opacity-50' : ''"
                      @click="toggleAllPermissions"
                    >
                      {{ isAllSelected ? 'Desmarcar tudo' : 'Marcar tudo' }}
                    </button>
                  </div>

                  <div
                    v-if="cargoAcessoTotal"
                    class="mt-3 flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700"
                  >
                    <ShieldCheck :size="14" class="shrink-0" />
                    Cargo com acesso total (Master). As permissões são fixas e não podem ser alteradas — protege o acesso do sistema.
                  </div>

                  <div class="mt-6 overflow-hidden rounded-xl border border-zinc-100">
                    <div class="grid grid-cols-[1fr_88px_88px_88px] items-center bg-zinc-50 px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-zinc-400">
                      <span>Modulo</span>
                      <span class="text-center">Visualizar</span>
                      <span class="text-center">Editar/Criar</span>
                      <span class="text-center">Excluir</span>
                    </div>

                    <div
                      v-for="item in PERMISSION_MATRIX"
                      :key="item.id"
                      class="grid grid-cols-[1fr_88px_88px_88px] items-center border-t border-zinc-100 px-4 py-3"
                    >
                      <div class="flex items-center gap-3">
                        <div class="flex h-9 w-9 items-center justify-center rounded-xl bg-zinc-50 text-zinc-600">
                          <component :is="item.icon" :size="18" />
                        </div>
                        <div>
                          <p class="text-sm font-semibold text-zinc-800">{{ item.label }}</p>
                          <p class="text-xs text-zinc-400">{{ item.description }}</p>
                        </div>
                      </div>

                      <div class="flex items-center justify-center">
                        <button
                          type="button"
                          :disabled="matrizBloqueada"
                          :class="[
                            'flex h-9 w-9 items-center justify-center rounded-full border transition-all',
                            permissaoMarcada(item.viewKey)
                              ? 'border-emerald-200 bg-emerald-50 text-emerald-600'
                              : 'border-zinc-200 bg-zinc-50 text-zinc-400',
                            matrizBloqueada ? 'cursor-not-allowed opacity-60' : 'hover:border-emerald-300',
                          ]"
                          @click="togglePermission(item.viewKey)"
                        >
                          <Check v-if="permissaoMarcada(item.viewKey)" :size="16" />
                          <XCircle v-else :size="16" />
                        </button>
                      </div>

                      <div class="flex items-center justify-center">
                        <button
                          type="button"
                          :disabled="matrizBloqueada"
                          :class="[
                            'flex h-9 w-9 items-center justify-center rounded-full border transition-all',
                            permissaoMarcada(item.manageKey)
                              ? 'border-emerald-200 bg-emerald-50 text-emerald-600'
                              : 'border-zinc-200 bg-zinc-50 text-zinc-400',
                            matrizBloqueada ? 'cursor-not-allowed opacity-60' : 'hover:border-emerald-300',
                          ]"
                          @click="togglePermission(item.manageKey)"
                        >
                          <Check v-if="permissaoMarcada(item.manageKey)" :size="16" />
                          <XCircle v-else :size="16" />
                        </button>
                      </div>

                      <div class="flex items-center justify-center">
                        <button
                          v-if="item.deleteKey"
                          type="button"
                          :disabled="matrizBloqueada"
                          :class="[
                            'flex h-9 w-9 items-center justify-center rounded-full border transition-all',
                            permissaoMarcada(item.deleteKey)
                              ? 'border-emerald-200 bg-emerald-50 text-emerald-600'
                              : 'border-zinc-200 bg-zinc-50 text-zinc-400',
                            matrizBloqueada ? 'cursor-not-allowed opacity-60' : 'hover:border-emerald-300',
                          ]"
                          @click="togglePermission(item.deleteKey)"
                        >
                          <Check v-if="permissaoMarcada(item.deleteKey)" :size="16" />
                          <XCircle v-else :size="16" />
                        </button>
                        <span v-else class="text-zinc-300">—</span>
                      </div>
                    </div>
                  </div>
                </div>
              </form>
            </div>

            <div class="flex flex-col gap-3 border-t border-zinc-200 bg-zinc-50 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <BaseButton
                  v-if="!isCreateMode && !isViewMode"
                  type="button"
                  variant="danger"
                  :disabled="deleteMutation.isPending.value"
                  @click="handleDelete"
                >
                  Excluir Cargo
                </BaseButton>
              </div>
              <div class="flex items-center justify-end gap-3">
                <BaseButton
                  type="button"
                  variant="secondary"
                  @click="closeModal"
                >
                  {{ isViewMode ? 'Fechar' : 'Descartar Alteracoes' }}
                </BaseButton>
                <BaseButton
                  v-if="!isViewMode"
                  type="submit"
                  variant="primary"
                  :is-loading="isPending"
                  @click="onSubmit"
                >
                  {{ isCreateMode ? 'Salvar Cargo' : 'Atualizar Cargo' }}
                </BaseButton>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
