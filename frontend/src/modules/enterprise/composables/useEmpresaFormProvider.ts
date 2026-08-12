import { ref, computed, watch, nextTick, provide, inject, type InjectionKey } from 'vue';
import { useToast } from '@/shared/composables/useToast';
import { buscarDadosCNPJ } from './useConsultaCNPJ';
import { useForm } from 'vee-validate';
import { empresaValidationSchema, EmpresaFormSchema } from '../schemas/empresa.schema';
import {
  useEmpresaQuery,
  useUpdateEmpresaMutation,
  useUploadCertificadoMutation,
  useUploadLogoMutation,
  useTestSefazMutation,
  useTestPrefeituraMutation,
  useWindowsCertificatesQuery,
} from './useEmpresaQuery';
import { useAuthStore } from '@/shared/stores/auth.store';
import { DEFAULT_FISCAL_SETTINGS, DEFAULT_ENDERECO } from '../constants/empresa.constants';
import {
  formatCEP,
  formatCNPJ,
  formatCPF,
  formatTelefone,
  unmaskDocument,
  unmaskPhone,
  unmaskCep,
} from '@/shared/utils/document.utils';
import type {
  EmpresaFormData,
  EmpresaFormContext,
  EmpresaUpdate,
  EmpresaRead,
  Endereco,
} from '../types/empresa.types';

// =============================================
// Injection Key (type-safe)
// =============================================

export const EMPRESA_FORM_KEY: InjectionKey<EmpresaFormContext> = Symbol('empresa-form');

// =============================================
// Default Form Values
// =============================================

const DEFAULT_FORM_VALUES: EmpresaFormData = {
  razao_social: '',
  nome_fantasia: '',
  documento: '',
  is_cnpj: true,
  email: '',
  telefone: '',
  celular: '',
  inscricao_estadual: '',
  inscricao_municipal: '',
  regime_tributario: '',
  cnae_principal: '',
  indicador_ie: '',
  natureza_juridica: '',
  tipo_atividade: '',
  cnaes_secundarios: '',
  data_abertura: '',
  website: '',
  url_logo: '',
  fiscal_settings: { ...DEFAULT_FISCAL_SETTINGS },
  endereco_principal: { ...DEFAULT_ENDERECO },
  certificado_senha: '',
};

// =============================================
// Funções utilitárias
// =============================================

function formatDocumento(documento: string, isCnpj: boolean | undefined): string {
  if (!documento) return '';
  const digits = documento.replace(/\D/g, '');
  if (isCnpj === true) return formatCNPJ(digits);
  if (isCnpj === false) return formatCPF(digits);
  if (digits.length === 14) return formatCNPJ(digits);
  if (digits.length === 11) return formatCPF(digits);
  return documento;
}

/**
 * Normaliza dados da API para formato do formulário
 * - Adiciona máscaras de formatação (CNPJ, telefone, CEP)
 * - Extrai primeiro endereço como endereco_principal
 * - Aplica valores default para campos ausentes
 *
 * @param data - Dados da empresa vindos da API
 * @returns Dados formatados para o formulário VeeValidate
 */
function normalizeEmpresaToForm(data: EmpresaRead): EmpresaFormData {
  const telefone = data.telefone ? formatTelefone(data.telefone) : '';
  const celular = data.celular ? formatTelefone(data.celular) : '';
  const enderecoPrincipal = data.enderecos?.[0];

  return {
    razao_social: data.razao_social ?? '',
    nome_fantasia: data.nome_fantasia ?? '',
    documento: formatDocumento(data.documento ?? '', data.is_cnpj),
    is_cnpj: data.is_cnpj ?? true,
    email: data.email ?? '',
    telefone,
    celular,
    inscricao_estadual: data.inscricao_estadual ?? '',
    inscricao_municipal: data.inscricao_municipal ?? '',
    regime_tributario: data.regime_tributario?.toString() ?? '',
    cnae_principal: data.cnae_principal ?? '',
    indicador_ie: data.indicador_ie ?? '',
    natureza_juridica: data.natureza_juridica ?? '',
    tipo_atividade: data.tipo_atividade ?? '',
    cnaes_secundarios: data.cnaes_secundarios ?? '',
    data_abertura: data.data_abertura ?? '',
    website: data.website ?? '',
    url_logo: data.url_logo ?? '',
    fiscal_settings: data.fiscal_settings ?? DEFAULT_FISCAL_SETTINGS,
    endereco_principal: enderecoPrincipal
      ? {
          ...enderecoPrincipal,
          cep: formatCEP(enderecoPrincipal.cep ?? ''),
        }
      : DEFAULT_ENDERECO,
    certificado_senha: '',
  };
}



