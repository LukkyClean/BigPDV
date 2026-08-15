#!/usr/bin/env node
/**
 * Varre o espectro de cores e barra o build se alguma paleta gerada for ilegível.
 *
 * O dono da loja escolhe a cor num seletor livre. Vermelho puro com texto branco
 * dá 4,0:1 e REPROVA na WCAG — é aquele botão que parece difícil de ler sem que
 * ninguém saiba dizer por quê. Rosa claro com texto branco dá ~1,6:1, invisível.
 * `derivarPaleta` existe para impedir isso corrigindo a luminosidade; este script
 * existe para provar que ela impede, em vez de a gente confiar que impede.
 *
 * Legibilidade aqui é conta fechada (razão de contraste), não gosto — então dá
 * para testar exaustivamente: 360 matizes × várias saturações × várias
 * luminosidades, mais os casos que o usuário citou como medo (vermelho, preto,
 * rosa) e os extremos.
 *
 * Não instala nada: usa o esbuild que já vem com o Vite para transpilar o módulo
 * TypeScript, no mesmo padrão dos outros `check:*`.
 *
 * Uso: node scripts/check-paleta.mjs
 */

import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const FONTE = join(RAIZ, 'frontend', 'src', 'shared', 'theme', 'paleta.ts');

// --- Transpila o módulo TS para poder importar aqui ---------------------------
const { build } = await import(
  pathToFileURL(join(RAIZ, 'frontend', 'node_modules', 'esbuild', 'lib', 'main.js')).href
);

const tmp = mkdtempSync(join(tmpdir(), 'paleta-'));
const saida = join(tmp, 'paleta.mjs');

try {
  await build({
    entryPoints: [FONTE],
    outfile: saida,
    format: 'esm',
    platform: 'node',
    bundle: true,
    logLevel: 'silent',
  });

  const {
    derivarPaleta, hexParaRgb, contraste, rgbParaOklch,
    CONTRASTE_MINIMO_TEXTO, CONTRASTE_MINIMO_UI, COR_PADRAO,
  } = await import(pathToFileURL(saida).href);

  const BRANCO = { r: 1, g: 1, b: 1 };
  const falhas = [];
  let testadas = 0;

  /** Toda paleta tem de satisfazer estas invariantes, venha de que cor vier. */
  function verificar(semente, origem) {
    testadas++;
    const p = derivarPaleta(semente);
    const primaria = hexParaRgb(p['brand-primary']);
    const clara = hexParaRgb(p['brand-primary-light']);
    const secundaria = hexParaRgb(p['brand-secondary']);

    if (!primaria || !clara || !secundaria) {
      falhas.push(`${origem} ${semente}: paleta com hex inválido`);
      return;
    }

    const registrar = (regra, valor, minimo) => {
      if (valor + 1e-9 < minimo) {
        falhas.push(
          `${origem} ${semente} → ${regra}: ${valor.toFixed(2)}:1 (mínimo ${minimo}:1)` +
            `  [primary ${p['brand-primary']}, light ${p['brand-primary-light']}, secondary ${p['brand-secondary']}]`,
        );
      }
    };

    // 1. Texto branco sobre o botão primário.
    registrar('texto branco sobre primária', contraste(primaria, BRANCO), CONTRASTE_MINIMO_TEXTO);
    // 2. A primária usada como texto/link sobre o fundo branco do sistema.
    registrar('primária como texto sobre branco', contraste(primaria, BRANCO), CONTRASTE_MINIMO_TEXTO);
    // 3. Primária como texto/ícone dentro da caixa clara.
    registrar('primária sobre tom claro', contraste(clara, primaria), CONTRASTE_MINIMO_TEXTO);
    // 4. Secundária como elemento de interface sobre branco.
    registrar('secundária sobre branco', contraste(secundaria, BRANCO), CONTRASTE_MINIMO_UI);

    // 5. Hover do botão: o texto branco continua legível ao passar o mouse.
    const hover = hexParaRgb(p['brand-primary-hover']);
    if (!hover) {
      falhas.push(`${origem} ${semente}: hover com hex inválido`);
    } else {
      registrar('texto branco sobre hover', contraste(hover, BRANCO), CONTRASTE_MINIMO_TEXTO);

      // E o hover precisa ser PERCEPTÍVEL: se sair igual à primária, o botão não
      // reage ao mouse e parece travado.
      if (contraste(hover, primaria) < 1.12) {
        falhas.push(
          `${origem} ${semente} → hover quase idêntico à primária ` +
            `(${p['brand-primary']} vs ${p['brand-primary-hover']})`,
        );
      }
    }

    // 6. O tom claro tem de ser realmente claro: é fundo de caixa sobre a tela
    //    branca, e se escurecer demais o texto escuro do sistema some nele.
    const lClara = rgbParaOklch(clara).l;
    if (lClara < 0.85) {
      falhas.push(`${origem} ${semente} → tom claro escuro demais (L=${lClara.toFixed(2)}, mínimo 0.85)`);
    }
  }

  // --- Roda de cores completa -------------------------------------------------
  for (let h = 0; h < 360; h += 1) {
    for (const s of [0.15, 0.35, 0.6, 0.85, 1]) {
      for (const v of [0.2, 0.45, 0.7, 0.95]) {
        verificar(hslParaHex(h, s, v), 'roda');
      }
    }
  }

  // --- Os medos declarados e os extremos --------------------------------------
  const NOMEADAS = {
    'vermelho puro': '#ff0000',
    'preto': '#000000',
    'branco': '#ffffff',
    'rosa claro': '#ffc0cb',
    'rosa choque': '#ff1493',
    'amarelo': '#ffff00',
    'verde limão': '#ccff00',
    'ciano': '#00ffff',
    'cinza médio': '#808080',
    'azul padrão': COR_PADRAO,
  };
  for (const [nome, hex] of Object.entries(NOMEADAS)) verificar(hex, nome);

  // --- Entrada inválida não pode derrubar nada --------------------------------
  for (const lixo of ['', '#', 'nao-e-cor', '#12', '#zzzzzz', 'rgb(1,2,3)']) {
    const p = derivarPaleta(lixo);
    if (!hexParaRgb(p['brand-primary'])) {
      falhas.push(`entrada inválida ${JSON.stringify(lixo)} não caiu no padrão`);
    }
    testadas++;
  }

  if (falhas.length) {
    console.error('\n\x1b[31m✖ BUILD BARRADO — paleta gera combinação ilegível\x1b[0m\n');
    for (const f of falhas.slice(0, 20)) console.error(`  • ${f}`);
    if (falhas.length > 20) console.error(`  … e mais ${falhas.length - 20} falha(s)`);
    console.error(`\n  ${falhas.length} de ${testadas} cores testadas falharam.`);
    console.error('  Ajuste os limites em shared/theme/paleta.ts.\n');
    process.exit(1);
  }

  console.log(`✓ paleta legível em ${testadas} cores testadas (roda completa + extremos)`);
} finally {
  rmSync(tmp, { recursive: true, force: true });
}

/** HSL simples só para gerar sementes variadas — a conversão de verdade é OKLCH. */
function hslParaHex(h, s, l) {
  const a = s * Math.min(l, 1 - l);
  const f = (n) => {
    const k = (n + h / 30) % 12;
    const cor = l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1));
    return Math.round(255 * cor).toString(16).padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}
