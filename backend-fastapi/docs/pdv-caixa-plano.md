# PDV — Plano da Fase 1 (Caixa, Leitor e o Segmento sem OS)

> **Status:** rascunho para debate. Nada foi executado.
> **Branch:** `feat/pdv`, criada a partir de `feat/segmento-serigrafia` (d43f072).
> **Primeiro cliente:** adega de bebidas. Não fiscal.
> **Data:** 15/08/2026

---

## 1. O que este documento é

O desenho da primeira entrega do PDV: **sessão de caixa**, **caminho do leitor de
código de barras** e **o segmento que não tem Ordem de Serviço**.

Ele não é um plano de "módulo de vendas", porque o módulo de vendas já existe e
funciona em três lojas. É um plano para as **pontas que faltam** em volta dele.

O que está fora, e por decisão, não por esquecimento: fiado (vai para o módulo de
gestão financeira, projeto seguinte), emissão fiscal (outro programador, se liga
aqui depois), fardo/embalagem, balança e casco retornável (só quando houver
cliente pedindo).

---

## 2. O princípio: PDV é modo, não segmento

Um mesmo motor precisa atender adega, mercado, distribuidora e qualquer loja de
balcão. Se cada tipo de negócio virar um PDV diferente, o custo de atender o
próximo é reescrita.

Então a regra aqui é a mesma que já rege a OS neste projeto:

- **O motor é um só.** Abrir caixa, vender, receber, fechar e conferir é igual em
  toda loja de balcão.
- **As diferenças são chavinhas por loja**, não por segmento. Tem adega que fia e
  adega que não fia; tem mercado com balança e mercado sem. Amarrar isso ao
  segmento obrigaria a fabricar um PDV por ramo.
- **O segmento `pdv` tem um trabalho só:** dizer que aquela loja não usa Ordem de
  Serviço. Ele não carrega diferença de comportamento nenhuma.
- **O caixa não é exclusividade do PDV.** Tem oficina, assistência e serigrafia que
  vendem produto no balcão e recebem dinheiro na mão. Elas têm o mesmo direito ao
  controle de gaveta — é assim que o mercado faz, e é como fica aqui: a chave existe
  para todo mundo, desligada por padrão (4.7).

Isso é a aplicação direta da regra de crescimento do projeto (`app/core/segmentos/__init__.py`):
segmento novo só acrescenta declaração; se exigir código novo, é sinal de metadado
faltando.

---

## 3. Levantamento: o que já existe (medido, não suposto)

### 3.1 A espinha da venda está de pé

Do "bipa o produto" até o "baixa o estoque", tudo existe e roda em produção:

| peça | onde | situação |
|---|---|---|
| venda de balcão **sem cliente** | `venda.py:37-44` (`cliente_id` nullable, comentado como "vendas rapidas de balcao") | pronto |
| carrinho, itens, item avulso | `modules/sales/components/SaleModal/` | pronto |
| múltiplos pagamentos + troco | `venda.py` (`troco` como property sobre os pagamentos) | pronto |
| cartão / juros / boleto / transferência | migration `7c2a9e5f1b30` | pronto |
| PIX com QR estático | `pixBrCode.ts` + `PixQrCode.vue` | pronto |
| cupom térmico ESC/POS | `sales/components/print/saleToEscPos.ts` | pronto |
| baixa de estoque no livro único | `movimentacoes_estoque` via `registrar_movimentacao()` | pronto |
| numeração oficial só ao finalizar | `venda.numero_venda` + `contador_venda.py` | pronto |
| aviso ao passar do estoque | `AvisoEstoqueNegativoModal.vue` | pronto |
| entrega / motoboy | `venda.entrega` | campo existe |

### 3.2 O que está modelado e **morto**

Duas coisas foram desenhadas, entraram no banco e nunca foram ligadas. Elas são
metade do trabalho desta fase — o desenho já está feito.

**`sessao_caixa`** (`db/models/sessao_caixa.py`) — tabela completa: `saldo_inicial`,
`saldo_final_esperado`, `data_abertura`, `data_fechamento`, `funcionario_id`,
status `ABERTO`/`FECHADO`, e um `CheckConstraint` de saldo não-negativo. A venda já
tem a FK (`venda.py:52`).

**E nada preenche.** Não existe service, endpoint, schema nem tela de caixa. A única
menção fora do model é um campo opcional no schema da venda (`schemas/vendas.py:149`).
Toda venda do sistema hoje grava `sessao_caixa_id = NULL`.

**`valor_atacado`** (`db/models/estoque.py:60`) — existe no banco e no cadastro de
produto, e **o módulo de vendas nunca lê**. Fica fora desta fase (é chavinha de
fase 2), mas registrado aqui para não ser redescoberto.

### 3.3 O leitor de código de barras: quase lá

O campo existe e é indexado (`produto.py:33`), **já está entre os campos de busca**
do CRUD (`db/crud/produto.py:20`), e há até um "exigir código de barras" nas
configurações de produtos.

A engrenagem de bipar também existe: em `ProductSearch.vue:76`, o Enter seleciona e
já joga no carrinho com quantidade 1, somando se o produto se repetir.

**Dois detalhes impedem que funcione com um leitor real:**

1. **A busca espera 300ms** (`useProductSearch.ts:22`, `refDebounced`). O leitor
   digita o código inteiro em milissegundos e manda Enter na sequência. Quando o
   Enter chega, `debouncedSearchTerm` ainda está vazio → `isSearching` é `false` →
   o handler cai no primeiro `if` e retorna sem fazer nada.
2. **O Enter exige item destacado.** `highlightedIndex` começa em `-1` e um `watch`
   o devolve para `-1` toda vez que a lista muda (`useProductSearch.ts`, watch de
   `sortedProducts`). Quem digita aperta a seta; leitor não aperta.

Resultado prático: o operador bipa, o código fica parado na caixa de busca e ele
termina no braço. Não é construir — é acertar o caminho.

### 3.4 Terminais

`terminais_conectados` (`db/models/terminal_conectado.py`) já registra cada máquina
por **HWID** único, com `ultima_sinc` de heartbeat. O frontend já sabe obter o HWID
(`shared/services/system/hwid.service.ts`). É a identidade de terminal que o
multi-caixa precisa, e ela já existe.

**Mas `sessao_caixa` não tem coluna de terminal.** Hoje a sessão sabe *quem* abriu,
não *onde*. Para dois caixas simultâneos isso é obrigatório — ver 4.1.

---

## 4. Fase 1 — Sessão de caixa

### 4.0 O padrão que estamos seguindo

Pesquisado nos sistemas do ramo (Conta Azul, vhsys, TOTVS, Saipos, Futura, Bling).
O consenso do mercado é enxuto e a gente adota inteiro:

- **Suprimento** — entrada de dinheiro que **não é venda** (o troco inicial, o
  reforço no meio do dia). Não entra no faturamento, mas entra na gaveta.
- **Sangria** — retirada de dinheiro que **não é venda** (leva pro cofre, paga um
  fornecedor na porta). Sai da gaveta, não é despesa da venda.
- **Motivo obrigatório** em ambas. É isso que transforma "sumiu dinheiro" em
  "saiu R$ 200 às 14h pro cofre, com o nome de quem tirou".
- **Sangria é permissão separada.** O padrão do mercado é operador poder suprir e
  só gerente poder sangrar.
- **Fechamento confere por forma de pagamento**, não só o total: dinheiro, cartão,
  PIX, cada um com seu esperado × contado.
- **Fechamento cego** (o operador digita o que contou **sem ver** o que o sistema
  esperava) é parâmetro configurável em todos eles. Ver 4.4.
- **Troca de operador** no mesmo terminal fecha a sessão de quem sai e abre a de
  quem entra. Ver 4.1.

