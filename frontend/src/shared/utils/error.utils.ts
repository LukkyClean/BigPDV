/**
 * @fileoverview Utilitários para tratamento de erros
 * @description Funções helper para extrair e formatar mensagens de erro da API
 */

import type { AxiosError } from 'axios';
import type { ApiError, ValidationError } from '@/shared/types/axios.types';
import { ERROR_MESSAGES, NETWORK_ERROR_MESSAGE, ConflictedData } from '@/shared/types/axios.types';

/**
 * Extrai a mensagem de erro de um ValidationError[] (422 Pydantic)
 * @param errors - Array de erros de validação
 * @returns Mensagem formatada
 */
/** Nomes amigáveis para o campo citado num erro de validação. */
const ROTULOS_CAMPO: Record<string, string> = {
  email: 'E-mail',
  senha: 'Senha',
  nome: 'Nome',
  confirmarSenha: 'Confirmação de senha',
  cpf: 'CPF',
  cnpj: 'CNPJ',
  genero: 'Gênero',
  tipo_conta: 'Tipo de conta',
  salario_bruto: 'Salário bruto',
  data_admissao: 'Data de admissão',
  data_nascimento: 'Data de nascimento',
  logradouro: 'Logradouro',
  numero: 'Número',
  bairro: 'Bairro',
  cidade: 'Cidade',
  estado: 'Estado (UF)',
  cep: 'CEP',
};

/** "endereco.0.estado" → "Estado (UF)"; "cpf" → "CPF". */
function rotuloDoCampo(caminho: string): string {
  const ultimo = caminho.split('.').filter((p) => !/^\d+$/.test(p)).pop() ?? caminho;
  return ROTULOS_CAMPO[ultimo] ?? ultimo;
}

/**
 * Formata o 422 de validação.
 *
 * ⚠ O backend NÃO usa o formato padrão do FastAPI. O handler em
 * `app/core/exceptions.py` emite `[{field, message}]`, e não `[{loc, msg}]`.
 * A versão anterior lia `firstError.loc[...]` e **estourava** (`undefined[...]`)
 * — a exceção acontecia dentro do `onError` da mutation, então o toast nunca
 * aparecia: o usuário via um 422 no console e absolutamente nada na tela.
 *
 * Aceita os dois formatos, e nunca lança: um erro ao formatar um erro deixa o
 * usuário sem nenhuma pista, que é o pior resultado possível.
 */
function formatValidationErrors(errors: ValidationError[]): string {
  if (!Array.isArray(errors) || errors.length === 0) return '';

  const partes = errors.slice(0, 3).map((erro) => {
    const bruto = erro as unknown as {
      field?: string;
      message?: string;
      loc?: unknown[];
      msg?: string;
    };
    const caminho = bruto.field
      ?? (Array.isArray(bruto.loc) ? bruto.loc.filter((p) => p !== 'body').join('.') : '');
    const mensagem = bruto.message ?? bruto.msg ?? '';
    if (!caminho && !mensagem) return '';
    return caminho ? `${rotuloDoCampo(caminho)}: ${mensagem}` : mensagem;
  }).filter(Boolean);

  if (partes.length === 0) return '';
  const resto = errors.length - partes.length;
  return resto > 0 ? `${partes.join(' • ')} (e mais ${resto})` : partes.join(' • ');
}

/**
 * Extrai a mensagem de erro de um ConflictedData[] (409 Conflict)
 * @param errors - Array de conflitos {campo, mensagem}
 * @returns Mensagem formatada concatenando todas as mensagens
 */
function formatConflictErrors(errors: ConflictedData[]): string {
  if (errors.length === 0) return '';
  return errors.map(e => e.mensagem).join('. ');
}

/**
 * Extrai mensagem de erro amigável de um AxiosError
 * @param error - Erro do Axios
 * @param defaultMessage - Mensagem padrão caso não encontre
 * @returns Mensagem de erro formatada para o usuário
 */
export function getErrorMessage(
  error: AxiosError<ApiError>,
  defaultMessage = 'Ocorreu um erro inesperado. Tente novamente.',
): string {
  // Erro de rede (sem resposta do servidor)
  if (!error.response) {
    if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
      return NETWORK_ERROR_MESSAGE;
    }
    if (error.code === 'ECONNABORTED') {
      return 'A requisição demorou muito. Tente novamente.';
    }
    return defaultMessage;
  }

  const { status, data } = error.response;

  // Verifica se há mensagem específica da API
  if (data?.detail) {
    // Se detail for um array
    if (Array.isArray(data.detail)) {
      // 409 Conflict: array de {campo, mensagem}
      if (data.detail.length > 0 && 'campo' in data.detail[0]) {
        return formatConflictErrors(data.detail as unknown as ConflictedData[]);
      }
      // 422 Validation: array de {loc, msg, type}
      return formatValidationErrors(data.detail);
    }
    // Se detail for uma string
    return data.detail;
  }

  // Verifica campo message
  if (data?.message) {
    return data.message;
  }

  // Retorna mensagem baseada no status HTTP
  if (status && ERROR_MESSAGES[status]) {
    return ERROR_MESSAGES[status];
  }

  return defaultMessage;
}

export function getConflictErrors(error: AxiosError<ApiError>): Record<string, string> | null {
  const data = error.response?.data;

  if (Array.isArray(data?.detail)) {
    const conflictedData: ConflictedData[] = data.detail as unknown as ConflictedData[];
    return conflictedData.reduce(
      (acc, curr) => {
        if (curr.campo && curr.mensagem) {
          acc[curr.campo] = curr.mensagem;
        }
        return acc;
      },
      {} as Record<string, string>,
    );
  }

  return null;
}

/**
 * Verifica se é um erro de rede
 * @param error - Erro do Axios
 * @returns true se for erro de rede
 */
export function isNetworkError(error: AxiosError): boolean {
  return !error.response && (error.code === 'ERR_NETWORK' || error.message === 'Network Error');
}

/**
 * Verifica se é um erro de autenticação
 * @param error - Erro do Axios
 * @returns true se for erro 401
 */
export function isAuthError(error: AxiosError): boolean {
  return error.response?.status === 401;
}

/**
 * Verifica se é um erro de conflito (registro duplicado)
 * @param error - Erro do Axios
 * @returns true se for erro 409
 */
export function isConflictError(error: AxiosError): boolean {
  return error.response?.status === 409;
}
