import { computed, unref, type MaybeRef } from 'vue';
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query';

import { REFETCH_CADASTROS } from '@/core/config/queryIntervals';
import { useToast } from '@/shared/composables/useToast';

import { financeiroKeys } from '../constants/queryKeys';
import * as service from '../services/financeiro.service';
import type {
  ConciliacaoBaixaLotePayload,
  ContaPagarBaixaPayload,
  ContaPagarFiltros,
  ContaPagarPayload,
  ContaReceberBaixaPayload,
  ContaReceberPayload,
  ExtratoFiltros,
} from '../schemas/financeiro.schema';

/**
 * Queries e mutations do módulo financeiro.
 *
 * TODA mutation invalida o PREFIXO inteiro (`financeiroKeys.todos`), nunca a
 * chave específica. Dar baixa numa conta mexe em quatro lugares ao mesmo tempo:
 * a lista, os totais do rodapé, o resultado do mês e as próximas a vencer.
 * Invalidar chave a chave deixaria algum desses desatualizado na tela, e o
 * usuário veria a conta sumir da lista com o total antigo embaixo.
 */

function useInvalidarFinanceiro() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: financeiroKeys.todos });
}

// ===========================================================================
// LEITURA
// ===========================================================================

export function usePlanoContasQuery(apenasAtivos: MaybeRef<boolean> = false) {
  return useQuery({
    queryKey: computed(() => [...financeiroKeys.planoContas(), unref(apenasAtivos)]),
    queryFn: () => service.listarPlanoContas(unref(apenasAtivos)),
    // Categoria é cadastro: muda uma vez por mês, não a cada minuto.
    staleTime: 1000 * 60 * 5,
  });
}

export function useContasBancariasQuery() {
  return useQuery({
    queryKey: [...financeiroKeys.todos, 'contas-bancarias'],
    queryFn: () => service.listarContasBancarias(true),
    staleTime: 1000 * 60 * 5,
  });
}

/**
 * A projeção dos próximos `dias`.
 *
 * Sem `refetchInterval`: nada aqui muda sozinho de minuto a minuto — o que
 * move a linha é alguém lançar ou dar baixa numa conta, e isso já invalida o
 * prefixo inteiro. Um polling curto só gastaria consulta.
 */
export function useFluxoCaixaQuery(dias: MaybeRef<number>) {
  return useQuery({
    queryKey: computed(() => financeiroKeys.fluxoCaixa(unref(dias))),
    queryFn: () => service.getFluxoCaixa(unref(dias)),
  });
}

export function useExtratoQuery(filtros: MaybeRef<ExtratoFiltros>) {
  return useQuery({
    queryKey: computed(() => financeiroKeys.extrato(unref(filtros))),
    queryFn: () => service.listarExtrato(unref(filtros)),
    refetchInterval: REFETCH_CADASTROS,
  });
}

export function useConciliacaoQuery(inicio: MaybeRef<string>, fim: MaybeRef<string>) {
  return useQuery({
    queryKey: computed(() =>
      financeiroKeys.conciliacao({ inicio: unref(inicio), fim: unref(fim) }),
    ),
    queryFn: () => service.getConciliacao(unref(inicio), unref(fim)),
    enabled: computed(() => !!unref(inicio) && !!unref(fim)),
  });
}

export function useContasPagarQuery(filtros: MaybeRef<ContaPagarFiltros>) {
  return useQuery({
    queryKey: computed(() => financeiroKeys.contasPagar(unref(filtros))),
    queryFn: () => service.listarContasPagar(unref(filtros)),
    // Financeiro não é tela de caixa: dois minutos é o intervalo dos cadastros,
    // e é o que basta para o outro terminal ver a conta que este lançou.
    refetchInterval: REFETCH_CADASTROS,
  });
}

export function useResumoQuery(inicio: MaybeRef<string>, fim: MaybeRef<string>) {
  return useQuery({
    queryKey: computed(() =>
      financeiroKeys.resumo({ inicio: unref(inicio), fim: unref(fim) }),
    ),
    queryFn: () => service.getResumo(unref(inicio), unref(fim)),
    enabled: computed(() => !!unref(inicio) && !!unref(fim)),
    refetchInterval: REFETCH_CADASTROS,
  });
}

export function useHistoricoRecebimentoQuery(contaId: MaybeRef<number | null>) {
  return useQuery({
    queryKey: computed(() => [...financeiroKeys.todos, 'historico-receber', unref(contaId)]),
    queryFn: () => service.listarHistoricoDoRecebimento(unref(contaId) as number),
    enabled: computed(() => !!unref(contaId)),
  });
}

export function useHistoricoContaQuery(contaId: MaybeRef<number | null>) {
  return useQuery({
    queryKey: computed(() => [...financeiroKeys.todos, 'historico', unref(contaId)]),
    queryFn: () => service.listarHistoricoDaConta(unref(contaId) as number),
    enabled: computed(() => !!unref(contaId)),
  });
}

