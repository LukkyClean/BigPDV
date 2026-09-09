import { z } from 'zod';
import { cpf, cnpj } from 'cpf-cnpj-validator';

// =============================================
// Helpers de normalização
// =============================================

/**
 * Remove todos os caracteres não numéricos
 * Usado para normalizar documento, telefone, CEP, etc.
 */
const normalizeDigits = (val: unknown): string =>
  typeof val === 'string' ? val.replace(/\D/g, '') : String(val ?? '');

// =============================================
// Schemas de Domínio (Backend Shape)
// =============================================

export const EnderecoSchema = z.object({
  id: z.number().int().positive().optional(),
  logradouro: z.string().min(1),
  numero: z.string().min(1),
  bairro: z.string().min(1),
  cidade: z.string().min(1),
  estado: z.string().length(2),
  cep: z.string().min(8).max(9),
  complemento: z.string().optional(),
  codigo_ibge: z.string().optional(),
});

export const FiscalSettingsSchema = z.object({
  id: z.number().int().positive().nullish(),
  empresa_id: z.number().int().positive().nullish(),
  ambiente_emissao: z.number().int().min(1).max(2).default(2),
  serie_nfe: z.number().int().nonnegative().default(1),
  ultimo_numero_nfe: z.number().int().nonnegative().default(0),
  serie_nfce: z.number().int().nonnegative().default(1),
  ultimo_numero_nfce: z.number().int().nonnegative().default(0),
  csc_token: z.string().nullish(),
  csc_id: z.string().nullish(),
  rps_serie: z.string().nullish(),
  rps_ultimo_numero: z.number().int().nonnegative().nullish(),
  prefeitura_login: z.string().nullish(),
  prefeitura_senha: z.string().nullish(),
  prefeitura_token_api: z.string().nullish(),
  regime_tributacao_iss: z.number().int().min(1).max(6).nullish(),
  // 'NUVEM' é gravado pelo upload de certificado (services/empresa.py).
  tipo_certificado: z
    .enum(['ARQUIVO', 'WINDOWS', 'NUVEM', 'NENHUM'])
    .nullish()
    .default('ARQUIVO'),
  certificado_digital_path: z.string().nullish(),
  certificado_validade: z.string().nullish(),
  certificado_subject: z.string().nullish(),
  certificado_thumbprint: z.string().nullish(),
});

