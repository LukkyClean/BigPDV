/**
 * @fileoverview Product form composable with provide/inject pattern
 * @description Manages form state, validation, and submission for create/edit
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
import { useForm } from 'vee-validate';
import { productValidationSchema } from '../schemas/product.schema';
import type {
  ProductFormData,
  ProdutoCreate,
  ProdutoUpdate,
  ProdutoRead,
} from '../types/products.types';
import { useCreateProductMutation, useUpdateProductMutation } from './useProductsQuery';
import { useProductModal } from './useProductModal';
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';
import { recursoDisponivel } from '@/shared/config/planos';
import { getProdutoFiscal } from '../services/product.service';

// =============================================
// Constants
// =============================================

const DEFAULT_FORM_VALUES: ProductFormData = {
  nome: '',
  codigo_produto: '',
  codigo_barras: '',
  unidade_medida: '',
  categoria: '',
  marca: '',
  fornecedor_id: '',
  localizacao_estoque: '',
  observacao: '',

  valor_entrada: 0,
  valor_varejo: 0,
  valor_atacado: 0,
  quantidade: 0,
  quantidade_minima: 0,
  quantidade_ideal: 0,

  image_url: '',

  fiscal_ncm: '',
  fiscal_cest: '',
  fiscal_cfop_padrao: '',
  // 0 = Nacional. É a origem da esmagadora maioria do varejo, e o campo é
  // obrigatório na emissão — nascer vazio só produzia pendência.
  fiscal_origem_mercadoria: '0',
  fiscal_unidade_tributavel: '',
  fiscal_gtin_tributavel: '',
  fiscal_cst_icms: '',
  fiscal_csosn: '',
  fiscal_aliquota_icms_display: '',
  fiscal_reducao_base_icms_display: '',
  fiscal_codigo_beneficio_fiscal: '',
  fiscal_aliquota_pis_display: '',
  fiscal_aliquota_cofins_display: '',
  fiscal_cst_pis: '',
  fiscal_cst_cofins: '',
  fiscal_c_class_trib: '',
  fiscal_cst_ibs_cbs: '',
  fiscal_aliquota_ibs_display: '',
  fiscal_aliquota_cbs_display: '',
  fiscal_c_benef: '',
};

// =============================================
// Helpers
// =============================================

function toCents(value?: number): number | undefined {
  if (value === null || value === undefined) return undefined;
  return Math.round(value * 100);
}

function toNumberOrUndefined(value?: string): number | undefined {
  if (!value) return undefined;
  const parsed = parseInt(value, 10);
  return Number.isNaN(parsed) ? undefined : parsed;
}

/** Percentual digitado ("18", "1.65") → centésimos de ponto (1800, 165). */
function percentualParaCentesimos(valor?: string): number | null {
  if (!valor) return null;
  const numero = Number(valor);
  return Number.isNaN(numero) ? null : Math.round(numero * 100);
}

/**
 * Monta o bloco fiscal a partir do formulário.
 *
 * Um só lugar para criação e edição: enquanto isto vivia dentro do `onSubmit`
 * do update, o cadastro simplesmente não mandava dado fiscal nenhum, e o
 * lojista precisava salvar, reabrir e preencher de novo.
 *
 * A unidade tributável cai para a comercial quando vazia — é a prática aceita
 * no varejo fracionado e o que o `payload_builder` do backend já faz.
 */
function construirPayloadFiscal(formData: ProductFormData): Record<string, unknown> {
  return {
    ncm: formData.fiscal_ncm || null,
    cest: formData.fiscal_cest || null,
    cfop_padrao: formData.fiscal_cfop_padrao || null,
    origem_mercadoria:
      formData.fiscal_origem_mercadoria !== '' && formData.fiscal_origem_mercadoria != null
        ? Number(formData.fiscal_origem_mercadoria)
        : null,
    unidade_tributavel: formData.fiscal_unidade_tributavel || formData.unidade_medida || null,
    gtin_tributavel: formData.fiscal_gtin_tributavel || null,
    cst_icms: formData.fiscal_cst_icms || null,
    csosn: formData.fiscal_csosn || null,
    aliquota_icms: percentualParaCentesimos(formData.fiscal_aliquota_icms_display),
    reducao_base_icms: percentualParaCentesimos(formData.fiscal_reducao_base_icms_display),
    codigo_beneficio_fiscal: formData.fiscal_codigo_beneficio_fiscal || null,
    aliquota_pis: percentualParaCentesimos(formData.fiscal_aliquota_pis_display),
    aliquota_cofins: percentualParaCentesimos(formData.fiscal_aliquota_cofins_display),
    cst_pis: formData.fiscal_cst_pis || null,
    cst_cofins: formData.fiscal_cst_cofins || null,
    c_class_trib: formData.fiscal_c_class_trib || null,
    cst_ibs_cbs: formData.fiscal_cst_ibs_cbs || null,
    aliquota_ibs: percentualParaCentesimos(formData.fiscal_aliquota_ibs_display),
    aliquota_cbs: percentualParaCentesimos(formData.fiscal_aliquota_cbs_display),
    c_benef: formData.fiscal_c_benef || null,
  };
}

