/**
 * @fileoverview TanStack Query composable for employees list
 * @description Manages employee listing with search and caching
 */

import type { UsuarioCreate } from '../types/employees.types';
import { computed, type Ref } from 'vue';
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query';
import {
  getFuncionarios,
  createFuncionario,
  updateFuncionario,
  toggleFuncionarioAtivo,
  concederAcessoFuncionario,
} from '../services/employee.service';
import type {
  FuncionarioCreate,
  FuncionarioRead,
  FuncionarioUpdate,
} from '../types/employees.types';
import type { AxiosError } from 'axios';
import type { ApiError } from '@/shared/types/axios.types';
import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage, getConflictErrors, isConflictError } from '@/shared/utils/error.utils';

import { REFETCH_CADASTROS } from '@/core/config/queryIntervals';

const QUERY_KEY = 'funcionarios';
const STALE_TIME = 1000 * 60 * 5; // 5 minutes

/**
 * Query for listing employees
 * @param searchTerm - Optional reactive search term
 */
export function useEmployeesQuery(searchTerm?: Ref<string>) {
  const cleanSearch = computed(() => searchTerm?.value?.trim() || undefined);

  return useQuery({
    queryKey: [QUERY_KEY, cleanSearch],
    queryFn: () => getFuncionarios(cleanSearch.value),
    staleTime: STALE_TIME,
    refetchInterval: REFETCH_CADASTROS,
  });
}

/**
 * Mutation for creating employee
 */
export function useCreateEmployeeMutation(setErrors: any) {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation<FuncionarioRead, AxiosError<ApiError>, FuncionarioCreate>({
    mutationFn: createFuncionario,
    onSuccess: () => {
      toast.success('Funcionario cadastrado com sucesso!');
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
    onError: (error) => {
      if (isConflictError(error)) {
        const conflictedErrors = getConflictErrors(error);
        console.log(conflictedErrors)
        if (conflictedErrors) {
          setErrors(conflictedErrors)
          toast.error('Erro ao cadastrar funcionário', 'Dados já registrados')
          return
        }
      }
      toast.error(getErrorMessage(error, 'Erro ao cadastrar funcionario') as string);
    },
  });
}

/**
 * Mutation for updating employee
 */
export function useConcederAcessoMutation(setErrors: any) {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation<
    FuncionarioRead,
    AxiosError<ApiError>,
    { id: number; usuario: UsuarioCreate }
  >({
    mutationFn: ({ id, usuario }) => concederAcessoFuncionario(id, usuario),
    onSuccess: () => {
      toast.success('Acesso criado', 'O funcionário já pode entrar no sistema.');
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
    onError: (error) => {
      if (isConflictError(error)) {
        const conflitos = getConflictErrors(error);
        if (conflitos) {
          setErrors(conflitos);
          toast.error('Erro ao criar acesso', 'Dados já registrados');
          return;
        }
      }
      toast.error(getErrorMessage(error, 'Erro ao criar acesso') as string);
    },
  });
}

export function useUpdateEmployeeMutation(setErrors: any) {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation< 
    FuncionarioRead,
    AxiosError<ApiError>,
    { id: number; data: FuncionarioUpdate }
  >({
    mutationFn: ({ id, data }) => updateFuncionario(id, data),
    onSuccess: () => {
      toast.success('Funcionario atualizado com sucesso!');
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
    onError: (error) => {
      if (isConflictError(error)) {
        const conflictedErrors = getConflictErrors(error);
        console.log(conflictedErrors)
        if (conflictedErrors) {
          setErrors(conflictedErrors)
          toast.error('Erro ao cadastrar funcionário', 'Dados já registrados')
          return
        }
      }
      toast.error(getErrorMessage(error, 'Erro ao atualizar funcionario') as string);
    },
  });
}

/**
 * Mutation for toggling employee active status
 */
export function useToggleEmployeeActiveMutation() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation<FuncionarioRead, AxiosError<ApiError>, number>({
    mutationFn: toggleFuncionarioAtivo,
    onSuccess: (data) => {
      const status = data.ativo ? 'ativado' : 'desativado';
      toast.success(`Funcionario ${status} com sucesso!`);
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Erro ao alterar status do funcionario') as string);
    },
  });
}
