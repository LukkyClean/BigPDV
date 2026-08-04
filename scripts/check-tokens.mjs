#!/usr/bin/env node
/**
 * Barra o build quando um token de marca é usado sem estar definido.
 *
 * O Tailwind v4 gera a utility `bg-brand-x` a partir da variável
 * `--color-brand-x` declarada no `@theme`. Se a variável não existe, a classe
 * NÃO é gerada — e o navegador ignora silenciosamente. O elemento continua na
 * tela, só que sem o fundo/borda que deveria ter.
 *
 * Foi o que aconteceu com `brand-primary-light`: usado em 46 lugares (cadastro
 * de empresa, fornecedores, OS, vendas, fiscal) e nunca declarado. Ninguém
 * percebeu porque nada quebra — apenas some.
 *
 * Esta guarda existe porque o erro é invisível em revisão de código: o `.vue`
 * parece correto, e o problema só aparece comparando com o `global.css`.
 *
 * Uso: node scripts/check-tokens.mjs
 */

import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(RAIZ, 'frontend', 'src');
const GLOBAL_CSS = join(SRC, 'shared', 'assets', 'styles', 'global.css');

/** Prefixos de utility que consomem uma cor do tema. */
const UTILITIES = [
  'bg', 'text', 'border', 'ring', 'shadow', 'from', 'via', 'to',
  'divide', 'outline', 'decoration', 'accent', 'caret', 'fill', 'stroke',
];

/**
 * `bg-brand-primary-light/20` → captura "brand-primary-light" (ignora a opacidade).
 *
 * Guloso de propósito. Com `+?` o casamento parava no primeiro segmento:
 * `bg-brand-off-white` virava "brand-off" (falso positivo) e
 * `bg-brand-primary-light` virava "brand-primary" — que existe, então a guarda
 * deixava passar exatamente o bug que ela foi escrita para pegar.
 */
const REGEX_USO = new RegExp(`\\b(?:${UTILITIES.join('|')})-(brand-[a-z0-9-]+)(?:/\\d{1,3})?\\b`, 'g');

if (!existsSync(GLOBAL_CSS)) {
  console.error(`✖ global.css não encontrado em ${relative(RAIZ, GLOBAL_CSS)}`);
  process.exit(1);
}

// Tokens declarados: --color-brand-primary: ... → "brand-primary"
const css = readFileSync(GLOBAL_CSS, 'utf8');
const declarados = new Set(
  [...css.matchAll(/--color-(brand-[a-z0-9-]+)\s*:/g)].map((m) => m[1]),
);

function arquivosFonte(dir, acc = []) {
  if (!existsSync(dir)) return acc;
  for (const entrada of readdirSync(dir, { withFileTypes: true })) {
    if (entrada.name.startsWith('.') || entrada.name === 'node_modules') continue;
    const caminho = join(dir, entrada.name);
    if (entrada.isDirectory()) arquivosFonte(caminho, acc);
    else if (/\.(vue|ts|tsx)$/.test(entrada.name) && statSync(caminho).isFile()) acc.push(caminho);
  }
  return acc;
}

/** token → [{arquivo, linha}] */
const usosIndefinidos = new Map();

for (const arquivo of arquivosFonte(SRC)) {
  readFileSync(arquivo, 'utf8').split('\n').forEach((linha, i) => {
    for (const [, token] of linha.matchAll(REGEX_USO)) {
      if (declarados.has(token)) continue;
      if (!usosIndefinidos.has(token)) usosIndefinidos.set(token, []);
      usosIndefinidos.get(token).push({ arquivo, linha: i + 1 });
    }
  });
}

if (usosIndefinidos.size) {
  console.error('\n\x1b[31m✖ BUILD BARRADO — token de marca usado sem estar definido\x1b[0m\n');
  console.error('  A classe não é gerada e o estilo some sem erro nenhum.');
  console.error(`  Declare a variável em ${relative(RAIZ, GLOBAL_CSS)} → @theme\n`);

  for (const [token, usos] of [...usosIndefinidos].sort()) {
    console.error(`  • \x1b[33m${token}\x1b[0m — ${usos.length} uso(s), falta \x1b[36m--color-${token}\x1b[0m`);
    for (const u of usos.slice(0, 3)) {
      console.error(`      ${relative(RAIZ, u.arquivo)}:${u.linha}`);
    }
    if (usos.length > 3) console.error(`      … e mais ${usos.length - 3}`);
  }
  console.error('');
  process.exit(1);
}

console.log(`✓ tokens de marca definidos (${declarados.size} declarados)`);
