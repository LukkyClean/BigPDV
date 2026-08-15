/**
 * @fileoverview Employee form composable with provide/inject pattern
 * @description Manages form state, validation, and submission for create/edit
 * Uses provide/inject to share form state between components within Vue's reactive context
 */

import {
  ref,
  watch,
  computed,
  provide,
  inject,
  type InjectionKey,
  type Ref,
  type ComputedRef,
} from 'vue';
import { useForm, useFieldArray, type FieldEntry } from 'vee-validate';
import { employeeValidationSchema } from '../schemas/employee.schema';
import type {
  EmployeeFormData,
  EnderecoFormData,
  FuncionarioCreate,
  FuncionarioUpdate,
  FuncionarioRead,
  State,
} from '../types/employees.types';
import { useCreateEmployeeMutation, useUpdateEmployeeMutation } from './useEmployeesQuery';
import { useEmployeeModal } from './useEmployeeModal';
import { useToast } from '@/shared/composables/useToast';
import { unmaskDocument, unmaskPhone, unmaskCep } from '@/shared/utils/unmask.utils';

// =============================================
// Constants
// =============================================

export const DEFAULT_ENDERECO: EnderecoFormData = {
  cep: '',
  logradouro: '',
  numero: '',
  complemento: '',
  bairro: '',
  cidade: '',
  estado: '',
};

/**
 * Rótulo de cada campo como ele aparece na TELA. Usado para dizer ao usuário
 * qual campo reprovou — a chave técnica ("cargo_id", "mae") não ajuda ninguém.
 */
const ROTULOS: Record<string, string> = {
  nome: 'Nome Completo',
  cpf: 'CPF',
  data_nascimento: 'Data Nascimento',
  jornada_trabalho: 'Jornada',
  genero: 'Gênero',
  rg: 'RG',
  telefone: 'Telefone',
  celular: 'Celular',
  email: 'E-mail',
  cnh: 'CNH',
  carteira_trabalho: 'Carteira de Trabalho',
  salario_bruto: 'Salário Bruto',
  tipo_contrato: 'Tipo de Contrato',
  data_admissao: 'Data Admissão',
  cargo_id: 'Cargo',
  mae: 'Nome da Mãe',
  pai: 'Nome do Pai',
  titular_conta: 'Titular da Conta',
  tipo_conta: 'Tipo da Conta',
  banco: 'Banco',
  agencia: 'Agência',
  conta: 'Conta',
  observacao: 'Observações',
  usuario_nome: 'Nome de Usuário',
  usuario_email: 'E-mail do Usuário',
  usuario_senha: 'Senha',
  // Endereço (array) — a seção não exibe erro por campo, então o toast é a
  // ÚNICA forma de o usuário saber que o problema está aqui.
  cep: 'CEP',
  logradouro: 'Logradouro',
  numero: 'Número',
  complemento: 'Complemento',
  bairro: 'Bairro',
  cidade: 'Cidade',
  estado: 'Estado',
};

/** "enderecos[0].cep" -> "Endereço 1: CEP"; "nome" -> "Nome Completo". */
function rotuloDoCampo(chave: string): string {
  const endereco = chave.match(/^enderecos\[(\d+)\]\.(.+)$/);
  if (endereco) {
    const [, indice, campo] = endereco;
    return `Endereço ${Number(indice) + 1}: ${ROTULOS[campo] ?? campo}`;
  }
  return ROTULOS[chave] ?? chave;
}

const DEFAULT_FORM_VALUES: EmployeeFormData = {
  // Dados Funcionario
  nome: '',
  cpf: '',
  data_nascimento: '',
  jornada_trabalho: '',
  genero: '',
  rg: '',
  telefone: '',
  celular: '',
  email: '',
  cargo_id: null,
  cnh: '',
  salario_bruto: 0,
  tipo_contrato: '',
  data_admissao: '',
  mae: '',
  pai: '',
  carteira_trabalho: '',

  // Usuario
  usuario_nome: '',
  usuario_email: '',
  usuario_senha: '',

  // Enderecos
  enderecos: [{ ...DEFAULT_ENDERECO }],

  // Dados Bancarios
  titular_conta: '',
  cpf_titular: '',
  tipo_conta: '',
  banco: '',
  agencia: '',
  conta: '',

  // Comissão (override do cargo). null = herda.
  comissao_venda_percentual: null,
  comissao_servico_percentual: null,
  meta_mensal: null,
  comissao_modo: null,

  // Observacoes
  observacao: '',
};

