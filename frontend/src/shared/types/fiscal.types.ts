// ---------------------------------------------------------------------------
// ARQUIVO: shared/types/fiscal.types.ts
// DESCRIÇÃO: Types compartilhados para verificação de completude fiscal.
// ---------------------------------------------------------------------------

export interface PendenciaFiscal {
  categoria: 'emitente' | 'destinatario' | 'item' | 'pagamento';
  campo: string;
  mensagem: string;
  referencia_id?: number | null;
  referencia_nome?: string | null;
}

export interface ResultadoVerificacaoFiscal {
  completo: boolean;
  pendencias: PendenciaFiscal[];
}
