#!/usr/bin/env node
/**
 * Prova que o DANFE NFC-e sai imprimível e completo nas duas bobinas, e barra
 * o build quando não sai.
 *
 * O cupom fiscal falha calado. Uma linha que estoura a coluna quebra no meio
 * de um número; a chave de acesso partida entre dois blocos vira erro de
 * digitação de quem tenta consultar a nota; a URL de consulta truncada não
 * abre. Nada disso aparece na tela do desenvolvedor — aparece no papel, com o
 * cliente esperando, e o cupom já foi entregue.
 *
 * A conta é fechada: o layout é determinístico e as colunas são conhecidas
 * (48 na bobina de 80mm, 32 na de 58mm). Então dá para gerar o cupom e conferir
 * cada invariante que a SEFAZ e o consumidor vão conferir.
 *
 * Não instala nada: usa o esbuild que já vem com o Vite, no mesmo padrão dos
 * outros `check:*`.
 *
 * Uso: node scripts/check-danfe-nfce.mjs
 */

import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const FONTE = join(
  RAIZ, 'frontend', 'src', 'modules', 'sales', 'components', 'print', 'nfceToEscPos.ts',
);

const { build } = await import(
  pathToFileURL(join(RAIZ, 'frontend', 'node_modules', 'esbuild', 'lib', 'main.js')).href
);

const tmp = mkdtempSync(join(tmpdir(), 'danfe-'));
const saida = join(tmp, 'nfceToEscPos.mjs');

/** Colunas por bobina — precisa espelhar COLUNAS em shared/services/escpos.ts. */
const COLUNAS = { '80': 48, '58': 32 };

const CHAVE = '23260912345678000190650010000012341098765432'; // 44 dígitos
const CPF = '52998224725';

