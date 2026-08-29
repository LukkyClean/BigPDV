# Diagnóstico: o consultor dentro do sistema

**Status:** plano fechado com o dono em 29/08/2026. **Nada implementado.**

## O objetivo, na palavra do dono

> "Montar um ambiente de apoio administrativo da empresa, para o dono não precisar pagar
> uma auditoria externa a não ser que precise muito."

Não é relatório mais bonito. É o **papel que um consultor externo cumpre**: olhar os
números e dizer *"seu custo fixo subiu 20% e a receita subiu 4%"*, *"você depende demais
de uma perna só"*, *"seu dinheiro está demorando mais a entrar que no trimestre passado"*.
O dono paga caro por isso e, na prática, só chama quando o problema já aconteceu.

Três consequências que atravessam todo o resto deste documento:

1. **Todo número tem que ser explicável e rastreável.** Auditoria não aceita "o sistema
   disse". Cada afirmação abre na conta que a gerou. É por isso que o Extrato e a trilha
   vieram antes, e por que o alerta já cai na lista filtrada.
2. **Conservador vale mais que impressionante.** Parecer errado com ar de certeza é pior
   que a ausência do parecer — o dono decide em cima dele.
3. **Linguagem de dono, não de contador.** "Sobrou", "o dinheiro acaba dia 12", "está na
   rua". Nunca DRE, EBITDA ou ciclo financeiro.

---

## Decisões tomadas com o dono

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Onde mora | **Tela própria**, item novo no submenu — igual foi feito com o Extrato |
| 2 | Projeção do ano entra? | **Sim**, com a inteligência de não mostrar quando não há histórico |
| 3 | Quebra venda × OS | **Resolver de forma segura para todos os segmentos** (ver abaixo) |
| 4 | Base ou PRO | **`FINANCEIRO_PRO`** (justificativa abaixo) |

### Sobre a #4 — por que PRO

A trava de licença separa o que a loja contratou. Hoje: registrar e controlar é
`FINANCEIRO` (Contas a Pagar/Receber, Visão Geral, Extrato, Plano de Contas); projetar e
conciliar é `FINANCEIRO_PRO` (Fluxo de Caixa, Conciliação).

O Diagnóstico é exatamente o produto que substitui a consultoria — é o mais premium do
módulo. Fica **`FINANCEIRO_PRO`**, junto com o Fluxo de Caixa, e a linha comercial fica
limpa de explicar:

> **base** = o sistema guarda e controla o seu dinheiro.
> **pro** = o sistema te avisa e te aconselha.

Os alertas de tendência (Fase 3) nascem no painel da Visão Geral, que é base — então
seguem a mesma mecânica já usada no `CAIXA_NEGATIVO`: o endpoint do resumo checa a licença
e só monta o alerta se houver PRO. Lista de módulos vazia libera, como em todo o resto.

### Sobre a #3 — a quebra que não quebra nenhum segmento

**A regra da casa:** pasta é por domínio, nunca por segmento; segmento novo só acrescenta
declaração, e se exigir Vue é falta de metadado.

Aplicada aqui, isso significa: **o frontend não pode conhecer "venda" nem "OS"**. Se a
tela tiver `v-if segmento === 'pdv'`, já nasceu errada — e a serigrafia, a marcenaria e o
que vier depois vão quebrar uma a uma.

**O desenho:** o backend devolve as origens como DADO, em lista, e a tela desenha o que
vier.

```
origens: [
  { chave: "VENDA", rotulo: "Vendas",  total: 210000 },
  { chave: "ORDEM_SERVICO", rotulo: "Serviços", total: 630000 }
]
```

Regras do backend ao montar essa lista:

- Uma origem que **não existe para a loja** não entra. Loja PDV (`usa_ordem_servico:
  False` no registry) recebe uma origem só, e o gráfico nasce com uma perna — não com uma
  perna vazia.
- Uma origem **sem nenhum movimento no período todo** também não entra: linha reta no zero
  polui o gráfico e não informa nada.
- O **rótulo vem do backend**, não de um dicionário no Vue. É o que permite a oficina ler
  "Serviços" e outro segmento ler outra coisa, por declaração.
- Origem nova (locação, assinatura, o que vier) é **uma declaração no backend** e aparece
  sozinha na tela.

**A quebra por natureza (produto × serviço) fica de fora desta rodada.** Ela é mais útil
para oficina — separa peça de mão de obra — mas exige somar item a item de venda e de OS,
com regras próprias de desconto e de item de garantia. É acréscimo natural depois que a
série existir, pelo mesmo caminho: mais uma origem declarada, nenhuma mudança de tela.

---

## O que o mercado faz (pesquisa de 29/08/2026)

### MAT / TTM — soma móvel de 12 meses

