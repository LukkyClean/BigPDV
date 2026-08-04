/**
 * @fileoverview Deriva a paleta do sistema a partir de UMA cor escolhida pelo dono.
 *
 * A regra central: o dono escolhe **matiz e saturação** ("é verde", "é vinho");
 * quem decide a **luminosidade de cada papel** é este módulo, e só aceita um valor
 * depois de conferir o contraste contra o texto que vai por cima. Usar a cor crua
 * como fundo de botão é o que produz rosa pastel com texto branco invisível.
 *
 * Trabalha em OKLCH, não HSL. No HSL "50% de luminosidade" não significa a mesma
 * coisa para todas as cores — um amarelo a 50% é muito mais claro que um azul a
 * 50% — então uma paleta derivada em HSL geraria, para o amarelo, um "tom escuro"
 * que na prática é claro, e o texto branco por cima sumiria. No OKLCH a mesma
 * luminosidade significa o mesmo brilho percebido em qualquer matiz.
 *
 * NÃO deriva `brand-action` (o preto da sidebar) nem `brand-off-white` (o fundo):
 * são fixos por contrato. É o que mantém o logo sempre legível — ele vive sobre o
 * preto — e o que garante que o texto de leitura do sistema, escuro sobre branco,
 * nunca seja tocado por escolha de cor nenhuma.
 *
 * Sem dependência externa: a matemática está aqui.
 */

// ===========================================================================
// CONTRATO DE LEGIBILIDADE
// ===========================================================================

/** Mínimo da WCAG AA para texto normal. Vale para texto sobre fundo colorido e
 *  para cor usada como texto sobre branco (links, valores em destaque). */
export const CONTRASTE_MINIMO_TEXTO = 4.5;

/** Mínimo da WCAG AA para elemento de interface e texto grande (bordas, ícones). */
export const CONTRASTE_MINIMO_UI = 3;

/** Cor de fábrica. É também o destino do "restaurar padrão". */
export const COR_PADRAO = '#045ca1';

/**
 * Paleta de fábrica, com os valores exatos que estão no global.css.
 *
 * Não é o que a derivação produziria a partir de `COR_PADRAO` — ela devolveria
 * um azul um pouco mais claro (#226eb5). Esses tons foram escolhidos a mão e são
 * a identidade atual do produto: derivá-los mudaria a cara do sistema de todos os
 * clientes que nunca pediram tema nenhum, e faria "restaurar padrão" devolver algo
 * diferente do que havia antes. Derivação é para cor personalizada; o padrão é
 * literal.
 */
export const PALETA_PADRAO: Paleta = {
  'brand-primary': '#045ca1',
  // O azul-marinho que o BaseButton usava chumbado (`blue-950`). Mantido literal
  // para o hover de hoje não mudar em instalação nenhuma.
  'brand-primary-hover': '#172554',
  'brand-primary-light': '#e8f1f9',
  'brand-secondary': '#5590bf',
};

/** Tokens que a paleta gera. Os demais (`brand-action`, `brand-grey`,
 *  `brand-off-white`) são fixos e não aparecem aqui de propósito. */
export interface Paleta {
  'brand-primary': string;
  /** Estado de hover do botão primário. Existe como token porque estava
   *  chumbado em `hover:bg-blue-950` no BaseButton: o botão assumia a cor da
   *  empresa e voltava a azul ao passar o mouse. */
  'brand-primary-hover': string;
  'brand-primary-light': string;
  'brand-secondary': string;
}

export interface Rgb { r: number; g: number; b: number }   // 0..1
export interface Oklch { l: number; c: number; h: number } // l 0..1, c 0..~0.4, h graus

// ===========================================================================
// CONVERSÕES
// ===========================================================================

const BRANCO: Rgb = { r: 1, g: 1, b: 1 };