try {
  await build({
    entryPoints: [FONTE],
    outfile: saida,
    format: 'esm',
    platform: 'node',
    bundle: true,
    logLevel: 'silent',
    alias: { '@': join(RAIZ, 'frontend', 'src') },
  });

  const { nfceToEscPos, quebrarChaveEmLinhas, mascararDocumentoConsumidor } =
    await import(pathToFileURL(saida).href);

  const falhas = [];
  const anotar = (msg) => falhas.push(msg);

  // ── Decodificador: bytes ESC/POS -> linhas de texto ──────────────────────
  // Só o suficiente para conferir layout: pula os comandos e guarda o texto.
  function paraLinhas(bytes) {
    const linhas = [];
    let atual = '';
    let temQr = false;

    for (let i = 0; i < bytes.length; i++) {
      const b = bytes[i];

      if (b === 0x1d && bytes[i + 1] === 0x28) {          // GS ( k — QR Code
        const tamanho = bytes[i + 3] | (bytes[i + 4] << 8);
        if (bytes[i + 5] === 0x31 && bytes[i + 6] === 0x50) temQr = true;
        i += 4 + tamanho;
        continue;
      }
      if (b === 0x1d && bytes[i + 1] === 0x56) { i += 3; continue; }  // corte
      if (b === 0x1b && bytes[i + 1] === 0x70) { i += 4; continue; }  // gaveta
      if (b === 0x1b && bytes[i + 1] === 0x40) { i += 1; continue; }  // ESC @ (2 bytes)
      if (b === 0x1b || b === 0x1d) { i += 2; continue; }             // 3 bytes

      if (b === 0x0a) { linhas.push(atual); atual = ''; continue; }
      atual += String.fromCharCode(b);
    }
    if (atual) linhas.push(atual);
    return { linhas, temQr };
  }

  const empresa = {
    nome: 'Supermercado Central',
    razaoSocial: 'SUPERMERCADO CENTRAL DE ALIMENTOS LTDA ME',
    cnpj: '12.345.678/0001-90',
    inscricaoEstadual: '06.123.456-7',
    endereco: '',
    enderecoLinha1: 'AV. COMERCIAL DOS TRABALHADORES, 500 - CENTRO',
    enderecoLinha2: 'QUIXADA - CE',
    contato: '', email: '', logo: null,
  };

  const venda = {
    id: 1, numero_venda: 1234, criado_em: '2026-09-04T10:15:00',
    subtotal: 1300, total: 1300, descontos: 0, entrega: 0, acrescimo: 0, troco: 200,
    cliente: null,
    produtos: [
      {
        id: 1, produto_id: 1020, sku: '1020', nome: 'COCA COLA LATA 350ML',
        quantidade: 1, valor_unitario: 500, total: 500, desconto: 0,
      },
      {
        // Descrição longa de propósito: é o que empurra a linha para fora da
        // coluna quando o truncamento não funciona.
        id: 2, produto_id: 3045, sku: 'PAOQJ-TRAD-500G',
        nome: 'PAO DE QUEIJO TRADICIONAL CONGELADO PACOTE 500G PREMIUM',
        quantidade: 2, valor_unitario: 400, total: 800, desconto: 50,
      },
    ],
    pagamentos: [{ forma_pagamento_id: 5, valor: 1500 }],
  };

  const documentoBase = {
    id: 1, status: 'AUTORIZADA', numero_documento: 1234, serie: 1,
    chave_acesso: CHAVE, protocolo_autorizacao: '135260001234567',
    data_autorizacao: '2026-09-04T10:15:00', data_emissao: '2026-09-04T10:15:00',
    ambiente_emissao: 1, valor_tributos: 245,
    qrcode: 'http://nfce.sefaz.ce.gov.br/qrcode?p=23260912345678000190650010000012341098765432|2|1|1|A1B2C3D4',
    url_consulta: 'http://nfce.sefaz.ce.gov.br/consulta',
  };

  const gerar = (bobina, documento = documentoBase, opcoes = {}) =>
    paraLinhas(nfceToEscPos(venda, documento, {
      bobina, empresa, resolverPagamento: () => 'PIX', ...opcoes,
    }));

  // ── 1. Nada pode estourar a largura do papel ─────────────────────────────
  for (const [bobina, colunas] of Object.entries(COLUNAS)) {
    const { linhas } = gerar(bobina);
    for (const linha of linhas) {
      if (linha.length > colunas) {
        anotar(
          `[${bobina}mm] linha com ${linha.length} caracteres (máx ${colunas}): `
          + `"${linha}"`,
        );
      }
    }
  }

  // ── 2. A chave de acesso precisa sair inteira e em blocos completos ──────
  for (const [bobina, colunas] of Object.entries(COLUNAS)) {
    const partes = quebrarChaveEmLinhas(CHAVE, colunas);
    const digitos = partes.join('').replace(/\D/g, '');

    if (digitos !== CHAVE) {
      anotar(`[${bobina}mm] a chave saiu alterada: ${digitos}`);
    }
    for (const parte of partes) {
      if (parte.length > colunas) {
        anotar(`[${bobina}mm] bloco da chave estourou a coluna: "${parte}"`);
      }
      for (const bloco of parte.split(' ')) {
        // O último bloco da chave tem 4 dígitos; nenhum pode sair partido.
        if (bloco.length !== 4) {
          anotar(`[${bobina}mm] bloco da chave partido ao meio: "${bloco}"`);
        }
      }
    }
  }

  // ── 3. O que a lei manda estar no cupom ──────────────────────────────────
  const OBRIGATORIOS = [
    ['DANFE NFC-e', 'título do documento'],
    ['CNPJ', 'CNPJ do emitente'],
    ['IE:', 'inscrição estadual do emitente'],
    ['QTD. TOTAL DE ITENS', 'quantidade total de itens'],
    ['VALOR TOTAL', 'valor total'],
    ['12.741', 'tributos aproximados (Lei da Transparência)'],
    ['CHAVE DE ACESSO', 'rótulo da chave de acesso'],
    ['Protocolo:', 'protocolo de autorização'],
  ];

  for (const bobina of Object.keys(COLUNAS)) {
    const { linhas, temQr } = gerar(bobina);
    const texto = linhas.join('\n');

    for (const [trecho, descricao] of OBRIGATORIOS) {
      if (!texto.includes(trecho)) {
        anotar(`[${bobina}mm] falta no cupom: ${descricao} ("${trecho}")`);
      }
    }
    if (!temQr) anotar(`[${bobina}mm] o cupom saiu SEM QR Code`);
    // A URL pode OCUPAR duas linhas na bobina estreita; o que não pode é
    // sair cortada. Por isso a comparação ignora as quebras.
    if (!linhas.join('').includes(documentoBase.url_consulta)) {
      anotar(`[${bobina}mm] a URL de consulta saiu truncada ou ausente`);
    }
  }

  // ── 4. O CPF do consumidor nunca sai por extenso ─────────────────────────
  // O cupom fica no balcão e vai para o lixo da loja; o número inteiro ali
  // entrega quem comprou a quem pegar o papel.
  for (const bobina of Object.keys(COLUNAS)) {
    const { linhas } = gerar(bobina, documentoBase, { documentoConsumidor: CPF });
    const texto = linhas.join('\n');

    if (texto.includes(CPF) || texto.includes('529.982.247-25')) {
      anotar(`[${bobina}mm] o CPF do consumidor saiu por extenso no cupom`);
    }
    if (!texto.includes('CPF')) {
      anotar(`[${bobina}mm] o consumidor informado não aparece no cupom`);
    }
  }

  const mascarado = mascararDocumentoConsumidor(CPF);
  if (mascarado.includes('982') || mascarado.includes('247')) {
    anotar(`máscara de CPF revela o miolo do número: "${mascarado}"`);
  }

  // ── 5. Sem consumidor, o cupom precisa DIZER isso ────────────────────────
  for (const bobina of Object.keys(COLUNAS)) {
    const { linhas } = gerar(bobina);
    if (!linhas.join('\n').includes('CONSUMIDOR NAO IDENTIFICADO')) {
      anotar(`[${bobina}mm] falta a declaração de consumidor não identificado`);
    }
  }

  // ── 6. Homologação precisa gritar que não vale ───────────────────────────
  for (const bobina of Object.keys(COLUNAS)) {
    const { linhas } = gerar(bobina, { ...documentoBase, ambiente_emissao: 2 });
    const texto = linhas.join('\n');
    if (!texto.includes('HOMOLOGACAO') || !texto.includes('SEM VALOR FISCAL')) {
      anotar(`[${bobina}mm] cupom de homologação sem o aviso de "sem valor fiscal"`);
    }
  }

  // ── 7. Sem o valor dos tributos, a linha não pode virar R$ 0,00 ──────────
  // Dizer ao consumidor que ele não pagou tributo é pior que omitir a linha.
  for (const bobina of Object.keys(COLUNAS)) {
    const { linhas } = gerar(bobina, { ...documentoBase, valor_tributos: null });
    const texto = linhas.join('\n');
    if (texto.includes('12.741')) {
      anotar(`[${bobina}mm] imprimiu a linha de tributos sem ter o valor`);
    }
  }

  // ── Resultado ────────────────────────────────────────────────────────────
  if (falhas.length) {
    console.error('\n✗ DANFE NFC-e: o cupom não sai correto.\n');
    for (const falha of falhas) console.error(`  - ${falha}`);
    console.error('');
    process.exit(1);
  }

  console.log('✓ DANFE NFC-e: cupom imprimível e completo em 58mm e 80mm.');
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
