/**
 * @fileoverview Tipos TypeScript para o módulo axios
 * @description Define as interfaces e tipos utilizados nas operações de erros
 * do axios
 */

/**
 * Interface para erro de validação de campo
 */
export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

/**
 * Interface para erro da API
 */
export interface ApiError {
  detail?: string | ValidationError[];
  message?: string;
  status?: number;
}

/**
 * Códigos de erro HTTP comuns
 */
export const HTTP_ERROR_CODES = {
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500,
  SERVICE_UNAVAILABLE: 503,
} as const;

/**
 * Mensagens de erro amigáveis para o usuário
 */
export const ERROR_MESSAGES: Record<number, string> = {
  [HTTP_ERROR_CODES.BAD_REQUEST]: 'Dados inválidos. Verifique as informações e tente novamente.',
  [HTTP_ERROR_CODES.UNAUTHORIZED]: 'Email ou senha incorretos.',
  [HTTP_ERROR_CODES.FORBIDDEN]: 'Você não tem permissão para realizar esta ação.',
  [HTTP_ERROR_CODES.NOT_FOUND]: 'Recurso não encontrado.',
  [HTTP_ERROR_CODES.CONFLICT]: 'Este registro já existe.',
  [HTTP_ERROR_CODES.UNPROCESSABLE_ENTITY]: 'Não foi possível processar os dados enviados.',
  [HTTP_ERROR_CODES.TOO_MANY_REQUESTS]: 'Muitas tentativas. Aguarde alguns minutos e tente novamente.',
  [HTTP_ERROR_CODES.INTERNAL_SERVER_ERROR]: 'Erro interno do servidor. Tente novamente mais tarde.',
  [HTTP_ERROR_CODES.SERVICE_UNAVAILABLE]: 'Serviço temporariamente indisponível. Tente novamente mais tarde.',
};

/**
 * Mensagem padrão para erros de rede
 */
// O backend é local (mesma máquina ou rede da loja) — não falar em "internet": numa
// loja sem link isso manda o operador olhar para o lugar errado.
export const NETWORK_ERROR_MESSAGE =
  'Sem comunicação com o servidor. Verifique se o servidor está ligado e conectado à rede local.';

export interface ConflictedData {
  campo: string,
  mensagem: string,
}