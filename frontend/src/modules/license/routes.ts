import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/licenca-erro',
    name: 'licenca.erro',
    component: () => import('./views/LicenseErrorView.vue'),
    meta: {
      skipLicenseCheck: true,
    },
    props: (route) => ({
      codigo: (route.query.codigo as string) || '',
      mensagem: (route.query.mensagem as string) || '',
    }),
  },
  {
    /**
     * A parede da licença vencida — com a porta de pagamento ao lado.
     *
     * `requiresAuth` porque a cobrança é do dono da licença: só faz sentido
     * depois de o sistema saber quem está na frente da tela.
     *
     * `skipLicenseCheck` fica FALSO de propósito. É justamente aqui que a
     * verificação precisa continuar rodando: é ela que percebe que a licença
     * voltou a valer e libera o sistema sozinho, sem reiniciar nada.
     */
    path: '/renovar-assinatura',
    name: 'licenca.renovar',
    component: () => import('./views/RenovarAssinaturaView.vue'),
    meta: {
      requiresAuth: true,
    },
  },
];

export default routes;