// =============================================
// Provider Composable
// =============================================

/**
 * Provider de contexto do formulário de empresa
 * Gerencia estado com VeeValidate e provide/inject pattern
 *
 * @returns Context com fields, state, computed e actions
 */
export function useEmpresaFormProvider() {
  // Dependencies
  const authStore = useAuthStore();
  const toast = useToast();
  const empresaId = computed(() => authStore.userData?.empresa?.id);

  // TanStack Query hooks
  const { data: empresaData, isLoading } = useEmpresaQuery();

  const updateMutation = useUpdateEmpresaMutation();
  const uploadCertMutation = useUploadCertificadoMutation();
  const uploadLogoMutation = useUploadLogoMutation();
  const testSefazMutation = useTestSefazMutation();
  const testPrefeituraMutation = useTestPrefeituraMutation();
  const { data: windowsCertificates, refetch: refetchWindowsCerts } = useWindowsCertificatesQuery();

  // VeeValidate Form
  const { handleSubmit, errors, defineField, resetForm, submitCount, values, meta } =
    useForm<EmpresaFormData>({
      validationSchema: empresaValidationSchema,
      initialValues: { ...DEFAULT_FORM_VALUES },
    });

  // =============================================
  // Define Fields (VeeValidate)
  // =============================================

  const [razao_social] = defineField('razao_social');
  const [nome_fantasia] = defineField('nome_fantasia');
  const [documento] = defineField('documento');
  const [is_cnpj] = defineField('is_cnpj');
  const [email] = defineField('email');
  const [telefone] = defineField('telefone');
  const [celular] = defineField('celular');
  const [inscricao_estadual] = defineField('inscricao_estadual');
  const [inscricao_municipal] = defineField('inscricao_municipal');
  const [regime_tributario] = defineField('regime_tributario');
  const [cnae_principal] = defineField('cnae_principal');
  const [indicador_ie] = defineField('indicador_ie');
  const [natureza_juridica] = defineField('natureza_juridica');
  const [tipo_atividade] = defineField('tipo_atividade');
  const [cnaes_secundarios] = defineField('cnaes_secundarios');
  const [data_abertura] = defineField('data_abertura');
  const [website] = defineField('website');
  const [url_logo] = defineField('url_logo');
  const [fiscal_settings] = defineField('fiscal_settings');
  const [endereco_principal] = defineField('endereco_principal');
  const [certificado_senha] = defineField('certificado_senha');

  // =============================================
  // API Error State
  // =============================================

  const apiError = ref<string | null>(null);

  // =============================================
  // Computed States
  // =============================================

  const isDirty = computed(() => meta.value.dirty);

  const isPending = computed(() => updateMutation.isPending.value);

  const canEmitirProducao = computed(() => {
    const settings = fiscal_settings.value;
    if (!settings) return false;

    const hasCertificado =
      settings.tipo_certificado === 'ARQUIVO'
        ? !!settings.certificado_digital_path
        : !!settings.certificado_thumbprint;

    return hasCertificado && !!settings.csc_token && !!settings.csc_id;
  });

  const hasCertificado = computed(() => {
    const settings = fiscal_settings.value;
    if (!settings) return false;

    return settings.tipo_certificado === 'ARQUIVO'
      ? !!settings.certificado_digital_path
      : !!settings.certificado_thumbprint;
  });

  // =============================================
  // Watchers - Sync com API
  // =============================================

  // CNPJ salvo no servidor — usado para evitar lookup automático no carregamento
  const cnpjSalvo = ref('');

  // Snapshot JSON dos valores carregados do servidor.
  // Comparado com os valores atuais do formulário para detectar alterações reais.
  // Evita dependência do meta.dirty do VeeValidate, que pode ter falsos positivos
  // ao comparar objetos com campos null (API) vs campos ausentes (DEFAULT_FORM_VALUES).
  const snapshotServidor = ref('');

  // Flag: true após resetForm ter se propagado completamente (2 ticks).
  // Impede que o guard de saída dispare durante o carregamento inicial.
  const formPronto = ref(false);

  watch(
    empresaData,
    (data) => {
      if (!data) return;
      formPronto.value = false;
      cnpjSalvo.value = (data.documento || '').replace(/\D/g, '');
      const formValues = { ...DEFAULT_FORM_VALUES, ...normalizeEmpresaToForm(data) };
      resetForm({ values: formValues });
      // Aguarda dois ciclos para cobrir:
      // 1. nextTick interno do VeeValidate (validate silent pós-reset)
      // 2. debounce de 5ms da validação silenciosa (debouncedSilentValidation)
      // 3. maska e demais diretivas que podem alterar values via input event
      // O watcher de values (flush:'post') mantém snapshotServidor atualizado durante
      // esse período; o setTimeout apenas sinaliza que a inicialização terminou.
      nextTick(() => {
        setTimeout(() => {
          snapshotServidor.value = JSON.stringify(values);
          formPronto.value = true;
        }, 50);
      });
    },
    { immediate: true },
  );

  // Mantém snapshotServidor sincronizado com values enquanto o formulário ainda
  // está em fase de inicialização (formPronto = false). Isso garante que qualquer
  // atualização pós-render (maska, coerção Zod via VeeValidate, etc.) seja
  // capturada no snapshot antes do guard de saída ser ativado.
  watch(
    values,
    () => {
      if (!formPronto.value) {
        snapshotServidor.value = JSON.stringify(values);
      }
    },
    { deep: true, flush: 'post' },
  );

  // True quando há alterações reais do usuário não salvas.
  // Usa comparação JSON em vez de meta.dirty para evitar falsos positivos.
  const temAlteracoesPendentes = computed(() => {
    if (!formPronto.value || !snapshotServidor.value) return false;
    return JSON.stringify(values) !== snapshotServidor.value;
  });

  // =============================================
  // Transform Functions
  // =============================================

  /**
   * Transforma dados do form para payload da API
   * NOTA: Quando chamado após EmpresaFormSchema.parse(), os campos
   * documento, telefone, celular e cep já estão normalizados (sem máscaras)
   *
   * @param formData - Dados do formulário (normalizados ou não)
   * @returns Payload formatado para a API
   */
  function transformToUpdatePayload(formData: EmpresaFormData): EmpresaUpdate {
    // Os dados podem vir já normalizados do Zod ou com máscaras (para outros usos)
    // Por segurança, aplicamos unmask caso ainda tenham máscaras
    const payload: EmpresaUpdate = {
      razao_social: formData.razao_social,
      nome_fantasia: formData.nome_fantasia || undefined,
      documento: formData.documento ? unmaskDocument(formData.documento) : undefined,
      is_cnpj: formData.is_cnpj,
      email: formData.email || undefined,
      telefone: formData.telefone ? unmaskPhone(formData.telefone) : undefined,
      celular: formData.celular ? unmaskPhone(formData.celular) : undefined,
      inscricao_estadual: formData.inscricao_estadual || undefined,
      inscricao_municipal: formData.inscricao_municipal || undefined,
      regime_tributario: formData.regime_tributario || undefined,
      cnae_principal: formData.cnae_principal || undefined,
      indicador_ie: formData.indicador_ie || undefined,
      natureza_juridica: formData.natureza_juridica || undefined,
      tipo_atividade: formData.tipo_atividade || undefined,
      cnaes_secundarios: formData.cnaes_secundarios || undefined,
      data_abertura: formData.data_abertura || undefined,
      website: formData.website || undefined,
    };

    // Transform endereco_principal -> endereco[]
    if (formData.endereco_principal) {
      payload.endereco = [
        {
          ...formData.endereco_principal,
          cep: formData.endereco_principal.cep ? unmaskCep(formData.endereco_principal.cep) : '',
          codigo_ibge: formData.endereco_principal.codigo_ibge?.replace(/[^\d]/g, ''),
        } as Endereco,
      ];
    }

    // Add fiscal settings with certificado_senha
    if (formData.fiscal_settings) {
      payload.fiscal_settings = {
        ...formData.fiscal_settings,
        certificado_senha: formData.certificado_senha ?? '',
      };
    }

    return payload;
  }

  // =============================================
  // Action Handlers
  // =============================================

  function handleLogoUpload(file: File) {
    uploadLogoMutation.mutate(file, {
      onSuccess: (updatedEmpresa) => {
        url_logo.value = updatedEmpresa.url_logo || '';
      },
    });
  }

  /**
   * Upload de certificado A1 com validação de senha.
   *
   * IMPORTANTE: A senha é passada como parâmetro e NÃO é persistida no state do form.
   * Ela trafega apenas nesta requisição para validação do certificado.
   *
   * @param file - Arquivo .pfx ou .p12
   * @param senha - Senha do certificado (usada apenas para validação)
   */
  function handleCertUpload(file: File, senha: string) {
    // Senha é passada diretamente para a mutation, não armazenada no state
    uploadCertMutation.mutate(
      { file, senha },
      {
        onSuccess: (updatedEmpresa) => {
          if (updatedEmpresa.fiscal_settings) {
            fiscal_settings.value = {
              ...fiscal_settings.value,
              tipo_certificado: updatedEmpresa.fiscal_settings.tipo_certificado,
              certificado_digital_path: updatedEmpresa.fiscal_settings.certificado_digital_path,
              certificado_validade: updatedEmpresa.fiscal_settings.certificado_validade,
              certificado_subject: updatedEmpresa.fiscal_settings.certificado_subject,
              certificado_thumbprint: undefined, // Limpar Windows se estava usando
            };
          }
          // Limpar senha do formulário após upload bem sucedido
          certificado_senha.value = '';
        },
      }
    );
  }

  // =============================================
  // CNPJ Lookup (BrasilAPI / Receita Federal)
  // =============================================

  const isConsultingCNPJ = ref(false);

  async function consultarCNPJ(cnpjDigits: string) {
    if (isConsultingCNPJ.value) return;
    isConsultingCNPJ.value = true;

    try {
      const dados = await buscarDadosCNPJ(cnpjDigits);

      razao_social.value = dados.razao_social || razao_social.value;
      nome_fantasia.value = dados.nome_fantasia || nome_fantasia.value;
      cnae_principal.value = dados.cnae_principal || cnae_principal.value;
      cnaes_secundarios.value = dados.cnaes_secundarios || cnaes_secundarios.value;
      if (dados.natureza_juridica) natureza_juridica.value = dados.natureza_juridica;
      data_abertura.value = dados.data_abertura || data_abertura.value;

      // Contato: preenche só se vazio
      if (!email.value && dados.email) email.value = dados.email;
      if (!telefone.value && dados.telefone) telefone.value = formatTelefone(dados.telefone);

      // Endereço completo
      endereco_principal.value = {
        ...endereco_principal.value,
        logradouro: dados.logradouro || endereco_principal.value.logradouro,
        numero: dados.numero || endereco_principal.value.numero,
        complemento: dados.complemento || endereco_principal.value.complemento,
        bairro: dados.bairro || endereco_principal.value.bairro,
        cidade: dados.cidade || endereco_principal.value.cidade,
        estado: dados.estado || endereco_principal.value.estado,
        cep: dados.cep ? formatCEP(dados.cep) : endereco_principal.value.cep,
        codigo_ibge: dados.codigo_ibge || endereco_principal.value.codigo_ibge,
      };

      toast.success('Dados da Receita Federal preenchidos automaticamente!');
    } catch {
      toast.error('CNPJ não encontrado na Receita Federal.');
    } finally {
      isConsultingCNPJ.value = false;
    }
  }

  // =============================================
  // Tipo de Pessoa (PF/PJ)
  // =============================================

  /**
   * Alterna a empresa entre Pessoa Física (CPF) e Pessoa Jurídica (CNPJ).
   *
   * O documento é limpo na troca porque CPF e CNPJ têm máscaras diferentes —
   * manter os dígitos antigos deixaria o campo com uma formatação que não
   * corresponde ao novo tipo. Ao virar PF, os campos exclusivos de PJ também
   * são zerados: a seção Dados Fiscais some da tela nesse modo, e um campo
   * escondido continuaria sendo enviado no payload (IE de uma empresa que
   * não tem IE).
   *
   * No-op quando o tipo não muda, para não marcar o formulário como sujo.
   */
  function setTipoPessoa(isCnpj: boolean) {
    if (is_cnpj.value === isCnpj) return;

    is_cnpj.value = isCnpj;
    documento.value = '';

    if (!isCnpj) {
      inscricao_estadual.value = '';
      inscricao_municipal.value = '';
      regime_tributario.value = '';
      indicador_ie.value = '';
      natureza_juridica.value = '';
      tipo_atividade.value = '';
      cnae_principal.value = '';
      cnaes_secundarios.value = '';
      data_abertura.value = '';
    }
  }

  function handleTestSefaz() {
    if (!empresaId.value) return;
    testSefazMutation.mutate(empresaId.value);
  }

  function handleTestPrefeitura() {
    if (!empresaId.value) return;
    testPrefeituraMutation.mutate(empresaId.value);
  }

  // =============================================
  // Submit Handler
  // =============================================

  const onSubmit = handleSubmit(
    async (formData) => {
      apiError.value = null;

      // ========== RUNTIME VALIDATION (HARD GATE) ==========
      // Mesmo com VeeValidate validando, fazemos uma verificação final
      // para garantir que dados programáticos/edge cases passem pelo Zod
      const parseResult = EmpresaFormSchema.safeParse(formData);
      if (!parseResult.success) {
        const firstError = parseResult.error.errors[0];
        apiError.value = firstError.message;
        console.error('[Zod Validation Failed]', parseResult.error.errors);
        return;
      }

      if (!empresaId.value) {
        apiError.value = 'ID da empresa não encontrado';
        return;
      }

      // Usar dados já normalizados pelo Zod parse
      const payload = transformToUpdatePayload(parseResult.data as EmpresaFormData);

      updateMutation.mutate(
        { data: payload },
        {
          onSuccess: () => {
            // Sincroniza snapshot com os valores atuais para zerar temAlteracoesPendentes
            snapshotServidor.value = JSON.stringify(values);
            resetForm({ values: { ...values } });
          },
          onError: (error: any) => {
            apiError.value = error?.response?.data?.detail || 'Erro ao salvar empresa';
          },
        },
      );
    },
    (validationErrors) => {
      console.log('[DEBUG] VeeValidate errors:', validationErrors);
    },
  );

  // =============================================
  // Build Context
  // =============================================

  const context: EmpresaFormContext = {
    // Fields
    razao_social,
    nome_fantasia,
    documento,
    is_cnpj,
    email,
    telefone,
    celular,
    inscricao_estadual,
    inscricao_municipal,
    regime_tributario,
    cnae_principal,
    indicador_ie,
    natureza_juridica,
    tipo_atividade,
    cnaes_secundarios,
    data_abertura,
    website,
    url_logo,
    fiscal_settings,
    endereco_principal,
    certificado_senha,

    // State
    errors,
    submitCount,
    values,
    apiError,
    isLoading,
    isPending,
    isDirty,

    // Computed
    canEmitirProducao,
    hasCertificado,

    // Mutations state
    isUploadingLogo: computed(() => uploadLogoMutation.isPending.value),
    isUploadingCert: computed(() => uploadCertMutation.isPending.value),
    isTestingSefaz: computed(() => testSefazMutation.isPending.value),
    isTestingPrefeitura: computed(() => testPrefeituraMutation.isPending.value),
    isLoadingCertificates: computed(() => false), // refetch is manual

    // Window Certificates
    windowsCertificates: windowsCertificates.value || [],

    // CNPJ Lookup
    cnpjSalvo,
    isConsultingCNPJ,
    consultarCNPJ,

    // Alterações pendentes
    formPronto,
    temAlteracoesPendentes,

    // Actions
    onSubmit,
    setTipoPessoa,
    handleLogoUpload,
    handleCertUpload,
    handleTestSefaz,
    handleTestPrefeitura,
    refetchWindowsCerts,
    resetForm: () => resetForm({ values: { ...DEFAULT_FORM_VALUES } }),
  };

  // Provide to children
  provide(EMPRESA_FORM_KEY, context);

  return context;
}

// =============================================
// Consumer Composable (Inject)
// =============================================

/**
 * Inject helper para form sections
 * Retorna o context fornecido por useEmpresaFormProvider
 *
 * @throws Error se usado fora do provider
 * @returns EmpresaFormContext
 */
export function useEmpresaForm(): EmpresaFormContext {
  const context = inject(EMPRESA_FORM_KEY);

  if (!context) {
    throw new Error(
      'useEmpresaForm must be used within a component that has called useEmpresaFormProvider',
    );
  }

  return context;
}
