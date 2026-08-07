import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

/**
 * O motor de paleta vem do app principal, por referência e não por cópia.
 *
 * `paleta.ts` não importa nada — é matemática de cor pura — então atravessa a
 * fronteira dos dois projetos sem arrastar dependência. E é ele que garante que
 * texto branco sobre a cor escolhida continue legível, com o `check:paleta` do
 * build do frontend varrendo 7216 cores para provar isso.
 *
 * Copiar as 284 linhas para cá criaria uma segunda verdade que nenhuma guarda
 * cobre — e paleta divergente é exatamente o tipo de coisa que só aparece
 * quando um cliente escolhe amarelo.
 */
const PALETA = fileURLToPath(new URL('../../frontend/src/shared/theme/paleta.ts', import.meta.url))
const FRONTEND = fileURLToPath(new URL('../../frontend', import.meta.url))

export default defineConfig({
  plugins: [vue()],
  base: '/form/',
  resolve: {
    alias: { '@paleta': PALETA },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 5174,
    // Sem isto o dev server recusa servir o arquivo de fora da raiz do projeto.
    fs: { allow: ['..', FRONTEND] },
  },
})
