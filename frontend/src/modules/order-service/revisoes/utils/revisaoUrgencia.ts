import type { RevisaoPendente } from '../services/revisao.service';
import { parseDataPura } from '@/shared/utils/date.utils';

/**
 * Urgência de uma revisão vencida.
 *
 * Vive fora do componente porque a mesma frase aparece em dois lugares — a aba
 * Revisões e o aviso do sino. Duas cópias divergiriam na primeira alteração, e
 * o usuário leria dois números diferentes para o mesmo veículo.
 */

/** Dias desde que a data-alvo passou. `proxima_revisao_data` é data pura. */
export function diasVencido(r: RevisaoPendente): number {
  if (!r.proxima_revisao_data) return 0;
  const alvo = parseDataPura(r.proxima_revisao_data);
  const hoje = new Date();
  return Math.max(0, Math.floor((hoje.getTime() - alvo.getTime()) / 86_400_000));
}

/** Quanto o hodômetro passou do alvo. */
export function kmExcedente(r: RevisaoPendente): number {
  if (r.km_atual == null || r.proxima_revisao_km == null) return 0;
  return Math.max(0, r.km_atual - r.proxima_revisao_km);
}

/** "Vencida há 12 dias" ou "15.000 km acima do alvo". */
export function urgenciaTexto(r: RevisaoPendente): string {
  if (r.motivo === 'data') {
    const d = diasVencido(r);
    return d <= 0 ? 'Vence hoje' : `Vencida há ${d} ${d === 1 ? 'dia' : 'dias'}`;
  }
  const km = kmExcedente(r);
  return km > 0 ? `${km.toLocaleString('pt-BR')} km acima do alvo` : 'Atingiu o KM alvo';
}
