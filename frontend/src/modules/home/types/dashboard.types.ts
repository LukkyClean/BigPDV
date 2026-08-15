import type { Component } from 'vue';

export interface QuickActionItem {
  id: string;
  icon: Component;
  label: string;
  variant: 'primary' | 'secondary';
  action: () => void;
}

export interface StatCardData {
  id: string;
  icon: Component;
  label: string;
  value: string;
  change: string;
  isPositive: boolean;
  // Sem movimento no periodo: mostra um rotulo amigavel no lugar da variacao.
  isEmpty: boolean;
  emptyLabel: string;
}

export type PeriodFilter = 'hoje' | 'semana' | 'mes';
