/**
 * @fileoverview Tipos TypeScript do módulo Enterprise
 * @description Interfaces e tipos para empresa, endereço, fiscal settings, etc.
 */

import type { Ref, ComputedRef } from 'vue';

// =============================================
// Tipos auxiliares
// =============================================

export type TipoCertificado = 'ARQUIVO' | 'WINDOWS' | 'NENHUM';
export type AmbienteEmissao = 1 | 2;
export type RegimeTributario = 1 | 2 | 3;
export type RegimeTributacaoISS = 1 | 2 | 3 | 4 | 5 | 6;

// =============================================
// Interfaces principais
// =============================================

/**
 * Configurações fiscais da empresa
 */
export interface FiscalSettings {
  id?: number;
  empresa_id?: number;
  ambiente_emissao: number;
  serie_nfe: number;
  ultimo_numero_nfe: number;
  serie_nfce: number;
  ultimo_numero_nfce: number;
  csc_token?: string;
  csc_id?: string;
  rps_serie?: string;
  rps_ultimo_numero?: number;
  prefeitura_login?: string;
  prefeitura_senha?: string;
  prefeitura_token_api?: string;
  regime_tributacao_iss?: number;
  tipo_certificado: TipoCertificado;
  certificado_digital_path?: string;
  certificado_validade?: string;
  certificado_subject?: string;
  certificado_thumbprint?: string;
}

/**
 * Certificado digital instalado no Windows
 */
export interface WindowsCertificate {
  thumbprint: string;
  subject: string;
  friendly_name: string;
  issuer: string;
  valid_until: string | null;
  serial_number: string;
}

/**
 * Endereço da empresa
 */
export interface Endereco {
  id?: number;
  logradouro: string;
  numero: string;
  bairro: string;
  cidade: string;
  estado: string;
  cep: string;
  complemento?: string;
  codigo_ibge?: string;
}

/**
 * Dados completos da empresa (leitura)
 */
export interface EmpresaRead {
  id: number;
  razao_social: string;
  nome_fantasia?: string;
  is_cnpj: boolean;
  documento: string;
  inscricao_estadual?: string;
  inscricao_municipal?: string;
  regime_tributario?: string;
  cnae_principal?: string;
  segmento?: string;
  indicador_ie?: string;
  natureza_juridica?: string;
  tipo_atividade?: string;
  cnaes_secundarios?: string;
  data_abertura?: string;
  website?: string;
  email?: string;
  telefone?: string;
  celular?: string;
  url_logo?: string;
  /** Cor da marca (#RRGGBB). Ausente/null = paleta de fábrica. */
  cor_tema?: string | null;
  /** Chave PIX do recebedor. O QR e montado offline a partir dela. */
  chave_pix?: string | null;
  pix_ativo?: boolean;
  fiscal_settings?: FiscalSettings;
  enderecos?: Endereco[];
}

/**
 * Payload para atualização da empresa
 */
export interface EmpresaUpdate {
  razao_social?: string;
  nome_fantasia?: string;
  is_cnpj?: boolean;
  documento?: string;
  inscricao_estadual?: string;
  inscricao_municipal?: string;
  regime_tributario?: string;
  cnae_principal?: string;
  indicador_ie?: string;
  natureza_juridica?: string;
  tipo_atividade?: string;
  cnaes_secundarios?: string;
  data_abertura?: string;
  website?: string;
  email?: string;
  telefone?: string;
  celular?: string;
  url_logo?: string;
  /** Cor da marca (#RRGGBB). Ausente/null = paleta de fábrica. */
  cor_tema?: string | null;
  /** Chave PIX do recebedor. O QR e montado offline a partir dela. */
  chave_pix?: string | null;
  pix_ativo?: boolean;
  endereco?: Endereco[];
  fiscal_settings?: Partial<FiscalSettings> & {
    certificado_senha?: string;
  };
}

/**
 * Resposta de teste de conexão (Sefaz/Prefeitura)
 */
export interface ConnectionTestResponse {
  success: boolean;
  message: string;
}

/**
 * Dados do formulário de empresa (VeeValidate)
 * Esta interface representa a estrutura do formulário com campos formatados (máscaras)
 */
export interface EmpresaFormData {
  razao_social: string;
  nome_fantasia: string;
  documento: string;
  is_cnpj: boolean;
  email: string;
  telefone: string;
  celular: string;
  inscricao_estadual: string;
  inscricao_municipal: string;
  regime_tributario: string;
  cnae_principal: string;
  indicador_ie: string;
  natureza_juridica: string;
  tipo_atividade: string;
  cnaes_secundarios: string;
  data_abertura: string;
  website: string;
  url_logo: string;
  fiscal_settings: Partial<FiscalSettings>;
  endereco_principal: Partial<Endereco>;
  certificado_senha: string;
}

