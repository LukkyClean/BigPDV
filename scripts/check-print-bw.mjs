#!/usr/bin/env node
/**
 * Barra o build quando entra cor num template de impressão.
 *
 * Impressão é preto e branco por decisão de produto: cupom térmico não imprime
 * cor, e no A4 a cor gasta tinta colorida do cliente sem acrescentar informação
 * — em todos os casos que existiam, ela era redundante com um texto que já estava
 * lá ("Reparado" escrito por extenso, o sinal `-` do desconto, o título
 * "CANCELAMENTO"). Converter para a escala neutra não perdeu nada.
 *
 * A regra também protege a paleta configurável: quando o dono da loja puder
 * escolher a cor do sistema, os documentos impressos NÃO podem segui-la — um
 * recibo é documento, não vitrine.
 *
 * Sem esta guarda, um `text-emerald-600` reaparece na primeira vez que alguém
 * copiar um bloco da tela para dentro de um template de impressão.
 *
 * Uso: node scripts/check-print-bw.mjs
 */

import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(RAIZ, 'frontend', 'src');

/**
 * Um arquivo entra na regra se contém `print-container` — o marcador que o
 * print-a4.css e o print-cupom.css usam para isolar o que vai para o papel.
 * Componentes auxiliares (cabeçalho, rodapé, assinaturas) são incluídos porque
 * são montados dentro desse container.
 */
const MARCADORES = ['print-container', 'print:block'];

/** Famílias de cor do Tailwind. Neutros (slate/zinc/gray/neutral/stone) e as
 *  cores puras black/white seguem permitidos. */
const CORES = [
  'red', 'orange', 'amber', 'yellow', 'lime', 'green', 'emerald', 'teal',
  'cyan', 'sky', 'blue', 'indigo', 'violet', 'purple', 'fuchsia', 'pink', 'rose',
  'brand',
];
// `(?:-[a-z]+)*` cobre nomes compostos (brand-primary-light) sem engolir o hífen
// do tom numérico — senão a mensagem sairia truncada em "text-emerald-" e quem
// fosse procurar no código não acharia.
const REGEX_COR = new RegExp(
  `\\b(?:bg|text|border|ring|from|via|to|decoration|outline|divide|shadow)-(?:${CORES.join('|')})(?:-[a-z]+)*(?:-\\d{2,3})?(?:/\\d{1,3})?\\b`,
  'g',
);

/** Arquivos .vue sob `dir`, recursivo. */
function arquivosVue(dir, acc = []) {
  if (!existsSync(dir)) return acc;
  for (const entrada of readdirSync(dir, { withFileTypes: true })) {
    if (entrada.name.startsWith('.') || entrada.name === 'node_modules') continue;
    const caminho = join(dir, entrada.name);
    if (entrada.isDirectory()) arquivosVue(caminho, acc);
    else if (entrada.name.endsWith('.vue') && statSync(caminho).isFile()) acc.push(caminho);
  }
  return acc;
}

const ocorrencias = [];

for (const arquivo of arquivosVue(SRC)) {
  const conteudo = readFileSync(arquivo, 'utf8');
  if (!MARCADORES.some((m) => conteudo.includes(m))) continue;

  conteudo.split('\n').forEach((linha, i) => {
    for (const achado of linha.match(REGEX_COR) ?? []) {
      ocorrencias.push({ arquivo, linha: i + 1, achado: achado.trim() });
    }
  });
}

if (ocorrencias.length) {
  console.error('\n\x1b[31m✖ BUILD BARRADO — cor em template de impressão\x1b[0m\n');
  console.error('  Documento impresso é preto e branco. Use a escala neutra');
  console.error('  (slate/zinc) e distinga por peso, borda ou texto — não por cor.\n');
  for (const o of ocorrencias) {
    console.error(`  • ${relative(RAIZ, o.arquivo)}:${o.linha}  →  ${o.achado}`);
  }
  console.error('');
  process.exit(1);
}

console.log('✓ templates de impressão em preto e branco');
