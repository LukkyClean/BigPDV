# Visão Geral: da fotografia para a direção

**Status:** plano, nada implementado. Escrito em 29/08/2026.

## A pergunta que a tela precisa responder

Hoje a Visão Geral responde *"como foi este mês"*. O dono precisa dela para responder
outra coisa:

> "Minhas vendas estão caindo e a oficina está segurando o mês. Isso é normal ou eu
> tenho um problema chegando?"

O sistema não consegue responder isso hoje, e a razão é estrutural: **ele soma venda e OS
num número só e esquece o mês passado**. Não existe série histórica por origem em lugar
nenhum da tela — o `TendenciaChart` do dashboard mostra faturamento por DIA do período
corrente, e some quando o mês vira.

Tudo que construímos até aqui olha para **estado**: "está vencido", "o dinheiro acaba dia
12", "falta categoria". Nada olha para **direção**.

---

## O que o mercado faz

Pesquisado em 29/08/2026.

### 1. MAT / TTM — soma móvel de 12 meses

O [Business Central tem relatório nativo de Moving Annual
Total](https://learn.microsoft.com/en-us/dynamics365/business-central/sales-powerbi-moving-annual-total):
a soma dos últimos 12 meses, recalculada a cada mês (entra o novo, sai o mais antigo).

**Por que é a melhor técnica:** ela mata a sazonalidade. Uma oficina vende menos em
janeiro todo ano; comparar janeiro com dezembro sempre dá "queda", e o dono aprende a
ignorar. O MAT sobe ou desce só quando o negócio muda de verdade. A recomendação clássica
é ter, ao lado de cada gráfico mensal, [a versão dos últimos doze
meses](https://www.growthforce.com/blog/the-value-of-trailing-twelve-months-charts).

### 2. Comparação com o MESMO mês do ano anterior (YoY)

Padrão em todos. Pelo mesmo motivo do item anterior: mês contra mês anterior é volátil e
confunde sazonalidade com tendência.

### 3. Poucos KPIs

Consenso na literatura de painel para PME: [acima de 10-12 indicadores o painel deixa de
gerar decisão](https://tcadvisorscpa.com/kpi-dashboard-small-business/). Os cinco núcleos
recomendados: receita, margem bruta, margem líquida, fluxo de caixa operacional e **DSO**
(prazo médio de recebimento).

### 4. Benchmark com o setor — o estado da arte

O [Xero lançou Industry Benchmarks em jun/2026](https://www.xero.com/us/media-releases/xero-introduces-industry-benchmarking-intelligence-for-small-businesses/):
nove drivers de saúde (receita, lucratividade, gestão de caixa, incluindo Debtor Days),
comparados com a mediana do setor e do país, e **rotulados** como à frente / na média /
atrás dos pares.

O insight não é o benchmark em si — é o **rótulo**. "R$ 8.400 de receita" não decide nada.
"Sua margem está atrás de 70% das oficinas do seu porte" decide.

### 5. Previsão

[Xero projeta 90 dias](https://www.xero.com/us/accounting-software/analytics/cash-flow/)
(cenários longos só no plano pago). O [Business Central usa Azure AI para prever
vendas](https://learn.microsoft.com/en-us/dynamics365/business-central/ui-extensions-sales-forecast),
**sobre o histórico de vendas** — sem série longa, não há previsão.

### O que NÃO copiar

- **Previsão por ML.** Precisa de série longa que nenhuma loja nossa tem, e o ganho sobre
  média móvel, numa loja de bairro, é ruído. Além disso, previsão que erra sem explicar
  destrói confiança mais rápido do que ausência de previsão.
- **Benchmark de setor, por enquanto.** Exige dados de várias lojas num lugar só. O ERP é
  local e offline por desenho; isso é assunto da plataforma, não do ERP, e envolve
  consentimento. Fica registrado como visão, não como fase.
- **Dashboard com 15 indicadores.** A tentação óbvia, e o jeito mais rápido de o dono
  parar de olhar.

---

## A restrição que decide tudo: não temos histórico

| Base | Histórico hoje |
|---|---|
| Banco de dev | 1 mês (ago/2026, 3 vendas) |
| Lojas em produção | Rodam esta linhagem desde **13/08/2026** |

**MAT precisa de 12 meses. YoY precisa de 13.** A melhor técnica do mercado é, hoje,
inaplicável — e vai ficando aplicável sozinha, mês a mês, sem ninguém fazer nada.

Isso não é motivo para não construir. É motivo para o sistema **saber o que ainda não pode
dizer**. É a decisão central deste plano:

> **PORTÃO DE HISTÓRICO.** Cada métrica declara quantos meses fechados exige. Abaixo
> disso, ela não aparece torta nem aparece vazia: aparece dizendo o que falta.
> *"Comparação disponível a partir de outubro — faltam 2 meses de histórico."*
>
> Um painel que projeta 12 meses a partir de 2 está inventando, e o dono decide em cima.
> Dois pontos fazem qualquer reta.

---

## As métricas escolhidas

Poucas, e cada uma responde uma pergunta que o dono realmente faz.

| Métrica | Pergunta | Portão |
|---|---|---|
| **Receita por origem** (venda × OS × outros) | "de onde vem meu dinheiro?" | 1 mês |
| **Variação vs. mês anterior**, por origem | "o que mudou?" | 2 meses |
| **Média dos últimos 3 meses**, por origem | "o mês foi fora da curva?" | 3 meses |
| **Concentração de receita** | "dependo de uma perna só?" | 1 mês |
| **DSO — prazo médio de recebimento** | "meu dinheiro está demorando mais a entrar?" | 2 meses |
| **Despesa fixa × receita** | "meu custo está subindo mais rápido que a venda?" | 3 meses |
| **MAT (12 meses móveis)**, por origem | "qual é a tendência REAL?" | 12 meses |
| **Comparação YoY** | "cresci de verdade ou é sazonalidade?" | 13 meses |

Repare que as quatro primeiras já funcionam em outubro/2026, e as duas últimas entram
sozinhas em agosto/2027.

---

## Fases

### Fase 1 — A série existe (base de tudo)

Sem isto nada mais é possível: hoje não há como perguntar "quanto foi a receita de julho
por origem" sem varrer as tabelas na mão.

- Endpoint `GET /financeiro/serie?meses=12` devolvendo, por mês fechado: receita por
  origem (venda, OS), despesa paga, resultado, e o que entrou de fato (livro).
- Reusa as MESMAS fontes da Visão Geral (`dashboard_crud.get_stats_agregados` e o livro),
  para não nascer um segundo número para o mesmo mês.
- `meses_disponiveis` na resposta: é o que alimenta os portões.
- **Sem migration.** Tudo já está nas tabelas.

### Fase 2 — A tela mostra direção

- Card "Faturado" ganha a quebra por origem, com a variação de cada uma.
- Um gráfico de barras por mês (6 meses), empilhado por origem — venda × OS.
- Cada número comparado ganha rótulo, não só seta: *"acima da sua média"*, *"na média"*,
  *"abaixo"*. É o insight do Xero aplicado sem benchmark de setor: **o par de comparação é
  a própria loja no passado**.
- Portões visíveis: onde falta histórico, a tela diz o que falta e quando estará pronto.

### Fase 3 — Alertas de tendência no painel

Entram no painel de atenção que já existe, com a mesma regra de limiar derivado do porte
(nada de valor digitado) e o mesmo "Adiar".

| Alerta | Regra proposta | Portão |
|---|---|---|
| `RECEITA_CAINDO` | 3 meses seguidos de queda na receita total | 4 meses |
| `ORIGEM_CAINDO` | uma origem caiu ≥30% contra a média de 3 meses | 4 meses |
| `DEPENDENCIA_DE_ORIGEM` | uma origem passou de 80% da receita | 3 meses |
| `CUSTO_SUBINDO_MAIS` | despesa cresce ≥2× mais rápido que a receita, 3 meses | 4 meses |
| `RECEBIMENTO_LENTO` | DSO subiu ≥50% contra a média | 3 meses |

Todos com ação e destino, como os sete atuais. Nenhum deles é "IA": são regras com limiar
escrito e defensável.

### Fase 4 — Projeção do ano (a mais arriscada)

- Média móvel de 3 meses + o que já está lançado (recorrentes e parcelas do Fluxo de
  Caixa) projetados 12 meses.
- **Faixa, nunca número seco:** "entre R$ 82 mil e R$ 104 mil". Número seco vira promessa.
- Portão de 6 meses, e o texto diz em cima de quantos meses a curva foi feita.
- Recalcula MAT quando houver 12 meses, e aí a projeção passa a nascer dele.

---

## Riscos

1. **A tela inchar.** Cada fase acrescenta conteúdo à Visão Geral, que hoje já tem painel
   de atenção + 3 cards + 4 cards + 2 blocos. A Fase 2 provavelmente exige repensar o
   layout, não só empilhar mais um bloco.
2. **Alerta de tendência é mais fácil de errar** que alerta de estado. "Vencido" é um
   fato; "caindo" é uma leitura. Limiar frouxo vira alarme falso, e o painel morre.
3. **Meses parciais.** O mês corrente NÃO entra em média nem em tendência — comparar 8
   dias com um mês fechado acusaria queda todo início de mês. Só meses fechados.
4. **Loja que ficou fechada** (férias, reforma) vira "queda" sem ser. Não há solução
   automática boa; o "Adiar" do painel é a válvula.

---

## Decisões que precisam do dono antes de codar

1. **Onde a série aparece:** dentro da Visão Geral (mais um bloco) ou numa aba/tela
   própria de "Tendência"? A Visão Geral já está cheia.
2. **Fase 4 entra?** É a que mais pode errar e a que mais impressiona numa demonstração.
3. **Quebra por origem:** venda × OS basta, ou separar produto × serviço dentro da OS?
   (A segunda é mais útil para oficina e mais cara de calcular.)
4. **`FINANCEIRO` ou `FINANCEIRO_PRO`?** Comparação simples parece base; projeção e MAT
   parecem PRO.

---

## Como provar cada fase

Mesma disciplina do resto do módulo:

- Série com meses faltando no meio (loja parada em julho) devolve zero, não buraco.
- Mês corrente nunca entra na média.
- Portão: com 2 meses de histórico, a comparação de 3 meses não aparece — e a tela diz
  por quê.
- Cada alerta de tendência com um teste do limiar exato, incluindo o caso que NÃO deve
  disparar.
- O número da série tem que bater com o `faturamento` da Visão Geral do mesmo mês. Se
  divergir, existem dois números para o mesmo mês e o módulo perdeu a confiança.
