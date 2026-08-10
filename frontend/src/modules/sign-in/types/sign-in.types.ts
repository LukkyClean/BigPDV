import type { Component } from 'vue';

/**
 * Segmentos de negócio disponíveis para seleção.
 * Fonte única em `shared/constants/segmentos.ts` — reexportado aqui só para
 * não quebrar quem já importava `BusinessSegment` deste arquivo.
 */
import type { Segmento as BusinessSegment } from '@/shared/constants/segmentos';

export type { BusinessSegment };

/**
 * Tipo de pessoa do responsável
 */
export type TipoPessoa = 'PF' | 'PJ';

/**
 * Interface para os dados de um segmento de negócio
 */
export interface SegmentOption {
  id: BusinessSegment;
  label: string;
  icon: string;
  description: string;
}

export interface FeaturesOptions {
  icon: Component;
  title: string;
  description: string;
}

/**
 * Dados da loja (Passo 1)
 */
export interface LojaData {
  nomeLoja: string;
  segmento: BusinessSegment | '';
  celular: string;
  emailLoja: string;
  telefone: string;
  // Endereço
  cep: string;
  logradouro: string;
  numero: string;
  complemento: string;
  bairro: string;
  cidade: string;
  estado: string;
}

/**
 * Dados do responsável (Passo 2)
 */
export interface ResponsavelData {
  tipoPessoa: TipoPessoa;
  nomeResponsavel: string;
  // Campos PF
  cpf: string;
  rg: string;
  genero: string;
  dataNascimento: string;
  // Campos PJ
  razaoSocial: string;
  cnpj: string;
  nomeFantasiaPJ: string;
  inscricaoEstadual: string;
  inscricaoMunicipal: string;
  regimeTributario: string;
  // Contato (ambos)
  celularResponsavel: string;
  emailResponsavel: string;
}

/**
 * Dados de acesso (Passo 3)
 */
export interface AcessoData {
  nomeUsuario: string;
  email: string;
  senha: string;
  confirmarSenha: string;
}

/**
 * Estado completo do sign-in
 */
export interface SignInData {
  loja: LojaData;
  responsavel: ResponsavelData;
  acesso: AcessoData;
}

/**
 * Etapas do fluxo de sign-in
 */
export type SignInStep = 0 | 1 | 2 | 3 | 4 | 5;

/**
 * Configuração de cada etapa
 */
export interface StepConfig {
  step: SignInStep;
  title: string;
  subtitle: string;
}

/**
 * Request para o setup inicial
 */
export interface SetupRequest {
  // Loja
  nome_loja: string;
  segmento?: string;
  celular?: string;
  email_loja?: string;
  telefone?: string;
  endereco?: {
    logradouro: string;
    numero: string;
    bairro: string;
    cidade: string;
    estado: string;
    cep: string;
    complemento?: string;
  }[];
  // Responsável
  tipo_pessoa: TipoPessoa;
  nome_responsavel: string;
  // PF
  cpf?: string;
  rg?: string;
  genero?: string;
  data_nascimento?: string;
  // PJ
  razao_social?: string;
  cnpj?: string;
  nome_fantasia_pj?: string;
  inscricao_estadual?: string;
  inscricao_municipal?: string;
  regime_tributario?: string;
  // Contato responsável
  celular_responsavel?: string;
  email_responsavel?: string;
  // Acesso
  nome_usuario: string;
  email: string;
  senha: string;
}

/**
 * Response da API ViaCEP
 */
export interface ViaCepResponse {
  cep: string;
  logradouro: string;
  complemento: string;
  bairro: string;
  localidade: string;
  uf: string;
  erro?: boolean;
}
