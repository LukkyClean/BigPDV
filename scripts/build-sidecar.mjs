#!/usr/bin/env node
/**
 * Gera o sidecar: o backend FastAPI empacotado num .exe que o instalador leva.
 *
 * Eram três passos manuais, não documentados em lugar nenhum — e por isso o
 * sidecar ficou 6 dias atrasado sem ninguém notar (16/07/2026). Agora é um
 * comando só, e o check-sidecar.mjs impede o build de publicar um desatualizado.
 *
 *   1. PyArmor  — ofusca app/ -> backend-fastapi/dist/  (run.py carrega daqui
 *                 quando APP_ENV=production)
 *   2. PyInstaller — empacota run.py + dist/ + alembic -> um .exe
 *   3. Copia     -> frontend/src-tauri/bin/erp-api-<target-triple>.exe
 *                 (o Tauri exige exatamente esse nome, com o triple da máquina)
 *
 * A saída do passo 2 vai para build/out/ de propósito: o run.spec empacota a
 * pasta `dist` inteira como dado, então deixar o .exe cair lá dentro faria a
 * próxima build embutir o .exe anterior dentro do novo.
 *
 * Uso: node scripts/build-sidecar.mjs
 */

import { existsSync, copyFileSync, mkdirSync, statSync, rmSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync, execSync } from 'node:child_process';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const BACKEND = join(RAIZ, 'backend-fastapi');
const PY = join(BACKEND, '.venv', 'Scripts', 'python.exe');
const PYARMOR = join(BACKEND, '.venv', 'Scripts', 'pyarmor.exe');
const SAIDA = join(BACKEND, 'build', 'out');
const BIN = join(RAIZ, 'frontend', 'src-tauri', 'bin');

function triple() {
  const saida = execSync('rustc -vV', { encoding: 'utf8' });
  const t = saida.match(/host:\s*(\S+)/)?.[1];
  if (!t) throw new Error('Não consegui descobrir o target triple do rustc.');
  return t;
}

function passo(n, texto) {
  console.log(`\n\x1b[36m[${n}/3]\x1b[0m ${texto}`);
}

function rodar(cmd, args, cwd) {
  execFileSync(cmd, args, { cwd, stdio: 'inherit' });
}

// --- Pré-checagens: falhar cedo e com motivo, não no meio do PyInstaller ---
if (!existsSync(PY)) {
  console.error(`\n✖ venv do backend não encontrada: ${PY}`);
  console.error('  Crie com: cd backend-fastapi && python -m venv .venv && .venv\\Scripts\\pip install -r requirements.txt\n');
  process.exit(1);
}
if (!existsSync(PYARMOR)) {
  console.error(`\n✖ pyarmor não encontrado: ${PYARMOR}`);
  console.error('  O sidecar roda o código ofuscado (run.py exige dist/ em produção).');
  console.error('  Instale com: backend-fastapi\\.venv\\Scripts\\pip install pyarmor\n');
  process.exit(1);
}

const ALVO = join(BIN, `erp-api-${triple()}.exe`);

passo(1, 'PyArmor — ofuscando app/ para dist/');
// -O dist: saída; -r: recursivo (o pacote app inteiro)
rodar(PYARMOR, ['gen', '-O', 'dist', '-r', 'app'], BACKEND);

passo(2, 'PyInstaller — empacotando o .exe');
rmSync(SAIDA, { recursive: true, force: true });
rodar(
  PY,
  ['-m', 'PyInstaller', 'run.spec', '--noconfirm', '--distpath', 'build/out', '--workpath', 'build/work'],
  BACKEND,
);

const gerado = join(SAIDA, 'run.exe');
if (!existsSync(gerado)) {
  console.error(`\n✖ O PyInstaller não produziu ${gerado}.`);
  console.error('  Confira o nome em run.spec (EXE(..., name=...)).\n');
  process.exit(1);
}

passo(3, `Copiando para ${ALVO.replace(RAIZ, '.')}`);
mkdirSync(BIN, { recursive: true });
copyFileSync(gerado, ALVO);

const mb = (statSync(ALVO).size / 1048576).toFixed(1);
console.log(`\n\x1b[32m✓ sidecar gerado\x1b[0m — ${mb} MB`);
console.log('  Confira com: node scripts/check-sidecar.mjs\n');