O [Business Central tem relatório nativo](https://learn.microsoft.com/en-us/dynamics365/business-central/sales-powerbi-moving-annual-total):
soma dos últimos 12 meses, recalculada a cada mês. **Mata a sazonalidade** — uma oficina
vende menos em janeiro todo ano, e comparar janeiro com dezembro sempre acusa queda. A
recomendação clássica é ter, ao lado de cada gráfico mensal, [a versão dos últimos doze
meses](https://www.growthforce.com/blog/the-value-of-trailing-twelve-months-charts).

### Comparar com o MESMO mês do ano anterior (YoY)

Padrão em todos, e pelo mesmo motivo: mês contra mês anterior confunde sazonalidade com
tendência.

### Poucos indicadores

[Acima de 10-12, o painel deixa de gerar
decisão](https://tcadvisorscpa.com/kpi-dashboard-small-business/). Os cinco núcleos:
receita, margem bruta, margem líquida, fluxo de caixa operacional e **DSO** (prazo médio
de recebimento).

### Rótulo, não número — o estado da arte

O [Xero lançou Industry Benchmarks em
jun/2026](https://www.xero.com/us/media-releases/xero-introduces-industry-benchmarking-intelligence-for-small-businesses/):
nove drivers de saúde comparados com a mediana do setor, **rotulados** como à frente / na
média / atrás dos pares.

O insight aproveitável não é o benchmark — é o rótulo. "R$ 8.400" não decide nada; *"abaixo
da sua média"* decide. **Nosso par de comparação é a própria loja no passado.**

### O que NÃO copiar

- **Previsão por ML.** Precisa de série longa que nenhuma loja nossa tem, e o ganho sobre
  média móvel numa loja de bairro é ruído. Previsão que erra sem explicar destrói
  confiança mais rápido que a ausência de previsão.
- **Benchmark de setor.** Exige dados de várias lojas num lugar só; o ERP é local e
  offline por desenho. É assunto da plataforma, envolve consentimento, e fica registrado
  como visão — não como fase.
- **Painel com 15 indicadores.** A tentação óbvia e o jeito mais rápido de o dono parar de
  olhar.

---

## A restrição que decide tudo: não temos histórico

| Base | Histórico hoje |
|---|---|
| Banco de dev | 1 mês (ago/2026, 3 vendas) |
| Lojas em produção | Esta linhagem roda desde **13/08/2026** |

MAT precisa de 12 meses. YoY precisa de 13. **A melhor técnica do mercado é inaplicável
hoje** — e vai ficando aplicável sozinha, mês a mês, sem ninguém fazer nada.

> **PORTÃO DE HISTÓRICO** — a decisão central deste plano.
>
> Cada métrica declara quantos **meses fechados** exige. Abaixo disso ela não aparece
> torta nem aparece vazia: aparece dizendo o que falta e quando vai existir.
>
> *"Comparação com a sua média chega em outubro — faltam 2 meses de histórico."*
>
> Dois pontos fazem qualquer reta. Um sistema que projeta 12 meses a partir de 2 está
> inventando, e o dono decide em cima.

O **mês corrente nunca entra** em média, tendência ou projeção: comparar 8 dias com um mês
fechado acusaria queda todo início de mês.

### O que aparece, e quando

| Métrica | Pergunta do dono | Portão | Disponível em |
|---|---|---|---|
| Receita por origem | "de onde vem meu dinheiro?" | 1 mês fechado | set/2026 |
| Concentração de origem | "dependo de uma perna só?" | 1 mês | set/2026 |
| Variação vs. mês anterior | "o que mudou?" | 2 meses | out/2026 |
| DSO (prazo de recebimento) | "meu dinheiro está demorando mais?" | 2 meses | out/2026 |
| Média dos últimos 3 meses | "este mês foi fora da curva?" | 3 meses | nov/2026 |
| Despesa fixa × receita | "meu custo sobe mais rápido que a venda?" | 3 meses | nov/2026 |
| **Projeção de 12 meses** | "onde isso vai dar?" | **6 meses** | fev/2027 |
| MAT (12 meses móveis) | "qual é a tendência real?" | 12 meses | ago/2027 |
| Comparação YoY | "cresci ou foi sazonalidade?" | 13 meses | set/2027 |

---

## Fases

### Fase 1 — A série existe

Sem isto nada mais é possível: hoje não há como perguntar "quanto foi a receita de julho
por origem" sem varrer tabela na mão.

**Backend**
- `GET /financeiro/serie?meses=12` → por mês FECHADO: origens (lista, como acima), despesa
  paga, resultado, e o que entrou de fato pelo livro.
- `meses_disponiveis` na resposta — é o que alimenta todos os portões da tela.
- Reusa as MESMAS fontes da Visão Geral (`dashboard_crud.get_stats_agregados` e o livro).
  Se a série discordar do card do mesmo mês, existem dois números para o mesmo mês e o
  módulo perde a confiança.
- Origens montadas pelo registry de segmento (`segmento_usa_ordem_servico`), nunca por
  lista fixa.

**Sem migration.** Todo o dado já está nas tabelas.

**Provas:** mês sem movimento devolve zero e não some da série; mês corrente fora; loja
PDV devolve uma origem só; o total do mês bate com o `faturamento` do resumo.

### Fase 2 — A tela

**Novo item de submenu, `FINANCEIRO_PRO`.** Nome proposto: **Diagnóstico** (alternativas:
"Saúde do Negócio", "Análise"). Posição: logo depois da Visão Geral — as duas são de
leitura, o resto do submenu é operação.

- Barras por mês (6 e 12), empilhadas por origem.
- Cada número comparado ganha **rótulo**, não só seta: "acima da sua média", "na média",
  "abaixo".
- Concentração de origem: "78% do seu dinheiro veio de Serviços".
- DSO com a leitura em dias.
- **Os portões aparecem como conteúdo**, não como espaço vazio: cada métrica ainda
  bloqueada mostra o que falta e a data em que vai existir.

**Provas:** com 1 mês de histórico a tela abre e explica; com 3, a média aparece; loja PDV
não mostra nada de OS em lugar nenhum.

### Fase 3 — Alertas de tendência no painel de atenção

Entram no painel que já existe, com a mesma regra de limiar derivado do porte e o mesmo
"Adiar". Gated por PRO, como o `CAIXA_NEGATIVO`.

| Alerta | Regra | Portão |
|---|---|---|
| `RECEITA_CAINDO` | 3 meses seguidos de queda | 4 meses |
| `ORIGEM_CAINDO` | uma origem caiu ≥30% contra a média de 3 meses | 4 meses |
| `DEPENDENCIA_DE_ORIGEM` | uma origem passou de 80% da receita | 3 meses |
| `CUSTO_SUBINDO_MAIS` | despesa cresce ≥2× mais rápido que a receita, por 3 meses | 4 meses |
| `RECEBIMENTO_LENTO` | DSO subiu ≥50% contra a média | 3 meses |

Todos com ação e destino, como os sete atuais. Cada um leva ao Diagnóstico com o recorte
que o originou — a mesma mecânica do `?filtro=` que já existe.

**Provas:** cada limiar com o caso que dispara E o caso que não dispara. Alerta de
tendência é mais fácil de errar que alerta de estado ("vencido" é fato; "caindo" é
leitura), e limiar frouxo mata o painel.

### Fase 4 — Projeção de 12 meses

Decisão do dono: **entra, com o portão.**

- Média móvel de 3 meses + o que já está lançado (recorrentes e parcelas, que o Fluxo de
  Caixa já sabe ler), projetados 12 meses.
- **Faixa, nunca número seco:** "entre R$ 82 mil e R$ 104 mil". Número seco vira promessa.
- A faixa **alarga quanto menor o histórico** — é a forma honesta de dizer "sei menos".
- Abaixo de 6 meses fechados a projeção não aparece: a tela diz quantos meses faltam.
- Quando houver 12 meses, a curva passa a nascer do MAT em vez da média de 3.
- O texto diz sempre em cima de quantos meses ela foi feita.

**Provas:** com 5 meses não projeta; com 6 projeta e a faixa é mais larga que com 12; a
projeção nunca aparece sem dizer a base.

---

## Riscos conhecidos

1. **Alerta de tendência erra mais que alerta de estado.** "Vencido" é fato; "caindo" é
   leitura. Limiar frouxo vira alarme falso e o painel morre.
2. **Loja fechada** (férias, reforma, obra na rua) vira "queda" sem ser. Não há solução
   automática boa — o "Adiar" é a válvula, e o texto do alerta não pode acusar, só
   apontar.
3. **Mês parcial.** Já resolvido pela regra do mês fechado, mas é o erro mais fácil de
   reintroduzir sem perceber.
4. **A Visão Geral inchar.** Resolvido pela decisão #1: a tendência tem casa própria.

---

## Ordem de execução

1. Fase 1 (série + provas) — nada aparece na tela ainda.
2. Fase 2 (tela + menu + portões) — o dono já usa.
3. Fase 3 (alertas) — só depois de a série ter sido conferida por ele na tela.
4. Fase 4 (projeção) — por último, e é a única que pode ser cortada sem prejudicar o resto.

Cada fase fecha com `pytest` verde, `vue-tsc` 0 e um roteiro de conferência de NÚMERO —
nunca de clique.
