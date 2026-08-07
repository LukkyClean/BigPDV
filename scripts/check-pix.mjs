#!/usr/bin/env node
/**
 * Prova que todo BR Code que o sistema gera é um BR Code válido, e barra o
 * build quando não for.
 *
 * O QR do PIX falha calado. Um payload com um comprimento errado, um acento
 * onde não cabe ou um CRC de um byte só de diferença vira um quadrado que
 * desenha bonito na tela e simplesmente não abre no app do banco — e o erro
 * aparece com o cliente esperando na frente do balcão, não aqui. Não dá para
 * "testar na hora": ou está provado antes, ou a loja descobre por você.
 *
 * Como isso é conta fechada (o padrão EMV é determinístico), dá para varrer:
 * cada chave × cada valor × cada nome sujo × cada cidade × cada txid, e sobre
 * cada payload gerado conferir as invariantes que o banco vai conferir.
 *
 * O CRC é checado contra uma segunda implementação, feita por tabela, escrita
 * aqui de propósito: duas implementações diferentes que concordam valem mais do
 * que uma implementação comparada consigo mesma.
 *
 * Não instala nada: usa o esbuild que já vem com o Vite, no mesmo padrão dos
 * outros `check:*`.
 *
 * Uso: node scripts/check-pix.mjs
 */

import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const FONTE = join(RAIZ, 'frontend', 'src', 'shared', 'utils', 'pixBrCode.ts');
const FONTE_ESCPOS = join(RAIZ, 'frontend', 'src', 'shared', 'services', 'escpos.ts');

const { build } = await import(
  pathToFileURL(join(RAIZ, 'frontend', 'node_modules', 'esbuild', 'lib', 'main.js')).href
);

const tmp = mkdtempSync(join(tmpdir(), 'pix-'));
const saida = join(tmp, 'pixBrCode.mjs');
const saidaEscpos = join(tmp, 'escpos.mjs');

