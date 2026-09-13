import type { SelectOption } from '@/shared/components/ui/BaseSelect/BaseSelect.vue';

/**
 * CSTs de ICMS que o FiscalTaxEngine calcula.
 * Espelha `tax_engine/constants.py:CST_ICMS_SUPORTADOS` — escolher fora desta
 * lista salva no cadastro e é recusado no gate de emissão.
 */
export const CST_ICMS_CALCULADOS = ['00', '20', '40', '41', '60'] as const;

/**
 * CSOSNs que o FiscalTaxEngine calcula.
 * Espelha `tax_engine/constants.py:CSOSN_SUPORTADOS`.
 */
export const CSOSN_CALCULADOS = ['101', '102', '500'] as const;

/**
 * CST de ICMS — regime normal.
 *
 * O rótulo vem primeiro em português e o código depois: quem cadastra produto
 * na loja não sabe o que é "tributada integralmente", sabe o que é "o imposto
 * é destacado na nota".
 */
export const CST_ICMS_OPTIONS: SelectOption[] = [
  { value: '00', label: '00 · Tributado normalmente — o ICMS é destacado na nota' },
  { value: '20', label: '20 · Com redução da base de cálculo — exige informar a redução' },
  { value: '40', label: '40 · Isento' },
  { value: '41', label: '41 · Não tributado' },
  { value: '60', label: '60 · Imposto já pago antes (ST) — pneus, bebidas, autopeças' },
  { value: '10', label: '10 · Tributada com cobrança de ICMS por ST' },
  { value: '30', label: '30 · Isenta/não tributada com cobrança de ICMS por ST' },
  { value: '50', label: '50 · Suspensão' },
  { value: '51', label: '51 · Diferimento' },
  { value: '70', label: '70 · Com redução da BC e cobrança do ICMS por ST' },
  { value: '90', label: '90 · Outros' },
];

/**
 * CSOSN — Simples Nacional.
 *
 * Os três primeiros são os que o motor calcula, e o 102 é a resposta da
 * esmagadora maioria dos produtos de revenda.
 */
export const CSOSN_OPTIONS: SelectOption[] = [
  { value: '102', label: '102 · Venda normal — o imposto vai na guia do Simples' },
  { value: '101', label: '101 · Venda com crédito ao cliente — só se o contador pedir' },
  { value: '500', label: '500 · Imposto já pago antes (ST) — exige o código CEST' },
  { value: '103', label: '103 · Isenção do ICMS para faixa de receita bruta' },
  { value: '201', label: '201 · Tributada com permissão de crédito e cobrança do ICMS por ST' },
  { value: '202', label: '202 · Tributada sem permissão de crédito e cobrança do ICMS por ST' },
  { value: '203', label: '203 · Isenção para faixa de receita bruta e cobrança do ICMS por ST' },
  { value: '300', label: '300 · Imune' },
  { value: '400', label: '400 · Não tributada pelo Simples Nacional' },
  { value: '900', label: '900 · Outros' },
];

// Baseado na legislação em tramitação — atualizar quando SEFAZ publicar tabela definitiva
export const CST_IBS_CBS_OPTIONS: SelectOption[] = [
  { value: '00', label: '00 - Tributação integral' },
  { value: '10', label: '10 - Tributação com alíquota diferenciada' },
  { value: '20', label: '20 - Imunidade' },
  { value: '30', label: '30 - Isenção' },
  { value: '40', label: '40 - Não incidência' },
  { value: '50', label: '50 - Redução de alíquota' },
  { value: '60', label: '60 - Suspensão' },
  { value: '70', label: '70 - Diferimento' },
  { value: '90', label: '90 - Outros' },
];

/**
 * CST de PIS/COFINS.
 *
 * O `49` não estava nesta lista e é justamente o que o Simples Nacional usa:
 * os tributos vão na guia única, não na nota (ver
 * `tax_engine/constants.py:CST_PIS_COFINS_SIMPLES`). Sem ele, a empresa do
 * Simples não conseguia escolher na tela o valor que o sistema deriva.
 */
export const CST_PIS_COFINS_OPTIONS: SelectOption[] = [
  { value: '49', label: '49 · Outras operações de saída — o PIS/COFINS do Simples vai na guia' },
  { value: '01', label: '01 · Tributável (alíquota básica)' },
  { value: '02', label: '02 · Tributável (alíquota diferenciada)' },
  { value: '04', label: '04 · Tributável monofásica (alíquota zero)' },
  { value: '05', label: '05 · Tributável por ST' },
  { value: '06', label: '06 · Tributável (alíquota zero)' },
  { value: '07', label: '07 · Isenta' },
  { value: '08', label: '08 · Sem incidência' },
  { value: '09', label: '09 · Com suspensão' },
];

/**
 * Unidades de medida de produto — lista ÚNICA.
 *
 * Havia duas: uma no cadastro (com G, ML, CM, PC) e esta, da unidade
 * tributável (com M2 e PAR). Dava para escolher uma unidade comercial que não
 * existia na tributável, e a tributável nasce igual à comercial.
 */
export const UNIDADE_PRODUTO_OPTIONS: SelectOption[] = [
  { value: 'UN', label: 'UN - Unidade' },
  { value: 'PC', label: 'PC - Peça' },
  { value: 'CX', label: 'CX - Caixa' },
  { value: 'PCT', label: 'PCT - Pacote' },
  { value: 'PAR', label: 'PAR - Par' },
  { value: 'KG', label: 'KG - Quilograma' },
  { value: 'G', label: 'G - Grama' },
  { value: 'L', label: 'L - Litro' },
  { value: 'ML', label: 'ML - Mililitro' },
  { value: 'M', label: 'M - Metro' },
  { value: 'CM', label: 'CM - Centímetro' },
  { value: 'M2', label: 'M2 - Metro quadrado' },
];

