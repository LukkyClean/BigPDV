/**
 * @fileoverview Constantes dos segmentos de negócio
 * @description Define os segmentos disponíveis com seus ícones e descrições
 */

import type { SegmentOption } from '../types/sign-in.types';

/**
 * Lista de segmentos de negócio disponíveis
 * Cada segmento possui um ícone SVG inline para garantir consistência visual
 */
export const BUSINESS_SEGMENTS: SegmentOption[] = [
  {
    id: 'assistencia_tecnica',
    label: 'Assistência Técnica',
    icon: 'computer',
    description: 'Reparo de computadores, celulares e eletrônicos',
  },
  {
    id: 'oficina_mecanica',
    label: 'Oficina Mecânica',
    icon: 'wrench',
    description: 'Manutenção e reparo de veículos',
  },
  {
    id: 'serigrafia',
    label: 'Serigrafia',
    icon: 'shirt',
    description: 'Estamparia de camisas, sacolas e brindes',
  },
  {
    id: 'mercado',
    label: 'Mercado',
    icon: 'store',
    description: 'Supermercados, mercearias e vendas no varejo',
  },
  {
    id: 'marcenaria',
    label: 'Marcenaria',
    icon: 'hammer',
    description: 'Fabricação e reparo de móveis',
  },
  {
    id: 'eletricista',
    label: 'Eletricista',
    icon: 'bolt',
    description: 'Serviços de instalação e manutenção elétrica',
  },
  {
    id: 'outros',
    label: 'Outros',
    icon: 'grid',
    description: 'Outros tipos de negócio',
  },
];

/**
 * Mapeia o ID do segmento para suas informações
 */
export function getSegmentById(id: string): SegmentOption | undefined {
  return BUSINESS_SEGMENTS.find((segment) => segment.id === id);
}

/**
 * Dicas contextuais por segmento, exibidas em Dados da Loja e Resumo
 */
export const SEGMENT_TIPS: Record<string, string> = {
  assistencia_tecnica:
    'Para assistências técnicas, recomendamos configurar ordens de serviço após o cadastro.',
  oficina_mecanica:
    'Para oficinas mecânicas, você poderá cadastrar veículos e peças no módulo de OS.',
  serigrafia:
    'Para serigrafias, cadastre a pintura por número de cores em Serviços e os tipos de sacola em Produtos — a OS já multiplica pelo que o cliente pedir.',
  mercado:
    'Para mercados, o módulo de estoque e PDV estarão prontos para uso imediato.',
  marcenaria:
    'Para marcenarias, as ordens de serviço com orçamento detalhado serão seu principal recurso.',
  eletricista:
    'Para eletricistas, as ordens de serviço com checklist de materiais facilitarão seu dia a dia.',
  outros:
    'Você poderá personalizar os módulos do sistema conforme a necessidade do seu negócio.',
};

/**
 * Retorna a dica contextual para um segmento
 */
export function getSegmentTip(segmentId: string): string {
  return SEGMENT_TIPS[segmentId] || SEGMENT_TIPS['outros'];
}
