/**
 * @fileoverview API service for employees
 * @description Handles all funcionario-related API calls
 */

import api from '@/api/axios';
import { ENDPOINT_PERMISSION_MAP } from '@/shared/constants/permissions.constants';
import type {
  FuncionarioCreate,
  FuncionarioRead,
  FuncionarioUpdate,
  UsuarioCreate,
} from '../types/employees.types';

const BASE_URL = 'funcionarios' as const;
export const EMPLOYEE_PERMISSION = ENDPOINT_PERMISSION_MAP[BASE_URL];

/**
 * Lista todos os funcionarios ativos ou busca por termo
 * @param buscar - Termo de busca opcional (nome, cpf, email, rg)
 */
export async function getFuncionarios(buscar?: string): Promise<FuncionarioRead[]> {
  const params = buscar ? { buscar } : undefined;
  const { data } = await api.get<FuncionarioRead[]>(`${BASE_URL}/`, { params });
  return data;
}

/**
 * Cria um novo funcionario com usuario e enderecos
 * @param funcionario - Dados do funcionario
 */
export async function createFuncionario(
  funcionario: FuncionarioCreate
): Promise<FuncionarioRead> {
  const { data } = await api.post<FuncionarioRead>(`${BASE_URL}/`, funcionario);
  return data;
}

/**
 * Atualiza dados de um funcionario existente
 * @param id - ID do funcionario
 * @param funcionario - Dados para atualizar
 */
export async function updateFuncionario(
  id: number,
  funcionario: FuncionarioUpdate
): Promise<FuncionarioRead> {
  const { data } = await api.put<FuncionarioRead>(`${BASE_URL}/${id}`, funcionario);
  return data;
}

/**
 * Ativa ou desativa um funcionario
 * @param id - ID do funcionario
 */
export async function toggleFuncionarioAtivo(id: number): Promise<FuncionarioRead> {
  const { data } = await api.put<FuncionarioRead>(`${BASE_URL}/toggle_ativo/${id}`);
  return data;
}

/**
 * Cria o login de um funcionario que foi cadastrado SEM acesso ao sistema.
 *
 * O backend recusa (409) se ele ja tiver usuario — trocar credencial de quem
 * esta trabalhando e outro assunto, e esta porta sobrescreveria a senha sem
 * ninguem pedir.
 */
export async function concederAcessoFuncionario(
  funcionarioId: number,
  usuario: UsuarioCreate
): Promise<FuncionarioRead> {
  const { data } = await api.post<FuncionarioRead>(
    `${BASE_URL}/${funcionarioId}/acesso`,
    usuario
  );
  return data;
}

/**
 * Atualiza o cargo de um funcionario
 * @param funcionarioId - ID do funcionario
 * @param cargoId - ID do novo cargo
 */
export async function updateFuncionarioCargo(
  funcionarioId: number,
  cargoId: number
): Promise<FuncionarioRead> {
  const { data } = await api.put<FuncionarioRead>(
    `${BASE_URL}/${funcionarioId}/cargo`,
    null,
    { params: { cargo_id: cargoId } }
  );
  return data;
}
