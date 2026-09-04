/**
 * @fileoverview Composable para lógica de login
 * @description Encapsula toda a lógica de estado, validação e submissão
 * do formulário de login utilizando Vee-Validate e Vue Query.
 */

import { ref, onMounted, reactive } from 'vue';
import { useForm } from 'vee-validate';
import { useMutation, useQueryClient } from '@tanstack/vue-query';
import { loginValidationSchema, type LoginFormData } from '../schemas/login.schema';
import {
  login,
  saveRememberMe,
  clearRememberMe,
  getRememberedEmail,
} from '../services/auth.service';
import type { LoginResponse } from '../types/auth.types';
import { useAuthStore } from '@/shared/stores/auth.store';
import type { ApiError } from '@/shared/types/axios.types';
import { getErrorMessage } from '@/shared/utils/error.utils';
import { useToast } from '@/shared/composables/useToast';
import type { AxiosError } from 'axios';
import { useAppNavigation } from '@/shared/composables/useAppNavigation';
import { storeToRefs } from 'pinia';

/**
 * Composable que gerencia o formulário de login
 * @returns Objeto com estados e métodos para o formulário
 */
export function useLogin() {
  const queryClient = useQueryClient();
  const authStore = useAuthStore();
  const { userData } = storeToRefs(authStore);
  const { goToHome, goToSignIn } = useAppNavigation();
  const toast = useToast();
  const rememberMe = ref(false);
  const savedEmail = ref<string | null>(null);
  const apiError = ref<string | null>(null);

  /**
   * Configuração do formulário com Vee-Validate
   */
  const { handleSubmit, errors, defineField, resetForm, submitCount } = useForm<LoginFormData>({
    validationSchema: loginValidationSchema,
  });

  /**
   * Definição dos campos do formulário
   */
  const loginData: LoginFormData = reactive({
    email: defineField('email')[0],
    senha: defineField('senha')[0],
  });

  /**
   * Mutation do Vue Query para login.
   *
   * O CACHE DO USUÁRIO ANTERIOR MORRE AQUI.
   *
   * O `logoutUser` só removia a chave `['user-me']`, e o `logoutAndRedirect`
   * troca de tela com `router.replace` — navegação de SPA, sem recarregar a
   * página. O `QueryClient` é o MESMO objeto de um login ao outro, então caixa,
   * vendas, dashboard e relatórios do usuário que saiu continuavam guardados.
   *
   * O sintoma que chegou da loja: entrar como funcionário e ver, por alguns
   * segundos, "Caixa aberto · <nome do master>" e o faturamento dele nos cards,
   * até o refetch corrigir. O TanStack entrega o cache na hora (`staleTime` de 5
   * min em `vueQueryConfig.ts`) e só depois vai à rede. E `/caixa/atual` responde
   * por `funcionario_id`: o dado é mesmo de cada um.
   *
   * ⚠️ POR QUE AQUI E NÃO NO LOGOUT. A `auth.store` chama `useUserQuery()` no
   * corpo da store — Pinia de setup roda uma vez e vive enquanto o app viver,
   * então esse observador NUNCA desmonta. Um `clear()` no logout o faria refazer
   * a busca na mesma hora, já sem token, direto no 401 do interceptor — que
   * chama o logout de novo. No login não existe esse laço: o token novo já está
   * gravado, e a rebusca disparada pelo `clear()` traz o usuário certo.
   */
  const loginMutation = useMutation<LoginResponse, AxiosError<ApiError>, LoginFormData>({
    mutationFn: (data) => login({ email: data.email, senha: data.senha }),
    onSuccess: async () => {
      // 0. Apaga o cache do usuário ANTERIOR — ver o bloco acima.
      queryClient.clear();

      // 1. Força a atualização e AGUARDA terminar
      await authStore.revalidateUser();

      // 2. Verificação de segurança: Se após revalidar, o usuário ainda for null, algo falhou.
      if (!userData.value) {
        apiError.value = 'Erro ao recuperar sessão. Faça login novamente.';
        authStore.logoutUser();
        return;
      }

      // Lógica do Lembrar-me
      if (rememberMe.value && loginData.email) {
        saveRememberMe(loginData.email);
      } else {
        clearRememberMe();
      }

      apiError.value = null;
      toast.success('Login realizado com sucesso!');

      // 3. Redirecionamento seguro
      if (userData.value.empresa) {
        goToHome();
      } else {
        goToSignIn();
      }
    },
    onError: (error) => {
      const detail = error.response?.data?.detail;
      if (typeof detail === 'object' && detail !== null && 'codigo' in detail) {
        const errorDetail = detail as unknown as { codigo: string; mensagem: string };
        apiError.value = errorDetail.mensagem;

        if (errorDetail.codigo === 'LIMITE_TERMINAIS') {
          toast.error(errorDetail.mensagem);
        }
      } else {
        apiError.value = getErrorMessage(error, 'Erro ao realizar login');
      }
    },
  });

  /**
   * Handler de submissão do formulário
   */
  const loginSubmit = handleSubmit((values) => {
    apiError.value = null;
    loginMutation.mutate(values);
  });

  /**
   * Carrega email salvo se "lembrar-me" estava ativo
   */
  onMounted(() => {
    savedEmail.value = getRememberedEmail();
    if (savedEmail.value) {
      rememberMe.value = true;
    }
  });

  return {
    // Campos do formulário
    loginData,
    savedEmail,
    rememberMe,

    // Estado de erros
    errors,
    apiError,

    // Estado de loading
    isLoading: loginMutation.isPending,

    // Métodos
    loginSubmit,
    resetForm,
    submitCount,
  };
}