/** True quando o lojista escreveu alguma coisa no bloco fiscal. */
function temDadoFiscal(payload: Record<string, unknown>): boolean {
  return Object.values(payload).some((valor) => valor !== null && valor !== '');
}

// =============================================
// Types for Injection
// =============================================

export interface ProductFormContext {
  nome: Ref<string>;
  codigo_produto: Ref<string>;
  codigo_barras: Ref<string>;
  unidade_medida: Ref<string>;
  categoria: Ref<string>;
  marca: Ref<string>;
  fornecedor_id: Ref<string>;
  localizacao_estoque: Ref<string>;
  observacao: Ref<string>;

  valor_entrada: Ref<number>;
  valor_varejo: Ref<number>;
  valor_atacado: Ref<number>;
  quantidade: Ref<number>;
  quantidade_minima: Ref<number>;
  quantidade_ideal: Ref<number>;

  imageFile: Ref<File | null>;
  image_url: Ref<string | null>;

  // Dados fiscais
  fiscal_ncm: Ref<string>;
  fiscal_cest: Ref<string>;
  fiscal_cfop_padrao: Ref<string>;
  fiscal_origem_mercadoria: Ref<string>;
  fiscal_unidade_tributavel: Ref<string>;
  fiscal_gtin_tributavel: Ref<string>;
  fiscal_cst_icms: Ref<string>;
  fiscal_csosn: Ref<string>;
  fiscal_aliquota_icms_display: Ref<string>;
  fiscal_reducao_base_icms_display: Ref<string>;
  fiscal_codigo_beneficio_fiscal: Ref<string>;
  fiscal_aliquota_pis_display: Ref<string>;
  fiscal_aliquota_cofins_display: Ref<string>;
  fiscal_cst_pis: Ref<string>;
  fiscal_cst_cofins: Ref<string>;
  fiscal_c_class_trib: Ref<string>;
  fiscal_cst_ibs_cbs: Ref<string>;
  fiscal_aliquota_ibs_display: Ref<string>;
  fiscal_aliquota_cbs_display: Ref<string>;
  fiscal_c_benef: Ref<string>;
  nfeDisponivel: boolean;

  errors: Ref<Record<string, string | undefined>>;
  submitCount: Ref<number>;
  values: ProductFormData;
  apiError: Ref<string | null>;
  isPending: ComputedRef<boolean>;

  onSubmit: (e?: Event) => void;
  resetForm: () => void;
}

export const PRODUCT_FORM_KEY: InjectionKey<ProductFormContext> = Symbol('product-form');

// =============================================
// Provider Composable (call in parent component)
// =============================================

