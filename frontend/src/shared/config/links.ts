/**
 * @fileoverview Links oficiais da StartBig.
 *
 * Fonte única. Estes endereços estavam duplicados em `SettingsMenu.vue` e
 * `Suporte.vue`, com a URL de compra ainda como placeholder numa terceira
 * cópia (`LicencaStatusBadge.vue`) — trocar o número do WhatsApp exigia achar
 * todos os pontos, e um deles ia ficar para trás.
 *
 * Não confundir com `config/planos.ts`: aquele diz QUAIS RECURSOS o plano
 * contratado libera; este diz PARA ONDE mandar o cliente.
 */

/** Mensagem pré-preenchida do suporte, já codificada para a URL do wa.me. */
const WHATSAPP_SUPORTE =
  'https://wa.me/5588996971128?text=Ol%C3%A1!%20Obrigado%20por%20entrar%20em%20contato%20com%20o%20suporte%20do%20StartBig.%20%F0%9F%91%8B%0A%0APara%20que%20eu%20possa%20direcionar%20sua%20solicita%C3%A7%C3%A3o%20o%20mais%20r%C3%A1pido%20poss%C3%ADvel%2C%20por%20favor%2C%20digite%20o%20n%C3%BAmero%20da%20op%C3%A7%C3%A3o%20que%20melhor%20descreve%20o%20que%20voc%C3%AA%20precisa%3A%0A%0A1%EF%B8%8F%E2%83%A3%20-%20D%C3%BAvidas%20sobre%20o%20sistema%20(Como%20usar)%0A2%EF%B8%8F%E2%83%A3%20-%20Relatar%20um%20erro%20ou%20instabilidade%0A3%EF%B8%8F%E2%83%A3%20-%20Sugest%C3%A3o%20de%20nova%20funcionalidade%0A4%EF%B8%8F%E2%83%A3%20-%20Assuntos%20financeiros%20%2F%20Mensalidade%0A%0APor%20favor%2C%20digite%20tamb%C3%A9m%20o%20seu%20nome%20e%20empresa.%20J%C3%A1%20volto%20para%20te%20atender';

export const LINKS = {
  /** Site institucional. */
  site: 'https://startbig.com.br',
  /** Página de planos — destino de todo aviso de licença vencendo ou vencida. */
  planos: 'https://startbig.com.br/#planos',
  /** Suporte no WhatsApp, com o menu de atendimento já no corpo da mensagem. */
  whatsapp: WHATSAPP_SUPORTE,
  /** Canal de tutoriais. */
  youtube: 'https://www.youtube.com/@StartBigOficial',
} as const;

export type LinkOficial = keyof typeof LINKS;
