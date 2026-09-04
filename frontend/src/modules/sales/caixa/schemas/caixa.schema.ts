import { z } from 'zod';

/**
 * @fileoverview Contrato do turno de caixa, espelhando `schemas/sessao_caixa.py`.
 *
 * Valores monetários trafegam em CENTAVOS (inteiros), como no resto do sistema.
 * A conversão para reais acontece só na hora de exibir.
 */

export const MovimentoCaixaSchema = z.object({
  id: z.number(),
  tipo: z.string(),
  origem: z.string(),
  valor: z.number(),
  motivo: z.string().nullable().optional(),
  forma_pagamento_id: z.number().nullable().optional(),
  funcionario_nome: z.string().nullable().optional(),
  criado_em: z.string(),
});

export const TotalPorFormaSchema = z.object({
  forma_pagamento_id: z.number().nullable().optional(),
  forma_pagamento_nome: z.string(),
  total: z.number(),
});

export const SessaoCaixaResumoSchema = z.object({
  sessao_id: z.number(),
  status: z.string(),
  funcionario_id: z.number(),
  funcionario_nome: z.string().nullable().optional(),
  terminal_hwid: z.string().nullable().optional(),
  terminal_nome: z.string().nullable().optional(),

  data_abertura: z.string(),
  data_fechamento: z.string().nullable().optional(),

  saldo_inicial: z.number(),
  total_vendas: z.number(),
  total_suprimentos: z.number(),
  total_sangrias: z.number(),

  // null = oculto pelo fechamento cego. Não é zero, e a tela não pode tratar
  // os dois como a mesma coisa.
  saldo_esperado_dinheiro: z.number().nullable(),
  saldo_contado: z.number().nullable().optional(),
  diferenca: z.number().nullable().optional(),

  por_forma: z.array(TotalPorFormaSchema).default([]),
  movimentos: z.array(MovimentoCaixaSchema).default([]),
});

export const AbrirCaixaSchema = z.object({
  saldo_inicial: z.number().int().min(0),
  terminal_hwid: z.string().nullable().optional(),
  // Só viaja quando a loja exige autorização para abrir e quem opera não é
  // gerente. Mesmo contrato da sangria: o backend devolve as sentinelas
  // REQUER_APROVACAO_GERENTE / PIN_GERENTE_INVALIDO e o modal de PIN é o mesmo.
  codigo_gerente: z.string().nullable().optional(),
});

export const MovimentoCaixaCreateSchema = z.object({
  valor: z.number().int().positive(),
  motivo: z.string().min(3).max(500),
  codigo_gerente: z.string().nullable().optional(),
});

export const FecharCaixaSchema = z.object({
  saldo_contado: z.number().int().min(0),
  observacao: z.string().max(500).nullable().optional(),
});

export type MovimentoCaixa = z.infer<typeof MovimentoCaixaSchema>;
export type TotalPorForma = z.infer<typeof TotalPorFormaSchema>;
export type SessaoCaixaResumo = z.infer<typeof SessaoCaixaResumoSchema>;
export type AbrirCaixaPayload = z.infer<typeof AbrirCaixaSchema>;
export type MovimentoCaixaPayload = z.infer<typeof MovimentoCaixaCreateSchema>;
export type FecharCaixaPayload = z.infer<typeof FecharCaixaSchema>;
