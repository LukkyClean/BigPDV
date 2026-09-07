/**
 * @fileoverview Recursos habilitados pelo plano contratado.
 *
 * A origem do dado é o BACKEND: `GET /licenca/status.recursos`, que sai de
 * `app/services/plano.py`. Até 05/09/2026 isto aqui era uma constante local
 * fixa em `nfe: true` — ou seja, o "gate" nunca barrou nada e o plano era uma
 * ficção do frontend.
 *
 * O QUE ESTE ARQUIVO É E O QUE NÃO É
 * ----------------------------------
 * É UX: decide o que MOSTRAR. Não é segurança, e não deve ser tratado como
 * tal. Quem recusa uma ação é o backend (`requer_modulo_fiscal`), e quem
 * recusa uma emissão em definitivo é a API remota da StartBig, que valida o
 * plano fora da máquina do cliente.
 *
 * POR QUE CONTINUA SÍNCRONO
 * -------------------------
 * `recursoDisponivel()` é chamado no setup de ~15 componentes (sidebar, PDV,
 * produtos, serviços, OS, empresa) e no guard de rota. Torná-lo assíncrono
 * obrigaria a mexer em todos eles. Lendo de um store já hidratado, a
 * assinatura fica igual e nenhum consumidor precisou mudar.
 */

import { usePlanoStore } from '@/shared/stores/plano.store';

type Recursos = {
  /** Emissão de notas fiscais (NF-e/NFC-e/NFS-e) e configurações fiscais. */
  nfe: boolean;
};

export type Recurso = keyof Recursos;

/**
 * True se o recurso está incluído no plano contratado.
 *
 * Ausente = indisponível. Enquanto a primeira resposta do backend não chega,
 * responde `false` de propósito: mostrar o módulo e escondê-lo meio segundo
 * depois é pior do que revelá-lo quando a resposta chega.
 */
export function recursoDisponivel(recurso: Recurso): boolean {
  return usePlanoStore().recursos[recurso] ?? false;
}

/**
 * QUANDO O VALOR JÁ ESTÁ PRONTO
 * -----------------------------
 * Os consumidores fazem `const nfeDisponivel = recursoDisponivel('nfe')` no
 * setup, capturando um booleano. Isso é correto porque a ETAPA 1 do
 * `router.beforeEach` AGUARDA `verificarLicenca()` e hidrata o store antes de
 * liberar a navegação — nenhum componente de rota monta com o store vazio.
 *
 * A consequência: o valor não reage a uma mudança no meio da sessão (ativar o
 * módulo pelo `POST /fiscal/ativar`, por exemplo). Ele se acerta na próxima
 * verificação de licença, que roda a cada 5 minutos, ou num reload.
 *
 * Se algum lugar precisar reagir na hora, use
 * `computed(() => recursoDisponivel('nfe'))` em vez de uma const — a função lê
 * do store, então dentro de um computed ela é reativa de graça.
 */
