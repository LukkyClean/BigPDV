/**
 * @fileoverview Aplica a paleta na página, sobrescrevendo os tokens do tema.
 *
 * O `global.css` declara os tokens no `@theme`, e o Tailwind v4 os emite como
 * custom properties no `:root`. Escrever as mesmas propriedades no
 * `documentElement` vence por especificidade, então as ~600 classes
 * `bg-brand-primary` espalhadas pelo sistema mudam de cor sem que nenhum
 * componente saiba que existe tema.
 *
 * `brand-action` (o preto da sidebar), `brand-grey` e `brand-off-white` (o fundo)
 * NÃO são tocados aqui, por contrato: é o que mantém o logo legível sobre a
 * sidebar e o texto de leitura escuro sobre fundo claro, aconteça o que acontecer
 * com a cor escolhida.
 */

import { derivarPaleta, type Paleta } from './paleta';

/** Guarda a cor escolhida para o boot seguinte, inclusive na tela de login —
 *  que roda antes de haver token para consultar o servidor. */
const CHAVE_LOCAL = 'tema_cor';

function escrever(paleta: Paleta): void {
  const raiz = document.documentElement;
  for (const [token, valor] of Object.entries(paleta)) {
    raiz.style.setProperty(`--color-${token}`, valor);
  }
}

/** Deriva e aplica. Chamar com a cor escolhida pelo dono. */
export function aplicarCor(cor: string): Paleta {
  const paleta = derivarPaleta(cor);
  escrever(paleta);
  return paleta;
}

/**
 * Volta aos tokens do `global.css` removendo as sobrescritas.
 *
 * Remove em vez de escrever os valores de fábrica: assim a folha de estilo volta
 * a ser a única fonte da verdade, e um ajuste futuro no `global.css` não fica
 * mascarado por um valor antigo grudado no elemento.
 */
export function limparPaleta(): void {
  const raiz = document.documentElement;
  for (const token of ['brand-primary', 'brand-primary-hover', 'brand-primary-light', 'brand-secondary']) {
    raiz.style.removeProperty(`--color-${token}`);
  }
}

/** Cor guardada neste terminal, se houver. */
export function corSalvaLocalmente(): string | null {
  try {
    return localStorage.getItem(CHAVE_LOCAL);
  } catch {
    return null; // modo restrito / storage indisponível: tema é opcional, segue sem
  }
}

export function guardarCorLocalmente(cor: string | null): void {
  try {
    if (cor) localStorage.setItem(CHAVE_LOCAL, cor);
    else localStorage.removeItem(CHAVE_LOCAL);
  } catch {
    /* idem: nunca deixar o tema derrubar o boot */
  }
}

/**
 * Aplica no boot o que este terminal viu por último — antes de qualquer requisição.
 *
 * Sem isso a tela de login abriria no azul e piscaria para a cor da empresa quando
 * o servidor respondesse. Nunca bloqueia: sem cor guardada, o `global.css` já
 * cuida do padrão.
 */
export function aplicarTemaSalvo(): void {
  const cor = corSalvaLocalmente();
  if (cor) aplicarCor(cor);
}

/**
 * Busca a cor no servidor e corrige o que este terminal aplicou de cache.
 *
 * Fire-and-forget de propósito: a cor NUNCA pode atrasar nem derrubar o boot. Se
 * o backend estiver fora, a tela abre com a última cor conhecida (ou no azul) e
 * o erro de conexão segue seu curso normal.
 *
 * É isto que faz "já se ajusta nos terminais": o servidor é a única fonte da
 * verdade, e cada caixa se alinha na abertura seguinte, sem configurar nada.
 *
 * A rota é pública porque a tela de login precisa dela antes de existir token.
 */
export async function sincronizarTemaDoServidor(): Promise<void> {
  try {
    const { default: api } = await import('@/api/axios');
    const { data } = await api.get<{ cor_tema: string | null }>('empresas/tema');
    const cor = data?.cor_tema ?? null;

    if (cor) {
      aplicarCor(cor);
      guardarCorLocalmente(cor);
    } else {
      limparPaleta();
      guardarCorLocalmente(null);
    }
  } catch {
    /* servidor fora ou ainda sem empresa: fica no cache/padrão */
  }
}
