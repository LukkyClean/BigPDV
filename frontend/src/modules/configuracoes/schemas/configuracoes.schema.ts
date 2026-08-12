import { z } from 'zod'

export const ConfiguracaoProdutosSchema = z.object({
  id: z.number(),
  empresa_id: z.number(),

  exigir_codigo_barras: z.boolean(),
  exigir_categoria: z.boolean(),
  exigir_preco_custo: z.boolean(),

  margem_lucro_padrao: z.number(),
  utilizar_preco_atacado: z.boolean(),

  permitir_venda_estoque_zerado: z.boolean(),
  quantidade_minima_padrao: z.number(),
  unidade_medida_padrao: z.string(),

  data_atualizacao: z.string(),
})

export const ConfiguracaoProdutosUpdateSchema = ConfiguracaoProdutosSchema
  .omit({ id: true, empresa_id: true, data_atualizacao: true })
  .partial()

export type ConfiguracaoProdutosRead = z.infer<typeof ConfiguracaoProdutosSchema>
export type ConfiguracaoProdutosUpdate = z.infer<typeof ConfiguracaoProdutosUpdateSchema>

export const ConfiguracaoClientesSchema = z.object({
  id: z.number(),
  empresa_id: z.number(),

  exigir_cpf_pf: z.boolean(),
  exigir_cnpj_pj: z.boolean(),
  exigir_celular: z.boolean(),
  exigir_rg_pf: z.boolean(),
  exigir_ie_pj: z.boolean(),
  exigir_email: z.boolean(),
  exigir_endereco: z.boolean(),

  tipo_pessoa_padrao: z.enum(['PF', 'PJ']),
  exibir_genero: z.boolean(),
  exibir_data_nascimento: z.boolean(),

  bloquear_faturamento_inativo: z.boolean(),
  oferecer_reativacao_rapida: z.boolean(),

  ativar_limite_credito: z.boolean(),
  bloquear_venda_limite: z.boolean(),

  data_atualizacao: z.string(),
})

export const ConfiguracaoClientesUpdateSchema = ConfiguracaoClientesSchema
  .omit({ id: true, empresa_id: true, data_atualizacao: true })
  .partial()

export type ConfiguracaoClientesRead = z.infer<typeof ConfiguracaoClientesSchema>
export type ConfiguracaoClientesUpdate = z.infer<typeof ConfiguracaoClientesUpdateSchema>

export const ConfiguracaoVendasSchema = z.object({
  id: z.number(),
  empresa_id: z.number(),

  permitir_desconto: z.boolean(),
  desconto_maximo_percent: z.number().int().min(0).max(100),
  exigir_cliente_identificado: z.boolean(),
  valor_minimo_venda: z.number().int().min(0),
  permitir_parcelamento: z.boolean(),
  parcelas_maximas: z.number().int().min(1).max(48),

  data_atualizacao: z.string(),
})

export const ConfiguracaoVendasUpdateSchema = ConfiguracaoVendasSchema
  .omit({ id: true, empresa_id: true, data_atualizacao: true })
  .partial()

export type ConfiguracaoVendasRead = z.infer<typeof ConfiguracaoVendasSchema>
export type ConfiguracaoVendasUpdate = z.infer<typeof ConfiguracaoVendasUpdateSchema>

export const GARANTIA_OPTIONS = [
  'Sem garantia',
  '30 dias',
  '60 dias',
  '90 dias',
  '6 meses',
  '1 ano',
] as const

/**
 * Apresentação dos comprovantes. Só a FORMA — o conteúdo é invariante (dados da
 * empresa, do cliente com endereço, itens discriminados e resumo do pagamento
 * saem sempre, porque protegem o cliente).
 * Ver backend-fastapi/docs/comprovantes-perfil-plano.md
 *
 * `.catch()` nos dois: uma loja atualizada cujo backend ainda não tenha as
 * colunas devolveria o campo ausente, e sem isso o Zod reprovaria a resposta
 * inteira — derrubando toda a config de OS por causa de um campo novo.
 */
export const FOLHA_OPTIONS = ['A4', 'A5'] as const
export const DENSIDADE_OPTIONS = ['normal', 'compacto'] as const

export const ConfiguracaoOSSchema = z.object({
  id: z.number(),
  empresa_id: z.number(),

  prazo_entrega_padrao: z.number().int().min(1),
  garantia_padrao: z.enum(GARANTIA_OPTIONS),
  prazo_abandono_dias: z.number().int().min(1),
  taxa_diagnostico_padrao: z.number().int().min(0),

  comprovante_entrada_folha: z.enum(FOLHA_OPTIONS).catch('A4'),
  comprovante_entrada_densidade: z.enum(DENSIDADE_OPTIONS).catch('normal'),
  comprovante_entrega_folha: z.enum(FOLHA_OPTIONS).catch('A4'),
  comprovante_entrega_densidade: z.enum(DENSIDADE_OPTIONS).catch('normal'),

  data_atualizacao: z.string(),
})

export const ConfiguracaoOSUpdateSchema = ConfiguracaoOSSchema
  .omit({ id: true, empresa_id: true, data_atualizacao: true })
  .partial()

export type ConfiguracaoOSRead = z.infer<typeof ConfiguracaoOSSchema>
export type ConfiguracaoOSUpdate = z.infer<typeof ConfiguracaoOSUpdateSchema>

export const ConfiguracaoSegurancaSchema = z.object({
  id: z.number(),
  empresa_id: z.number(),

  tem_pin_configurado: z.boolean(),

  secoes_protegidas: z.array(z.string()),
  requer_pin_cancelar_venda: z.boolean(),
  requer_pin_reabrir_venda: z.boolean(),
  requer_pin_desconto_venda: z.boolean(),
  requer_pin_alterar_preco_venda: z.boolean(),
  requer_pin_cancelar_os: z.boolean(),
  requer_pin_reabrir_os: z.boolean(),
  requer_pin_desconto_os: z.boolean(),

  data_atualizacao: z.string(),
})

export const PinGerenteSchema = z
  .string()
  .regex(/^\d{4,6}$/, 'O PIN deve ter de 4 a 6 dígitos numéricos')

export const ConfiguracaoSegurancaUpdateSchema = ConfiguracaoSegurancaSchema
  .omit({ id: true, empresa_id: true, data_atualizacao: true, tem_pin_configurado: true })
  .partial()
  .extend({ pin_gerente: PinGerenteSchema.optional() })

export type ConfiguracaoSegurancaRead = z.infer<typeof ConfiguracaoSegurancaSchema>
export type ConfiguracaoSegurancaUpdate = z.infer<typeof ConfiguracaoSegurancaUpdateSchema>
