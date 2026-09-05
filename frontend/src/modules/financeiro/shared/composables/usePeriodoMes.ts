import { computed, ref } from 'vue';

/**
 * Navegação por MÊS, que é a unidade do financeiro.
 *
 * Diferente do `usePeriodo` dos Relatórios de propósito: lá os presets são
 * "hoje / ontem / 7 dias", porque a pergunta é sobre movimento recente. Aqui a
 * pergunta é sempre sobre um mês fechado — aluguel, folha e fornecedor têm
 * ciclo mensal, e "últimos 7 dias" não responde nada sobre eles.
 */

/** Formata como YYYY-MM-DD no fuso LOCAL — o dia que o lojista vê no calendário. */
function isoLocal(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dia = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${dia}`;
}

/**
 * `mesInicial` no formato YYYY-MM. Existe para o clique num card da Visão Geral
 * abrir a outra tela NO MESMO MÊS que o dono estava olhando -- sem isto ele
 * conferia agosto, clicava em "Entrou" e caía em setembro, com outros números.
 * Valor ausente ou inválido cai no mês atual, que é o padrão de sempre.
 */
export function usePeriodoMes(mesInicial?: string) {
  const hoje = new Date();
  const casa = /^(\d{4})-(\d{2})/.exec(mesInicial ?? '');
  const ano = ref(casa ? Number(casa[1]) : hoje.getFullYear());
  const mes = ref(casa ? Number(casa[2]) - 1 : hoje.getMonth()); // 0-11

  // Dia 0 do mês SEGUINTE é o último dia deste — a única forma que não erra em
  // fevereiro nem em ano bissexto.
  const range = computed(() => ({
    inicio: isoLocal(new Date(ano.value, mes.value, 1)),
    fim: isoLocal(new Date(ano.value, mes.value + 1, 0)),
  }));

  const rotulo = computed(() =>
    new Date(ano.value, mes.value, 1)
      .toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
      .replace(/^\w/, (c) => c.toUpperCase()),
  );

  const ehMesAtual = computed(
    () => ano.value === hoje.getFullYear() && mes.value === hoje.getMonth(),
  );

  function mover(passo: number) {
    const d = new Date(ano.value, mes.value + passo, 1);
    ano.value = d.getFullYear();
    mes.value = d.getMonth();
  }

  return { ano, mes, range, rotulo, ehMesAtual, anterior: () => mover(-1), proximo: () => mover(1) };
}
