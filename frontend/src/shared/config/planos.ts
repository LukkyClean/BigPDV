/**
 * @fileoverview Recursos habilitados para esta licença.
 *
 * ANTES era uma tabela fixa no código (`START: { nfe: false }`), e o próprio
 * arquivo dizia que seria o único ponto a trocar quando o módulo fiscal
 * chegasse. Chegou: agora a resposta vem da LICENÇA, pela lista de módulos que
 * a plataforma assina dentro do JWT.
 *
 * O que isso muda na prática: liberar a NF-e para uma loja passou a ser um
 * clique no app da web — por plano ou por cliente — em vez de sidecar novo,
 * instalador novo e uma viagem até a loja.
 *
 * A assinatura de `recursoDisponivel` foi mantida de propósito: os cinco
 * lugares que perguntam "tem NF-e?" (formulário de produto, de serviço, de
 * empresa, o layout do Centro Fiscal e a sidebar) continuam iguais, sem saber
 * de onde veio a resposta.
 *
 * LEITURA ÚNICA, e isso é seguro: o `router.beforeEach` preenche a store de
 * módulos ANTES do primeiro render (ver `router/index.ts`), então quem lê no
 * setup já encontra a lista. A sidebar, que lê dentro de um `computed`, ainda
 * reage sozinha se a licença mudar no meio da sessão.
 */

import { MODULOS } from '@/shared/constants/modulos.constants';
import { useModulosStore } from '@/shared/stores/modulos.store';

type Recursos = {
  /** Emissão de notas fiscais (NF-e/NFC-e/NFS-e) e configurações fiscais. */
  nfe: boolean;
};

export type Recurso = keyof Recursos;

/** Qual módulo da licença responde por cada recurso. */
const MODULO_DO_RECURSO: Record<Recurso, string> = {
  nfe: MODULOS.NFE,
};

/**
 * True se o recurso está liberado para esta licença.
 *
 * Para a NF-e, licença sem resposta ou com lista vazia responde FALSE — a
 * exceção mora em `modulos.store.ts`, junto do porquê.
 *
 * Precisa ser chamada dentro de um `setup()` ou de um `computed`, porque
 * consulta uma store do Pinia.
 */
export function recursoDisponivel(recurso: Recurso): boolean {
  return useModulosStore().temModulo(MODULO_DO_RECURSO[recurso]);
}
