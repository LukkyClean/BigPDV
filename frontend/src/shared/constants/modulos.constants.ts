/**
 * @fileoverview Identificadores dos módulos contratáveis.
 *
 * São as chaves técnicas que a plataforma emite dentro do JWT assinado da
 * licença, e que `modulos.store` compara. Ficam centralizadas aqui porque cada
 * uma é usada em dois lugares distantes — a declaração do menu e o `meta` da
 * rota — e um erro de digitação entre os dois não falha: o item aparece e a
 * rota barra, ou o contrário, sem erro nenhum no console.
 *
 * ⚠️ ESTES VALORES SÃO IMUTÁVEIS depois que a plataforma emitir o primeiro
 * token com eles. O JWT vive 7 dias, então renomear um identificador tira o
 * recurso de todo cliente em campo até o último token expirar. Mudar de ideia
 * sobre o recorte comercial é barato ENQUANTO nenhum token os carrega.
 */

export const MODULOS = {
  /**
   * Gestão financeira básica: contas a pagar, contas a receber, plano de contas
   * e o resultado do mês. Concedido a todos os planos hoje.
   *
   * Travado mesmo assim, e não por excesso de zelo: conceder o módulo a mais um
   * plano é um clique na licença, enquanto tirar a trava do código exige
   * sidecar novo, instalador novo e ir até a loja.
   */
  FINANCEIRO: 'FINANCEIRO',

  /** Fluxo de caixa projetado e conciliação. Só no plano superior. */
  FINANCEIRO_PRO: 'FINANCEIRO_PRO',

  /**
   * Centro Fiscal: emissão de NF-e, dados fiscais de produto e serviço,
   * certificado digital e inutilização de numeração.
   *
   * Ao contrário dos demais, NEGA por padrão: licença sem resposta ou com
   * lista vazia NÃO libera. Ver `MODULOS_NEGADOS_SEM_RESPOSTA` em
   * `shared/stores/modulos.store.ts` e o gêmeo em `app/core/modulos.py`.
   *
   * A string precisa bater com a que o backend usa em
   * `requer_modulo("NFE")` e com a que a plataforma emite no JWT.
   */
  NFE: 'NFE',

  /**
   * Cupom fiscal eletrônico (NFC-e, modelo 65).
   *
   * SEPARADO do NFE, e não por capricho: a plataforma tem família de rotas
   * (`/erp/fiscal/nfce/...`), cota e concessão próprias para o modelo 65. Uma
   * loja pode ter NF-e e não ter cupom, e o contrário também.
   *
   * Também NEGA por padrão. Ver `MODULOS_NEGADOS_SEM_RESPOSTA`.
   */
  NFCE: 'NFCE',
} as const;

export type Modulo = (typeof MODULOS)[keyof typeof MODULOS];