try {
  await build({
    entryPoints: [FONTE],
    outfile: saida,
    format: 'esm',
    platform: 'node',
    bundle: true,
    logLevel: 'silent',
  });
  await build({
    entryPoints: [FONTE_ESCPOS],
    outfile: saidaEscpos,
    format: 'esm',
    platform: 'node',
    bundle: true,
    logLevel: 'silent',
  });

  const {
    montarPixBrCode, normalizarChavePix, crc16, paraAsciiImprimivel,
    NOME_TAMANHO_MAXIMO, CIDADE_TAMANHO_MAXIMO, TXID_TAMANHO_MAXIMO,
    VALOR_TAMANHO_MAXIMO, CHAVE_TAMANHO_MAXIMO,
  } = await import(pathToFileURL(saida).href);

  const falhas = [];
  let testados = 0;
  const anotar = (msg) => falhas.push(msg);

  // ── CRC por tabela: a segunda opinião ──────────────────────────────────────
  const TABELA = new Uint16Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i << 8;
    for (let bit = 0; bit < 8; bit++) c = c & 0x8000 ? ((c << 1) ^ 0x1021) & 0xffff : (c << 1) & 0xffff;
    TABELA[i] = c;
  }
  const crcTabela = (texto) => {
    let crc = 0xffff;
    for (let i = 0; i < texto.length; i++) {
      crc = (TABELA[((crc >> 8) ^ texto.charCodeAt(i)) & 0xff] ^ (crc << 8)) & 0xffff;
    }
    return crc.toString(16).toUpperCase().padStart(4, '0');
  };

  // Vetor canônico do CRC16/CCITT-FALSE. Existem várias variantes de CRC16 e
  // elas dão resultados diferentes; este vetor prova que é a certa.
  if (crc16('123456789') !== '29B1') {
    anotar(`CRC do vetor "123456789" deu ${crc16('123456789')}, esperado 29B1`);
  }
  if (crcTabela('123456789') !== '29B1') {
    anotar('a implementação de conferência (tabela) está errada — corrija o script');
  }

  // Âncora externa: um BR Code de exemplo publicado no padrão, com o CRC que
  // ele traz. Duas implementações nossas concordarem não prova que ambas estão
  // certas — concordar com um payload de fora, sim.
  const PUBLICADO =
    '00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-426655440000' +
    '5204000053039865802BR5913Fulano de Tal6008BRASILIA62070503***6304';
  if (crc16(PUBLICADO) !== '1D3D') {
    anotar(`CRC do exemplo publicado deu ${crc16(PUBLICADO)}, esperado 1D3D`);
  }

  // ── Leitor de TLV: desmonta o payload como o app do banco faria ────────────
  function lerTlv(texto, ondeEstou) {
    const campos = [];
    let i = 0;
    while (i < texto.length) {
      if (i + 4 > texto.length) {
        anotar(`${ondeEstou}: sobrou lixo no fim (${JSON.stringify(texto.slice(i))})`);
        return null;
      }
      const id = texto.slice(i, i + 2);
      const tam = Number(texto.slice(i + 2, i + 4));
      if (!/^\d{2}$/.test(texto.slice(i + 2, i + 4))) {
        anotar(`${ondeEstou}: campo ${id} declara comprimento não numérico`);
        return null;
      }
      const valor = texto.slice(i + 4, i + 4 + tam);
      if (valor.length !== tam) {
        anotar(`${ondeEstou}: campo ${id} promete ${tam} caracteres e entrega ${valor.length}`);
        return null;
      }
      campos.push([id, valor]);
      i += 4 + tam;
    }
    return Object.fromEntries(campos);
  }

  /** Tudo que o app do banco exige de um BR Code, conferido de uma vez. */
  function verificar(params, origem) {
    testados++;
    const payload = montarPixBrCode(params);
    const { chave, reconhecida } = normalizarChavePix(params.chave);

    if (!chave || chave.length > CHAVE_TAMANHO_MAXIMO) {
      if (payload !== '') anotar(`${origem}: chave inválida deveria gerar payload vazio`);
      return;
    }
    if (!payload) {
      anotar(`${origem}: payload vazio com chave válida (${JSON.stringify(chave)})`);
      return;
    }

    // 1. ASCII imprimível de ponta a ponta — é o que mantém honesta a contagem
    //    de comprimento, que o padrão declara em bytes.
    const forasteiro = [...payload].find((c) => c.charCodeAt(0) < 0x20 || c.charCodeAt(0) > 0x7e);
    if (forasteiro) {
      anotar(`${origem}: caractere fora do ASCII imprimível (U+${forasteiro.codePointAt(0).toString(16)})`);
    }

    // 2. CRC: presente, no fim, e igual ao da segunda implementação.
    if (payload.slice(-8, -4) !== '6304') {
      anotar(`${origem}: não termina com o campo 63 de 4 caracteres`);
      return;
    }
    const corpo = payload.slice(0, -4);
    const crcNoPayload = payload.slice(-4);
    if (crcNoPayload !== crcTabela(corpo)) {
      anotar(`${origem}: CRC ${crcNoPayload}, tabela diz ${crcTabela(corpo)}`);
    }
    if (!/^[0-9A-F]{4}$/.test(crcNoPayload)) {
      anotar(`${origem}: CRC ${crcNoPayload} não é hex maiúsculo de 4 casas`);
    }

    // 3. Estrutura: desmonta e confere campo a campo.
    const campos = lerTlv(payload, origem);
    if (!campos) return;

    if (campos['00'] !== '01') anotar(`${origem}: campo 00 = ${campos['00']}, esperado 01`);
    if (!['11', '12'].includes(campos['01'])) anotar(`${origem}: campo 01 = ${campos['01']}`);
    if (campos['52'] !== '0000') anotar(`${origem}: MCC = ${campos['52']}, esperado 0000`);
    if (campos['53'] !== '986') anotar(`${origem}: moeda = ${campos['53']}, esperado 986`);
    if (campos['58'] !== 'BR') anotar(`${origem}: país = ${campos['58']}, esperado BR`);

    // 4. A chave sai de dentro do QR exatamente como foi normalizada. Este é o
    //    campo que decide se o dinheiro chega em alguém.
    const conta = lerTlv(campos['26'] ?? '', `${origem} (campo 26)`);
    if (!conta) return;
    if (conta['00'] !== 'br.gov.bcb.pix') anotar(`${origem}: GUI = ${conta['00']}`);
    if (conta['01'] !== chave) {
      anotar(`${origem}: chave no QR = ${JSON.stringify(conta['01'])}, normalizada = ${JSON.stringify(chave)}`);
    }

    // 5. Tetos de comprimento — estourar aqui é QR recusado.
    if ((campos['59'] ?? '').length > NOME_TAMANHO_MAXIMO) anotar(`${origem}: nome com ${campos['59'].length} caracteres`);
    if ((campos['60'] ?? '').length > CIDADE_TAMANHO_MAXIMO) anotar(`${origem}: cidade com ${campos['60'].length} caracteres`);
    if (!campos['59']) anotar(`${origem}: campo 59 (nome) vazio`);
    if (!campos['60']) anotar(`${origem}: campo 60 (cidade) vazio`);

    // 6. Valor: formato fixo de duas casas, ponto decimal, dentro do teto.
    const centavos = Math.round(params.valorCentavos ?? 0);
    const esperado = centavos > 0 ? (centavos / 100).toFixed(2) : '';
    if (esperado && esperado.length <= VALOR_TAMANHO_MAXIMO) {
      if (campos['54'] !== esperado) anotar(`${origem}: valor = ${campos['54']}, esperado ${esperado}`);
      if (campos['01'] !== '12') anotar(`${origem}: com valor, o campo 01 devia ser 12 (uso único)`);
    } else {
      if ('54' in campos) anotar(`${origem}: valor não deveria existir (${campos['54']})`);
      if (campos['01'] !== '11') anotar(`${origem}: sem valor, o campo 01 devia ser 11 (reutilizável)`);
    }

    // 7. txid: alfanumérico ou os três asteriscos do QR estático.
    const extra = lerTlv(campos['62'] ?? '', `${origem} (campo 62)`);
    if (!extra) return;
    const txid = extra['05'];
    if (txid !== '***' && !/^[A-Za-z0-9]{1,25}$/.test(txid ?? '')) {
      anotar(`${origem}: txid inválido (${JSON.stringify(txid)})`);
    }
    if ((txid ?? '').length > TXID_TAMANHO_MAXIMO) anotar(`${origem}: txid com ${txid.length} caracteres`);

    // Reconhecer a chave é bom, mas não é obrigatório: o cadastro aceita texto
    // de propósito. O que não pode é gerar QR quebrado por causa disso.
    void reconhecida;
  }

  // ── A varredura ────────────────────────────────────────────────────────────
  const CHAVES = [
    '52998224725',                              // CPF válido, limpo
    '529.982.247-25',                           // o mesmo, com máscara
    '11222333000181',                           // CNPJ
    '11.222.333/0001-81',
    '11987654321',                              // celular de 11 dígitos (NÃO é CPF)
    '(11) 98765-4321',
    '+5511987654321',
    '1133334444',                               // fixo de 10 dígitos
    'loja@exemplo.com.br',
    'LOJA@EXEMPLO.COM.BR',
    '123e4567-e89b-12d3-a456-426614174000',     // aleatória
    '123E4567-E89B-12D3-A456-426614174000',
    'chave-que-ninguem-reconhece',              // passa literal, com aviso na tela
  ];

  const VALORES = [
    undefined, 0, 1, 5, 99, 100, 999, 1000, 12345, 100000, 999999, 123456789, 99999999999,
    // O estouro: 13 caracteres é o teto do campo 54.
    99999999999999,
  ];

  const NOMES = [
    'Oficina do Zé',
    'AÇÃO MECÂNICA LTDA',
    'Comércio de Peças e Serviços Automotivos do Vale Ltda ME',  // estoura os 25
    'José  da   Silva',                                          // espaço repetido
    '  espaço nas pontas  ',
    'Loja 🔧 do Zé',                                             // emoji
    'Ñoño & Filhos',
    '',                                                          // cai no padrão
    '中文商店',                                                   // some inteiro
  ];

  const CIDADES = [
    'São Paulo', 'BRASÍLIA', 'Santa Bárbara d\'Oeste', 'Poços de Caldas', '', 'Ji-Paraná',
  ];

  const TXIDS = [
    undefined, '', '***', 'V1234', 'OS-0001', 'os/2026/0007', 'A'.repeat(40), '###', '  ',
  ];

  // Combinação cheia nas dimensões que interagem (chave × valor), e as demais
  // varridas contra uma base fixa — o produto completo seria milhões de casos
  // sem cobrir nada de novo.
  for (const chave of CHAVES) {
    for (const valorCentavos of VALORES) {
      verificar({ chave, valorCentavos, nome: 'Oficina do Zé', cidade: 'São Paulo' }, `chave×valor ${chave}/${valorCentavos}`);
    }
  }
  for (const nome of NOMES) {
    for (const cidade of CIDADES) {
      verificar({ chave: '52998224725', valorCentavos: 12345, nome, cidade }, `nome×cidade ${JSON.stringify(nome)}/${JSON.stringify(cidade)}`);
    }
  }
  for (const txid of TXIDS) {
    verificar({ chave: 'loja@exemplo.com.br', valorCentavos: 5000, nome: 'Loja', cidade: 'Recife', txid }, `txid ${JSON.stringify(txid)}`);
  }

  // Entrada que não deveria existir não pode derrubar nada.
  for (const lixo of [undefined, null, '', '   ', '@', '+', '0'.repeat(200)]) {
    testados++;
    const p = montarPixBrCode({ chave: lixo, valorCentavos: 100, nome: 'X', cidade: 'Y' });
    if (typeof p !== 'string') anotar(`entrada ${JSON.stringify(lixo)} não devolveu string`);
  }

  // ── Normalização: os casos que decidem para onde o dinheiro vai ────────────
  const ESPERADO = [
    ['529.982.247-25', 'CPF', '52998224725'],
    ['52998224725', 'CPF', '52998224725'],
    ['11.222.333/0001-81', 'CNPJ', '11222333000181'],
    // 11 dígitos, mas o dígito verificador de CPF não fecha: é telefone.
    ['11987654321', 'TELEFONE', '+5511987654321'],
    ['(11) 98765-4321', 'TELEFONE', '+5511987654321'],
    ['+55 11 98765-4321', 'TELEFONE', '+5511987654321'],
    ['5511987654321', 'TELEFONE', '+5511987654321'],
    ['1133334444', 'TELEFONE', '+551133334444'],
    ['LOJA@Exemplo.com.BR', 'EMAIL', 'loja@exemplo.com.br'],
    ['  loja@exemplo.com  ', 'EMAIL', 'loja@exemplo.com'],
    ['123E4567-E89B-12D3-A456-426614174000', 'ALEATORIA', '123e4567-e89b-12d3-a456-426614174000'],
    ['nao e chave nenhuma', 'INDEFINIDA', 'nao e chave nenhuma'],
    ['', 'INDEFINIDA', ''],
  ];
  for (const [entrada, tipo, chave] of ESPERADO) {
    testados++;
    const r = normalizarChavePix(entrada);
    if (r.tipo !== tipo || r.chave !== chave) {
      anotar(`normalizar ${JSON.stringify(entrada)} → ${r.tipo}/${JSON.stringify(r.chave)}, esperado ${tipo}/${JSON.stringify(chave)}`);
    }
  }

  // ── Dobra para ASCII ───────────────────────────────────────────────────────
  const ASCII = [
    ['São Paulo', 15, 'Sao Paulo'],
    ['AÇÃO MECÂNICA', 25, 'ACAO MECANICA'],
    ['José  da   Silva', 25, 'Jose da Silva'],
    ['  espaço  ', 25, 'espaco'],
    ['中文', 25, ''],
    ['Comércio de Peças e Serviços', 25, 'Comercio de Pecas e Servi'],
  ];
  for (const [entrada, limite, esperado] of ASCII) {
    testados++;
    const r = paraAsciiImprimivel(entrada, limite);
    if (r !== esperado) {
      anotar(`ascii ${JSON.stringify(entrada)} → ${JSON.stringify(r)}, esperado ${JSON.stringify(esperado)}`);
    }
  }

  // ── O comando nativo de QR da impressora térmica ───────────────────────────
  //
  // O QR no cupom não é imagem: é o comando GS ( k, em que o tamanho dos dados
  // viaja em dois bytes separados do conteúdo. Errar essa contagem por um não
  // desenha um QR torto — desenha lixo, ou nada, e só se descobre com o papel na
  // mão. Aqui a gente desmonta o fluxo de bytes e confere.
  const { EscPosBuilder } = await import(pathToFileURL(saidaEscpos).href);

  for (const bobina of ['58', '80']) {
    for (const chave of ['52998224725', 'loja@exemplo.com.br', '123e4567-e89b-12d3-a456-426614174000']) {
      testados++;
      const payload = montarPixBrCode({
        chave, valorCentavos: 45000, nome: 'Oficina do Zé', cidade: 'São Paulo', txid: 'OS000123',
      });
      const bytes = new EscPosBuilder(bobina).qrCode(payload).build();
      const origem = `escpos ${bobina}mm/${chave}`;

      // Localiza o comando que armazena os dados: GS ( k pL pH 49 80 48
      let i = 0;
      let achou = false;
      while (i < bytes.length - 7) {
        if (bytes[i] === 0x1d && bytes[i + 1] === 0x28 && bytes[i + 2] === 0x6b) {
          const pL = bytes[i + 3];
          const pH = bytes[i + 4];
          const tamanho = pL + (pH << 8);
          if (bytes[i + 5] === 0x31 && bytes[i + 6] === 0x50 && bytes[i + 7] === 0x30) {
            achou = true;
            // pL/pH contam os 3 bytes de cabeçalho (cn, fn, m) junto com os dados.
            const dados = bytes.slice(i + 8, i + 8 + tamanho - 3);
            const texto = String.fromCharCode(...dados);
            if (texto !== payload) {
              anotar(`${origem}: dados do QR divergem do payload (${dados.length} de ${payload.length} bytes)`);
            }
            // Depois de armazenar tem de vir a ordem de imprimir; sem ela a
            // impressora engole o símbolo em silêncio.
            const resto = bytes.slice(i + 8 + tamanho - 3);
            const imprime = [0x1d, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x51, 0x30];
            if (!imprime.every((b, k) => resto[k] === b)) {
              anotar(`${origem}: falta o comando de impressão do QR depois dos dados`);
            }
            break;
          }
          i += 5 + tamanho;
          continue;
        }
        i++;
      }
      if (!achou) anotar(`${origem}: comando GS ( k de dados não encontrado no fluxo`);
    }
  }

  // Payload vazio não pode emitir comando nenhum.
  testados++;
  if (new EscPosBuilder('80').qrCode('').build().length !== new EscPosBuilder('80').build().length) {
    anotar('escpos: QR vazio emitiu bytes');
  }

  if (falhas.length) {
    console.error('\n\x1b[31m✖ BUILD BARRADO — BR Code do PIX inválido\x1b[0m\n');
    for (const f of falhas.slice(0, 20)) console.error(`  • ${f}`);
    if (falhas.length > 20) console.error(`  … e mais ${falhas.length - 20} falha(s)`);
    console.error(`\n  ${falhas.length} problema(s) em ${testados} casos testados.`);
    console.error('  Ajuste shared/utils/pixBrCode.ts.\n');
    process.exit(1);
  }

  console.log(`✓ BR Code válido em ${testados} casos (chaves × valores × nomes × cidades × txid)`);
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
