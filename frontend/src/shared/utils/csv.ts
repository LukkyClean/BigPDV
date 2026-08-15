import { isTauri } from '@tauri-apps/api/core';

/** Monta o conteúdo CSV (separador ";" + BOM UTF-8 — combo que o Excel PT-BR abre certo). */
function montarCsv(headers: string[], rows: (string | number)[][]): string {
  const esc = (v: string | number): string => {
    const s = String(v ?? '');
    return /[";\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const sep = ';';
  const linhas = [headers, ...rows].map((r) => r.map(esc).join(sep));
  return '﻿' + linhas.join('\r\n'); // BOM UTF-8
}

/** Download por blob — funciona no navegador (dev via localhost). */
function baixarNoNavegador(filename: string, conteudo: string): void {
  const blob = new Blob([conteudo], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 0);
}

/**
 * Gera um CSV e o entrega ao usuário.
 * - No app (Tauri/WebView, que bloqueia download por blob): grava na pasta de dados
 *   do app e abre no programa padrão (Excel) via plugin-opener.
 * - No navegador (dev): baixa via blob.
 */
export async function saveCsv(
  filename: string,
  headers: string[],
  rows: (string | number)[][],
): Promise<string | null> {
  const conteudo = montarCsv(headers, rows);

  if (isTauri()) {
    const { writeTextFile, BaseDirectory } = await import('@tauri-apps/plugin-fs');
    const { appLocalDataDir, join } = await import('@tauri-apps/api/path');
    await writeTextFile(filename, conteudo, { baseDir: BaseDirectory.AppLocalData });
    const caminho = await join(await appLocalDataDir(), filename);
    // Abrir no Excel é um bônus: se a permissão de abrir ainda não estiver ativa,
    // o arquivo já está salvo no caminho retornado (avisamos o usuário).
    try {
      const { openPath } = await import('@tauri-apps/plugin-opener');
      await openPath(caminho);
    } catch {
      /* sem permissão de abrir — arquivo permanece salvo */
    }
    return caminho;
  }

  baixarNoNavegador(filename, conteudo);
  return null;
}