A fórmula da gaveta, que é o que o fechamento precisa acertar:

```
esperado em dinheiro = saldo_inicial + vendas em dinheiro + suprimentos - sangrias - trocos
```

### 4.1 O modelo de operação (multi-operador e multi-caixa)

Ficou definido que a loja tem **dois vendedores em turnos** e **dois caixas
operando ao mesmo tempo**, com o servidor instalado à parte dando referência aos
terminais.

**Proposta: a sessão é de um par (terminal × operador).**

- Cada terminal tem **no máximo uma sessão ABERTA** por vez.
- Dois terminais vendendo juntos = **duas sessões abertas simultâneas**. Elas não
  se enxergam nem se somam até o relatório.
- Troca de turno no mesmo terminal = **fecha a sessão do operador A, abre a do B**.
  Ninguém herda gaveta de ninguém sem conferir — é justamente o momento em que a
  diferença precisa aparecer, com nome.
- O servidor separado não muda nada disso: ele já é a fonte única (banco na
  máquina servidora), e o terminal se identifica pelo HWID que já existe.

**Consequência no banco:** `sessao_caixa` precisa de uma coluna de terminal
(`terminal_hwid`), mais um índice que garanta uma única sessão `ABERTO` por
terminal. É migration nova.

### 4.1.1 Topologia: nem todo terminal é caixa

A adega abre com **um PC só** — servidor e caixa na mesma máquina. Mas a topologia
que vem depois é a clássica: **o PC do dono mais um, dois ou três caixas.**

E aí aparece uma coisa que com um computador só fica invisível: **a máquina do dono
não é um caixa.** É retaguarda — onde se olha relatório, se confere o dia, se
autoriza uma sangria. Se `exigir_caixa_aberto` valesse para ela, o dono seria
obrigado a abrir um caixa que ele não opera só para mexer no próprio sistema.

**Proposta: o terminal tem nome e papel.**

- **Nome amigável** — "Caixa 01", "Balcão", "Escritório". O HWID continua sendo a
  identidade real da máquina; o nome é para gente. Faz diferença no dia a dia: o
  fechamento diz *"Caixa 02 — João, diferença de R$ 5,00"*, e não um hash.
- **Papel** — `PDV` ou `RETAGUARDA`. Só terminal `PDV` abre caixa e é cobrado por
  `exigir_caixa_aberto`.

**O caso de um PC só continua sem configuração nenhuma:** terminal sem papel
definido se comporta como `PDV` quando o caixa está ligado. A adega instala e usa.
No dia em que entrar a segunda máquina, o dono nomeia as duas e marca a dele como
retaguarda — sem redesenho, sem migração de dados.

**Onde isso mora.** `terminais_conectados` já existe, já é chaveada por HWID único e
já registra cada máquina no login. Ganha duas colunas **nullable** (`nome`,
`papel`). É uma tabela que participa do heartbeat de licença, então a regra é
estrita: colunas nullable, nenhuma mudança de comportamento para quem não preencher.

**O que isso deixa pronto de brinde:** com dois ou três caixas, o dono vai querer o
**resumo do dia consolidado** — o total da loja somando as sessões, além do
fechamento de cada uma. Como o registro financeiro carrega `sessao_caixa_id` e a
sessão carrega o terminal, isso é agrupamento sobre dado que já vai existir. Não é
peça nova; é uma leitura a mais.

### 4.2 O que muda no banco

| mudança | tabela | por quê |
|---|---|---|
| coluna `terminal_hwid` | `sessao_caixa` | sem ela não existe multi-caixa |
| índice único parcial (`terminal_hwid` onde `status='ABERTO'`) | `sessao_caixa` | impede duas sessões abertas no mesmo terminal — a trava tem que ser do banco, não da tela |
| coluna `saldo_final_informado` | `sessao_caixa` | o que o operador **contou**, ao lado do que o sistema **esperava** (`saldo_final_esperado`, que já existe) |
| tabela nova: o **livro do dinheiro** | — | ver 4.8 — substitui a `movimentacao_caixa` que estava proposta aqui; sangria e suprimento viram movimentos com outra `origem` |
| 4 colunas booleanas | `configuracao_vendas` | as chavinhas de 4.7 — todas com padrão igual ao comportamento de hoje |
| `nome` e `papel`, ambas nullable | `terminais_conectados` | 4.1.1 — sem preencher, comportamento idêntico ao de hoje |

Nada disso mexe em tabela que os três segmentos em produção usam. A `venda` só
passa a **preencher** uma FK que já existe.

**Quando a venda ganha a sessão:** na **finalização**, junto com o `numero_venda` —
não na criação do rascunho. Carrinho aberto não é dinheiro na gaveta, e amarrar
cedo faria um rascunho esquecido de ontem entrar no caixa de hoje.

### 4.3 As operações

1. **Abrir caixa** — informa o troco inicial. Sem caixa aberto, não vende (ver 4.5).
2. **Suprimento** — entrada de dinheiro com motivo obrigatório.
3. **Sangria** — retirada com motivo obrigatório, atrás de permissão própria.
4. **Fechar caixa** — conferência por forma de pagamento, diferença calculada e
   registrada, sessão vira `FECHADO`.
5. **Resumo da sessão** — o "espelho" do fechamento: vendas do turno, por forma de
   pagamento, sangrias, suprimentos, esperado × contado, diferença. Imprimível na
   mesma térmica que já imprime o cupom.

### 4.4 Fechamento cego — proposta

É parâmetro em todos os sistemas pesquisados. Proponho **existir desde já, e vir
desligado por padrão**:

- Desligado, o operador vê o esperado e confirma. É o que serve o dono da adega,
  que é o próprio caixa.
- Ligado, ele digita o que contou sem ver o esperado, e a diferença aparece só
  depois. É o que serve quando entra funcionário.

Fazer a chavinha agora custa pouco; fazer depois obriga a mexer numa tela que já
está rodando na loja. **Ponto para debate:** o padrão sai desligado ou ligado?

### 4.5 "Não vende sem caixa aberto" — o ponto mais perigoso do plano

É o comportamento correto de PDV, e é também o único item aqui que pode **quebrar
as três lojas que já rodam**.

Informática, oficina e serigrafia vendem hoje sem nunca terem aberto caixa. Se a
exigência virar regra geral, elas param de vender no dia da atualização.

**A trava é o padrão da chave, e o padrão é desligado** (4.7). Loja que não ligar
nada continua exatamente como está — inclusive gravando `sessao_caixa_id = NULL`,
como sempre gravou. Isso não é sugestão de implementação: é a condição para esta
fase poder ir para produção.

Repare que a proteção **não** é "só o segmento PDV tem caixa" — qualquer loja pode
ligar. A proteção é que **ninguém liga sem querer**.

### 4.5.1 A regra do que entra na gaveta

Decorre direto de abrir o caixa para quem faz serviço: se uma oficina liga
`controlar_caixa`, o dinheiro que entra pela **OS** precisa cair na sessão — senão o
fechamento nunca bate, e um controle que não bate é pior que controle nenhum.

A boa notícia é que **os dois módulos já registram cobrança em linha própria**
(`venda_pagamento` e `ordem_servico_pagamento`), e é daí que sai a regra inteira.
Não precisa de tela de cobrança nova.

#### A regra, em três frases

1. **A unidade é o pagamento — não a venda, não a OS.**
   A venda é atômica (tudo acontece no checkout), mas a OS não: entra sinal na
   segunda, quita na sexta, às vezes em terminais e operadores diferentes. Amarrar
   a *OS* a uma sessão estaria errado por construção. Amarrar **cada pagamento**
   está certo nos dois casos.

2. **O pagamento carimba a sessão aberta naquele terminal, no instante do registro.**
   OS aberta segunda e paga sexta cai na sessão de sexta — porque foi na sexta que
   o dinheiro entrou na gaveta.