export function useProductFormProvider() {
  const { selectedProduct, isCreateMode, closeModal, isOpen } = useProductModal();
  const configStore = useConfiguracoesStore();

  const {
    handleSubmit,
    errors,
    defineField,
    setValues,
    resetForm,
    submitCount,
    values,
    setErrors,
  } = useForm<ProductFormData>({
    validationSchema: productValidationSchema,
    initialValues: { ...DEFAULT_FORM_VALUES },
  });

  const imageFile = ref<File | null>(null);

  const createMutation = useCreateProductMutation(setErrors, imageFile);
  const updateMutation = useUpdateProductMutation(setErrors, imageFile);

  const [nome] = defineField('nome');
  const [codigo_produto] = defineField('codigo_produto');
  const [codigo_barras] = defineField('codigo_barras');
  const [unidade_medida] = defineField('unidade_medida');
  const [categoria] = defineField('categoria');
  const [marca] = defineField('marca');
  const [fornecedor_id] = defineField('fornecedor_id');
  const [localizacao_estoque] = defineField('localizacao_estoque');
  const [observacao] = defineField('observacao');

  const [valor_entrada] = defineField('valor_entrada');
  const [valor_varejo] = defineField('valor_varejo');
  const [valor_atacado] = defineField('valor_atacado');
  const [quantidade] = defineField('quantidade');
  const [quantidade_minima] = defineField('quantidade_minima');
  const [quantidade_ideal] = defineField('quantidade_ideal');
  
  const [image_url] = defineField('image_url');

  // Campos fiscais
  const nfeDisponivel = recursoDisponivel('nfe');
  const [fiscal_ncm] = defineField('fiscal_ncm');
  const [fiscal_cest] = defineField('fiscal_cest');
  const [fiscal_cfop_padrao] = defineField('fiscal_cfop_padrao');
  const [fiscal_origem_mercadoria] = defineField('fiscal_origem_mercadoria');
  const [fiscal_unidade_tributavel] = defineField('fiscal_unidade_tributavel');
  const [fiscal_gtin_tributavel] = defineField('fiscal_gtin_tributavel');
  const [fiscal_cst_icms] = defineField('fiscal_cst_icms');
  const [fiscal_csosn] = defineField('fiscal_csosn');
  const [fiscal_aliquota_icms_display] = defineField('fiscal_aliquota_icms_display');
  const [fiscal_reducao_base_icms_display] = defineField('fiscal_reducao_base_icms_display');
  const [fiscal_codigo_beneficio_fiscal] = defineField('fiscal_codigo_beneficio_fiscal');
  const [fiscal_aliquota_pis_display] = defineField('fiscal_aliquota_pis_display');
  const [fiscal_aliquota_cofins_display] = defineField('fiscal_aliquota_cofins_display');
  const [fiscal_cst_pis] = defineField('fiscal_cst_pis');
  const [fiscal_cst_cofins] = defineField('fiscal_cst_cofins');
  const [fiscal_c_class_trib] = defineField('fiscal_c_class_trib');
  const [fiscal_cst_ibs_cbs] = defineField('fiscal_cst_ibs_cbs');
  const [fiscal_aliquota_ibs_display] = defineField('fiscal_aliquota_ibs_display');
  const [fiscal_aliquota_cbs_display] = defineField('fiscal_aliquota_cbs_display');
  const [fiscal_c_benef] = defineField('fiscal_c_benef');

  const apiError = ref<string | null>(null);

  async function populateForm(product: ProdutoRead) {
    setValues({
      nome: product.nome,
      codigo_produto: product.codigo_produto,
      codigo_barras: product.codigo_barras || '',
      unidade_medida: product.unidade_medida || '',
      categoria: product.categoria || '',
      marca: product.marca || '',
      fornecedor_id: product.fornecedor_id ? String(product.fornecedor_id) : '',
      localizacao_estoque: product.localizacao_estoque || '',
      observacao: product.observacao || '',

      valor_entrada: product.estoque.valor_entrada ? product.estoque.valor_entrada / 100 : 0,
      valor_varejo: product.estoque.valor_varejo / 100,
      valor_atacado: product.estoque.valor_atacado ? product.estoque.valor_atacado / 100 : 0,
      quantidade: product.estoque.quantidade,
      quantidade_minima: product.estoque.quantidade_minima || 0,
      quantidade_ideal: product.estoque.quantidade_ideal || 0,
      image_url: product.fotos?.find((foto) => foto.principal)?.url || null,
    });

    // Carrega dados fiscais em paralelo (se módulo ativo)
    if (nfeDisponivel) {
      try {
        const fiscal = await getProdutoFiscal(product.id);
        if (fiscal) {
          setValues({
            fiscal_ncm: fiscal.ncm ?? '',
            fiscal_cest: fiscal.cest ?? '',
            fiscal_cfop_padrao: fiscal.cfop_padrao ?? '',
            fiscal_origem_mercadoria: fiscal.origem_mercadoria != null ? String(fiscal.origem_mercadoria) : '',
            fiscal_unidade_tributavel: fiscal.unidade_tributavel ?? '',
            fiscal_gtin_tributavel: fiscal.gtin_tributavel ?? '',
            fiscal_cst_icms: fiscal.cst_icms ?? '',
            fiscal_csosn: fiscal.csosn ?? '',
            fiscal_aliquota_icms_display: fiscal.aliquota_icms != null ? String(fiscal.aliquota_icms / 100) : '',
            fiscal_reducao_base_icms_display: fiscal.reducao_base_icms != null ? String(fiscal.reducao_base_icms / 100) : '',
            fiscal_codigo_beneficio_fiscal: fiscal.codigo_beneficio_fiscal ?? '',
            fiscal_aliquota_pis_display: fiscal.aliquota_pis != null ? String(fiscal.aliquota_pis / 100) : '',
            fiscal_aliquota_cofins_display: fiscal.aliquota_cofins != null ? String(fiscal.aliquota_cofins / 100) : '',
            fiscal_cst_pis: fiscal.cst_pis ?? '',
            fiscal_cst_cofins: fiscal.cst_cofins ?? '',
            fiscal_c_class_trib: fiscal.c_class_trib ?? '',
            fiscal_cst_ibs_cbs: fiscal.cst_ibs_cbs ?? '',
            // Sem `Math.round`: ele estava só neste par e comia a casa
            // decimal — 5,5% era gravado como 550 e voltava 6.
            fiscal_aliquota_ibs_display: fiscal.aliquota_ibs != null ? String(fiscal.aliquota_ibs / 100) : '',
            fiscal_aliquota_cbs_display: fiscal.aliquota_cbs != null ? String(fiscal.aliquota_cbs / 100) : '',
            fiscal_c_benef: fiscal.c_benef ?? '',
          } as any, false);
        }
      } catch {
        // Falha ao carregar fiscal não deve bloquear a edição do produto
      }
    }
  }

  watch(
    [selectedProduct, isOpen],
    ([product, open]) => {
      if (!open) return;
      if (product) {
        populateForm(product);
      } else {
        resetForm({
          values: {
            ...DEFAULT_FORM_VALUES,
            unidade_medida: configStore.unidadeMedidaPadrao,
            quantidade_minima: configStore.quantidadeMinimaPadrao,
          },
        });
      }
    },
    { immediate: true },
  );

  function transformToCreateRequest(formData: ProductFormData): ProdutoCreate {
    // O bloco fiscal viaja no MESMO POST: o backend grava os dois numa
    // transação só, então um NCM torto derruba o produto junto em vez de
    // deixar meio cadastro no banco.
    const fiscal = nfeDisponivel ? construirPayloadFiscal(formData) : null;

    return {
      ...(fiscal && temDadoFiscal(fiscal) ? { fiscal } : {}),
      nome: formData.nome,
      codigo_produto: formData.codigo_produto,
      codigo_barras: formData.codigo_barras || undefined,
      unidade_medida: formData.unidade_medida || undefined,
      observacao: formData.observacao || undefined,
      categoria: formData.categoria || undefined,
      marca: formData.marca || undefined,
      fornecedor_id: toNumberOrUndefined(formData.fornecedor_id),
      localizacao_estoque: formData.localizacao_estoque || undefined,
      estoque: {
        valor_varejo: toCents(formData.valor_varejo) || 0,
        quantidade: formData.quantidade || undefined,
        valor_entrada: toCents(formData.valor_entrada),
        valor_atacado: toCents(formData.valor_atacado),
        quantidade_minima: formData.quantidade_minima || undefined,
        quantidade_ideal: formData.quantidade_ideal || undefined,
      },
    };
  }

  const onSubmit = handleSubmit(
    async (formData) => {
      apiError.value = null;

      const errosConfig: Record<string, string> = {};
      if (configStore.exigirCodigoBarras && !formData.codigo_barras) {
        errosConfig.codigo_barras = 'Código de barras é obrigatório';
      }
      if (configStore.exigirCategoria && !formData.categoria) {
        errosConfig.categoria = 'Categoria é obrigatória';
      }
      if (configStore.exigirPrecoCusto && (!formData.valor_entrada || formData.valor_entrada <= 0)) {
        errosConfig.valor_entrada = 'Preço de custo é obrigatório';
      }
      if (Object.keys(errosConfig).length > 0) {
        setErrors(errosConfig);
        return;
      }

      if (isCreateMode.value) {
        const request = transformToCreateRequest(formData);
        createMutation.mutate(request, {
          onSuccess: () => {
            closeModal();
            resetForm({
              values: {
                ...DEFAULT_FORM_VALUES,
                unidade_medida: configStore.unidadeMedidaPadrao,
                quantidade_minima: configStore.quantidadeMinimaPadrao,
              },
            });
          },
        });
      } else if (selectedProduct.value) {
        const updateData: ProdutoUpdate & { fiscal?: Record<string, unknown> } = {
          nome: formData.nome,
          codigo_produto: formData.codigo_produto,
          codigo_barras: formData.codigo_barras || undefined,
          unidade_medida: formData.unidade_medida || undefined,
          observacao: formData.observacao || undefined,
          categoria: formData.categoria || undefined,
          marca: formData.marca || undefined,
          fornecedor_id: toNumberOrUndefined(formData.fornecedor_id),
          localizacao_estoque: formData.localizacao_estoque || undefined,
          estoque: {
            valor_varejo: toCents(formData.valor_varejo),
            quantidade: formData.quantidade,
            valor_entrada: toCents(formData.valor_entrada),
            valor_atacado: toCents(formData.valor_atacado),
            quantidade_minima: formData.quantidade_minima || undefined,
            quantidade_ideal: formData.quantidade_ideal || undefined,
          },
        };

        // Mesma montagem do cadastro (ver `construirPayloadFiscal`). Na edição
        // o service chama o endpoint separado de fiscal.
        if (nfeDisponivel) {
          updateData.fiscal = construirPayloadFiscal(formData);
        }

        updateMutation.mutate(
          { id: selectedProduct.value.id, data: updateData },
          {
            onSuccess: () => {
              closeModal();
              resetForm({
                values: {
                  ...DEFAULT_FORM_VALUES,
                  unidade_medida: configStore.unidadeMedidaPadrao,
                  quantidade_minima: configStore.quantidadeMinimaPadrao,
                },
              });
            },
          },
        );
      }
    },
    (validationErrors) => {
      console.log('[DEBUG] Validation errors:', validationErrors);
    },
  );

  const isPending = computed(
    () => createMutation.isPending.value || updateMutation.isPending.value,
  );

  const context: ProductFormContext = {
    nome,
    codigo_produto,
    codigo_barras,
    unidade_medida,
    categoria,
    marca,
    fornecedor_id,
    localizacao_estoque,
    observacao,
    valor_entrada,
    valor_varejo,
    valor_atacado,
    quantidade,
    quantidade_minima,
    quantidade_ideal,
    imageFile,
    image_url,
    fiscal_ncm,
    fiscal_cest,
    fiscal_cfop_padrao,
    fiscal_origem_mercadoria,
    fiscal_unidade_tributavel,
    fiscal_gtin_tributavel,
    fiscal_cst_icms,
    fiscal_csosn,
    fiscal_aliquota_icms_display,
    fiscal_reducao_base_icms_display,
    fiscal_codigo_beneficio_fiscal,
    fiscal_aliquota_pis_display,
    fiscal_aliquota_cofins_display,
    fiscal_cst_pis,
    fiscal_cst_cofins,
    fiscal_c_class_trib,
    fiscal_cst_ibs_cbs,
    fiscal_aliquota_ibs_display,
    fiscal_aliquota_cbs_display,
    fiscal_c_benef,
    nfeDisponivel,
    errors,
    submitCount,
    values,
    apiError,
    isPending,
    onSubmit,
    resetForm: () => resetForm({
      values: {
        ...DEFAULT_FORM_VALUES,
        unidade_medida: configStore.unidadeMedidaPadrao,
        quantidade_minima: configStore.quantidadeMinimaPadrao,
      },
    }),
  };

  provide(PRODUCT_FORM_KEY, context);

  return context;
}

// =============================================
// Consumer Composable (call in child components)
// =============================================

export function useProductForm(): ProductFormContext {
  const context = inject(PRODUCT_FORM_KEY);

  if (!context) {
    throw new Error(
      'useProductForm must be used within a component that has called useProductFormProvider',
    );
  }

  return context;
}
