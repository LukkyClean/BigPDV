import { isTauri } from '@tauri-apps/api/core';

/**
 * Entrega um arquivo binário ao usuário — mesma regra do `saveCsv`:
 * - No app (Tauri/WebView bloqueia download por blob): grava na pasta de dados
 *   do app e tenta abrir no programa padrão; devolve o caminho.
 * - No navegador (dev): download por blob; devolve null.
 */
export async function salvarArquivo(nome: string, conteudo: Blob): Promise<string | null> {
  if (isTauri()) {
    const { writeFile, BaseDirectory } = await import('@tauri-apps/plugin-fs');
    const { appLocalDataDir, join } = await import('@tauri-apps/api/path');
    const bytes = new Uint8Array(await conteudo.arrayBuffer());
    await writeFile(nome, bytes, { baseDir: BaseDirectory.AppLocalData });
    const caminho = await join(await appLocalDataDir(), nome);
    try {
      const { openPath } = await import('@tauri-apps/plugin-opener');
      await openPath(caminho);
    } catch {
      /* sem permissão de abrir — o arquivo já está salvo no caminho devolvido */
    }
    return caminho;
  }

  const url = URL.createObjectURL(conteudo);
  const a = document.createElement('a');
  a.href = url;
  a.download = nome;
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 0);
  return null;
}
