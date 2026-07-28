#!/usr/bin/env node
/**
 * Barra o build quando o sidecar está mais velho que o backend.
 *
 * O instalador empacota o backend como um .exe (o "sidecar"). Ele NÃO é gerado
 * pelo `tauri build` — é um binário solto em frontend/src-tauri/bin/, feito à
 * mão. Nada comparava as datas, então dava para publicar um instalador com o
 * frontend novo e o backend velho, calado. Aconteceu: em 16/07/2026 o sidecar
 * estava 6 dias atrasado e teria quebrado a oficina (o contrato sem
 * `capacidades` derruba Vistoria, Revisões, aprovação e garantia).
 *
 * Este script roda antes do build e falha alto quando isso acontece.
 * Uso: node scripts/check-sidecar.mjs
 */

import { existsSync, statSync, readdirSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const BACKEND = join(RAIZ, 'backend-fastapi');
const OFUSCADO = join(BACKEND, 'dist');

/** Alvo do Rust nesta máquina — o Tauri exige o sufixo no nome do sidecar. */
function targetTriple() {
  try {
    const saida = execSync('rustc -vV', { encoding: 'utf8' });
    return saida.match(/host:\s*(\S+)/)?.[1] ?? 'x86_64-pc-windows-msvc';
  } catch {
    return 'x86_64-pc-windows-msvc';
  }
}

const SIDECAR = join(RAIZ, 'frontend', 'src-tauri', 'bin', `erp-api-${targetTriple()}.exe`);

/** Arquivo mais recente sob `dir` (recursivo), ignorando caches e o próprio build. */
function maisRecente(dir, ignorar = []) {
  let top = { arquivo: null, mtime: 0 };
  if (!existsSync(dir)) return top;
  for (const entrada of readdirSync(dir, { withFileTypes: true })) {
    if (entrada.name.startsWith('.') || ignorar.includes(entrada.name)) continue;
    const caminho = join(dir, entrada.name);
    if (entrada.isDirectory()) {
      if (['__pycache__', 'node_modules', 'dist', 'build', '.venv'].includes(entrada.name)) continue;
      const sub = maisRecente(caminho, ignorar);
      if (sub.mtime > top.mtime) top = sub;
    } else {
      const m = statSync(caminho).mtimeMs;
      if (m > top.mtime) top = { arquivo: caminho, mtime: m };
    }
  }
  return top;
}

const data = (ms) => new Date(ms).toLocaleString('pt-BR');
const erros = [];

// 1. O sidecar existe?
if (!existsSync(SIDECAR)) {
  erros.push(
    `Sidecar não encontrado: ${relative(RAIZ, SIDECAR)}\n` +
      `   O instalador sai sem backend. Ele não está versionado no git — cada máquina precisa gerar o seu.`,
  );
} else {
  const mSidecar = statSync(SIDECAR).mtimeMs;

  // 2. O código-fonte do backend é mais novo que o sidecar?
  const fonte = maisRecente(join(BACKEND, 'app'));
  if (fonte.arquivo && fonte.mtime > mSidecar) {
    erros.push(
      `Sidecar DESATUALIZADO — o instalador levaria o backend velho.\n` +
        `   sidecar : ${data(mSidecar)}\n` +
        `   backend : ${data(fonte.mtime)}  (${relative(RAIZ, fonte.arquivo)})`,
    );
  }

  // 3. O código ofuscado (entrada do PyInstaller) é mais novo que o sidecar?
  //    Sem isto, regerar só o .exe reempacota código antigo e o bug persiste.
  if (existsSync(OFUSCADO)) {
    const ofuscado = maisRecente(OFUSCADO);
    if (ofuscado.arquivo && ofuscado.mtime > mSidecar) {
      erros.push(
        `O código ofuscado é mais novo que o sidecar — falta reempacotar.\n` +
          `   sidecar  : ${data(mSidecar)}\n` +
          `   dist/    : ${data(ofuscado.mtime)}`,
      );
    }
  }
}

if (erros.length) {
  console.error('\n\x1b[31m✖ BUILD BARRADO — sidecar inconsistente\x1b[0m\n');
  for (const e of erros) console.error(`  • ${e}\n`);
  console.error('  Para resolver:\x1b[36m npm run build:sidecar \x1b[0m(na pasta frontend/)\n');
  console.error('  Detalhes em CLAUDE.md → "Sidecar (backend empacotado)".\n');
  process.exit(1);
}

console.log('✓ sidecar em dia com o backend');
