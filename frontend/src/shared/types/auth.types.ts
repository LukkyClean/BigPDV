import type { PermissionKey } from '@/shared/constants/permissions.constants';
import { EnderecoFormData } from './address.types';

export type Permissions = PermissionKey;

export interface Company {
  id: number;
  razao_social: string;
  nome_fantasia: string;
  documento: string;
  telefone: string;
  celular: string;
  email: string;
  enderecos: EnderecoFormData[];
  url_logo: string;
  segmento?: string;
  /**
   * Se a loja trabalha com Ordem de Serviço. Derivado do segmento pelo registry
   * do backend — ver `useOrdemServico`. Opcional porque backend mais antigo que
   * o frontend não devolve o campo; nesse caso o padrão é TER OS.
   */
  usa_ordem_servico?: boolean;
  /**
   * Rotulo do regime fiscal (ex.: "Simples Nacional"). Vem do login — ver
   * `schemas/auth.py`. É TEXTO DE EXIBICAO: quem decide CSOSN vs CST no
   * backend é `empresas.crt`, não este campo.
   */
  regime_tributario?: string | null;
  /** Inscricao Estadual. Obrigatoria no cabecalho do DANFE NFC-e. */
  inscricao_estadual?: string | null;
  /** Chave PIX do recebedor. Vem do login junto do resto da identidade da empresa. */
  chave_pix?: string | null;
  pix_ativo?: boolean;
  ativo: boolean;
}

export interface Position {
  nome: string;
  permissoes: Record<string, boolean>;
}

export interface User {
  id: number;
  funcionario_id?: number;
  nome: string;
  email: string;
  url_perfil?: string;
  ativo: boolean;
  is_master: boolean;
  empresa?: Company;
  cargo?: Position;
}

export interface UserResponse extends User {}
