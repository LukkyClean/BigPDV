#!/usr/bin/env node
/**
 * Trava o Modo Balcão dentro das fronteiras dele, e barra o build quando ele
 * vaza.
 *
 * POR QUE ESTE ARQUIVO EXISTE. O Modo Balcão é uma chave por MÁQUINA que acelera
 * o fluxo de venda de balcão. Ele só pode existir porque, DESLIGADO, o módulo de
 * vendas se comporta exatamente como sempre se comportou — é essa inércia que
 * permite ligá-lo numa adega sem tocar nas lojas de assistência, oficina e
 * serigrafia que já rodam em produção.
 *
 * Essa inércia não é uma propriedade do código: é uma disciplina. Cada novo
 * `if (modoBalcao)` que alguém escrever em outro arquivo é um lugar a mais onde
 * "desligado" pode deixar de significar "como era antes" — e a regressão não
 * aparece aqui, aparece na loja, custando sidecar, instalador e uma viagem.
 *
 * O QUE ESTE GUARD FAZ: confere que só os arquivos declarados abaixo conhecem a
 * chave. Ele NÃO testa comportamento — não sabe se o ON funciona nem se o OFF
 * ficou igual. Isso continua sendo verificação manual no app (fase 1 do plano em
 * `backend-fastapi/docs/pdv-profissional-plano.md`). "Tem guard" não é "tem teste
 * do Modo Balcão", e é de propósito: o frontend não tem infraestrutura de teste,
 * e montá-la é decisão de outro projeto.
 *
 * O que ele protege é a ARQUITETURA — o raio de alcance da chave. É a parte que
 * dá para provar de graça, em todo build.
 *
 * Uso: node scripts/check-balcao.mjs
 */

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, dirname, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const FONTE = join(RAIZ, 'frontend', 'src');

/**
 * Os únicos arquivos autorizados a conhecer o Modo Balcão.
 *
 * Mexer nesta lista é uma decisão, não um detalhe: cada nome aqui é um lugar
 * onde alguém precisa provar de novo, à mão, que a chave desligada não mudou
 * nada. Se você está acrescentando uma linha, o teste manual de OFF volta a ser
 * obrigatório antes do commit.
 */
const AUTORIZADOS = [
  // O store: a chave em si.
  'shared/stores/balcao.store.ts',
  // O botão que liga, e o começo da venda que ele desvia.
  'modules/sales/SalesView.vue',
  // A emenda de uma venda na próxima.
  'modules/sales/components/SaleModal.vue',
  // Foco no Dinheiro, checkbox dispensado à vista, troco em fonte de balcão.
  'modules/sales/components/SaleModal/FinishSaleModal.vue',
];

/** Como a chave aparece no código. Qualquer um destes conta como "conhece". */
const MARCAS = [
  /\bmodoBalcao\b/,
  /\buseBalcaoStore\b/,
  /balcao\.store/,
  /startbig-modo-balcao/,
];

const EXTENSOES = ['.ts', '.vue', '.js', '.tsx', '.jsx'];

function varrer(dir, achados = []) {
  for (const nome of readdirSync(dir)) {
    const caminho = join(dir, nome);
    if (statSync(caminho).isDirectory()) {
      varrer(caminho, achados);
      continue;
    }
    if (EXTENSOES.some((ext) => nome.endsWith(ext))) achados.push(caminho);
  }
  return achados;
}

const arquivos = varrer(FONTE);
const conhecem = [];

for (const caminho of arquivos) {
  const texto = readFileSync(caminho, 'utf8');
  if (MARCAS.some((marca) => marca.test(texto))) {
    conhecem.push(relative(FONTE, caminho).split(sep).join('/'));
  }
}

const falhas = [];

// 1. Vazamento: alguém novo conhece a chave.
const intrusos = conhecem.filter((c) => !AUTORIZADOS.includes(c));
for (const intruso of intrusos) {
  falhas.push(`${intruso} conhece o Modo Balcão e não está na lista de autorizados`);
}

// 2. Lista velha: um autorizado que não usa mais. Não é perigoso, mas uma lista
//    que mente deixa de servir como fronteira — e é uma linha para consertar.
const orfaos = AUTORIZADOS.filter((a) => !conhecem.includes(a));
for (const orfao of orfaos) {
  falhas.push(`${orfao} está autorizado mas não menciona mais o Modo Balcão — remova da lista`);
}

// 3. O padrão é DESLIGADO, e tem que continuar sendo.
//
//    Um localStorage ausente, corrompido ou de outra instalação não pode ligar
//    sozinho um modo que muda o fluxo da venda numa loja que nunca pediu por ele.
//    A leitura segura é comparar com 'true' — inverter para `!== 'false'` faria
//    toda máquina virgem nascer com o modo ligado.
const STORE = join(FONTE, 'shared', 'stores', 'balcao.store.ts');
let fonteStore = '';
try {
  fonteStore = readFileSync(STORE, 'utf8');
} catch {
  falhas.push('shared/stores/balcao.store.ts não existe — o Modo Balcão perdeu o store');
}

if (fonteStore) {
  if (!/===\s*'true'|===\s*"true"/.test(fonteStore)) {
    falhas.push("balcao.store.ts não compara o valor guardado com 'true' — o padrão desligado não está garantido");
  }
  if (/!==\s*'false'|!==\s*"false"/.test(fonteStore)) {
    falhas.push("balcao.store.ts usa `!== 'false'`: disco vazio passaria a LIGAR o modo sozinho");
  }
  if (!/catch\s*{[^}]*return\s+false/s.test(fonteStore)) {
    falhas.push('balcao.store.ts: a leitura do disco não devolve false quando o localStorage falha');
  }
}

if (falhas.length) {
  console.error('\n\x1b[31m✖ BUILD BARRADO — o Modo Balcão saiu da fronteira\x1b[0m\n');
  for (const f of falhas) console.error(`  • ${f}`);
  console.error(
    '\n  Desligado, o módulo de vendas tem que se comportar como sempre — é o que\n' +
    '  protege as lojas de assistência, oficina e serigrafia que já rodam.\n' +
    '  Se a expansão for intencional, acrescente o arquivo em AUTORIZADOS\n' +
    '  (scripts/check-balcao.mjs) E refaça o teste manual de OFF no app.\n'
  );
  process.exit(1);
}

console.log(
  `✓ Modo Balcão contido em ${conhecem.length} arquivo(s) autorizados ` +
  `(${arquivos.length} varridos), padrão desligado preservado`
);