export function hexParaRgb(hex: string): Rgb | null {
  const limpo = hex.trim().replace(/^#/, '');
  const completo = limpo.length === 3 ? limpo.split('').map((c) => c + c).join('') : limpo;
  if (!/^[0-9a-fA-F]{6}$/.test(completo)) return null;
  return {
    r: parseInt(completo.slice(0, 2), 16) / 255,
    g: parseInt(completo.slice(2, 4), 16) / 255,
    b: parseInt(completo.slice(4, 6), 16) / 255,
  };
}

export function rgbParaHex({ r, g, b }: Rgb): string {
  const canal = (v: number) =>
    Math.round(Math.min(1, Math.max(0, v)) * 255).toString(16).padStart(2, '0');
  return `#${canal(r)}${canal(g)}${canal(b)}`;
}

/** sRGB (com gama) → linear. Necessário antes de qualquer conta de cor. */
function paraLinear(c: number): number {
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

function paraSrgb(c: number): number {
  return c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
}

/** sRGB → OKLCH (via OKLab, matrizes de Björn Ottosson). */
export function rgbParaOklch(rgb: Rgb): Oklch {
  const r = paraLinear(rgb.r);
  const g = paraLinear(rgb.g);
  const b = paraLinear(rgb.b);

  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);

  const L = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s;
  const A = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s;
  const B = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s;

  const c = Math.sqrt(A * A + B * B);
  const h = c < 1e-7 ? 0 : ((Math.atan2(B, A) * 180) / Math.PI + 360) % 360;
  return { l: L, c, h };
}

/** OKLCH → sRGB. Pode sair fora do gamut — ver `ajustarParaGamut`. */
export function oklchParaRgb({ l: L, c, h }: Oklch): Rgb {
  const rad = (h * Math.PI) / 180;
  const A = c * Math.cos(rad);
  const B = c * Math.sin(rad);

  const l_ = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3;
  const m_ = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3;
  const s_ = (L - 0.0894841775 * A - 1.291485548 * B) ** 3;

  return {
    r: paraSrgb(4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_),
    g: paraSrgb(-1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_),
    b: paraSrgb(-0.0041960863 * l_ - 0.7034186147 * m_ + 1.707614701 * s_),
  };
}

const dentroDoGamut = ({ r, g, b }: Rgb): boolean =>
  [r, g, b].every((v) => v >= -1e-4 && v <= 1 + 1e-4);

/**
 * Reduz a saturação até a cor caber no sRGB, preservando luminosidade e matiz.
 *
 * Sem isto, um verde muito saturado numa luminosidade alta "estoura" e volta com
 * canais fora de 0..1, que o arredondamento corta — mudando a cor de forma
 * imprevisível e, o que importa aqui, mudando o contraste que já tínhamos
 * calculado.
 */
export function ajustarParaGamut(cor: Oklch): Rgb {
  if (dentroDoGamut(oklchParaRgb(cor))) return oklchParaRgb(cor);

  let baixo = 0;
  let alto = cor.c;
  for (let i = 0; i < 24; i++) {
    const meio = (baixo + alto) / 2;
    if (dentroDoGamut(oklchParaRgb({ ...cor, c: meio }))) baixo = meio;
    else alto = meio;
  }
  return oklchParaRgb({ ...cor, c: baixo });
}

// ===========================================================================
// CONTRASTE (WCAG 2.1)
// ===========================================================================

function luminanciaRelativa({ r, g, b }: Rgb): number {
  return 0.2126 * paraLinear(r) + 0.7152 * paraLinear(g) + 0.0722 * paraLinear(b);
}

/** Razão de contraste entre duas cores: 1 (idênticas) a 21 (preto no branco). */
export function contraste(a: Rgb, b: Rgb): number {
  const la = luminanciaRelativa(a);
  const lb = luminanciaRelativa(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

/** Branco ou preto — o que for mais legível sobre `fundo`. */
export function textoSobre(fundo: Rgb): '#ffffff' | '#000000' {
  return contraste(fundo, BRANCO) >= contraste(fundo, { r: 0, g: 0, b: 0 })
    ? '#ffffff'
    : '#000000';
}

// ===========================================================================
// DERIVAÇÃO
// ===========================================================================

/**
 * Arredonda a cor para o que o hex de 8 bits consegue representar.
 *
 * Toda medição de contraste passa por aqui antes de decidir. Medir no espaço
 * contínuo e só depois arredondar produzia paleta que passava no cálculo e
 * reprovava na tela: a busca parava exatamente em 4,50:1 e o arredondamento
 * derrubava para 4,49:1. Verificar o valor que de fato vai ser usado é o que
 * torna a garantia exata em vez de aproximada.
 */
function quantizar(rgb: Rgb): Rgb {
  return hexParaRgb(rgbParaHex(rgb))!;
}

/**
 * Escurece a partir de `lInicial` até passar o contraste mínimo contra
 * `referencia`. Devolve a primeira luminosidade que serve, já quantizada.
 *
 * Percorre em passos pequenos em vez de busca binária porque a relação entre
 * luminosidade e contraste não é monotônica depois do ajuste de gamut — a
 * redução de saturação mexe no resultado.
 */
function escurecerAte(base: Oklch, lInicial: number, referencia: Rgb, minimo: number): Rgb {
  for (let l = lInicial; l >= 0.05; l -= 0.005) {
    const rgb = quantizar(ajustarParaGamut({ ...base, l }));
    if (contraste(rgb, referencia) >= minimo) return rgb;
  }
  // Piso teórico: preto puro contrasta 21:1 com branco, então não se chega aqui.
  return quantizar(ajustarParaGamut({ ...base, l: 0.05 }));
}

/** Luminosidade de partida do primário. Abaixo disso o botão compete com a
 *  sidebar preta; acima, quase nenhuma matiz sustenta texto branco. */
const L_PRIMARIA_INICIAL = 0.62;

/** Teto de saturação: acima disso a cor vira néon e cansa em área grande. */
const CROMA_MAXIMO = 0.26;

/**
 * Gera a paleta a partir da cor escolhida.
 *
 * Nunca falha: entrada inválida cai no padrão. É de propósito — cor não pode ser
 * motivo de tela quebrada.
 */
export function derivarPaleta(corEscolhida: string): Paleta {
  const semente = hexParaRgb(corEscolhida);

  // Sem cor escolhida, cor inválida ou a própria cor de fábrica: devolve os tons
  // literais do produto. Ver a nota em PALETA_PADRAO.
  if (!semente || rgbParaHex(semente) === COR_PADRAO) return { ...PALETA_PADRAO };

  const base = rgbParaOklch(semente);

  // Só matiz e saturação vêm da escolha; a luminosidade é nossa.
  const matiz: Oklch = { l: 0, c: Math.min(base.c, CROMA_MAXIMO), h: base.h };

  // O tom claro vem PRIMEIRO, e é ele que baliza a primária.
  //
  // A primária aparece como texto/ícone em dois fundos: o branco da tela e a
  // caixa clara. A caixa é levemente tingida, logo um pouco mais escura que o
  // branco — é o caso pior. Derivando-a antes e exigindo que a primária passe
  // contra ela, o branco fica satisfeito por consequência.
  //
  // Foi o que faltava na primeira versão: eu media contra o branco puro e o
  // resultado reprovava por centésimos justamente sobre a caixa clara.
  // L alta e croma baixo de propósito. A caixa clara é a restrição que APERTA a
  // primária — quanto mais escura ela for, mais escura a primária precisa ser
  // para se ler ali. Em 0.95 o vermelho puro saía em #bd4235, com 5,26:1 contra
  // o branco quando 4,5 bastava: escurecido além da conta, e o dono percebia como
  // "apagado". Subindo a caixa para perto do branco, a primária ganha vivacidade
  // sem que nenhum contraste caia abaixo do mínimo.
  const clara = quantizar(
    ajustarParaGamut({ l: 0.972, c: Math.min(matiz.c, 0.03), h: matiz.h }),
  );

  const primaria = escurecerAte(matiz, L_PRIMARIA_INICIAL, clara, CONTRASTE_MINIMO_TEXTO);

  // Secundária: apoio decorativo, um degrau mais clara que a primária. Exigência
  // menor (elemento de interface, não texto corrido).
  const secundaria = escurecerAte(
    matiz,
    Math.min(0.72, rgbParaOklch(primaria).l + 0.17),
    BRANCO,
    CONTRASTE_MINIMO_UI,
  );

  // Hover: um degrau mais escuro que a primária, mantendo texto branco legível.
  // Parte da luminosidade da primária menos um passo fixo, então a diferença é
  // perceptível em qualquer matiz (é o que o OKLCH garante).
  const hover = escurecerAte(
    matiz,
    Math.max(0.12, rgbParaOklch(primaria).l - 0.12),
    BRANCO,
    CONTRASTE_MINIMO_TEXTO,
  );

  return {
    'brand-primary': rgbParaHex(primaria),
    'brand-primary-hover': rgbParaHex(hover),
    'brand-primary-light': rgbParaHex(clara),
    'brand-secondary': rgbParaHex(secundaria),
  };
}
