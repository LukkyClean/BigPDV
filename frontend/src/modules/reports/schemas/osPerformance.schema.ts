import { z } from 'zod';

export const OSReparoResumoSchema = z.object({
  reparado: z.number(),
  sem_reparo: z.number(),
  condenado: z.number(),
  nao_informado: z.number(),
  taxa_reparo_pct: z.number(),
});

export const OSStatusItemSchema = z.object({
  status: z.string(),
  quantidade: z.number(),
});

export const OSTecnicoItemSchema = z.object({
  funcionario_id: z.number(),
  nome: z.string(),
  finalizadas: z.number(),
  tempo_medio_horas: z.number().nullable(),
  faturamento: z.number(),
});

export const RelatorioOSPerformanceSchema = z.object({
  inicio: z.string(),
  fim: z.string(),
  abertas: z.number(),
  finalizadas: z.number(),
  tempo_medio_horas: z.number().nullable(),
  faturamento_total: z.number(),
  reparo: OSReparoResumoSchema,
  por_status: z.array(OSStatusItemSchema),
  por_tecnico: z.array(OSTecnicoItemSchema),
});

export type RelatorioOSPerformance = z.infer<typeof RelatorioOSPerformanceSchema>;
export type OSTecnicoItem = z.infer<typeof OSTecnicoItemSchema>;
export type OSStatusItem = z.infer<typeof OSStatusItemSchema>;
