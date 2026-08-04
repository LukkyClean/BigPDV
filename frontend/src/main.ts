import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import { createPinia } from 'pinia';
import { VueQueryPlugin } from '@tanstack/vue-query';
import { vueQueryOptions } from './core/config/vueQueryConfig';
import { vMaska } from 'maska/vue';

import { initBackendUrl } from '@/api/backendUrl';
import { aplicarTemaSalvo, sincronizarTemaDoServidor } from '@/shared/theme/aplicar';

import '@/shared/assets/styles/global.css';
import 'vue-sonner/style.css';

async function startApp() {
  await initBackendUrl();

  // Cor conhecida deste terminal, aplicada ANTES de montar: sem isto a tela de
  // login abriria no azul e piscaria para a cor da empresa quando o servidor
  // respondesse. É síncrono e local — não espera rede.
  aplicarTemaSalvo();

  const app = createApp(App);
  const pinia = createPinia();
  app.use(pinia);
  app.use(router);
  app.use(VueQueryPlugin, vueQueryOptions);
  app.directive('maska', vMaska);
  app.mount('#app');

  // Depois de montar, alinha com o servidor. Fire-and-forget: a tela já está de
  // pé, e cor nunca pode ser motivo de espera.
  void sincronizarTemaDoServidor();
}

startApp();
