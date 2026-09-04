/**
 * @fileoverview Fonte ÚNICA dos segmentos de negócio no frontend.
 *
 * POR QUE ESTE ARQUIVO EXISTE. Serigrafia foi acrescentada em quatro lugares
 * diferentes e ainda assim o onboarding recusou o cadastro com
 * "Invalid enum value ... received 'serigrafia'": faltava a quinta lista, o
 * `z.enum` do schema do Zod. Ela era um `as const` solto, sem vínculo com o
 * tipo `BusinessSegment`, então o `vue-tsc` não tinha como cobrar.
 *
 * Agora a lista é uma só e tudo deriva dela: o tipo (`typeof SEGMENTOS[number]`),
 * o enum do Zod, os cards do onboarding e as dicas. Segmento novo entra aqui e
 * o compilador cobra o resto — os cards e as dicas são `Record<Segmento, ...>`,
 * então faltar um deixa de compilar em vez de falhar na cara do usuário.
 *
 * Espelha `SEGMENTOS_VALIDOS` em `app/schemas/auth.py`. Esse espelho o
 * TypeScript não alcança: ao acrescentar um segmento, mexa nos dois.
 */

export const SEGMENTOS = [
  'assistencia_tecnica',
  'oficina_mecanica',
  'serigrafia',
  // Era 'mercado'. Virou 'pdv' porque o produto é o mesmo para adega,
  // mercearia, papelaria e distribuidora — o nome do valor tem que dizer o que
  // ele é, não o ramo de um cliente. É também o único segmento sem Ordem de
  // Serviço. A migration b3c4d5e6f7a8 converte as empresas já gravadas.
  'pdv',
  'marcenaria',
  'eletricista',
  'outros',
] as const;

export type Segmento = (typeof SEGMENTOS)[number];