/**
 * Tipo inferido do EmpresaFormSchema (Zod)
 * Representa os dados após normalização do Zod (sem máscaras)
 *
 * NOTA: Para usar este tipo, importe de '../schemas/empresa.schema':
 * import type { EmpresaFormSchemaData } from '../schemas/empresa.schema';
 */
// Re-export será feito no schema para evitar dependência circular

/**
 * Context do formulário de empresa (provide/inject)
 */
export interface EmpresaFormContext {
  // ========== FIELD REFS (VeeValidate defineField) ==========
  razao_social: Ref<string>;
  nome_fantasia: Ref<string>;
  documento: Ref<string>;
  is_cnpj: Ref<boolean>;
  email: Ref<string>;
  telefone: Ref<string>;
  celular: Ref<string>;
  inscricao_estadual: Ref<string>;
  inscricao_municipal: Ref<string>;
  regime_tributario: Ref<string>;
  cnae_principal: Ref<string>;
  indicador_ie: Ref<string>;
  natureza_juridica: Ref<string>;
  tipo_atividade: Ref<string>;
  cnaes_secundarios: Ref<string>;
  data_abertura: Ref<string>;
  website: Ref<string>;
  url_logo: Ref<string>;
  fiscal_settings: Ref<Partial<FiscalSettings>>;
  endereco_principal: Ref<Partial<Endereco>>;
  certificado_senha: Ref<string>;

  // ========== FORM STATE ==========
  errors: Ref<Record<string, string | undefined>>;
  submitCount: Ref<number>;
  values: EmpresaFormData; // Não é Ref
  apiError: Ref<string | null>;
  isLoading: Ref<boolean>
  isPending: ComputedRef<boolean>;
  isDirty: ComputedRef<boolean>;

  // ========== COMPUTED FLAGS ==========
  canEmitirProducao: ComputedRef<boolean>;
  hasCertificado: ComputedRef<boolean>;

  // ========== LOADING STATES ==========
  isUploadingLogo: ComputedRef<boolean>;
  isUploadingCert: ComputedRef<boolean>;
  isTestingSefaz: ComputedRef<boolean>;
  isTestingPrefeitura: ComputedRef<boolean>;
  isLoadingCertificates: ComputedRef<boolean>;

  // ========== WINDOW CERTIFICATES ==========
  windowsCertificates: WindowsCertificate[];

  // ========== CNPJ LOOKUP ==========
  cnpjSalvo: Ref<string>;
  isConsultingCNPJ: Ref<boolean>;
  consultarCNPJ: (cnpj: string) => void;

  // ========== DIRTY TRACKING ==========
  formPronto: Ref<boolean>;
  temAlteracoesPendentes: ComputedRef<boolean>;

  // ========== ACTIONS ==========
  onSubmit: (e?: Event) => void;
  setTipoPessoa: (isCnpj: boolean) => void;
  handleLogoUpload: (file: File) => void;
  handleCertUpload: (file: File, senha: string) => void;
  handleTestSefaz: () => void;
  handleTestPrefeitura: () => void;
  refetchWindowsCerts: () => void;
  resetForm: () => void;
}

// =============================================
// Funções auxiliares específicas de empresa
// =============================================
// NOTA: Funções genéricas de formatação (CNPJ, CPF, CEP, Telefone)
// foram movidas para @/shared/utils/document.utils.ts

/**
 * Formata endereço em uma linha
 * @param endereco - Objeto de endereço
 * @returns Endereço formatado em uma linha
 */
export function formatEnderecoLinha(endereco?: Endereco): string {
  if (!endereco) return '';
  const parts = [
    endereco.logradouro,
    endereco.numero,
    endereco.bairro,
    endereco.cidade,
    endereco.estado,
  ].filter(Boolean);
  return parts.join(', ');
}

// /**
//  * Verifica se empresa pode emitir em produção
//  * @param empresa - Dados da empresa
//  * @returns true se pode emitir em produção
//  */
// export function canEmitirProducao(empresa: Empresa): boolean {
//   const settings = empresa.fiscal_settings;
//   if (!settings) return false;

//   const hasCertificado =
//     settings.tipo_certificado === 'ARQUIVO'
//       ? Boolean(settings.certificado_digital_path)
//       : Boolean(settings.certificado_thumbprint);

//   const hasCSC = Boolean(settings.csc_token && settings.csc_id);

//   return hasCertificado && hasCSC;
// }

// /**
//  * Verifica se empresa pode emitir NFSe
//  * @param empresa - Dados da empresa
//  * @returns true se pode emitir NFSe
//  */
// export function canEmitirNFSe(empresa: Empresa): boolean {
//   const settings = empresa.fiscal_settings;
//   if (!settings) return false;

//   const hasCertificado =
//     settings.tipo_certificado === 'ARQUIVO'
//       ? Boolean(settings.certificado_digital_path)
//       : Boolean(settings.certificado_thumbprint);

//   const hasPrefeitura = Boolean(settings.prefeitura_login && settings.prefeitura_senha);

//   return hasCertificado && hasPrefeitura;
// }
