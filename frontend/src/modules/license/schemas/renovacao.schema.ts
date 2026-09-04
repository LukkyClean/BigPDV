import { z } from 'zod';

/**
 * Contrato da renovação de assinatura, do lado da loja.
 *
 * Espelha `app/schemas/licenca.py` (seção "Renovação de Assinatura"). O backend
 * local já traduziu o camelCase da API StartBig para snake_case — aqui não há
 * tradução nenhuma, só validação.
 */

export const MetodoPagamentoSchema = z.enum(['PIX', 'CARTAO']);

export const RenovacaoPeriodoSchema = z.object({
  codigo: z.string(),
  nome: z.string(),
  valor_centavos: z.number(),
  dias: z.number().nullable().optional(),
  /** O que a API manda hoje. `dias` vem nulo. */
  meses: z.number().nullable().optional(),
  /** Fração: 0.054 = 5%. Quem calcula preço é o servidor; aqui só se exibe. */
  desconto: z.number().nullable().optional(),
  metodos: z.array(z.string()).default([]),
});

/**
 * `disponivel: false` **não é erro** — é o estado normal enquanto a API de
 * cobrança não subiu. A tela mostra "indisponível" e o motivo, sem alarme.
 */
export const RenovacaoPlanosSchema = z.object({
  disponivel: z.boolean(),
  periodos: z.array(RenovacaoPeriodoSchema).default([]),
  motivo: z.string().nullable().optional(),
  /** Nome do plano contratado — "Plano Start". Não confundir com os períodos. */
  plano: z.string().nullable().optional(),
  /** Quantos computadores ao mesmo tempo. Vem da licença local. */
  limite_terminais: z.number().nullable().optional(),
});

/**
 * PIX e cartão devolvem o mesmo objeto com metades diferentes preenchidas:
 * PIX traz `pix_copia_e_cola`, cartão traz `url_checkout`. Quem decide o que
 * mostrar é o `metodo`.
 */
export const CobrancaSchema = z.object({
  cobranca_id: z.string(),
  metodo: z.string(),
  valor_centavos: z.number(),
  descricao: z.string().nullable().optional(),
  expira_em: z.string().nullable().optional(),
  pix_copia_e_cola: z.string().nullable().optional(),
  qr_code_base64: z.string().nullable().optional(),
  url_checkout: z.string().nullable().optional(),
});

export const CobrancaStatusSchema = z.object({
  cobranca_id: z.string(),
  status: z.string(),
  pago_em: z.string().nullable().optional(),
  data_vencimento: z.string().nullable().optional(),
  /**
   * O sinal de vitória — e não é o `status`.
   *
   * `status: 'PAGA'` diz que o dinheiro caiu; `licenca_renovada: true` diz que
   * o vencimento novo **já está gravado nesta máquina**. Só o segundo significa
   * que a loja destravou.
   */
  licenca_renovada: z.boolean().default(false),
});

export type MetodoPagamento = z.infer<typeof MetodoPagamentoSchema>;
export type RenovacaoPeriodoDataType = z.infer<typeof RenovacaoPeriodoSchema>;
export type RenovacaoPlanosDataType = z.infer<typeof RenovacaoPlanosSchema>;
export type CobrancaDataType = z.infer<typeof CobrancaSchema>;
export type CobrancaStatusDataType = z.infer<typeof CobrancaStatusSchema>;