export const EmpresaSchema = z.object({
  razao_social: z.string().min(1),
  nome_fantasia: z.string().optional(),
  is_cnpj: z.boolean().default(true),
  documento: z.string().min(11),
  inscricao_estadual: z.string().optional(),
  inscricao_municipal: z.string().optional(),
  regime_tributario: z.string().min(1).optional(),
  cnae_principal: z.string().optional(),
  email: z.string().email().or(z.literal('')).optional(),
  telefone: z.string().optional(),
  celular: z.string().optional(),
  url_logo: z.string().optional(),
  cor_tema: z.string().regex(/^#[0-9a-fA-F]{6}$/).nullable().optional(),
  chave_pix: z.string().max(77).nullable().optional(),
  pix_ativo: z.boolean().nullable().optional(),
  fiscal_settings: FiscalSettingsSchema.optional(),
  enderecos: z.array(EnderecoSchema).optional(),
}).passthrough();

// =============================================
// Schemas de Formulário - Validação (VeeValidate)
// =============================================
// NOTA: Schemas de validação NÃO usam z.preprocess para evitar
// que o isDirty do VeeValidate fique sempre true

/**
 * Schema de endereço para validação (VeeValidate)
 * - Aceita CEP com ou sem máscara
 * - NÃO normaliza (para preservar isDirty)
 */
export const EnderecoFormValidationSchema = z.object({
  id: z.number().int().positive().optional(),
  cep: z.string().optional().or(z.literal('')),
  logradouro: z.string().min(1, 'Logradouro é obrigatório'),
  numero: z.string().min(1, 'Número é obrigatório'),
  bairro: z.string().min(1, 'Bairro é obrigatório'),
  cidade: z.string().min(1, 'Cidade é obrigatória'),
  estado: z.string().length(2, 'Estado deve ter 2 caracteres'),
  complemento: z.string().optional().or(z.literal('')),
  codigo_ibge: z.string().optional().or(z.literal('')),
});

/**
 * Schema de endereço para normalização (submit)
 * - Normaliza CEP para dígitos apenas
 */
export const EnderecoFormSchema = z.object({
  id: z.number().int().positive().optional(),
  cep: z.preprocess(
    normalizeDigits,
    z.string().max(8).optional().or(z.literal(''))
  ),
  logradouro: z.string().min(1, 'Logradouro é obrigatório'),
  numero: z.string().min(1, 'Número é obrigatório'),
  bairro: z.string().min(1, 'Bairro é obrigatório'),
  cidade: z.string().min(1, 'Cidade é obrigatória'),
  estado: z.string().length(2, 'Estado deve ter 2 caracteres'),
  complemento: z.string().optional().or(z.literal('')),
  codigo_ibge: z.string().optional().or(z.literal('')),
});

/**
 * Schema de configurações fiscais para formulário
 * - Usa z.coerce para converter strings de inputs para números
 * - Usa .nullish() para aceitar null, undefined e o tipo esperado
 */
export const FiscalSettingsFormSchema = z.object({
  id: z.number().int().positive().nullish(),
  empresa_id: z.number().int().positive().nullish(),
  ambiente_emissao: z.number().int().min(1).max(2).default(2),
  serie_nfe: z.coerce.number().int().nonnegative().default(1),
  ultimo_numero_nfe: z.coerce.number().int().nonnegative().default(0),
  serie_nfce: z.coerce.number().int().nonnegative().default(1),
  ultimo_numero_nfce: z.coerce.number().int().nonnegative().default(0),
  csc_token: z.string().nullish().or(z.literal('')),
  csc_id: z.string().nullish().or(z.literal('')),
  rps_serie: z.string().nullish().or(z.literal('')),
  rps_ultimo_numero: z.coerce.number().int().nonnegative().nullish(),
  prefeitura_login: z.string().nullish().or(z.literal('')),
  prefeitura_senha: z.string().nullish().or(z.literal('')),
  prefeitura_token_api: z.string().nullish().or(z.literal('')),
  regime_tributacao_iss: z.coerce.number().int().min(1).max(6).nullish(),
  // 'NUVEM' é gravado pelo upload de certificado (services/empresa.py).
  tipo_certificado: z
    .enum(['ARQUIVO', 'WINDOWS', 'NUVEM', 'NENHUM'])
    .nullish()
    .default('ARQUIVO'),
  certificado_digital_path: z.string().nullish().or(z.literal('')),
  certificado_validade: z.string().nullish().or(z.literal('')),
  certificado_subject: z.string().nullish().or(z.literal('')),
  certificado_thumbprint: z.string().nullish().or(z.literal('')),
});

/**
 * Schema de validação do formulário (VeeValidate)
 * - NÃO usa z.preprocess para preservar o isDirty
 * - Validações básicas de formato
 */
export const EmpresaFormValidationSchema = z.object({
  // Identificação
  razao_social: z.string().min(1, 'Razão Social é obrigatória'),
  nome_fantasia: z.string().optional().or(z.literal('')),
  is_cnpj: z.boolean().default(true),
  documento: z.string().min(1, 'Documento é obrigatório'),
  cnae_principal: z.string().optional().or(z.literal('')),
  indicador_ie: z.string().optional().or(z.literal('')),
  natureza_juridica: z.string().optional().or(z.literal('')),
  tipo_atividade: z.string().optional().or(z.literal('')),
  cnaes_secundarios: z.string().optional().or(z.literal('')),
  data_abertura: z.string().optional().or(z.literal('')),
  website: z.string().optional().or(z.literal('')),
  url_logo: z.string().optional().or(z.literal('')),
  cor_tema: z.string().regex(/^#[0-9a-fA-F]{6}$/).nullable().optional(),
  chave_pix: z.string().max(77).nullable().optional(),
  pix_ativo: z.boolean().nullable().optional(),

  // Contato
  email: z.string().email('Email inválido').optional().or(z.literal('')),
  telefone: z.string().optional().or(z.literal('')),
  celular: z.string().optional().or(z.literal('')),

  // Dados Fiscais
  inscricao_estadual: z.string().optional().or(z.literal('')),
  inscricao_municipal: z.string().optional().or(z.literal('')),
  regime_tributario: z.string().optional().or(z.literal('')),

  // Endereço Principal (nested - singular, não array)
  endereco_principal: EnderecoFormValidationSchema.partial(),

  // Configurações Fiscais (nested)
  //
  // DELIBERADAMENTE FROUXO AQUI. Nenhum destes campos é editável nesta tela --
  // eles vivem no Centro Fiscal, que os valida lá. Nesta tela eles só
  // transitam: chegam do servidor, ficam no formulário e voltam no Salvar.
  //
  // Validá-los aqui não protege nada e cria um beco: um valor que o servidor
  // gravou e que este schema não conhece reprova o `handleSubmit`, e o erro
  // aponta para um campo que não está na tela. O lojista clica em Salvar e o
  // formulário inteiro para, sem indicação de onde.
  //
  // Foi exatamente o que aconteceu quando o upload de certificado passou a
  // gravar `tipo_certificado: 'NUVEM'` de verdade (8960ee8): a tela de Empresa
  // parou de salvar, com um toast dizendo "fiscal_settings" e nada mais. Mesmo
  // formato do caso do `complemento`, que bloqueou o cadastro de uma loja.
  //
  // O `EmpresaFormSchema` (normalização) segue estrito de propósito: é ele que
  // coage série e numeração para número antes de enviar.
  fiscal_settings: z.record(z.unknown()).optional(),

  // Campo apenas do form
  certificado_senha: z.string().optional().or(z.literal('')),
});

/**
 * Schema principal do formulário de empresa (para normalização no submit)
 * - Usa z.preprocess para normalizar documento, telefone, celular
 * - Validações condicionais via superRefine
 * - Usado apenas no runtime validation antes de enviar para API
 */
export const EmpresaFormSchema = z.object({
  // Identificação
  razao_social: z.string().min(1, 'Razão Social é obrigatória'),
  nome_fantasia: z.string().optional().or(z.literal('')),
  is_cnpj: z.boolean().default(true),
  documento: z.preprocess(
    normalizeDigits,
    z.string().min(11, 'Documento inválido').max(14, 'Documento inválido')
  ),
  cnae_principal: z.string().optional().or(z.literal('')),
  indicador_ie: z.string().optional().or(z.literal('')),
  natureza_juridica: z.string().optional().or(z.literal('')),
  tipo_atividade: z.string().optional().or(z.literal('')),
  cnaes_secundarios: z.string().optional().or(z.literal('')),
  data_abertura: z.string().optional().or(z.literal('')),
  website: z.string().optional().or(z.literal('')),
  url_logo: z.string().optional().or(z.literal('')),
  cor_tema: z.string().regex(/^#[0-9a-fA-F]{6}$/).nullable().optional(),
  chave_pix: z.string().max(77).nullable().optional(),
  pix_ativo: z.boolean().nullable().optional(),

  // Contato
  email: z.string().email('Email inválido').optional().or(z.literal('')),
  telefone: z.preprocess(normalizeDigits, z.string().optional().or(z.literal(''))),
  celular: z.preprocess(normalizeDigits, z.string().optional().or(z.literal(''))),

  // Dados Fiscais
  inscricao_estadual: z.string().optional().or(z.literal('')),
  inscricao_municipal: z.string().optional().or(z.literal('')),
  regime_tributario: z.string().optional().or(z.literal('')),

  // Endereço Principal (nested - singular, não array)
  endereco_principal: EnderecoFormSchema.partial(),

  // Configurações Fiscais (nested)
  fiscal_settings: FiscalSettingsFormSchema.partial(),

  // Campo apenas do form (não vai para API diretamente no payload principal)
  certificado_senha: z.string().optional().or(z.literal('')),
})
.superRefine((data, ctx) => {
  // ========== 1. Validação de documento por tipo (CNPJ/CPF) ==========
  const docDigits = data.documento || '';

  if (data.is_cnpj) {
    if (docDigits.length !== 14) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'CNPJ deve ter 14 dígitos',
        path: ['documento'],
      });
    } else if (!cnpj.isValid(docDigits)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'CNPJ inválido',
        path: ['documento'],
      });
    }
  } else {
    if (docDigits.length !== 11) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'CPF deve ter 11 dígitos',
        path: ['documento'],
      });
    } else if (!cpf.isValid(docDigits)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'CPF inválido',
        path: ['documento'],
      });
    }
  }

  // ========== 2. Certificado ARQUIVO requer senha quando há arquivo ==========
  const settings = data.fiscal_settings;
  if (
    settings?.tipo_certificado === 'ARQUIVO' &&
    settings.certificado_digital_path &&
    !data.certificado_senha
  ) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Senha do certificado é obrigatória para certificado A1',
      path: ['certificado_senha'],
    });
  }

  // ========== 3. Certificado WINDOWS requer thumbprint ==========
  // Nota: Esta validação só é acionada se tipo_certificado === 'WINDOWS'
  // e não há thumbprint selecionado
  // if (settings?.tipo_certificado === 'WINDOWS' && !settings.certificado_thumbprint) {
  //   ctx.addIssue({
  //     code: z.ZodIssueCode.custom,
  //     message: 'Selecione um certificado do Windows',
  //     path: ['fiscal_settings', 'certificado_thumbprint'],
  //   });
  // }

  // ========== 4. Ambiente produção requer CSC ==========
  if (settings?.ambiente_emissao === 1 && (!settings.csc_id || !settings.csc_token)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'CSC (ID e Token) são obrigatórios para ambiente de produção',
      path: ['fiscal_settings', 'csc_id'],
    });
  }
});