// ===========================================================================
// ESCRITA
// ===========================================================================

export function useCriarContaPagar() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: (payload: ContaPagarPayload) => service.criarContaPagar(payload),
    onSuccess: () => {
      invalidar();
      toast.success('Conta lançada');
    },
  });
}

export function useAtualizarContaPagar() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<ContaPagarPayload> }) =>
      service.atualizarContaPagar(id, payload),
    onSuccess: () => {
      invalidar();
      toast.success('Conta atualizada');
    },
  });
}

export function useCancelarContaPagar() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: (id: number) => service.cancelarContaPagar(id),
    onSuccess: () => {
      invalidar();
      // "Cancelada", nunca "excluída": a linha continua no banco, e chamar de
      // exclusão faria o usuário procurá-la na lixeira que não existe.
      toast.success('Conta cancelada');
    },
  });
}

export function usePagarConta() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ContaPagarBaixaPayload }) =>
      service.pagarConta(id, payload),
    onSuccess: () => {
      invalidar();
      toast.success('Pagamento registrado');
    },
  });
}

export function useEstornarPagamento() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ id, motivo }: { id: number; motivo: string }) =>
      service.estornarPagamento(id, motivo),
    onSuccess: () => {
      invalidar();
      toast.success('Pagamento estornado', 'A conta voltou para pendente.');
    },
  });
}

export function useCriarPlanoConta() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: (nome: string) => service.criarPlanoConta(nome),
    onSuccess: () => {
      invalidar();
      toast.success('Categoria criada');
    },
  });
}

export function useAtualizarPlanoConta() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: { nome?: string; ativo?: boolean } }) =>
      service.atualizarPlanoConta(id, dados),
    onSuccess: () => invalidar(),
    onError: () => toast.error('Não foi possível salvar a categoria'),
  });
}

// ===========================================================================
// CONTAS A RECEBER
// ===========================================================================

export function useContasReceberQuery(filtros: MaybeRef<ContaPagarFiltros>) {
  return useQuery({
    queryKey: computed(() => financeiroKeys.contasReceber(unref(filtros))),
    queryFn: () => service.listarContasReceber(unref(filtros)),
    refetchInterval: REFETCH_CADASTROS,
  });
}

export function useCriarContaReceber() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: (payload: ContaReceberPayload) => service.criarContaReceber(payload),
    onSuccess: () => {
      invalidar();
      toast.success('Cobrança lançada');
    },
  });
}

export function useAtualizarContaReceber() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<ContaReceberPayload> }) =>
      service.atualizarContaReceber(id, payload),
    onSuccess: () => {
      invalidar();
      toast.success('Cobrança atualizada');
    },
  });
}

export function useCancelarContaReceber() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: (id: number) => service.cancelarContaReceber(id),
    onSuccess: () => {
      invalidar();
      toast.success('Cobrança cancelada');
    },
  });
}

export function useReceberConta() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ContaReceberBaixaPayload }) =>
      service.receberConta(id, payload),
    onSuccess: () => {
      invalidar();
      toast.success('Recebimento registrado');
    },
  });
}

export function useEstornarRecebimento() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ id, motivo }: { id: number; motivo: string }) =>
      service.estornarRecebimento(id, motivo),
    onSuccess: () => {
      invalidar();
      toast.success('Recebimento estornado', 'A cobrança voltou para pendente.');
    },
  });
}

export function useAdiarAlerta() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ codigo, dias }: { codigo: string; dias?: number }) =>
      service.adiarAlerta(codigo, dias),
    onSuccess: () => {
      invalidar();
      toast.success('Aviso adiado — ele volta se o problema continuar');
    },
  });
}

export function useBaixarLote() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: (payload: ConciliacaoBaixaLotePayload) => service.baixarLote(payload),
    onSuccess: (resultado) => {
      invalidar();
      toast.success(
        `${resultado.quantidade} cobrança(s) conferida(s)` +
          (resultado.diferenca !== 0 ? ' com diferença' : ''),
      );
    },
  });
}

export function useAtualizarContaBancaria() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: ({ id, ...payload }: { id: number; saldo_informado?: number }) =>
      service.atualizarContaBancaria(id, payload),
    onSuccess: () => {
      invalidar();
      toast.success('Saldo atualizado');
    },
  });
}

export function useCriarContaBancaria() {
  const invalidar = useInvalidarFinanceiro();
  const toast = useToast();

  return useMutation({
    mutationFn: (payload: { nome: string; tipo: string; principal?: boolean }) =>
      service.criarContaBancaria(payload),
    onSuccess: () => {
      invalidar();
      toast.success('Conta cadastrada');
    },
  });
}
