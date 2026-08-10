import { z } from 'zod';
import { toTypedSchema } from '@vee-validate/zod';
import { cpf, cnpj } from 'cpf-cnpj-validator';

import { SEGMENTOS } from '@/shared/constants/segmentos';

/**
 * Segmentos válidos — vêm da fonte única em `shared/constants/segmentos.ts`.
 *
 * Esta lista já foi um `as const` local, e foi exatamente isso que fez o
 * onboarding recusar "serigrafia" com "Invalid enum value" mesmo depois de o
 * segmento existir em todo o resto do sistema: sem vínculo com o tipo, o
 * `vue-tsc` não tinha o que cobrar.
 */
const businessSegments = SEGMENTOS;

/**
 * Schema da loja + endereço (Passo 1)
 */
export const lojaSchema = z.object({
  // Loja
  nomeLoja: z
    .string({ required_error: 'Nome da loja é obrigatório' })
    .min(2, 'Nome da loja deve ter no mínimo 2 caracteres')
    .max(100, 'Nome da loja deve ter no máximo 100 caracteres'),
  segmento: z.enum(businessSegments, {
    required_error: 'Selecione um segmento',
    invalid_type_error: 'Segmento inválido',
  }),
  celular: z
    .string({ required_error: 'Celular é obrigatório' })
    .min(14, 'Celular inválido')
    .max(16, 'Celular inválido'),
  emailLoja: z
    .string({ required_error: 'E-mail é obrigatório' })
    .email('E-mail inválido')
    .max(255, 'E-mail deve ter no máximo 255 caracteres'),
  telefone: z
    .string()
    .max(14, 'Telefone inválido')
    .optional()
    .or(z.literal('')),

  // Endereço
  cep: z
    .string({ required_error: 'CEP é obrigatório' })
    .length(9, 'CEP deve ter 8 dígitos'),
  logradouro: z
    .string({ required_error: 'Logradouro é obrigatório' })
    .min(3, 'Logradouro deve ter no mínimo 3 caracteres')
    .max(200, 'Logradouro deve ter no máximo 200 caracteres'),
  numero: z
    .string()
    .max(10, 'Número deve ter no máximo 10 caracteres')
    .optional()
    .or(z.literal('')),
  complemento: z
    .string()
    .max(100, 'Complemento deve ter no máximo 100 caracteres')
    .optional()
    .or(z.literal('')),
  bairro: z
    .string({ required_error: 'Bairro é obrigatório' })
    .min(2, 'Bairro deve ter no mínimo 2 caracteres')
    .max(100, 'Bairro deve ter no máximo 100 caracteres'),
  cidade: z
    .string({ required_error: 'Cidade é obrigatória' })
    .min(2, 'Cidade deve ter no mínimo 2 caracteres')
    .max(100, 'Cidade deve ter no máximo 100 caracteres'),
  estado: z
    .string({ required_error: 'Estado é obrigatório' })
    .length(2, 'Estado deve ter 2 caracteres'),
});

export const lojaValidationSchema = toTypedSchema(lojaSchema);
export type LojaFormData = z.infer<typeof lojaSchema>;

/**
 * Schema do responsável (Passo 2)
 * Validação condicional por tipo de pessoa via superRefine
 */
export const responsavelSchema = z.object({
  tipoPessoa: z.enum(['PF', 'PJ'], {
    required_error: 'Selecione o tipo de pessoa',
  }),
  nomeResponsavel: z
    .string({ required_error: 'Nome é obrigatório' })
    .min(3, 'Nome deve ter no mínimo 3 caracteres')
    .max(255, 'Nome deve ter no máximo 255 caracteres'),
  // Campos PF
  cpf: z.string().optional().or(z.literal('')),
  rg: z.string().max(20, 'RG inválido').optional().or(z.literal('')),
  genero: z.string().optional().or(z.literal('')),
  dataNascimento: z.string().optional().or(z.literal('')),
  // Campos PJ
  razaoSocial: z.string().max(255).optional().or(z.literal('')),
  cnpj: z.string().optional().or(z.literal('')),
  nomeFantasiaPJ: z.string().max(255).optional().or(z.literal('')),
  inscricaoEstadual: z.string().max(50).optional().or(z.literal('')),
  inscricaoMunicipal: z.string().max(50).optional().or(z.literal('')),
  regimeTributario: z.string().max(50).optional().or(z.literal('')),
  // Contato
  celularResponsavel: z
    .string()
    .min(14, 'Celular inválido')
    .max(16, 'Celular inválido')
    .optional()
    .or(z.literal('')),
  emailResponsavel: z
    .string()
    .email('E-mail inválido')
    .max(255)
    .optional()
    .or(z.literal('')),
}).superRefine((data, ctx) => {
  if (data.tipoPessoa === 'PF') {
    // CPF obrigatório e válido para PF
    if (!data.cpf || data.cpf.length === 0) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: 'CPF é obrigatório', path: ['cpf'] });
    } else if (!cpf.isValid(data.cpf)) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: 'CPF inválido', path: ['cpf'] });
    }
  } else if (data.tipoPessoa === 'PJ') {
    // Razão Social obrigatória para PJ
    if (!data.razaoSocial || data.razaoSocial.length < 3) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: 'Razão Social é obrigatória (mín. 3 caracteres)', path: ['razaoSocial'] });
    }
    // CNPJ obrigatório e válido para PJ
    if (!data.cnpj || data.cnpj.length === 0) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: 'CNPJ é obrigatório', path: ['cnpj'] });
    } else if (!cnpj.isValid(data.cnpj)) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: 'CNPJ inválido', path: ['cnpj'] });
    }
  }
});

export const responsavelValidationSchema = toTypedSchema(responsavelSchema);
export type ResponsavelFormData = z.infer<typeof responsavelSchema>;

/**
 * Schema dos dados de acesso (Passo 3)
 */
export const acessoSchema = z.object({
  nomeUsuario: z
    .string({ required_error: 'Nome do usuário é obrigatório' })
    .min(2, 'Nome deve ter no mínimo 2 caracteres')
    .max(255, 'Nome deve ter no máximo 255 caracteres'),
  email: z
    .string({ required_error: 'E-mail é obrigatório' })
    .email('E-mail inválido')
    .max(255, 'E-mail deve ter no máximo 255 caracteres'),
  senha: z
    .string({ required_error: 'Senha é obrigatória' })
    .min(8, 'Senha deve ter no mínimo 8 caracteres')
    .max(72, 'Senha deve ter no máximo 72 caracteres'),
  confirmarSenha: z
    .string({ required_error: 'Confirmação de senha é obrigatória' })
    .min(8, 'Confirmação deve ter no mínimo 8 caracteres'),
}).refine(
  (data) => data.senha === data.confirmarSenha,
  {
    message: 'As senhas não coincidem',
    path: ['confirmarSenha'],
  }
);

export const acessoValidationSchema = toTypedSchema(acessoSchema);
export type AcessoFormData = z.infer<typeof acessoSchema>;
