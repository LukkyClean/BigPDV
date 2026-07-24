/**
 * @fileoverview Types for the employees module
 * @description Matches backend schemas for Funcionario, Usuario, Endereco
 */

import type { Component } from 'vue';

// =============================================
// ENUMS (matching backend core/enum.py)
// =============================================

export type Gender = 'MASCULINO' | 'FEMININO' | 'OUTRO';
export type BankAccountType = 'POUPANCA' | 'CORRENTE';
export type State =
  | 'AC' | 'AL' | 'AP' | 'AM' | 'BA' | 'CE' | 'DF' | 'ES' | 'GO'
  | 'MA' | 'MT' | 'MS' | 'MG' | 'PA' | 'PB' | 'PR' | 'PE' | 'PI'
  | 'RJ' | 'RN' | 'RS' | 'RO' | 'RR' | 'SC' | 'SP' | 'SE' | 'TO';

// =============================================
// USUARIO TYPES (matching usuario.py)
// =============================================

export interface UsuarioCreate {
  nome: string;
  email: string;
  senha: string;
}

export interface UsuarioRead {
  id: number;
  nome: string;
  email: string;
  url_perfil: string | null;
  ativo: boolean;
}

// =============================================
// ENDERECO TYPES (matching endereco.py)
// =============================================

export interface Endereco {
  logradouro: string;
  numero: string;
  bairro: string;
  cidade: string;
  estado: State;
  cep: string;
  complemento?: string;
}

export interface EnderecoRead extends Endereco {
  id: number;
  id_entidade: number;
  tipo_entidade: string;
}

export interface EnderecoUpdate {
  id?: number;
  logradouro?: string;
  numero?: string;
  bairro?: string;
  cidade?: string;
  estado?: State;
  cep?: string;
  complemento?: string;
}

// =============================================
// FUNCIONARIO TYPES (matching funcionario.py)
// =============================================

export interface FuncionarioBase {
  nome: string;
  cpf: string;
  telefone?: string;
  celular?: string;
  email?: string;
  rg?: string;
  carteira_trabalho?: string;
  cnh?: string;
  genero?: Gender;
  banco?: string;
  titular_conta?: string;
  agencia?: string;
  conta?: string;
  tipo_conta?: BankAccountType;
  data_nascimento?: string; // ISO date string YYYY-MM-DD
  mae?: string;
  pai?: string;
  observacao?: string;
  jornada_trabalho?: string;
  salario_bruto?: number;
  tipo_contrato?: string;
  data_admissao?: string; // ISO date string YYYY-MM-DD
  cargo_id?: number;
  // Comissão (override do cargo). Vazio/null = herda do cargo (cascata).
  // Percentuais em BASIS POINTS (500 = 5,00%); meta em centavos.
  comissao_venda_percentual?: number | null;
  comissao_servico_percentual?: number | null;
  meta_mensal?: number | null;
  comissao_modo?: 'direto' | 'meta' | null;
}

export interface FuncionarioCreate extends FuncionarioBase {
  usuario: UsuarioCreate;
  endereco?: Endereco[];
}

export interface FuncionarioRead extends FuncionarioBase {
  id: number;
  ativo: boolean;
  usuario: UsuarioRead;
  endereco?: EnderecoRead[];
}

export interface FuncionarioUpdate extends FuncionarioBase { 
  endereco?: EnderecoUpdate[];
}

// =============================================
// UI TYPES (for components)
// =============================================

export interface TabOption {
  id: 'employee' | 'position';
  label: string;
}

export type StatsKeys =
  | 'actives_now'
  | 'all_employees'
  | 'in_vacation'
  | 'left_employees';

export interface CardInfo {
  key: StatsKeys;
  icon: Component;
  label: string;
}

// =============================================
// FORM TYPES
// =============================================

export interface EnderecoFormData {
  cep: string;
  logradouro: string;
  numero: string;
  complemento: string;
  bairro: string;
  cidade: string;
  estado: string;
}

export interface EmployeeFormData {
  // Dados Funcionario
  nome: string;
  cpf: string;
  data_nascimento: string;
  jornada_trabalho: string;
  genero: Gender | '';
  rg: string;
  telefone: string;
  celular: string;
  email: string;
  cargo_id: number | null;
  cnh: string;
  salario_bruto: number;
  tipo_contrato: string;
  data_admissao: string;
  mae: string;
  pai: string;
  carteira_trabalho: string;

  // Usuario (for creating login - only in create mode)
  usuario_nome: string;
  usuario_email: string;
  usuario_senha: string;

  // Enderecos (array)
  enderecos: EnderecoFormData[];

  // Dados Bancarios
  titular_conta: string;
  cpf_titular: string;
  tipo_conta: BankAccountType | '';
  banco: string;
  agencia: string;
  conta: string;

  // Comissão (override do cargo). null = herda.
  comissao_venda_percentual: number | null;
  comissao_servico_percentual: number | null;
  meta_mensal: number | null;
  comissao_modo: 'direto' | 'meta' | null;

  // Observacoes
  observacao: string;
}

// =============================================
// MODAL TYPES
// =============================================

export type ModalMode = 'create' | 'edit' | 'view';

export interface ModalState {
  isOpen: boolean;
  mode: ModalMode;
  employeeId: number | null;
}

// =============================================
// TABLE TYPES
// =============================================

export type EmployeeStatus = 'active' | 'vacation' | 'inactive';

export interface EmployeeTableItem {
  id: number;
  name: string;
  email: string;
  role: string;
  status: EmployeeStatus;
  avatarUrl?: string;
}