// =============================================
// Types for Injection
// =============================================

export interface EmployeeFormContext {
  // Dados Funcionario fields
  nome: Ref<string>;
  cpf: Ref<string>;
  data_nascimento: Ref<string>;
  jornada_trabalho: Ref<string>;
  genero: Ref<string>;
  rg: Ref<string>;
  telefone: Ref<string>;
  celular: Ref<string>;
  email: Ref<string>;
  cargo_id: Ref<number | null>;
  cnh: Ref<string>;
  salario_bruto: Ref<number>;
  tipo_contrato: Ref<string>;
  data_admissao: Ref<string>;
  mae: Ref<string>;
  pai: Ref<string>;
  carteira_trabalho: Ref<string>;

  // Usuario fields
  usuario_nome: Ref<string>;
  usuario_email: Ref<string>;
  usuario_senha: Ref<string>;

  // Dados Bancarios fields
  titular_conta: Ref<string>;
  tipo_conta: Ref<string>;
  banco: Ref<string>;
  agencia: Ref<string>;
  conta: Ref<string>;

  // Comissão (override do cargo)
  comissao_venda_percentual: Ref<number | null | undefined>;
  comissao_servico_percentual: Ref<number | null | undefined>;
  meta_mensal: Ref<number | null | undefined>;
  comissao_modo: Ref<'direto' | 'meta' | null | undefined>;

  // Observacoes
  observacao: Ref<string>;

  // Enderecos
  enderecos: Ref<FieldEntry<EnderecoFormData>[]>;
  handleAddEndereco: () => void;
  handleRemoveEndereco: (index: number) => void;

  // Form state
  errors: Ref<Record<string, string | undefined>>;
  submitCount: Ref<number>;
  values: EmployeeFormData;
  apiError: Ref<string | null>;
  isPending: ComputedRef<boolean>;

  // Actions
  onSubmit: (e?: Event) => void;
  resetForm: () => void;
}

// Injection key for type safety
export const EMPLOYEE_FORM_KEY: InjectionKey<EmployeeFormContext> = Symbol('employee-form');

// =============================================
// Provider Composable (call in parent component)
// =============================================