export const UNIDADE_SERVICO_OPTIONS: SelectOption[] = [
  { value: 'SV', label: 'SV - Serviço' },
  { value: 'HR', label: 'HR - Hora' },
  { value: 'UN', label: 'UN - Unidade' },
];

/**
 * O "?" de cada campo fiscal, em português de loja.
 *
 * Uma frase e um exemplo. É o item mais barato do plano de cadastro
 * (`docs/cadastro-produto-plano.md`, D6d) e o que mais muda a sensação de
 * entender a tela: o lojista não deve precisar procurar o que é CSOSN.
 */
export const AJUDA_CAMPO_FISCAL: Record<string, string> = {
  ncm: 'Código de 8 dígitos que diz ao governo QUE mercadoria é esta. Sai na nota e define o imposto. Ex.: 9608.10.00 para caneta esferográfica. Na dúvida, confirme com seu contador ou com a nota de compra do fornecedor.',
  cfop: 'Diz o QUE a operação é: venda dentro do estado, venda para outro estado, devolução. Para venda comum dentro do estado, 5102.',
  unidade_tributavel: 'Como o produto é medido na nota. O normal é ser igual à unidade de venda — só muda quando você vende em caixa e tributa por unidade, por exemplo.',
  origem: 'De onde a mercadoria veio. "0 - Nacional" cobre quase tudo no varejo; importado só quando você mesmo importou ou comprou de importador.',
  cst_icms: 'Como o ICMS é tratado neste produto. O padrão de revenda é "tributado normalmente". Se o fornecedor já pagou o imposto por você (pneu, bebida, autopeça), é ST.',
  csosn: 'A mesma coisa que o CST, para quem é do Simples Nacional. Na maioria dos produtos é 102: o imposto vai na guia do Simples e não é destacado na nota.',
  cest: 'Código exigido apenas para produtos com substituição tributária (quando o imposto já foi pago antes). Se o produto não tem ST, deixe em branco.',
  gtin: 'O código de barras que vale para o fisco (EAN de 8, 13 ou 14 dígitos). Se o produto não tem código de barras de verdade, deixe em branco — inventar número faz a nota ser rejeitada.',
  aliquota_icms: 'O percentual de ICMS deste produto no seu estado. Ex.: 18. Em branco, o sistema usa o padrão da UF.',
  reducao_base_icms: 'Quanto da base de cálculo é reduzido, em percentual. Só existe com CST 20, e quem informa é o contador.',
  beneficio_fiscal: 'Código do benefício concedido pelo estado (cBenef). Obrigatório com CST 20 em SP, PR, RS, SC e GO.',
  cst_pis: 'Como o PIS é tratado. No Simples Nacional é 49: o tributo vai na guia única e não na nota.',
  cst_cofins: 'Como a COFINS é tratada. No Simples Nacional é 49, pelo mesmo motivo do PIS.',
  aliquota_pis: 'Percentual de PIS. Só aparece quando o CST é tributável. Ex.: 1.65.',
  aliquota_cofins: 'Percentual de COFINS. Só aparece quando o CST é tributável. Ex.: 7.60.',
  c_class_trib: 'Classificação tributária do IBS/CBS, a nova regra da Reforma Tributária. Ainda em transição — preencha só se o contador indicar.',
  cst_ibs_cbs: 'Situação tributária do item no IBS/CBS (Reforma Tributária). Preencha só se o contador indicar.',
  aliquota_ibs: 'Percentual de IBS. Faz parte da Reforma Tributária e ainda está em transição.',
  aliquota_cbs: 'Percentual de CBS. Faz parte da Reforma Tributária e ainda está em transição.',
  c_benef_ibs: 'Código de benefício fiscal do IBS/CBS, quando houver.',
};

/**
 * Formas de pagamento na nota fiscal — o campo `tPag` do layout da NF-e.
 *
 * O gate de emissão RECUSA a nota enquanto houver forma de pagamento ativa
 * sem código. Rótulo em português primeiro, código depois, pela mesma razão
 * do CSOSN: quem administra a loja não decora tabela da SEFAZ.
 *
 * Sobre o PIX: a NT 2023.004 separou 17 (dinâmico, QR gerado por cobrança) de
 * 20 (estático, QR fixo do estabelecimento). O padrão do sistema é 17, que é
 * o de uso geral; quem usa só o QR fixo na parede troca para 20.
 */
export const CODIGO_SEFAZ_PAGAMENTO_OPTIONS: SelectOption[] = [
  { value: '01', label: 'Dinheiro (01)' },
  { value: '02', label: 'Cheque (02)' },
  { value: '03', label: 'Cartão de Crédito (03)' },
  { value: '04', label: 'Cartão de Débito (04)' },
  { value: '05', label: 'Fiado / Crédito da Loja (05)' },
  { value: '15', label: 'Boleto Bancário (15)' },
  { value: '16', label: 'Depósito Bancário (16)' },
  { value: '17', label: 'PIX dinâmico — QR por cobrança (17)' },
  { value: '20', label: 'PIX estático — QR fixo da loja (20)' },
  { value: '18', label: 'Transferência / Carteira Digital (18)' },
  { value: '10', label: 'Vale Alimentação (10)' },
  { value: '11', label: 'Vale Refeição (11)' },
  { value: '12', label: 'Vale Presente (12)' },
  { value: '13', label: 'Vale Combustível (13)' },
  { value: '19', label: 'Programa de Fidelidade / Cashback (19)' },
  { value: '90', label: 'Sem pagamento (90)' },
  { value: '99', label: 'Outros (99)' },
];