export const WindowsCertificateSchema = z.object({
  thumbprint: z.string(),
  subject: z.string(),
  friendly_name: z.string(),
  issuer: z.string(),
  valid_until: z.string(),
  serial_number: z.string(),
});

export const ConnectionTestResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
});

// Tipos inferidos
export type EnderecoZod = z.infer<typeof EnderecoSchema>;
export type FiscalSettingsZod = z.infer<typeof FiscalSettingsSchema>;
export type EmpresaZod = z.infer<typeof EmpresaSchema>;
export type WindowsCertificateZod = z.infer<typeof WindowsCertificateSchema>;
export type ConnectionTestResponseZod = z.infer<typeof ConnectionTestResponseSchema>;

// Funções de validação
export function validateEmpresa(data: unknown): EmpresaZod | null {
  try {
    return EmpresaSchema.parse(data);
  } catch {
    return null;
  }
}

export function validateEndereco(data: unknown): EnderecoZod | null {
  try {
    return EnderecoSchema.parse(data);
  } catch {
    return null;
  }
}

export function validateFiscalSettings(data: unknown): FiscalSettingsZod | null {
  try {
    return FiscalSettingsSchema.parse(data);
  } catch {
    return null;
  }
}

// =============================================
// VeeValidate Integration
// =============================================

import { toTypedSchema } from '@vee-validate/zod';

/**
 * Schema de validação para VeeValidate
 * Usa EmpresaFormValidationSchema (sem preprocess) para preservar isDirty
 * O EmpresaFormSchema (com preprocess) é usado apenas no submit para normalização
 */
export const empresaValidationSchema = toTypedSchema(EmpresaFormValidationSchema);

/**
 * Type inference do schema de domínio
 */
export type EmpresaSchemaData = z.infer<typeof EmpresaSchema>;

/**
 * Type inference do schema de formulário
 * Usado para tipagem do VeeValidate e valores do form
 */
export type EmpresaFormSchemaData = z.infer<typeof EmpresaFormSchema>;
