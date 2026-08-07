/**
 * @fileoverview Veste a página do celular com a identidade da loja.
 *
 * Esta página é um app à parte: build próprio, Tailwind próprio, e o `@theme` do
 * `main.css` traz a cor de fábrica chumbada. Era por isso que ela abria azul por
 * mais que o dono trocasse a cor do sistema — ela simplesmente não sabia que
 * existe tema.
 *
 * A cor chega junto com os dados do checklist, na mesma requisição que a página
 * já fazia. Escrever as custom properties no `documentElement` vence o `@theme`
 * por especificidade, então as 19 classes `bg-brand-primary` espalhadas pelos
 * componentes mudam de cor sem que nenhum deles saiba disso.
 *
 * `brand-action`, `brand-grey` e `brand-off-white` NÃO são tocados — mesmo
 * contrato do app principal: são o preto do texto e o fundo claro, e precisam
 * continuar legíveis venha a cor que vier.
 */
import { derivarPaleta } from '@paleta'

/**
 * Base do backend. A página é servida pelo próprio backend em produção, então
 * `origin` já é o endereço certo; em desenvolvimento ela roda no Vite, numa
 * porta diferente. Mesma regra do `api/axios.ts`, ao lado.
 */
function baseDoBackend(): string {
  return import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin
}

/** Caminho salvo no banco → URL que o celular consegue abrir. */
export function urlDaLogo(caminho: string | null | undefined): string | null {
  if (!caminho) return null
  if (caminho.startsWith('http')) return caminho
  return `${baseDoBackend()}/static/${caminho.replace(/^static\//, '')}`
}

/**
 * Aplica a cor da loja. Sem cor cadastrada, não faz nada: o `@theme` do
 * `main.css` já é o padrão de fábrica, e sobrescrever com o mesmo valor só
 * criaria uma segunda fonte da verdade.
 */
export function aplicarCorDaEmpresa(cor: string | null | undefined): void {
  if (!cor) return

  const paleta = derivarPaleta(cor)
  for (const [token, valor] of Object.entries(paleta)) {
    document.documentElement.style.setProperty(`--color-${token}`, valor)
  }
}
