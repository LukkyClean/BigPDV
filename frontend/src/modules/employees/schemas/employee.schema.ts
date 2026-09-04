/**
 * @fileoverview Zod validation schemas for employee forms
 * @description Validates employee data with CPF validation and nested structures
 */

import { z } from 'zod';
import { toTypedSchema } from '@vee-validate/zod';
import { cpf } from 'cpf-cnpj-validator';

// =============================================
// REUSABLE SCHEMAS
// =============================================

const genderSchema = z
  .enum(['MASCULINO', 'FEMININO', 'OUTRO'])
  .optional()
  .or(z.literal(''));

const bankAccountTypeSchema = z
  .enum(['POUPANCA', 'CORRENTE'])
  .optional()
  .or(z.literal(''));

/**
 * Schema for address (single)
 */
export const enderecoSchema = z.object({
  cep: z.string().min(9, 'CEP deve ter 8 digitos').max(9).optional().or(z.literal('')),
  logradouro: z
    .string()
    .min(3, 'Logradouro deve ter no minimo 3 caracteres')
    .max(255)
    .optional()
    .or(z.literal('')),
  numero: z.string().min(1, 'Numero e obrigatorio').max(20).optional().or(z.literal('')),
  complemento: z.string().max(100).optional().or(z.literal('')),
  bairro: z.string().min(2, 'Bairro deve ter no minimo 2 caracteres').max(100).optional().or(z.literal('')),
  cidade: z.string().min(2, 'Cidade deve ter no minimo 2 caracteres').max(100).optional().or(z.literal('')),
  estado: z.string().length(2, 'Estado deve ter 2 caracteres').optional().or(z.literal('')),
})
  /**
   * Endereço é tudo ou nada.
   *
   * Cada campo aceitava '' isoladamente, então um endereço pela metade passava
   * aqui e ia para o servidor — que exige os seis (`schemas/endereco.py`) e
   * devolvia 422. Como o erro do 422 não chegava à tela, o usuário clicava em
   * Salvar e não acontecia nada, sem nenhuma pista do motivo.
   *
   * Deixar em branco continua válido: quem não quer endereço não preenche nada.
   */
  .superRefine((endereco, ctx) => {
    const OBRIGATORIOS = ['cep', 'logradouro', 'numero', 'bairro', 'cidade', 'estado'] as const;
    const preenchidos = OBRIGATORIOS.filter((campo) => !!endereco[campo]?.trim());
    if (preenchidos.length === 0 || preenchidos.length === OBRIGATORIOS.length) return;

    for (const campo of OBRIGATORIOS) {
      if (!endereco[campo]?.trim()) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: [campo],
          message: 'Obrigatório quando o endereço é preenchido',
        });
      }
    }
  });

// =============================================
// MAIN EMPLOYEE SCHEMA
// =============================================

export const employeeSchema = z
  .object({
    // Dados Funcionario - Required
    nome: z
      .string({ required_error: 'Nome e obrigatorio' })
      .min(3, 'Nome deve ter no minimo 3 caracteres')
      .max(255),
    cpf: z
      .string({ required_error: 'CPF e obrigatorio' })
      .min(14, 'CPF invalido')
      .max(14, 'CPF invalido'),

    // Dados Funcionario - Optional
    data_nascimento: z.string().optional().or(z.literal('')),
    jornada_trabalho: z.string().max(100).optional().or(z.literal('')),
    genero: genderSchema,
    rg: z.string().max(20).optional().or(z.literal('')),
    telefone: z.string().max(15).optional().or(z.literal('')),
    celular: z.string().max(16).optional().or(z.literal('')),
    email: z.string().email('Email invalido').optional().or(z.literal('')),
    cargo_id: z.number().nullable().optional(),
    cnh: z.string().max(20).optional().or(z.literal('')),
    salario_bruto: z.number().optional(),
    tipo_contrato: z.string().max(50).optional().or(z.literal('')),
    data_admissao: z.string().optional().or(z.literal('')),
    mae: z.string().max(255).optional().or(z.literal('')),
    pai: z.string().max(255).optional().or(z.literal('')),
    carteira_trabalho: z.string().max(50).optional().or(z.literal('')),

    // Funcionário SEM acesso ao sistema: só a ficha, sem login.
    //
    // Fica no formulário (e não num ref solto) para o reset limpar junto — uma
    // chavinha que sobrevive ao fechar do modal reaparece marcada no próximo
    // cadastro, e aí alguém cria sem querer um funcionário que não consegue
    // entrar no sistema.
    sem_acesso: z.boolean().optional().default(false),

    // Usuario (obrigatório só no create COM acesso — validação manual no onSubmit)
    usuario_nome: z.string().max(255).optional().or(z.literal('')),
    usuario_email: z.string().email('Email do usuario inválido').max(255).optional().or(z.literal('')),
    usuario_senha: z.string().max(72).optional().or(z.literal('')),

    // Enderecos (optional array)
    enderecos: z.array(enderecoSchema).optional().default([]),

    // Dados Bancarios
    titular_conta: z.string().max(255).optional().or(z.literal('')),
    tipo_conta: bankAccountTypeSchema,
    banco: z.string().max(50).optional().or(z.literal('')),
    agencia: z.string().max(10).optional().or(z.literal('')),
    conta: z.string().max(20).optional().or(z.literal('')),

    // Comissão (override do cargo). null = herda. Basis points / centavos.
    comissao_venda_percentual: z.number().min(0).max(10000).nullable().optional(),
    comissao_servico_percentual: z.number().min(0).max(10000).nullable().optional(),
    meta_mensal: z.number().min(0).nullable().optional(),
    comissao_modo: z.enum(['direto', 'meta']).nullable().optional(),

    // Observacoes
    observacao: z.string().max(500).optional().or(z.literal('')),
  })
  .refine((data) => cpf.isValid(data.cpf), {
    message: 'CPF invalido',
    path: ['cpf'],
  });

