/**
 * @fileoverview Plano contratado e recursos habilitados.
 *
 * POR AGORA é LOCAL e fixo no plano Start (a v1 é NÃO-fiscal). Quando o módulo
 * fiscal chegar, este arquivo é o único ponto a trocar: passar a ler o plano/
 * recursos da licença/contrato (ex.: GET /licenca/status) em vez da constante.
 *
 * Regra: nada de fiscal/NF-e aparece enquanto `recursoDisponivel('nfe')` for false.
 */

export type Plano = 'START'; // futuros: 'PRO', 'FISCAL', ...

/** Plano atual do cliente. Único ponto a mudar quando houver upgrade real. */
export const PLANO_ATUAL: Plano = 'START';

type Recursos = {
  /** Emissão de notas fiscais (NF-e/NFC-e/NFS-e) e configurações fiscais. */
  nfe: boolean;
};

const RECURSOS_POR_PLANO: Record<Plano, Recursos> = {
  START: { nfe: false },
};

export type Recurso = keyof Recursos;

/** True se o recurso está incluído no plano atual. */
export function recursoDisponivel(recurso: Recurso): boolean {
  return RECURSOS_POR_PLANO[PLANO_ATUAL]?.[recurso] ?? false;
}
