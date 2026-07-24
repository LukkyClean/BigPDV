import api from '@/api/axios';
import { safeParseResponse } from '@/shared/utils/parse.utils';

import type { PeriodFilter } from '../types/dashboard.types';
import type {
  DashboardStatsData,
  OSVencendoResponseData,
  EstoqueBaixoResponseData,
  UltimasVendasResponseData,
  MeuResumoStatsData,
  MinhaFilaResponseData,
  OSAtrasadaResponseData,
  OSAguardandoRetiradaResponseData,
  AtividadeHojeResponseData,
  RankingFuncionariosResponseData,
  OSPorStatusResponseData,
  FormasPagamentoResponseData,
  OSAtrasadaEmpresaResponseData,
  TendenciaResponseData,
} from '../schemas/dashboard.schema';
import {
  DashboardStatsSchema,
  TendenciaResponseSchema,
  OSVencendoResponseSchema,
  EstoqueBaixoResponseSchema,
  UltimasVendasResponseSchema,
  MeuResumoStatsSchema,
  MinhaFilaResponseSchema,
  OSAtrasadaResponseSchema,
  OSAguardandoRetiradaResponseSchema,
  AtividadeHojeResponseSchema,
  RankingFuncionariosResponseSchema,
  OSPorStatusResponseSchema,
  FormasPagamentoResponseSchema,
  OSAtrasadaEmpresaResponseSchema,
} from '../schemas/dashboard.schema';

const DASHBOARD_URL = '/dashboard';

export const dashboardService = {
  async getStats(periodo: PeriodFilter): Promise<DashboardStatsData> {
    const { data } = await api.get<DashboardStatsData>(`${DASHBOARD_URL}/stats`, {
      params: { periodo },
    });
    return safeParseResponse(DashboardStatsSchema, data, 'dashboardService.getStats');
  },

  async getOSVencendo(): Promise<OSVencendoResponseData> {
    const { data } = await api.get<OSVencendoResponseData>(`${DASHBOARD_URL}/os-vencendo`);
    return safeParseResponse(OSVencendoResponseSchema, data, 'dashboardService.getOSVencendo');
  },

  async getEstoqueBaixo(): Promise<EstoqueBaixoResponseData> {
    const { data } = await api.get<EstoqueBaixoResponseData>(`${DASHBOARD_URL}/estoque-baixo`);
    return safeParseResponse(
      EstoqueBaixoResponseSchema,
      data,
      'dashboardService.getEstoqueBaixo',
    );
  },

  async getUltimasVendas(): Promise<UltimasVendasResponseData> {
    const { data } = await api.get<UltimasVendasResponseData>(`${DASHBOARD_URL}/ultimas-vendas`);
    return safeParseResponse(
      UltimasVendasResponseSchema,
      data,
      'dashboardService.getUltimasVendas',
    );
  },

  async getMeuResumo(periodo: PeriodFilter): Promise<MeuResumoStatsData> {
    const { data } = await api.get<MeuResumoStatsData>(`${DASHBOARD_URL}/meu-resumo`, {
      params: { periodo },
    });
    return safeParseResponse(MeuResumoStatsSchema, data, 'dashboardService.getMeuResumo');
  },

  async getTendencia(periodo: PeriodFilter): Promise<TendenciaResponseData> {
    const { data } = await api.get<TendenciaResponseData>(`${DASHBOARD_URL}/tendencia`, {
      params: { periodo },
    });
    return safeParseResponse(TendenciaResponseSchema, data, 'dashboardService.getTendencia');
  },

  async getMinhaTendencia(periodo: PeriodFilter): Promise<TendenciaResponseData> {
    const { data } = await api.get<TendenciaResponseData>(`${DASHBOARD_URL}/minha-tendencia`, {
      params: { periodo },
    });
    return safeParseResponse(TendenciaResponseSchema, data, 'dashboardService.getMinhaTendencia');
  },

  async getMinhasOSVencendo(): Promise<OSVencendoResponseData> {
    const { data } = await api.get<OSVencendoResponseData>(`${DASHBOARD_URL}/minhas-os-vencendo`);
    return safeParseResponse(OSVencendoResponseSchema, data, 'dashboardService.getMinhasOSVencendo');
  },

  async getMinhasUltimasVendas(): Promise<UltimasVendasResponseData> {
    const { data } = await api.get<UltimasVendasResponseData>(`${DASHBOARD_URL}/minhas-ultimas-vendas`);
    return safeParseResponse(UltimasVendasResponseSchema, data, 'dashboardService.getMinhasUltimasVendas');
  },

  async getMinhaFila(): Promise<MinhaFilaResponseData> {
    const { data } = await api.get<MinhaFilaResponseData>(`${DASHBOARD_URL}/minha-fila`);
    return safeParseResponse(MinhaFilaResponseSchema, data, 'dashboardService.getMinhaFila');
  },

  async getMinhasOSAtrasadas(): Promise<OSAtrasadaResponseData> {
    const { data } = await api.get<OSAtrasadaResponseData>(`${DASHBOARD_URL}/minhas-os-atrasadas`);
    return safeParseResponse(OSAtrasadaResponseSchema, data, 'dashboardService.getMinhasOSAtrasadas');
  },

  async getOSAguardandoRetirada(): Promise<OSAguardandoRetiradaResponseData> {
    const { data } = await api.get<OSAguardandoRetiradaResponseData>(`${DASHBOARD_URL}/os-aguardando-retirada`);
    return safeParseResponse(OSAguardandoRetiradaResponseSchema, data, 'dashboardService.getOSAguardandoRetirada');
  },

  async getMinhaAtividadeHoje(): Promise<AtividadeHojeResponseData> {
    const { data } = await api.get<AtividadeHojeResponseData>(`${DASHBOARD_URL}/minha-atividade-hoje`);
    return safeParseResponse(AtividadeHojeResponseSchema, data, 'dashboardService.getMinhaAtividadeHoje');
  },

  async getRankingFuncionarios(periodo: PeriodFilter): Promise<RankingFuncionariosResponseData> {
    const { data } = await api.get<RankingFuncionariosResponseData>(`${DASHBOARD_URL}/ranking-funcionarios`, {
      params: { periodo },
    });
    return safeParseResponse(RankingFuncionariosResponseSchema, data, 'dashboardService.getRankingFuncionarios');
  },

  async getOSPorStatus(): Promise<OSPorStatusResponseData> {
    const { data } = await api.get<OSPorStatusResponseData>(`${DASHBOARD_URL}/os-por-status`);
    return safeParseResponse(OSPorStatusResponseSchema, data, 'dashboardService.getOSPorStatus');
  },

  async getFormasPagamento(periodo: PeriodFilter): Promise<FormasPagamentoResponseData> {
    const { data } = await api.get<FormasPagamentoResponseData>(`${DASHBOARD_URL}/formas-pagamento`, {
      params: { periodo },
    });
    return safeParseResponse(FormasPagamentoResponseSchema, data, 'dashboardService.getFormasPagamento');
  },

  async getOSAtrasadasEmpresa(): Promise<OSAtrasadaEmpresaResponseData> {
    const { data } = await api.get<OSAtrasadaEmpresaResponseData>(`${DASHBOARD_URL}/os-atrasadas-empresa`);
    return safeParseResponse(OSAtrasadaEmpresaResponseSchema, data, 'dashboardService.getOSAtrasadasEmpresa');
  },
};
