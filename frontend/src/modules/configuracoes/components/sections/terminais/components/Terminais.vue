<script setup lang="ts">
/**
 * Os computadores da loja.
 *
 * POR QUE ESTA TELA EXISTE. As máquinas já se identificam sozinhas por HWID
 * desde sempre — o que faltava era gente conseguir dizer QUAL é qual. Sem nome,
 * a coluna Terminal do relatório de caixa mostrava vazio, e "diferença de
 * R$ 5,00" não dizia em qual gaveta; sem papel, o computador do escritório era
 * tratado como um caixa e passava a pedir abertura de turno para consultar
 * relatório.
 *
 * Salva por linha, na hora. Não usa o botão "Aplicar" do rodapé de propósito:
 * batizar uma máquina é uma ação por máquina, e agrupá-las num formulário só
 * faria o dono salvar quatro coisas para mudar uma.
 */
import { computed, reactive } from 'vue';
import { Check, Monitor, MonitorCog, ShieldAlert } from 'lucide-vue-next';

import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { useImpressaoStore } from '@/shared/stores/impressao.store';
import {
  useAtualizarTerminalMutation,
  useEsteTerminalQuery,
  useTerminaisQuery,
} from '@/modules/sales/caixa/composables/queries/useTerminaisQuery';
import type { PapelTerminal } from '@/modules/sales/caixa/services/terminal.service';

const { terminais, isLoading, isError } = useTerminaisQuery();
const { esteTerminal } = useEsteTerminalQuery();
const atualizar = useAtualizarTerminalMutation();

const impressao = useImpressaoStore();

/**
 * O nome em edição, por terminal.
 *
 * Pré-preenche com o nome que a configuração de impressão desta máquina já
 * guarda no disco: quem escreveu "Caixa 01" ali não deve ter que escrever de
 * novo, e os dois nomes concordando é melhor do que a loja ter dois nomes para
 * o mesmo computador.
 */
const rascunho = reactive<Record<number, string>>({});

function nomeEmEdicao(id: number, atual: string | null, ehEsta: boolean): string {
  if (rascunho[id] !== undefined) return rascunho[id];
  if (atual) return atual;
  return ehEsta ? (impressao.config?.nome_terminal ?? '') : '';
}

function ehEstaMaquina(hwid: string): boolean {
  return esteTerminal.value?.hwid === hwid;
}

const temTerminais = computed(() => terminais.value.length > 0);

function salvarNome(id: number, valor: string) {
  atualizar.mutate({ id, nome: valor.trim() || null });
}

function definirPapel(id: number, papel: PapelTerminal) {
  atualizar.mutate({ id, papel });
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div>
      <h3 class="text-base font-semibold text-zinc-900">Computadores da loja</h3>
      <p class="mt-1 text-sm text-zinc-500">
        Dê um nome a cada máquina e diga quais são caixas. O nome aparece no
        relatório de fechamento, ao lado da diferença de cada turno.
      </p>
    </div>

    <!-- A regra, dita antes de a pessoa escolher errado -->
    <div class="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
      <ShieldAlert class="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
      <p class="text-xs leading-relaxed text-amber-800">
        <strong>Retaguarda é exceção.</strong> Toda máquina é tratada como caixa
        até alguém dizer o contrário — inclusive as que ainda não foram
        configuradas. Marque como retaguarda só o computador que não recebe
        dinheiro, como o do escritório: ele deixa de pedir abertura de turno.
      </p>
    </div>

    <p v-if="isLoading" class="text-sm text-zinc-400">Carregando terminais…</p>

    <p v-else-if="isError" class="rounded-lg bg-zinc-50 p-4 text-sm text-zinc-500">
      Só o responsável pela loja pode ver e configurar os terminais.
    </p>

    <p v-else-if="!temTerminais" class="rounded-lg bg-zinc-50 p-4 text-sm text-zinc-500">
      Nenhuma máquina cadastrada ainda. Elas aparecem aqui sozinhas conforme
      cada computador entra no sistema.
    </p>

    <div v-else class="flex flex-col gap-3">
      <div
        v-for="t in terminais"
        :key="t.id"
        class="rounded-xl border border-zinc-200 bg-white p-4"
        :class="ehEstaMaquina(t.hwid) ? 'ring-1 ring-brand-primary/40' : ''"
      >
        <div class="mb-3 flex items-center gap-2">
          <component
            :is="t.papel === 'RETAGUARDA' ? MonitorCog : Monitor"
            class="h-4 w-4 shrink-0 text-zinc-400"
          />
          <span class="text-xs font-semibold uppercase tracking-wide text-zinc-400">
            {{ t.papel === 'RETAGUARDA' ? 'Retaguarda' : 'Caixa' }}
          </span>
          <span
            v-if="ehEstaMaquina(t.hwid)"
            class="rounded-full bg-brand-primary/10 px-2 py-0.5 text-[10px] font-bold text-brand-primary"
          >
            ESTE COMPUTADOR
          </span>
          <span v-if="!t.papel" class="text-[10px] text-zinc-400">
            (padrão — nunca configurado)
          </span>
        </div>

        <div class="flex flex-wrap items-end gap-3">
          <div class="min-w-[200px] flex-1">
            <BaseInput
              :model-value="nomeEmEdicao(t.id, t.nome, ehEstaMaquina(t.hwid))"
              label="Nome da máquina"
              placeholder="Caixa 01, Balcão, Escritório…"
              @update:model-value="(v: string) => (rascunho[t.id] = v)"
            />
          </div>

          <BaseButton
            variant="secondary"
            size="md"
            class="gap-1"
            :disabled="atualizar.isPending.value"
            @click="salvarNome(t.id, nomeEmEdicao(t.id, t.nome, ehEstaMaquina(t.hwid)))"
          >
            <Check :size="16" />
            Salvar nome
          </BaseButton>

          <div class="flex overflow-hidden rounded-lg border border-zinc-200">
            <button
              type="button"
              class="px-3 py-2 text-xs font-semibold transition-colors cursor-pointer"
              :class="t.papel !== 'RETAGUARDA'
                ? 'bg-brand-primary text-white'
                : 'bg-white text-zinc-500 hover:bg-zinc-50'"
              @click="definirPapel(t.id, 'PDV')"
            >
              É caixa
            </button>
            <button
              type="button"
              class="px-3 py-2 text-xs font-semibold transition-colors cursor-pointer"
              :class="t.papel === 'RETAGUARDA'
                ? 'bg-brand-primary text-white'
                : 'bg-white text-zinc-500 hover:bg-zinc-50'"
              @click="definirPapel(t.id, 'RETAGUARDA')"
            >
              Retaguarda
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
