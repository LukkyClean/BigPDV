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
  /** Chave PIX do recebedor. Vem do login junto do resto da identidade da empresa. */
  chave_pix?: string | null;
  pix_ativo?: boolean;
  /**
   * Regime tributário como RÓTULO de tela ("Simples Nacional", "Lucro
   * Presumido"...). Serve para exibir e para o formulário fiscal sugerir
   * campos — nunca para decidir tributação.
   *
   * Quem decide CSOSN vs CST é o `crt` abaixo, que é o código numérico da
   * NF-e. Texto muda, código não.
   */
  regime_tributario?: string | null;
  /** Código de Regime Tributário da NF-e: 1=Simples, 2=Simples excesso, 3=Normal, 4=MEI. */
  crt?: number | null;
  /**
   * Inscrição Estadual. O backend sempre devolveu; faltava aqui.
   *
   * Vai impressa no cupom da NFC-e — é dado obrigatório do emitente no
   * documento fiscal, não enfeite de cabeçalho.
   */
  inscricao_estadual?: string | null;
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