3. **Só entra o que foi recebido. Promessa não é gaveta.**
   Pagamento com `vencimento` no futuro (boleto, prazo, fiado) **não** entra na
   sessão: é conta a receber. O evento de caixa acontece no dia em que for
   efetivamente pago — e quem vai registrar isso é o **módulo de gestão
   financeira**. É exatamente aqui que a fronteira entre os dois projetos cai
   sozinha, sem a gente ter que inventar.

E a quarta, implícita: loja sem caixa ligado grava `NULL` em tudo, como hoje.

#### O que isso exige no banco

| mudança | tabela | por quê |
|---|---|---|
| `sessao_caixa_id` | `venda_pagamento` | o fechamento passa a ler **daqui** |
| `sessao_caixa_id` | `ordem_servico_pagamento` | o mesmo carimbo, do lado da OS |
| `data_pagamento` | `ordem_servico_pagamento` | **não existe hoje** — a linha só tem `vencimento`; sem o instante do registro não há como saber em que turno o dinheiro entrou |

`venda_pagamento` já tem `data_pagamento` ("Momento exato do registro do
pagamento"), então metade do caminho está feita.

**Por que o fechamento lê do pagamento e não de `venda.sessao_caixa_id`:** a venda
pode ser reaberta e refinalizada em outro dia. Se o fechamento lesse do nível da
venda, reabrir uma venda de ontem mexeria no caixa de ontem. No nível do pagamento
isso não acontece — cada linha de dinheiro fica onde caiu.
`venda.sessao_caixa_id` continua sendo preenchido (é útil saber em que turno a
venda foi feita), mas **não é a fonte do fechamento**.

#### O que a gente ganha de brinde

Você observou que as duas telas de cobrança já alimentam relatório. Com o carimbo
da sessão, o mesmo dado passa a poder ser agrupado **por turno e por operador** —
sem query nova, sem tela nova. O "resumo de sessão" de 4.3 é literalmente essa
leitura filtrada por sessão.

#### Corte de escopo

A **fase 1 liga o caixa só para vendas**. O lado da OS fica declarado como
pré-requisito: **empresa de serviço não deve ligar `controlar_caixa` antes de ele
existir**. Assim a adega abre no prazo e a oficina não recebe promessa quebrada.

Quando chegar, é barato: duas colunas, um `data_pagamento` e a mesma leitura de
fechamento. O caro é a máquina de caixa — e ela já vai estar pronta.

### 4.6 Identidade do operador — quem está no caixa

Sangria só significa alguma coisa se houver um nome atrás dela. "Saíram R$ 200"
não resolve nada; "o Fulano tirou R$ 200 às 14h20 pro cofre" resolve. Então a
identidade do operador não é enfeite: é o que faz o controle existir.

**Como o mercado faz.** O padrão é o turno carregar o operador, e a troca ser um
ato explícito: fecha o turno (F6 no Eagle/Futura), informa **login e senha** de
quem assume, abre o turno novo. O sistema Futura trata isso como parâmetro
("Controla Troca de Operador") e descreve o caso exato do dono da adega: *"o caixa
precisa ser fechado para que outro funcionário possa logar no mesmo terminal"*.

**Como fica aqui.** O modelo já está certo: `sessao_caixa.funcionario_id` amarra o
turno a uma pessoa. Duas formas de preencher esse campo:

**A — o operador é o usuário logado** *(proposta para a fase 1)*
Quem abriu o caixa é quem está logado no sistema. Troca de turno = fechar o caixa,
sair, o próximo entra com a credencial dele e abre o caixa novo. Zero máquina nova
de autenticação, e é literalmente o comportamento que a Futura descreve.

**B — operador como identidade própria dentro do app**
O terminal fica logado como estação e o operador entra/sai só do caixa, sem
derrubar a sessão do sistema. Mais confortável em loja de turno corrido, mas é uma
segunda camada de identidade para construir e manter.

**Recomendação: A agora, B depois se doer.** E o ponto que torna essa escolha
barata: **o banco é o mesmo nas duas.** `funcionario_id` na sessão não muda. Migrar
de A para B depois é trocar como o campo é preenchido, não remodelar nada.

**Autorização de supervisor (vale trazer junto).** Padrão encontrado em vários
sistemas: quando o operador não tem permissão para uma operação, o sistema pede
**login e senha de um usuário autorizado ali na hora** e libera aquela operação
específica, sem trocar quem está no caixa. É o que faz a sangria funcionar de
verdade numa loja onde o gerente não fica sentado no PDV — e resolve o incômodo de
"ou o operador pode tudo, ou tem que chamar o dono pra trocar de usuário".

### 4.7 Convivência: onde as chavinhas moram

A pergunta central: **como o caixa existe para a adega sem atrapalhar informática,
oficina e serigrafia?**

**O mercado já respondeu, e a resposta não é "por segmento" — é "por empresa".**
O Bling tem "Utilizar controle de caixa" nas configurações da empresa. O ERP da
Aliare tem o parâmetro "Controlar abertura/fechamento de caixa" na rotina de Frente
de Caixa, e um "Controlar gaveta" separado para a quebra. Nenhum deles pergunta o
ramo do cliente: pergunta se aquela empresa quer o controle.

**E aqui isso não precisa de mecanismo novo.** Já existe `configuracao_vendas`
(`db/models/configuracao_vendas.py`) — tabela de configuração **por empresa**, com
exatamente esse formato de chave: `permitir_desconto`, `exigir_cliente_identificado`,
`permitir_parcelamento`, `parcelas_maximas`. As chaves do caixa entram ali, do lado
das que já existem:

| chave | o que faz | padrão |
|---|---|---|
| `controlar_caixa` | liga o caixa: abertura, sangria, suprimento, fechamento | **desligado** |
| `exigir_caixa_aberto` | sem sessão aberta, não finaliza venda | **desligado** |
| `fechamento_cego` | operador digita o contado sem ver o esperado | **desligado** |
| `sangria_exige_autorizacao` | sangria pede permissão ou autorização de supervisor | **ligado** |

**Suprimento é livre para o operador; só a sangria é travada.** É o padrão do
mercado, e a assimetria tem razão de ser: pôr dinheiro na gaveta não cria risco de
desvio — tirar, sim. Travar as duas só faria o operador chamar o gerente para
colocar troco, que é exatamente o tipo de atrito que faz loja desligar o controle.

**Todos os padrões são o comportamento de hoje.** Uma loja que atualiza e não mexe
em nada continua vendendo exatamente como vendia — nenhuma tela nova, nenhuma trava
nova. É isso que faz esta fase poder ir para produção sem risco para os três
segmentos que já rodam.

**E o segmento não decide, só sugere.** Quando a loja se cadastra como `pdv`, o
onboarding **semeia** essas chaves ligadas. Depois disso quem manda é a
configuração, não o segmento. Duas consequências que são justamente o que se quer:

- A adega já nasce com o caixa ligado, sem ninguém precisar caçar configuração.
- Uma **oficina que queira** controle de caixa — tem balcão, tem funcionário
  recebendo dinheiro, e o dono quer saber da gaveta — simplesmente liga a chave.
  Ninguém decide por ela que "empresa de serviço não precisa disso".

É o mesmo raciocínio das capacidades da OS: o motor é um só, quem liga é a loja.

### 4.8 O livro do dinheiro — organizando pensando no geral

As telas de cobrança que alimentam o caixa são as mesmas que vão alimentar a gestão
financeira. Então vale desenhar isso **uma vez**, agora, em vez de fazer o caixa do
jeito curto e refazer daqui a dois meses.

#### O projeto já resolveu esse problema — no estoque

`movimentacoes_estoque` é, nas palavras do próprio arquivo, *"o livro-razão ÚNICO do
estoque"*: uma linha por movimento, com uma coluna `origem` dizendo quem causou
(venda, OS, cadastro, ajuste manual) e FKs opcionais (`venda_id`,
`ordem_servico_id`) apontando para a causa. Quem quer saber do estoque lê **um
lugar só**, não importa de onde veio o movimento.

O dinheiro hoje **não tem esse livro**. Tem duas tabelas de cobrança
(`venda_pagamento`, `ordem_servico_pagamento`) e nada que as una. Foi por isso que a
pergunta "quanto tem que estar na gaveta?" não tem resposta hoje.

#### A distinção que organiza tudo: cobrança ≠ movimento

Hoje as duas coisas são a mesma linha, porque tudo é à vista. **Fiado quebra isso** —
e é justamente o próximo módulo:

- **Cobrança** é o *combinado*: forma, parcelas, juros, bandeira, vencimento.
  Uma venda de R$ 500 a prazo gera **uma cobrança hoje e zero dinheiro na gaveta**.
- **Movimento** é o *dinheiro que andou*: R$ 500 entrando no mês que vem.

Enquanto tudo é à vista dá pra fingir que são a mesma coisa. No dia em que a adega
fiar, deixa de dar.

#### A proposta

**Um livro-razão do dinheiro**, no mesmo espírito do de estoque:

| coluna | papel |
|---|---|
| `origem` | `VENDA`, `ORDEM_SERVICO`, `SANGRIA`, `SUPRIMENTO`, `ABERTURA` — e, quando o financeiro chegar, `RECEBIMENTO` e `DESPESA` |
| `venda_pagamento_id`, `ordem_servico_pagamento_id` | FKs opcionais para a cobrança que causou (o mesmo padrão do estoque) |
| `sessao_caixa_id` | em que turno caiu; `NULL` para loja sem caixa |
| `valor`, `forma_pagamento_id`, `funcionario_id`, `data` | o movimento em si |
| `motivo` | obrigatório em sangria e suprimento |

**As tabelas de cobrança não mudam de forma.** Elas continuam onde estão, com os
dados que já têm — ninguém migra registro de dinheiro de loja em produção, que é o
tipo de migração mais perigoso que existe. Elas só ganham o `sessao_caixa_id` de
4.5.1, que é conveniência de consulta.

**E a tabela `movimentacao_caixa` que eu tinha proposto em 4.2 deixa de existir.**
Sangria e suprimento não são uma categoria à parte: são movimentos de dinheiro com
outra `origem`. Uma tabela a menos, e o fechamento passa a somar tudo do mesmo
lugar.

#### O que isso entrega

- **Fechamento de caixa** = ler o livro filtrado pela sessão, agrupado por forma.
- **Gestão financeira** = ler o mesmo livro (o que entrou e saiu) + as cobranças em
  aberto (o que ainda devem). Não precisa de fonte nova.
- **Relatório por turno e por operador** sai de graça, como você notou.
- **Fiado** encaixa sem remodelar: a cobrança nasce sem movimento, e o recebimento
  futuro vira um movimento com `origem = RECEBIMENTO`.

#### O cuidado

Um pagamento à vista passa a gerar **duas linhas**: a cobrança e o movimento. É a
mesma duplicação que o estoque já aceita (item de venda + movimentação), e é o preço
de ter um livro único.

O risco concreto é **contagem dupla no faturamento**: os relatórios de hoje somam as
cobranças. Enquanto o livro do dinheiro for lido só pelo caixa e pelo financeiro,
nada muda. Se um dia alguém somar os dois, o faturamento dobra. Fica registrado
aqui como armadilha conhecida.

---

## 5. Fase 2 — O caminho do leitor

Escopo pequeno e bem delimitado, em cima da engrenagem que já existe:

1. **Atalho do debounce para código de barras.** Quando o termo digitado tem cara
   de EAN (só dígitos, comprimento de código de barras), consultar sem esperar os
   300ms.
2. **Resultado único e exato → adiciona sozinho.** Se a busca por código de barras
   retorna exatamente um produto, entra no carrinho sem exigir seta nem Enter em
   item destacado.
3. **O foco volta pra busca** depois de cada item (já acontece hoje via
   `focusSearchInput`) — confirmar que sobrevive ao caminho novo.

Fora de escopo aqui: etiqueta de balança (o EAN com peso embutido), que é assunto
de mercado, não de adega.

---

## 6. Fase 3 — O segmento `pdv` e o sumiço da OS

Uma adega não pode ver Ordem de Serviço em lugar nenhum. Varredura completa do
frontend: são **oito** superfícies, e duas coisas diferentes a fazer em cada uma —
**esconder** o que não se aplica e **adaptar** o que fica vazio depois.

### 6.1 Menu lateral

`SIDEBAR_SECTIONS` (`mainLayout/constants/layout.constants.ts`) tem o item
`services` → "Serviços". Hoje a sidebar filtra **só por permissão**
(`BaseSidebar.vue:24-29`); não existe filtro por segmento nem por capacidade.

### 6.2 A rota — **não basta esconder o menu**

`/servicos` está registrada em `mainLayout/routes.ts:89`. Sumir com o item da
barra deixa a rota viva: quem digitar a URL (ou tiver a aba salva) entra na tela de
OS. Precisa de guard de rota, não só de menu.

### 6.3 Relatórios

- `OSPerformanceSection.vue` — seção inteira de desempenho de OS
  (`ReportsDashboard.vue:263-264`)
- KPI "Serviços (OS)" (`ReportsDashboard.vue:117`)
- o subtítulo que conta `qtd_os` junto com `qtd_vendas` (`ReportsDashboard.vue:107`)
- `useOSPerformanceQuery.ts` + `schemas/osPerformance.schema.ts`

### 6.4 Dashboard (Início)

Oito componentes e seis queries falam de OS:

`OSAguardandoRetiradaTable`, `OSAtrasadasBanner`, `OSAtrasadasEmpresaBanner`,
`OSPorStatusWidget`, `OSVencendoTable`, `MinhaFilaTable`, além dos trechos de OS
em `AtividadeHoje`, `DashboardMaster`, `DashboardFuncionario`, `RankingFuncionarios`
e `TendenciaChart`.

**Atenção:** esconder o componente sem desligar a query deixa o polling rodando à
toa contra o servidor. As duas coisas andam juntas.

### 6.5 Cargos / matriz de permissões

`PERMISSION_MATRIX` (`employees/constants/positions.constants.ts:105`) tem a linha
`services` → "Servicos". Numa adega, oferecer permissão de um módulo que não existe
confunde quem cadastra funcionário.

### 6.5.1 Configurações → seção "Ordens de Serviço"

`configuracoes/components/sections/ordens-de-servico/` é uma **seção inteira de
configuração** — prazos, numeração, regras de OS. Numa adega ela não faz sentido
nenhum, e é das piores de esquecer: o dono entra em Configurações e encontra uma
aba de um módulo que ele não tem.

Junto vem `useConfiguracoesOSQuery` / `useSalvarConfiguracoesOSMutation`, que também
devem parar de rodar.

### 6.5.2 Configurações → Impressão → documento de OS

Em `ImpressaoPeriferico.vue` há a chave *"Ao criar ou finalizar a OS"*, ao lado de
*"Ao finalizar a venda"*. A primeira sai; a segunda fica.

### 6.5.3 Comissão por serviço

Dois lugares, e este é o mais silencioso dos oito:

- **cadastro** — `employees/components/form/ComissaoSection.vue` pede
  `comissao_servico_percentual` ao lado do de venda. Numa adega, metade do
  formulário é sobre algo que não existe.
- **relatório** — `reports/components/ComissaoSection.vue` tem as colunas
  "Serviços (R$)" e "% Serviço", e o texto de estado vazio diz *"atribua vendas/OS
  aos funcionários"*.

O campo continua na tabela (`cargo.comissao_servico_percentual`) — some da **tela**,
não do banco.

### 6.6 Esconder ≠ adaptar

As oito superfícies acima resolvem o **esconder**. Mas duas delas ficam com buraco
depois, e aí é trabalho de verdade:

- **Dashboard** — tirando os widgets de OS, sobra um Início pela metade. Uma adega
  quer ver *vendas de hoje, caixa aberto, ticket médio, estoque baixo* — coisas que
  em boa parte já existem, mas precisam ocupar o espaço que era da OS.
- **Relatórios** — sai o Desempenho de OS, entra a seção de caixa (11.2).

**E aqui vale a regra do documento inteiro: adapta-se para "loja que só vende
produto", não para a adega.** A adega é a primeira instalação, não o molde.

O que salva isso de virar chute é que **não há widget novo para inventar**. Tudo que
uma loja de balcão quer ver no Início já existe no sistema, servindo vendas hoje:

| a loja quer ver | já existe |
|---|---|
| vendas de hoje / do mês | `useDashboardStatsQuery`, `TendenciaChart` |
| últimas vendas | `RecentTransactions` |
| formas de pagamento | `FormasPagamentoWidget` |
| estoque baixo | `EstoqueBaixoTable` |
| ranking de vendedores | `RankingFuncionarios` (parte de vendas) |
| caixa aberto e do turno | vem desta fase |

Ou seja: adaptar é **rearranjar o que já existe** para ocupar o espaço que era da
OS — não é desenhar tela nova por dedução. Isso serve adega, mercadinho, papelaria
ou loja de ração igualmente, porque nenhum desses widgets é de bebida.

**Proposta de disciplina:** a fase 1 faz o **esconder** das oito e o rearranjo do
que já existe. O que **não** se faz agora é inventar widget novo — esse espera ter
dono real pedindo, como sempre neste projeto.

### 6.7 Como ligar isso — proposta

Reaproveitar o mecanismo que o projeto já tem em vez de inventar outro: **uma
capacidade**, no mesmo espírito de `CAP_VISTORIA` e `CAP_DIAGNOSTICO`, respondendo
"esta loja usa Ordem de Serviço?".

- O segmento `pdv` simplesmente **não a declara**.
- Os três segmentos em produção a declaram, e **nada muda para eles** — é o mesmo
  padrão que fez a serigrafia não encostar na oficina.
- Menu, rota, relatórios, dashboard e matriz de cargos passam a perguntar isso, e
  não "qual é o segmento?".

**Backend não muda.** Os endpoints de OS continuam existindo e respondendo; a loja
de PDV simplesmente não os chama. Menos superfície de risco para quem já roda.

### 6.8 `mercado` vira `pdv` — **decidido**

`SEGMENTOS` (`shared/constants/segmentos.ts:19`) já oferece `mercado`, e o backend
já o aceita (`schemas/auth.py:13`). Fica decidido **rebatizar o valor gravado**, e
não só o rótulo da tela: o produto se chama PDV e atende adega, mercado,
distribuidora e o que vier — o nome do valor tem que dizer o que ele é.

O que a troca exige, em ordem:

1. `shared/constants/segmentos.ts` — `mercado` → `pdv` na lista única. O
   `Record<Segmento, ...>` faz o compilador cobrar o card e a dica; sem eles não
   compila, que é o comportamento desejado.
2. `app/schemas/auth.py` — o mesmo no `SEGMENTOS_VALIDOS`. **Este espelho o
   TypeScript não alcança**: esquecer aqui produz o erro de sempre
   (*"Invalid enum value ... received 'pdv'"*) no cadastro.
3. Migration de dado: `UPDATE empresas SET segmento = 'pdv' WHERE segmento = 'mercado'`.

**O risco aqui é baixo e vale dizer por quê:** `empresa.segmento` é
`String(50)` nullable (`db/models/empresa.py:46`) — texto puro, sem enum no banco,
sem constraint para brigar. E as três lojas em produção são `assistencia_tecnica`,
`oficina_mecanica` e `serigrafia`, então na prática o `UPDATE` deve tocar **zero
linhas**. Ele existe para o caso de alguma instalação ter escolhido "Mercado" no
onboarding — se ficasse para trás, essa loja teria um segmento que o `Literal`
recusa, e o sintoma seria falha em salvar dados da empresa.

Também vale rever o texto do card e da dica: hoje falam de supermercado
(`sign-in/constants/segments.ts`), e o segmento passa a ser qualquer negócio de
venda de produto no balcão.

---

## 7. As duas portas: fiscal e financeiro

### 7.1 A porta para o fiscal

O módulo fiscal é de outro programador e entra depois, como plano contratável.
Duas regras de projeto para que ele se ligue sem retrabalho:

1. **A venda é a fonte, o fiscal é o assinante.** Não gravar nada de documento
   fiscal na `venda` agora. Quando o fiscal chegar, ele referencia a venda; a
   venda não precisa saber que ele existe.
2. **A sessão de caixa é operacional, não fiscal.** O resumo de fechamento é
   relatório de gaveta. O equivalente fiscal (redução Z e afins) é outra história e
   mora no módulo fiscal.

Já existe um `origin/feat/fiscal-module` no remoto. Vale combinar o ponto de
encontro antes que as duas linhas cresçam.

### 7.2 A porta para a gestão financeira

O módulo seguinte nasce com **contas a receber** e **contas a pagar**, e cresce
dali. Ele não precisa inventar fonte de dado nenhuma — herda tudo desta fase:

| ele precisa de | já vai existir |
|---|---|
| o que entrou e saiu | o livro do dinheiro (4.8) |
| o que foi combinado | as tabelas de cobrança, intactas |
| a diferença entre prometido e recebido | a distinção cobrança × movimento |

**Contas a receber** = cobrança com `vencimento` e **sem movimento**. Fiado é o
primeiro caso disso, e o desenho de 4.5.1 já o comporta: a venda existe, o dinheiro
não entrou, o fechamento do caixa fica certo. Quando o cliente pagar, nasce um
movimento com `origem = RECEBIMENTO` na sessão daquele dia — e a conta se quita.

**Contas a pagar** = movimento de **saída** que não é sangria. E aqui o livro já
resolve um caso que costuma dar nó: pagar o fornecedor **em dinheiro da gaveta** é
um movimento **com** sessão; pagar o mesmo fornecedor **por transferência** é um
movimento **sem** sessão. Como `sessao_caixa_id` é nullable, os dois cabem na mesma
tabela sem gambiarra — o que passou pela gaveta tem sessão, o que não passou, não
tem.

**O que precisa ser decidido agora** (porque a tabela nasce nesta fase): o livro tem
que distinguir **entrada de saída** desde o primeiro dia — seja por um campo `tipo`,
seja por valor com sinal. Sem isso, contas a pagar não cabe e a tabela teria que ser
alterada depois.

#### Registrar os gastos da empresa — o que já vem na fase 1

O objetivo declarado do módulo financeiro é registrar os gastos da empresa. Vale
separar em dois, porque **metade disso já nasce nesta fase, de graça**:

| tipo de gasto | exemplo | onde é registrado |
|---|---|---|
| **saiu da gaveta** | pagar o entregador de bebida na porta, comprar gelo | **fase 1** — é sangria com motivo, e já vira movimento de saída no livro |
| **não passou pela gaveta** | aluguel, energia, boleto de fornecedor, transferência | **módulo financeiro** — movimento de saída sem sessão |

Ou seja: no dia em que a adega abrir, o dinheiro que sai do caixa **já fica
registrado com valor, motivo, data e o nome de quem tirou**. O que falta é o gasto
que nunca encostou na gaveta — e é justamente o que o financeiro vem fazer.

A costura para isso já está pronta no desenho: mesma tabela, `origem = DESPESA`,
`sessao_caixa_id` nulo. Nenhuma remodelagem quando o módulo chegar.

**O que NÃO se decide agora:** o conceito de *conta* (Caixa, Banco X, Banco Y), que
os sistemas maiores usam para separar de onde o dinheiro saiu. Quando o financeiro
precisar, é **uma coluna nullable a mais** — não é motivo para inflar o desenho
hoje. A regra que vale aqui é a mesma do resto do projeto: só entra o que tem dono
pedindo.

#### O financeiro vale para TODOS os segmentos — e as 2 condições para isso

Confirmado na implementação da fase 2: o livro **não é do PDV**. A única coluna que
o liga ao caixa é `sessao_caixa_id`, e ela é nullable — `NULL` significa "não passou
por gaveta nenhuma". Uma assistência técnica, uma oficina ou uma serigrafia usam a
mesma tabela sem nenhuma adaptação, e **nenhuma migração de dados será necessária**.

Mas duas coisas ficaram propositalmente estreitas na fase 2, por segurança, e
**precisam ser alargadas quando o módulo financeiro chegar**:

**1. O portão da escrita.** Hoje o livro só é escrito com `controlar_caixa` ligado
(`registrar_pagamentos_de_venda` sai na primeira linha sem isso). Foi assim para
provar a inércia. Uma oficina que queira **financeiro sem caixa** teria o livro
vazio — só apareceriam as despesas digitadas à mão, e nada do que entrou.

*Como alargar:* o portão passa a ser `controlar_caixa` **OU** o financeiro ligado.
Sem caixa, o movimento nasce com `sessao_caixa_id = NULL`, que é exatamente o que a
coluna já significa. É uma condição a mais num `if`, não um remodelamento.

**2. O lado da OS.** A fase 2 ligou só a **venda**. Para informática, oficina e
serigrafia isso é o lado *menor* — o dinheiro delas entra pela **OS**. Sem o
vínculo de 4.5.1, o financeiro desses segmentos nasceria enxergando quase nada.

*Ou seja:* o que em 4.5.1 é "pré-requisito para empresa de serviço ligar o caixa"
é, aqui, **pré-requisito para o financeiro servir os três segmentos que já rodam**.
É o mesmo trabalho, e agora tem dois motivos.

**Resumo para o planejamento:** o módulo financeiro atende todos os segmentos sem
retrabalho de modelo. O que ele exige antes é ligar a OS ao livro e alargar o
portão — as duas coisas aditivas, e as duas já mapeadas neste documento.

---

## 8. O que fica de fora (e por quê)

| item | destino |
|---|---|
| **Fiado / contas a receber** | módulo de gestão financeira, projeto seguinte. O PDV só registra "saiu fiado, cliente X, valor Y" e entrega. |
| **Preço de atacado** | chavinha de fase 2. O campo já existe e não é lido. |
| **Fardo / embalagem** | quando houver cliente pedindo. |
| **Balança / granel** | idem. O estoque já é fracionário. |
| **Casco retornável** | idem. |
| **Emissão fiscal** | outro programador, plano contratável. |

---

## 9. Riscos e como provar que não quebrou

Esta fase é diferente da serigrafia num ponto que importa: **serigrafia só
acrescentou declaração; o PDV mexe em vendas, dashboard, relatórios e menu — código
que as três lojas em produção usam todo dia.**

### 9.1 O que é inerte por construção

A parte de **dados** não incomoda ninguém, e isso é uma propriedade do desenho, não
uma esperança:

- As tabelas de cobrança **não mudam de forma**. Ganham um `sessao_caixa_id`
  nullable, que fica `NULL` como já fica hoje.
- Os relatórios de hoje continuam lendo **as cobranças**. O livro do dinheiro é
  fonte nova, lida só pelo caixa e (depois) pelo financeiro.
- O fluxo de venda, checkout, cupom e baixa de estoque não é tocado.
- Os endpoints de OS no backend não são tocados.

**Decisão: o livro do dinheiro só é escrito quando a loja tem `controlar_caixa`
ligado.** Um `if`, e as três lojas seguem com o mesmo caminho de código que têm
hoje — o que permite *provar* que nada mudou, em vez de argumentar que não mudou.

O custo dessa decisão é pequeno e correto: loja que liga o caixa depois começa o
livro naquele dia. É assim que abrir um livro-caixa funciona na vida real.

**O que roda em todo mundo de qualquer jeito** são as migrations: tabela nova e
colunas novas são criadas no banco de toda loja que atualizar. Risco baixo, mas não
zero — e valem as regras de sempre deste projeto (`create_all` roda **antes** das
migrations; migration nova decide pela presença do schema **antigo**).

### 9.2 Onde o risco realmente mora

Não é no banco. É no **frontend compartilhado**:

- a busca de produto que o leitor vai mexer é a **mesma** que as três lojas usam
  para vender;
- sidebar, dashboard, relatórios e matriz de cargos são telas que as três abrem
  todo dia, e vão ganhar uma condição nova.

É aí que a prova medida tem que ser feita — não no livro do dinheiro.

| risco | prova exigida |
|---|---|
| exigir caixa aberto derrubar as três lojas | venda em loja sem modo PDV, medida antes × depois |
| sumiço da OS vazar para quem tem OS | as três lojas continuam vendo menu, rota, dashboard, relatórios e cargos idênticos |
| leitor quebrar a busca por nome | digitar nome continua funcionando como hoje |
| query órfã de widget escondido | conferir que a requisição parou junto com o componente |

Regra do projeto que vale aqui inteira: a prova é **medida** (antes × depois,
comparando com o arquivo do `git show HEAD`), nunca deduzida.

E o lembrete de sempre: nada disso chega na loja sem `npm run build:sidecar` e
instalador novo.

---

## 10. Plano de execução seguro

Três lojas reais vendem todo dia com este código. O plano é ordenado por **risco
crescente**: o que não incomoda ninguém vai primeiro, o que mexe em tela
compartilhada vai por último.

**Três regras que valem para todas as etapas:**

1. **Cada etapa é um commit que fecha sozinho.** Em qualquer ponto dá para parar
   com o sistema funcionando.
2. **Cada etapa tem uma prova medida** — comparação de fato entre antes e depois,
   nunca "eu revisei e está certo".
3. **A branch é `feat/pdv` e não encosta no `master`.** O instalador do cliente sai
   desta linhagem.

### Etapa 0 — Congelar o "antes" (não muda nada)

Sem baseline não existe prova medida. Antes de tocar em qualquer arquivo:

- rodar a suíte inteira (`pytest test/`) e o `npx vue-tsc --noEmit`, e **guardar o
  resultado** — é o "antes" de todas as comparações seguintes
- confirmar que o sidecar está em dia (`npm run check:sidecar`)
- separar uma **cópia verbatim** do banco de uma loja real para testar migração
  (cópia funciona; transplante de banco a licença recusa)

### Etapa 0.5 — Fuso do dia da loja *(FEITA em 15/08/2026)*

Entrou antes da etapa 1 por uma razão técnica: **o fechamento de caixa filtra por
tempo**. Construir o caixa sobre um filtro de data quebrado faria o fechamento
nascer com o mesmo defeito — e um caixa que fecha com 3h de venda no dia errado é
pior que um relatório torto.

**O bug:** o banco grava em UTC e o filtro recebia data local sem converter. No
Brasil (UTC-3), toda venda depois das 21h caía no dia seguinte.

**O que mudou:**

- `app/core/tempo.py` — novo, o único lugar que converte dia da loja ↔ UTC
- `app/services/relatorio.py` — 5 pontos passam por `intervalo_utc()`
- `app/services/dashboard.py` — `_calcular_periodo` deixa de usar "hoje" em UTC
- `app/db/crud/dashboard.py` — **2 dos 4** pontos convertem

**A distinção que evitou uma regressão:** `criado_em` e `data_criacao` são
*instantes* em UTC e convertem; `data_previsao` é *data pura de calendário*
escolhida por uma pessoa e **não** converte. Converter os quatro teria quebrado as
OS atrasadas.

**Detalhe de Windows:** o escape hatch `STARTBIG_TZ` aceita deslocamento fixo
(`-03:00`) além de nome IANA, porque **Windows não traz o banco de fusos** — o nome
levantaria `ZoneInfoNotFoundError` em toda máquina de loja, cairia calado no fuso do
sistema, e ninguém perceberia.

**Prova medida:**

| | resultado |
|---|---|
| suíte antes (baseline) | 410 passed |
| suíte depois | **416 passed** (410 + 6 novos), zero regressão |
| `vue-tsc` | exit 0 |
| testes novos **sem** o fix | **2 failed** — exatamente os dois do bug de produção |
| testes novos **com** o fix | 6 passed |

O "2 failed sem o fix" foi obtido revertendo o fix com `git stash` e rodando de
novo. É o que prova que o teste testa alguma coisa.

Os testes novos (`test/api/v1/test_fuso_relatorio.py`) são **determinísticos** — não
dependem da hora em que a suíte roda, ao contrário dos de `test_custo_estoque.py`,
que eram o detector antigo e piscavam à noite.

### Etapa 1 — Schema, e nada mais *(inerte)*

Só migration. Nenhuma linha de negócio lê ou escreve as colunas novas.

- `sessao_caixa`: `terminal_hwid`, `saldo_final_informado`, índice único parcial de
  sessão aberta por terminal
- tabela nova do registro financeiro (4.8)
- `sessao_caixa_id` em `venda_pagamento` e em `ordem_servico_pagamento`
- `data_pagamento` em `ordem_servico_pagamento`
- 4 booleanos em `configuracao_vendas`, **com padrão igual ao comportamento de hoje**

**Prova:** a cópia do banco da loja real sobe, a migração aplica, o app abre e vende
igual. Suíte verde. Migration guarda pela presença do schema antigo (`create_all`
roda antes das migrations).

### Etapa 2 — Backend do caixa, atrás da chave *(inerte com a chave desligada)*

Service e endpoints de abrir, suprir, sangrar, fechar e resumo. A escrita no
registro financeiro e o carimbo da sessão acontecem **só** com `controlar_caixa`
ligado.

**Prova (a mais importante do plano):** com a chave desligada, finalizar uma venda e
comparar as linhas gravadas com as do mesmo fluxo antes da etapa — `venda`,
`venda_pagamento` e `movimentacoes_estoque` têm que sair **idênticas**, e o registro
financeiro tem que sair **vazio**. Mais os testes novos do caminho ligado.

### Etapa 3 — Frontend do caixa *(primeiro toque em tela compartilhada)*

Modais de abertura, sangria, suprimento, fechamento e resumo do turno — **dentro do
PDV** (11.2), atrás da mesma chave.

**Atenção: esta etapa é menos inerte do que as anteriores.** Como o caixa vive
dentro da tela de vendas, os arquivos de `sales` são editados — e `sales` é a tela
que as três lojas usam todo dia. Os arquivos novos ficam no subdomínio
`sales/caixa/`, mas alguém tem que chamá-los a partir da tela existente.

**Prova:** com a chave desligada, a tela de vendas renderiza **idêntica** à de antes
— nenhum botão, atalho, modal ou requisição a mais. Comparação contra o arquivo do
`git show HEAD`, na mão, na tela.

> **Ponto de parada seguro.** Até aqui nada é visível para as três lojas. Se o
> projeto precisar pausar, pausa aqui — com a ressalva de que a etapa 3 encostou em
> `sales` e por isso pede a verificação acima antes de ir para a loja.

### Etapa 4 — O caminho do leitor *(primeiro risco compartilhado)*

Commit isolado, sozinho, sem nada mais junto. Mexe na busca de produto — a **mesma**
que as três lojas usam para vender.

**Prova:** com o arquivo do `git show HEAD` do lado, verificar que (a) digitar nome
continua achando e adicionando como hoje, (b) digitar código parcial continua
funcionando, (c) bipar agora adiciona sozinho. Os três casos testados na mão, não
deduzidos.

### Etapa 5 — Segmento `pdv` e o sumiço da OS *(maior risco compartilhado)*

Capacidade nova, e as cinco superfícies: menu, **guard de rota**, relatórios,
dashboard (componente **e** query) e matriz de cargos.

**Prova, nos dois sentidos:**
- loja de assistência/oficina/serigrafia: menu, rota, dashboard, relatórios e cargos
  **idênticos** ao antes;
- loja `pdv`: nenhuma menção a OS em lugar nenhum, **incluindo digitar `/servicos`
  na barra de endereço**;
- nenhuma requisição de OS saindo na loja `pdv` (widget escondido com query viva é
  polling à toa).

### Etapa 6 — Instalar na adega

`npm run build:sidecar` → instalador → instalação → ligar as chaves **só na adega**.

**Prova:** conferir o hash do `erp-api.exe` depois de instalar (o backend roda como
task agendada e o `.exe` travado já deixou de ser substituído antes), abrir caixa,
vender bipando, sangrar, fechar conferindo.

### Ordem de merge

Etapas 1–3 podem ir para as lojas existentes sem que ninguém perceba — são a rede
de segurança do resto. Etapas 4 e 5 são as que pedem cuidado e não devem viajar
juntas no mesmo instalador.

---

## 11. Mapa de pastas — onde cada coisa vai morar

Levantado lendo os módulos maduros (`order-service`, `products`), não o que o
CLAUDE.md descreve. Onde os dois divergem, **vale o código**.

### 11.1 O padrão observado

**Backend — um arquivo por entidade, mesmo nome nas cinco camadas:**

```
app/db/models/<entidade>.py        ORM
app/db/crud/<entidade>.py          acesso a dados
app/schemas/<entidade>.py          Pydantic (entrada/saída)
app/services/<entidade>.py         regra de negócio
app/api/v1/endpoints/<entidade>.py rotas  → registrar em api/v1/api.py
app/core/enum.py                   enums (todos juntos, num arquivo só)
alembic/versions/<hash>_<desc>.py  migration
```

**Frontend — módulo com subdomínios, `views/` na raiz do módulo:**

```
modules/<modulo>/
├── views/                  ← a página fica AQUI, na raiz do módulo
├── <subdominio>/
│   ├── components/
│   ├── composables/
│   ├── constants/
│   ├── schemas/
│   ├── services/
│   ├── types/
│   └── utils/
└── shared/                 ← o que cruza subdomínios do módulo
```

É o formato de `order-service/{ordens, revisoes, servicos, shared}` e de
`products/{inventory, suppliers, shared}` — em ambos, `views/` mora na raiz.

**Duas correções ao que se poderia supor:**

1. **Rota não é `routes.ts` no módulo.** Só `auth`, `license`, `sign-in` e
   `network-config` têm o seu, porque vivem **fora** da casca do app. Toda página de
   dentro é filha da rota do `mainLayout` (`mainLayout/routes.ts`). O caixa entra
   **lá**, não num arquivo novo.
2. **`sales` é a exceção, não o modelo.** Ele é plano, tem o `SalesView.vue` solto
   na raiz e não tem `views/`. **Não vamos reorganizá-lo** — é código que três lojas
   usam todo dia, e mexer na estrutura por estética é exatamente o risco que este
   projeto não aceita. Ao editar arquivo de lá, segue-se o estilo de lá.

**Composables têm dois dialetos** no projeto: `queries/ mutates/ flows/ form/`
(sales) e `request/ form/ modal/` (ordens). Para o módulo novo adotamos o primeiro —
é o mais explícito e é o do vizinho de domínio.

### 11.2 Onde o caixa vai morar

**O princípio de agrupamento deste código é: um módulo por entrada de menu.**
`products` junta inventory e suppliers porque os dois vivem sob "Produtos";
`order-service` junta ordens, revisões e serviços sob "Serviços".

Caixa e Gestão Financeira serão **entradas de menu distintas**, com permissões e
públicos distintos (operador no balcão × dono no escritório — a fronteira de 4.7).
Logo, **módulos distintos**. O caixa não entra dentro de `sales`: venda e turno de
caixa são domínios diferentes, e a regra do projeto é pasta por **domínio**.

**Backend:**

```
app/db/models/sessao_caixa.py              JÁ EXISTE — ganha colunas
app/db/models/movimentacao_financeira.py   NOVO — o livro (4.8)
app/db/crud/sessao_caixa.py                NOVO
app/db/crud/movimentacao_financeira.py     NOVO
app/schemas/sessao_caixa.py                NOVO
app/services/sessao_caixa.py               NOVO — abrir/sangrar/suprir/fechar
app/api/v1/endpoints/sessao_caixa.py       NOVO → registrar em api/v1/api.py
app/core/enum.py                           SessaoCaixaStatus JÁ EXISTE;
                                           acrescentar origem e tipo do movimento
```

**Nome da tabela do livro: `movimentacoes_financeiras`**, arquivo
`movimentacao_financeira.py`. É o espelho direto de `movimentacoes_estoque` /
`movimentacao_estoque.py` — mesmo papel (livro-razão único), mesmo nome de padrão.
Quem já conhece um entende o outro sem explicação.

**Frontend — dentro de `sales`, e sem item de menu.**

Decidido: **o operador abre o caixa de dentro do PDV.** Não existe entrada "Caixa"
no menu lateral. E está certo: o operador já está na tela de venda, com fila na
frente — obrigá-lo a navegar para outro lugar para sangrar é atrito puro. É também o
que os sistemas do ramo fazem (abrir/fechar turno em tecla de atalho, dentro do
PDV).

Como o caixa acontece no fluxo da venda, ele mora junto:

```
modules/sales/
├── SalesView.vue                  já existe (estrutura plana — não mexer)
├── components/ …                  já existe
└── caixa/                         NOVO — primeiro subdomínio de sales
    ├── components/                AberturaModal, SangriaModal,
    │                              SuprimentoModal, FechamentoModal,
    │                              ResumoSessaoPrint
    ├── composables/
    │   ├── queries/               useSessaoAtualQuery, useResumoSessaoQuery
    │   ├── mutates/               useAbrirCaixaMutation, useSangriaMutation…
    │   └── flows/                 orquestração dos modais
    ├── schemas/
    ├── services/
    ├── types/
    └── constants/
```

**Isto não reorganiza `sales`.** Nenhum arquivo existente é movido ou renomeado —
só se acrescenta uma pasta ao lado. `sales` continua com a estrutura plana que tem
hoje, e o subdomínio novo nasce organizado.

**Rota:** nenhuma. Não há tela nova para navegar.
**Menu:** nada. `layout.constants.ts` não é tocado por causa do caixa.
**Chaves de cache:** prefixo próprio em `shared/constants/entityKeys.ts` — toda
`queryKey` pende de lá, e mutation invalida **só o prefixo** (chave-irmã não é
alcançada; tem que ser filha).

**Onde o dono consulta o histórico.** As operações são do operador, mas "quem fechou
com diferença ontem" é pergunta do dono, e não pode viver dentro do PDV. O lugar
natural é **Relatórios**, que já é a tela do dono e já é organizada em seções
(Faturamento, Estoque, Comissão, Desempenho de OS). Entra como mais uma seção,
visível só com `controlar_caixa` ligado — sem módulo novo e sem menu novo.

### 11.3 Onde a gestão financeira vai morar (para não improvisar depois)

```
modules/financeiro/
├── views/
├── contas-receber/     subdomínio
├── contas-pagar/       subdomínio
└── shared/
```

Mesmo formato de `products`. O backend reaproveita
`movimentacao_financeira` — o módulo nasce sem tabela nova de dinheiro.

### 11.4 A regra de trabalho

**Antes de criar qualquer arquivo:** abrir o vizinho mais próximo e seguir o que ele
faz — nomes, camadas, estilo de import, densidade de comentário. Arquivo novo que
destoa da pasta é dívida no dia seguinte.

**Ao editar arquivo existente:** o estilo é o do arquivo, não o meu. Vale
especialmente em `sales`, que tem estrutura própria e não vai ser reorganizado.

---

## 12. Decidido e em aberto

### Decidido (16/08/2026)

- **Multi-operador e multi-caixa entram no desenho desde já**, mesmo com a adega
  abrindo com um PC só. A máquina fica pronta; a loja liga quando crescer.
- **Operador = usuário logado** (opção A de 4.6). Troca de turno fecha o caixa.
- **As chavinhas moram em `configuracao_vendas`, por empresa**, com padrão igual ao
  comportamento de hoje (4.7). Segmento semeia, configuração manda.
- **Fechamento cego é construído agora e sai desligado.** Na adega o dono é o
  próprio caixa; a chave espera o dia em que entrar funcionário.
- **Sangria com autorização de supervisor** — login e senha na hora, sem trocar
  quem está no caixa.
- **O caixa é do padrão do mercado e vale para qualquer segmento**, não só para o
  PDV: oficina, assistência e serigrafia que vendem no balcão podem ligar. A
  segurança vem do padrão desligado, não de proibir.
- **A OS entra no caixa depois** (4.5.1). Até lá, empresa de serviço não deve ligar
  `controlar_caixa` — o fechamento não fecharia.
- **Livro-razão único do dinheiro** (4.8), no mesmo molde do de estoque, já pensando
  no módulo financeiro. Cobrança (o combinado) e movimento (o dinheiro que andou)
  passam a ser coisas distintas. As tabelas de cobrança **não** são migradas.

- **Topologia pronta desde já** (4.1.1): terminal com nome e papel (`PDV` ou
  `RETAGUARDA`), porque a máquina do dono não é caixa. A adega instala com um PC só
  e **sem configurar nada** — terminal sem papel se comporta como `PDV`.

- **`mercado` vira `pdv` no valor gravado** (6.7), com migration de dado — não só o
  rótulo da tela.
- **O livro nasce com entrada × saída** (7.2), para contas a pagar caber sem
  alteração de tabela depois. Gasto pago em dinheiro da gaveta já fica registrado
  na fase 1; gasto que não passa pelo caixa é do módulo financeiro.

- **Suprimento livre, sangria travada** (4.7) — padrão do mercado. Pôr dinheiro na
  gaveta não cria risco de desvio; tirar, sim.
- **O caixa se abre de dentro do PDV, sem item no menu** (11.2). O frontend fica em
  `modules/sales/caixa/` — pasta nova ao lado, sem mover nada do que existe. O
  histórico para o dono vira seção em **Relatórios**.

**O desenho está fechado.** Não há decisão de arquitetura pendente para começar a
executar.

### Em aberto — para a cliente, não para o desenho

1. A adega **fia**? Não muda nada no que está desenhado (fiado é cobrança sem
   movimento, e as telas são do módulo financeiro). Muda só a **urgência** do
   financeiro: se ela fia muito, ele deixa de ser "o próximo" e passa a andar
   junto, senão a loja fecha o caixa certo mas continua com o caderninho do lado.