export function useEmployeeFormProvider() {
  const { selectedEmployee, isCreateMode, closeModal } = useEmployeeModal();
  const toast = useToast();

  // Initialize form
  const { handleSubmit, errors, defineField, setValues, resetForm, submitCount, values, setErrors } =
    useForm<EmployeeFormData>({
      validationSchema: employeeValidationSchema,
      initialValues: { ...DEFAULT_FORM_VALUES },
    });

  const createMutation = useCreateEmployeeMutation(setErrors);
  const updateMutation = useUpdateEmployeeMutation(setErrors);


  // Define all fields
  const [nome] = defineField('nome');
  const [cpf] = defineField('cpf');
  const [data_nascimento] = defineField('data_nascimento');
  const [jornada_trabalho] = defineField('jornada_trabalho');
  const [genero] = defineField('genero');
  const [rg] = defineField('rg');
  const [telefone] = defineField('telefone');
  const [celular] = defineField('celular');
  const [email] = defineField('email');
  const [cargo_id] = defineField('cargo_id');
  const [cnh] = defineField('cnh');
  const [salario_bruto] = defineField('salario_bruto');
  const [tipo_contrato] = defineField('tipo_contrato');
  const [data_admissao] = defineField('data_admissao');
  const [mae] = defineField('mae');
  const [pai] = defineField('pai');
  const [carteira_trabalho] = defineField('carteira_trabalho');

  const [usuario_nome] = defineField('usuario_nome');
  const [usuario_email] = defineField('usuario_email');
  const [usuario_senha] = defineField('usuario_senha');

  const [titular_conta] = defineField('titular_conta');
  const [tipo_conta] = defineField('tipo_conta');
  const [banco] = defineField('banco');
  const [agencia] = defineField('agencia');
  const [conta] = defineField('conta');

  const [comissao_venda_percentual] = defineField('comissao_venda_percentual');
  const [comissao_servico_percentual] = defineField('comissao_servico_percentual');
  const [meta_mensal] = defineField('meta_mensal');
  const [comissao_modo] = defineField('comissao_modo');

  const [observacao] = defineField('observacao');

  // Field array for enderecos
  const {
    fields: enderecos,
    push: pushEndereco,
    remove: removeEndereco,
  } = useFieldArray<EnderecoFormData>('enderecos');

  const apiError = ref<string | null>(null);

  // Handlers for enderecos
  function handleAddEndereco() {
    pushEndereco({ ...DEFAULT_ENDERECO });
  }

  function handleRemoveEndereco(index: number) {
    removeEndereco(index);
  }

  // Populate form when editing
  function populateForm(employee: FuncionarioRead) {
    setValues({
      nome: employee.nome,
      cpf: employee.cpf,
      data_nascimento: employee.data_nascimento || undefined,
      jornada_trabalho: employee.jornada_trabalho || '',
      genero: employee.genero || '',
      rg: employee.rg || '',
      telefone: employee.telefone || '',
      celular: employee.celular || '',
      email: employee.email || '',
      cargo_id: employee.cargo_id,
      cnh: employee.cnh || '',
      salario_bruto: employee.salario_bruto || 0,
      tipo_contrato: employee.tipo_contrato || '',
      data_admissao: employee.data_admissao || undefined,
      mae: employee.mae || '',
      pai: employee.pai || '',
      carteira_trabalho: employee.carteira_trabalho || '',
      usuario_nome: '',
      usuario_email: '',
      usuario_senha: '',
      enderecos:
        employee.endereco?.map((e) => ({
          cep: e.cep,
          logradouro: e.logradouro,
          numero: e.numero,
          complemento: e.complemento || '',
          bairro: e.bairro,
          cidade: e.cidade,
          estado: e.estado,
        })) || [],
      titular_conta: employee.titular_conta || '',
      tipo_conta: employee.tipo_conta || '',
      banco: employee.banco || '',
      agencia: employee.agencia || '',
      conta: employee.conta || '',
      comissao_venda_percentual: employee.comissao_venda_percentual ?? null,
      comissao_servico_percentual: employee.comissao_servico_percentual ?? null,
      meta_mensal: employee.meta_mensal ?? null,
      comissao_modo: employee.comissao_modo ?? null,
      observacao: employee.observacao || '',
    });
  }

  // Watch for employee changes
  watch(
    selectedEmployee,
    (employee) => {
      if (employee) {
        populateForm(employee);
      } else {
        resetForm({ values: { ...DEFAULT_FORM_VALUES } });
      }
    },
    { immediate: true },
  );


/**
 * Endereço em branco não vai no payload.
 *
 * O formulário começa com uma linha de endereço vazia, e mandá-la fazia o
 * backend recusar com 422 (lá os seis campos são obrigatórios). Quem não quer
 * endereço simplesmente não preenche.
 */
function enderecoTemConteudo(e: { cep?: string; logradouro?: string; numero?: string; bairro?: string; cidade?: string; estado?: string }): boolean {
  return [e.cep, e.logradouro, e.numero, e.bairro, e.cidade, e.estado].some((v) => !!v?.trim());
}
  // Transform to API format
  function transformToCreateRequest(formData: EmployeeFormData): FuncionarioCreate {
    return {
      nome: formData.nome,
      cpf: unmaskDocument(formData.cpf),
      telefone: formData.telefone ? unmaskPhone(formData.telefone) : undefined,
      celular: formData.celular ? unmaskPhone(formData.celular) : undefined,
      email: formData.email || undefined,
      rg: formData.rg || undefined,
      carteira_trabalho: formData.carteira_trabalho || undefined,
      cnh: formData.cnh || undefined,
      genero: formData.genero || undefined,
      titular_conta: formData.titular_conta || undefined,
      banco: formData.banco || undefined,
      agencia: formData.agencia || undefined,
      conta: formData.conta || undefined,
      tipo_conta: formData.tipo_conta || undefined,
      data_nascimento: formData.data_nascimento || undefined,
      mae: formData.mae || undefined,
      pai: formData.pai || undefined,
      observacao: formData.observacao || undefined,
      jornada_trabalho: formData.jornada_trabalho || undefined,
      salario_bruto: formData.salario_bruto || undefined,
      tipo_contrato: formData.tipo_contrato || undefined,
      data_admissao: formData.data_admissao || undefined,
      cargo_id: formData.cargo_id || undefined,
      // Comissão (override do cargo). null = herda -> omite.
      comissao_venda_percentual: formData.comissao_venda_percentual ?? undefined,
      comissao_servico_percentual: formData.comissao_servico_percentual ?? undefined,
      meta_mensal: formData.meta_mensal ?? undefined,
      comissao_modo: formData.comissao_modo ?? undefined,
      usuario: {
        nome: formData.usuario_nome,
        email: formData.usuario_email,
        senha: formData.usuario_senha,
      },
      endereco:
        formData.enderecos.some(enderecoTemConteudo)
          ? formData.enderecos.filter(enderecoTemConteudo).map((e) => ({
              logradouro: e.logradouro,
              numero: e.numero,
              bairro: e.bairro,
              cidade: e.cidade,
              estado: e.estado as State,
              cep: unmaskCep(e.cep),
              complemento: e.complemento || undefined,
            }))
          : undefined,
    };
  }

  // Submit handler
  const onSubmit = handleSubmit(
    async (formData) => {
      apiError.value = null;

      if (isCreateMode.value) {
        // Validate user fields in create mode
        if (!formData.usuario_nome || formData.usuario_nome.length < 3) {
          apiError.value = 'Nome de usuario deve ter no minimo 3 caracteres';
          return;
        }
        if (!formData.usuario_email || !formData.usuario_email.includes('@')) {
          apiError.value = 'Email do usuario e obrigatorio';
          return;
        }
        if (!formData.usuario_senha || formData.usuario_senha.length < 8) {
          apiError.value = 'Senha deve ter no minimo 8 caracteres';
          return;
        }

        const request = transformToCreateRequest(formData);
        createMutation.mutate(request, {
          onSuccess: () => {
            closeModal();
            resetForm({ values: { ...DEFAULT_FORM_VALUES } });
          },
        });
      } else if (selectedEmployee.value) {
        const updateData: FuncionarioUpdate = {
          // Dados Pessoais e Identidade
          nome: formData.nome,
          cpf: unmaskDocument(formData.cpf), // Removendo máscara para o backend
          email: formData.email || undefined,
          telefone: formData.telefone ? unmaskPhone(formData.telefone) : undefined,
          celular: formData.celular ? unmaskPhone(formData.celular) : undefined,
          rg: formData.rg || undefined,
          cnh: formData.cnh || undefined,
          carteira_trabalho: formData.carteira_trabalho || undefined,
          genero: formData.genero || undefined,
          data_nascimento: formData.data_nascimento || undefined,
          mae: formData.mae || undefined,
          pai: formData.pai || undefined,

          // Financeiro
          titular_conta: formData.titular_conta || undefined,
          banco: formData.banco || undefined,
          agencia: formData.agencia || undefined,
          conta: formData.conta || undefined,
          tipo_conta: formData.tipo_conta || undefined,
          salario_bruto: formData.salario_bruto || undefined,

          // Empresa
          cargo_id: formData.cargo_id || undefined,
          jornada_trabalho: formData.jornada_trabalho || undefined,
          tipo_contrato: formData.tipo_contrato || undefined,
          data_admissao: formData.data_admissao || undefined,

          // Comissão (override). Envia null explícito p/ permitir LIMPAR e voltar a herdar.
          comissao_venda_percentual: formData.comissao_venda_percentual,
          comissao_servico_percentual: formData.comissao_servico_percentual,
          meta_mensal: formData.meta_mensal,
          comissao_modo: formData.comissao_modo,

          // Observações
          observacao: formData.observacao || undefined,

          // Endereços (Mantendo a lógica de ID para edição)
          endereco:
            // Guarda o índice ORIGINAL antes de filtrar: é ele que casa com o
            // `id` do endereço já salvo. Filtrar primeiro deslocaria a posição
            // e gravaria por cima do endereço errado.
            formData.enderecos.some(enderecoTemConteudo)
              ? formData.enderecos
                  .map((e, idx) => ({ e, idx }))
                  .filter(({ e }) => enderecoTemConteudo(e))
                  .map(({ e, idx }) => ({
                  id: selectedEmployee.value?.endereco?.[idx]?.id,
                  logradouro: e.logradouro,
                  numero: e.numero,
                  bairro: e.bairro,
                  cidade: e.cidade,
                  estado: e.estado as State,
                  cep: unmaskCep(e.cep),
                  complemento: e.complemento || undefined,
                }))
              : undefined,
        };

        updateMutation.mutate(
          { id: selectedEmployee.value.id, data: updateData },
          {
            onSuccess: () => {
              closeModal();
              resetForm({ values: { ...DEFAULT_FORM_VALUES } });
            },
          },
        );
      }
    },
    ({ errors: camposInvalidos }) => {
      // O handleSubmit do vee-validate falha CALADO: se a validação reprova, ele
      // não chama a mutation e não avisa ninguém. Antes aqui só havia um
      // console.log('[DEBUG]'), então o usuário clicava em Salvar, nada
      // acontecia, e não dava para saber o motivo — ainda mais porque a seção de
      // Endereço não exibe erro por campo.
      const nomes = Object.keys(camposInvalidos).map(rotuloDoCampo);
      const unicos = [...new Set(nomes)];
      toast.error(
        unicos.length === 1
          ? `Verifique o campo: ${unicos[0]}`
          : `Verifique ${unicos.length} campos`,
        unicos.join(' • '),
      );
    },
  );

  const isPending = computed(
    () => createMutation.isPending.value || updateMutation.isPending.value,
  );

  // Create context object
  const context: EmployeeFormContext = {
    nome,
    cpf,
    data_nascimento,
    jornada_trabalho,
    genero,
    rg,
    telefone,
    celular,
    email,
    cargo_id,
    cnh,
    salario_bruto,
    tipo_contrato,
    data_admissao,
    mae,
    pai,
    carteira_trabalho,
    usuario_nome,
    usuario_email,
    usuario_senha,
    titular_conta,
    tipo_conta,
    banco,
    agencia,
    conta,
    comissao_venda_percentual,
    comissao_servico_percentual,
    meta_mensal,
    comissao_modo,
    observacao,
    enderecos,
    handleAddEndereco,
    handleRemoveEndereco,
    errors,
    submitCount,
    values,
    apiError,
    isPending,
    onSubmit,
    resetForm: () => resetForm({ values: { ...DEFAULT_FORM_VALUES } }),
  };

  // Provide context to children
  provide(EMPLOYEE_FORM_KEY, context);

  return context;
}

// =============================================
// Consumer Composable (call in child components)
// =============================================

export function useEmployeeForm(): EmployeeFormContext {
  const context = inject(EMPLOYEE_FORM_KEY);

  if (!context) {
    throw new Error(
      'useEmployeeForm must be used within a component that has called useEmployeeFormProvider',
    );
  }

  return context;
}