export const employeeValidationSchema = toTypedSchema(employeeSchema);
export type EmployeeSchemaData = z.infer<typeof employeeSchema>;

// =============================================
// UPDATE SCHEMA (partial validation - no user fields)
// =============================================

export const employeeUpdateSchema = z
  .object({
    // Dados Funcionario - Required
    nome: z
      .string({ required_error: 'Nome e obrigatorio' })
      .min(3, 'Nome deve ter no minimo 3 caracteres')
      .max(255),
    cpf: z
      .string({ required_error: 'CPF e obrigatorio' })
      .min(14, 'CPF invalido')
      .max(14, 'CPF invalido'),

    // Dados Funcionario - Optional
    data_nascimento: z.string().optional().or(z.literal('')),
    jornada_trabalho: z.string().max(100).optional().or(z.literal('')),
    genero: genderSchema,
    rg: z.string().max(20).optional().or(z.literal('')),
    telefone: z.string().max(15).optional().or(z.literal('')),
    celular: z.string().max(16).optional().or(z.literal('')),
    email: z.string().email('Email invalido').optional().or(z.literal('')),
    cargo_id: z.number().nullable().optional(),
    cnh: z.string().max(20).optional().or(z.literal('')),
    salario_bruto: z.string().optional().or(z.literal('')),
    tipo_contrato: z.string().max(50).optional().or(z.literal('')),
    data_admissao: z.string().optional().or(z.literal('')),
    mae: z.string().max(255).optional().or(z.literal('')),
    pai: z.string().max(255).optional().or(z.literal('')),
    carteira_trabalho: z.string().max(50).optional().or(z.literal('')),

    // Enderecos (optional array)
    enderecos: z.array(enderecoSchema).optional().default([]),

    // Dados Bancarios
    titular_conta: z.string().max(255).optional().or(z.literal('')),
    tipo_conta: bankAccountTypeSchema,
    banco: z.string().max(50).optional().or(z.literal('')),
    agencia: z.string().max(10).optional().or(z.literal('')),
    conta: z.string().max(20).optional().or(z.literal('')),

    // Comissão (override do cargo). null = herda. Basis points / centavos.
    comissao_venda_percentual: z.number().min(0).max(10000).nullable().optional(),
    comissao_servico_percentual: z.number().min(0).max(10000).nullable().optional(),
    meta_mensal: z.number().min(0).nullable().optional(),
    comissao_modo: z.enum(['direto', 'meta']).nullable().optional(),

    // Observacoes
    observacao: z.string().max(500).optional().or(z.literal('')),
  })
  .refine((data) => cpf.isValid(data.cpf), {
    message: 'CPF invalido',
    path: ['cpf'],
  });

export const employeeUpdateValidationSchema = toTypedSchema(employeeUpdateSchema);
export type EmployeeUpdateSchemaData = z.infer<typeof employeeUpdateSchema>;
