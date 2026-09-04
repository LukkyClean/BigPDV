# PDV — Plano do Balcão Profissional (fases 1 a 5)

> **Status:** plano fechado, pronto para executar. Nada foi implementado.
> **Branch:** `feat/pdv`, em cima de `1111c8d`.
> **Continua:** `pdv-caixa-plano.md` (fases 0–5) e `pdv-onde-paramos.md` (retomada de 15/08).
> **Primeiro cliente:** adega de bebidas. Não fiscal.
> **Data:** 17/08/2026

---

## 1. O que este documento é

O que falta para o balcão da adega funcionar como **PDV de verdade**: sem mouse no
fluxo feliz, sem recusa silenciosa, e sem quebrar as três lojas que já rodam.

Ele não repete o `pdv-caixa-plano.md`. Aquele desenhou o caixa, o leitor e o
segmento sem OS — tudo entregue (fases 0 a 5, commits `af49009` a `84db7e8`). Este
aqui parte de uma leitura de código feita depois da entrega, que achou cinco
silêncios no caminho de teclado, mais duas frentes que o `pdv-onde-paramos.md` já
tinha listado e ninguém executou.

**Onde estamos, em números:**

| | |
|---|---|
| Fases 0–5 | commitadas e verificadas no app |
| Suíte | 445 testes (pytest), `vue-tsc` em zero |
| Frontend | **nenhuma infraestrutura de teste** — sem vitest, sem playwright, zero `.spec.ts` |
| Modo Balcão | codado, **na árvore, sem commit**; guard `check:balcao` no build |
| Fase 2 | **codada (A–F)**, `vue-tsc` 0 e `npm run build` verde, **sem teste no app** |
| Fase 3 | **codada** (tabela `terminais` + migration `a1b2c3d4e5f6` + tela), 457 pytest |
| Sidecar | **atrasado desde a fase 0.5** |

---

## 2. Os três princípios

### 2.1 Silêncio é bug

Toda recusa fala. Hoje o PDV tem **cinco** jeitos diferentes de não fazer nada sem
dizer por quê: código não encontrado, empate de código, esgotado pelo teclado, Enter
sem destaque e **falha de rede durante a bipada** (`catch { return false }` em
`ProductSearch.vue:105`). O operador aprende a desconfiar do sistema, e a partir daí
ele confere tudo duas vezes — que é o oposto de balcão rápido.

O quinto é o mais perigoso porque é **intermitente**: transforma erro técnico em
"não aconteceu nada".

### 2.2 A mão não sai do teclado

O critério não é "dá para fazer pelo teclado", é **"dá para fazer a venda inteira
sem tocar no mouse"**. Cada vez que a mão sai do teclado, custa mais tempo do que o
passo que ela foi executar.

### 2.3 Prova medida, não deduzida

Três lojas rodam esta linhagem. Cada fase termina com um teste no app instalado ou
no balcão de verdade — não com "o teste passou". A regressão aqui custa sidecar,
instalador e uma ida à loja.

---

## 3. Fase 1 — Fechar o Modo Balcão que está na árvore

**Custo:** uma sessão. **Risco:** baixo. **É dívida em aberto.**

Quatro arquivos modificados e um store novo (`shared/stores/balcao.store.ts`) estão
sem commit e nunca rodaram no app. Enquanto isso durar, todo trabalho novo na tela
de vendas nasce em cima de código não verificado — e quando algo quebrar, não vai
dar para saber se foi o balcão ou o conserto novo.

É a fase 1 porque mexe na **mesma tela** da fase 2. Uma ida ao balcão testa as
duas, e o commit sai limpo: primeiro o balcão, depois o teclado.

Tratar como **checkpoint imutável**: commit do Modo Balcão, prova ON, prova OFF,
nenhum refactor junto. Só então começa a fase 2. É o que mantém o `git bisect` útil.

1. **Abrir o app e ligar a chavinha.** Conferir os três comportamentos: venda que
   começa sem cliente (`iniciarVendaSemCliente`), foco nascendo no botão Dinheiro
   (`[data-forma-dinheiro]`), e o troco em fonte grande — inclusive zerado.
2. **Testar com a chave desligada**, contra a baseline do `git show HEAD`.
3. **Guard script de isolamento** (ver 3.1).
4. **Commitar separado** do que vem na fase 2.

### 3.1 Por que guard script, e não teste automatizado

O frontend não tem infraestrutura de teste nenhuma, e o Modo Balcão é frontend puro
**por construção** — o `balcao.store.ts` grava em localStorage e não muda nenhuma
regra de backend. Os 445 pytest não alcançam nada disso, nem em princípio.

Montar vitest/playwright + mocks de Pinia, TanStack e axios para cobrir isto é
decisão arquitetural própria, não item de fase de balcão. Enfiada aqui, ela tira a
fase 1 de *uma sessão* para *uma semana* e empurra todo o resto — exatamente a
armadilha que o plano evita na fase 5.

A barreira idiomática deste repositório é o **guard de build** (`check:tokens`,
`check:paleta`, `check:pix`, `check:print-bw`, `check:sidecar`). Um `check:balcao`
trava o invariante que de fato ameaça as três lojas: que `modoBalcao` só seja lido
nos arquivos autorizados, isto é, que a chave não vaze para o resto do módulo.

⚠️ **O guard protege arquitetura, não comportamento.** Escrever isso no DoD, para
que daqui a três meses ninguém leia "tem guard" como "tem teste do Modo Balcão".

> **Prova (manual, e é assim mesmo).** Com o Modo Balcão desligado, uma venda de
> assistência técnica produz os mesmos efeitos de negócio e o mesmo layout funcional
> da versão anterior — mesmo modal de cliente, mesmo checkbox, mesmos totais, mesmos
> campos no cupom. Não é comparação byte a byte: horário e número sequencial variam
> por natureza. Ligado: a venda começa no produto e o Enter no Dinheiro fecha.

---

## 4. Fase 2 — O caminho de teclado

**Custo:** 2 a 3 dias. **Risco:** baixo. **É a maior dor no balcão.**

Cinco dos seis achados são o mesmo problema visto de ângulos diferentes: **quando o
atalho do leitor não morde, o operador fica sem caminho de teclado.** O sexto é
código morto.

### 4.0 Estoque zerado: não é decisão de produto, é a tela ignorando a chave

**A configuração já existe.** `permitir_venda_estoque_zerado` vive em
`configuracao_produtos` (por empresa, `default=True`), tem tela em Configurações
(Produtos e Estoque · Regras de Vendas), e o backend a aplica em dois pontos:
`services/venda.py:158-164` (adicionar item) e `:216-221` (atualizar item).

**O módulo de vendas nunca a lê.** `ProductSearch`, `ProductOption` e
`useProductSearch` decidem por conta própria — e erram nos dois sentidos:

| Chave | Backend | Tela hoje | Resultado |
|---|---|---|---|
| Ligada (padrão) | aceita vender zerado | bloqueia clique e Enter no zero | a loja configurou "pode" e o sistema diz "não pode" |
| Desligada | recusa | abre "Vender mesmo assim" | o operador confirma e leva erro do servidor |

Há ainda dois desencontros menores no mesmo lugar:

- **Limiar.** O backend decide por `quantidade > estoque_disponivel` (insuficiente);
  os dois guards do front estão em `estoque <= 0` — `ProductOption.vue:30`
  (`isDisabled`) e `useProductSearch.ts:194` (Enter). O `tryAutoAdd` já usa o limiar
  certo, e é por ele que clique e Enter já passam para estoque positivo insuficiente.
- **Default divergente.** `configuracoes.store.ts:72` assume `?? false`; o modelo
  assume `True`. Divergem enquanto a configuração não existir.

**Então o commit B não muda regra de negócio de ninguém.** Ele faz a tela obedecer a
chave que a loja já tem:

> **Chave ligada** → avisa e deixa passar, nos três caminhos, no mesmo limiar do
> backend. **Chave desligada** → bloqueia com mensagem que explica o porquê — nem
> silêncio, nem modal que termina em erro do servidor.

Nada a comunicar às três lojas: o comportamento passa a seguir a configuração delas,
que hoje é ignorada.

### 4.1 A função de domínio

As três portas convergem para uma função só. Não é estética: é o que impede a sexta
porta de nascer com regra própria.

```
leitor ─────┐
teclado ────┼──> tentarAdicionarProduto(...)
clique ─────┘
```

**Ela é assíncrona.** Para estoque zerado, aguarda a decisão do
`AvisoEstoqueNegativoModal` e só então resolve com o resultado final da tentativa.
Sem isso, o refactor reproduz o bug atual dentro da abstração nova: hoje
`tryAutoAdd` abre o modal e retorna `void`, e quem conclui é o `confirmarAutoAdd`,
depois, por outro caminho — o chamador nunca sabe o que aconteceu.

Cinco resultados. `out_of_stock` **não** é um deles: é uma transição que exige
decisão humana.

```
tentarAdicionarProduto()
    ↓
resolver código
    ├─ inexistente → not_found  + feedback
    ├─ ambíguo     → ambiguous  + feedback
    ├─ erro        → error      + feedback
    └─ encontrado
          ↓
       estoque?
          ├─ suficiente → added
          └─ zerado
                ↓
            aguarda modal
               ├─ cancelar  → cancelled
               └─ confirmar → added
```

### 4.2 Os seis commits

| | Commit | Conteúdo |
|---|---|---|
| **A** | convergência estrutural | As três portas passam a chamar `tentarAdicionarProduto`. **Nenhum comportamento muda.** |
| **B** | estoque | As três portas passam a ler `permitirVendaEstoqueZerado` e a usar o limiar do backend. Corrige o default do store (`?? false` → `?? true`) |
| **C** | resolução de código | `not_found`, `ambiguous` e **`error`** ganham feedback |
| **D** | seleção | Destaque determinístico: nasce em `0`, o watch volta para `0` |
| **E** | leitor | Flush do debounce quando o atalho não morde |
| **F** | limpeza | Remove `quantityInputRef` (declarado, exportado, nunca ligado) |

**Regra do commit A, e ela é dura:** pode **mover** código, não pode reescrever
condição. Se você se pegar mexendo num `if`, aquilo pertence a B–F. Num repositório
sem teste de frontend, "não mudou comportamento" não é demonstrável por execução —
só por leitura do diff. A regra é o que torna a leitura suficiente.

A vantagem não é estética. Se depois da implantação aparecer *"EAN funciona mas SKU
interno parou de selecionar"*, dá para achar qual mudança introduziu a regressão, em
vez de investigar um commit de 300 linhas que refatorou e mudou cinco regras ao
mesmo tempo.

### 4.3 A dependência: B antes de D

`sortedProducts` empurra o esgotado para o fim da lista. Se o produto de código
exato estiver zerado, o índice 0 é **outro** produto — e destacar o primeiro
cegamente aponta a arma para o item errado.

Com o B feito, o produto certo pode ficar no topo mesmo zerado, e o aviso segura a
venda por um instante. Daí a ordem `B → D → E`, com `C` independente e encaixável em
qualquer ponto.

O **E não é feature separada**: "cair na busca com o item certo já destacado" *é* o
D aplicado ao caminho do leitor. O código próprio dele é só o flush do debounce, e
isso não tem valor nenhum sem o D. Podem ser um commit lógico só.

### 4.4 Por que ficou mais barato do que parecia

`db/crud/produto.py` já tem `_CAMPOS_EXATOS` e **já joga o casamento exato de
`codigo_produto` / `codigo_barras` para o topo da lista**. Destacar o primeiro
resultado não é só ergonomia — é herdar de graça um ranking já calculado.

Consequência: **código interno de 4 dígitos e SKU alfanumérico voltam a ter caminho
de teclado sem mexer no `MIN_DIGITOS` nem no regex.** O `pareceCodigoDeBarras` deixa
de ser um portão e vira o que o comentário dele já diz que ele é: um atalho para
pular o debounce, não a única via.

(`sku` no front é alias de `codigo_produto` — `schemas/produto.py:63` — então o
`encontrarPorCodigoExato` e a busca do backend falam do mesmo campo.)

### 4.5 Por que o silêncio do leitor é pior do que parece

Quando `tentarBipar` devolve `false`, o Enter cai em `composableKeydown` — mas
nesse instante `isSearching` é **false**, porque `debouncedSearchTerm` ainda está
vazio (o leitor digitou em 5 ms, o debounce é 300 ms). Morre no early-return da
`:163`.

Não é "o Enter não escolheu nada na lista" — é que **a lista ainda não existe**
quando o Enter chega. O segundo Enter também não resolve, agora por causa do índice
`-1`. Dois bugs empilhados, um sintoma só.

### 4.6 São DUAS telas de produto, não uma (achado da execução)

Descoberto ao implementar: o módulo tem duas buscas de produto vivas ao mesmo
tempo, as duas chamando `useProductSearch`.

| | Busca inline (a barra) | Adicionar Produto (a modal) |
|---|---|---|
| Teclado | setas + Enter | **nenhum** — nem ligava o `handleKeydown` |
| Leitor de código de barras | sim | não |
| Quantidade / desconto | não, sempre 1 | sim |
| Regra de estoque | `tryAutoAdd` | `handleAdd` — **segunda escrita da mesma regra** |

A modal era **mouse-only por construção**. Isso reforça o commit A em vez de
enfraquecê-lo: a convergência não juntou três portas, juntou quatro, e apagou uma
regra de estoque duplicada que já tinha deixado de ser idêntica à irmã.

**As duas continuam existindo, e a decisão sobre isso fica em aberto** — a inline
é o caminho de 95% das vendas de balcão, a modal é o caso "3 unidades com
desconto". O que mudou é que agora as duas se alcançam pelo teclado e obedecem à
mesma regra:

- **F3** abre a modal de dentro da venda (o atalho não existia; F3 estava livre).
- Dentro da modal, seta escolhe e Enter seleciona; com produto selecionado, Enter
  adiciona. Enter na lista **não** pula direto para o carrinho: a quantidade é o
  motivo de a tela existir.
- O botão de quantidade da lista inline abre a modal **já buscando o produto**
  (`termoInicial`), em vez de obrigar a digitar de novo.

### 4.7 Orçamento não segue a chave — e é o backend que manda

`services/venda.py` consulta `permitir_venda_estoque_zerado`.
`services/orcamento.py` (`:106` e `:151`) **não consulta**: recusa estoque
insuficiente sempre.

Aplicar a mesma regra nos dois faria o orçamento abrir "vender mesmo assim" para
algo que o servidor recusa em seguida — exatamente o bug que a fase 2 conserta,
reintroduzido na porta ao lado. Cada fluxo espelha o **seu** backend.

Fica registrado como divergência do backend, não como decisão de tela: os dois
serviços discordam sobre a mesma regra. Unificá-los é mexer em regra de venda das
três lojas e não entra aqui.

### 4.8 O gatilho do refetch

`useProductQuery` roda com `refetchInterval: REFETCH_REALTIME` (10 s). O TanStack
preserva a referência quando o dado não muda, então o watch só dispara quando algo
muda de verdade — e o que muda em PDV é o **estoque, alterado por outro terminal**.
O destaque pode sumir da mão do operador porque o colega do outro caixa vendeu uma
unidade. É raro, e é exatamente o cenário de duas máquinas da fase 3.

> **Prova.** Vinte bipadas no leitor da loja, sem tocar no mouse, com três tipos de
> código: EAN-13 de garrafa, código interno de 4 dígitos e SKU alfanumérico. Mais um
> produto zerado e um código cadastrado em dois produtos. **Nenhuma das 22
> tentativas pode terminar em silêncio.**
>
> **Prova do código compartilhado (obrigatória):** uma venda de assistência técnica
> com produto zerado, **com a chave ligada e com a chave desligada**. Ligada: clique,
> Enter e leitor chegam à mesma decisão e o servidor aceita. Desligada: os três
> recusam com a mesma mensagem, e nenhum deles chega a mandar requisição que o
> servidor vá negar. Mesma prova em oficina e serigrafia.

---

## 5. Fase 3 — Terminais persistentes

**Custo:** média — **inclui migration**. **Risco:** baixo. **Destrava "servidor + 2
caixas".**

As colunas `nome` e `papel` existem em `terminais_conectados` desde a fase 1, e não
há tela para preenchê-las. Mas o trabalho não é a tela.

### 5.1 O invariante já existe; o que falta é durabilidade

`terminal_conectado.py:50` documenta a semântica, e ela já é a segura:

```
papel = NULL       → exige abertura de caixa
papel = PDV        → exige abertura de caixa
papel = RETAGUARDA → não exige          ← exceção explícita, nunca fallback
```

**Invariante da fase 3: terminal não configurado nunca perde a trava de caixa.**
Errar para "cobra turno demais" custa um clique de configuração; errar para "não
cobra" custa o controle da gaveta — e falha em silêncio, porque nada quebra: o
dinheiro só não bate no fim do dia.

Então não é "implementar a trava". É **preservar a semântica enquanto se adiciona
uma forma durável de configurar a exceção**.

### 5.2 Duas tabelas, não uma

`terminais_conectados` é volátil: nome e papel evaporam no logout. O dono marca o PC
como RETAGUARDA, sai no fim do dia, e amanhã a linha voltou a NULL. O invariante
segura (volta a pedir turno, o lado seguro), mas o recurso não funciona — a
configuração se desfaz sozinha todo dia.

"Terminal é entidade persistente ou sessão?" — são **as duas coisas**, e por isso
são duas tabelas:

```
Terminal (durável, chaveado por HWID)      TerminalConectado (volátil)
├── hwid                                   ├── hwid
├── nome                                   ├── ultima_sinc
└── papel                                  └── estado de conexão
```

Tornar durável a tabela de conexão misturaria dois tempos de vida na mesma linha.

**Consequências práticas de não fazer:** a coluna **Terminal** do relatório de caixa
fica vazia — e aí não dá para saber qual gaveta fechou faltando; e o PC do dono
continua pedindo abertura de turno para consultar relatório, criando sessão fantasma
que nunca fecha direito.

> **Prova.** Dois PCs ligados, configurados, **logout e login**: nome e papel
> continuam lá. O relatório de caixa mostra o nome de cada terminal na coluna, e a
> retaguarda abre o sistema sem pedir turno.

---

## 6. Fase 4 — Instalar na adega

**Custo:** meio dia. **Risco:** alto se apressado.

`npm run build:sidecar` → instalador → instalar → ligar as chaves lá.

O sidecar está desatualizado desde a fase 0.5, quando o backend mudou. Um instalador
gerado hoje sem regerar o sidecar leva o backend velho, e o sintoma chega como
"segmento `pdv` recusado no cadastro" ou "relatório de caixa mostrando zeros".

### 6.1 O procedimento, em ordem

```
build do código
   ↓
build do sidecar          ← npm run build:sidecar
   ↓
build do instalador
   ↓
versão/build identificável
   ↓
instalação
   ↓
reinício do backend       ← task agendada StartBigServer
   ↓
smoke test
```

### 6.2 Build ID no health — obrigatório, não sugestão

Hoje `/api/health` devolve `{"status": "ok"}` e nada mais; o `version="1.0.0"` está
chumbado no metadata do FastAPI e não sai por lugar nenhum. O backend não tem noção
de qual build ele é.

O ponto de resolver já existe: o `build-sidecar.mjs` é quem empacota, então é ele
quem carimba SHA + timestamp num arquivo que entra no bundle, e o health lê.

```
build-sidecar.mjs → gera metadata de build → empacota → /api/health expõe
```

Isso transforma "essa máquina está rodando qual build?" de meia hora de diagnóstico
num olhar. Considerando que "código novo com processo antigo" já custou duas rodadas
de investigação, é o melhor retorno por linha do plano.

⚠️ O endpoint é **aberto** — fora do router v1, sem autenticação. Regra explícita:
**somente metadata de identificação (versão, build, sidecar). Nunca segredo,
caminho interno ou configuração.**

### 6.3 A ordem das lojas

> **Não mande as fases 4 e 5 do plano do caixa no mesmo instalador** para as três
> lojas que já rodam. Se algo quebrar, você precisa saber se foi o leitor ou o sumiço
> da Ordem de Serviço. Para a **adega** tanto faz — é instalação nova.

Nada a comunicar às lojas sobre estoque zerado (ver 4.0): o comportamento passa a
seguir a configuração que cada uma já tem.

> **Prova.** Uma venda real na adega, do `F2` ao cupom saindo, com a gaveta abrindo.
> Depois abrir e fechar o caixa e conferir a diferença no relatório.

---

## 7. Fase 5 — Permissões de verdade

**Custo:** projeto próprio, o maior dos cinco. **Risco:** pode trancar as 3 lojas.

Você cria um cargo e marca **só "Visualizar"** em Vendas, esperando que a pessoa
olhe mas não apague. **Ela apaga.** O sistema não pergunta *"pode EXCLUIR em
Vendas?"*, pergunta *"tem ALGUMA permissão em Vendas?"* — e "Visualizar" já responde
que sim:

```python
# app/api/v1/endpoints/venda.py
module_permission = ["venda", "view_sales", "manage_sales", "delete_sales"]

# app/core/depends.py
if any(permissoes.get(p) is True for p in perms):
    return usuario_token          # basta UMA
```

É uma porta com três chaves na parede cuja fechadura só confere se você tem
*alguma* chave. Vale para produtos também: `POST /produtos/` exige `"produto"`, a
mesma chave do GET.

**Isso é pior que não ter a granularidade:** a tela dá a sensação de ter limitado
alguém que continua podendo tudo.

### 7.1 O limite de escopo — explícito

> **Não refatorar o sistema de permissões inteiro.** Corrigir somente a semântica
> necessária para que `view` / `manage` / `delete` funcionem corretamente e de forma
> compatível.

Sem esse limite, a fase 5 come o tempo das fases 1–4 e aumenta exatamente o risco
que o plano tenta evitar.

### 7.2 A matriz, antes do código

| Ação | Permissão |
|---|---|
| Listar / consultar vendas | `view_sales` |
| Criar / editar venda | `manage_sales` |
| Excluir venda | `delete_sales` |
| Listar produtos | `view_produtos` |
| Alterar produto | `manage_produtos` |
| Excluir produto | `delete_produtos` |

**A regra vale no backend, endpoint por endpoint.** `GET` → `view_*`, `POST`/`PATCH`
→ `manage_*`, `DELETE` → `delete_*`. Se a proteção ficar só no frontend, a
granularidade continua falsa. Cada endpoint precisa de auditoria individual.

Testar com seis perfis: master, cargo legado migrado, cargo só-view, cargo sem
permissão, gerente/administrador, usuário comum. Isso evita que a implementação vire
uma sequência de `if` espalhada.

### 7.3 Migração antes da semântica nova — e sai num instalador só

```
view_sales existente  ──migração──>  manage_sales
```

e só então a regra nova passa a valer para cargos criados dali em diante.

Isso **não exige duas releases**. `app/core/tarefas.py` roda `aplicar_migracoes()`
no startup, antes de o backend servir a primeira requisição — a ordem é garantida
dentro do mesmo instalador. Nenhuma viagem intermediária à loja.

### 7.4 O que mais falta

**Redefinir senha de funcionário.** Hoje só existe `PATCH /usuarios/me/senha` (cada
um troca a própria). Ninguém redefine a de outro, nem o master. Operador que esquece
a senha não tem caminho no sistema.

> **Prova.** Instalação sobre banco copiado de produção → startup → migração →
> aplicação sobe → **todo mundo que trabalhava ontem continua trabalhando**. E um
> cargo novo com só "Visualizar" recebe 403 ao tentar excluir.

---

## 8. A prova final: a venda sem mouse

Cronometrar uma venda de três garrafas, do `F2` ao cupom, contando **saídas
voluntárias do teclado no fluxo feliz**. Voluntárias porque, se aparecer erro
inesperado, o operador tem que poder usar o mouse — a métrica mede o caminho normal,
não vira algema.

**O alvo é zero.** Registrar também o tempo, como baseline objetiva para comparar
alterações futuras:

```
Venda: 3 produtos
Tempo: XX s
Saídas do teclado: 0
Códigos: EAN-13 · interno · SKU
```

É esse número, e não a suíte de testes, que diz se o PDV ficou profissional.
"445 testes + vue-tsc 0" prova integridade técnica; não prova ergonomia.

---

## 9. Definition of Done

**Fase 1** — Modo Balcão commitado isoladamente · ON e OFF comprovados no app ·
OFF comparado contra a baseline do `git show HEAD` · guard de isolamento no build ·
nenhum framework novo · DoD registra que o guard protege arquitetura, não
comportamento.

**Fase 2** — As 22 tentativas produzem resposta · nenhum caminho de entrada tem
regra divergente de estoque · **os três caminhos respeitam
`permitir_venda_estoque_zerado` nos dois estados, no mesmo limiar do backend** · EAN,
código interno e SKU funcionam sem mouse · código ambíguo nunca é escolhido
automaticamente · erro de rede na bipada produz feedback · prova medida do fluxo de
assistência técnica antes/depois.

**Fase 3** — Dois terminais persistem nome e papel **através do logout** ·
retaguarda não pede abertura de caixa · terminal não configurado continua pedindo.

**Fase 4** — Sidecar reconstruído · build identificável no `/api/health` · backend
reiniciado · venda real da adega chega ao cupom · gaveta e relatório conferidos.

**Fase 5** — Banco de produção copiado continua funcionando · `view` não concede
escrita · `manage` não concede exclusão · `delete` é exigido para excluir ·
redefinição administrativa de senha funciona · master/gerente/administrador
preservam exatamente as regras atuais.

**Final** — Venda de três garrafas · `F2` → cupom · zero saídas voluntárias do
teclado · tempo registrado.

---

## 10. O que fica de fora, e por decisão

- **Código de balança** (EAN-13 começando em 2, com peso ou preço embutido). Adega
  vende garrafa fechada. Se entrar hortifrúti ou frios fatiados, vira obrigatório —
  e aí não é só ler o prefixo: o preço passa a vir do código em vez do cadastro, e a
  quantidade precisa virar fracionária no módulo de vendas, que hoje não é. É
  sprint, não ajuste.
- **Multiplicador de quantidade** (digitar `3` `*` antes de bipar). Padrão em PDV
  brasileiro e barato, mas só faz sentido depois do caminho de teclado da fase 2.
  Primeira coisa da próxima rodada.
- **Infraestrutura de teste de frontend.** Decisão arquitetural legítima e própria,
  com mérito próprio. Não entra escondida numa fase de balcão.
- **Categoria na sangria** ("fornecedor", "retirada do dono", "despesa fixa").
  Decidido em 17/08/2026: fica para o **módulo financeiro**. Uma categoria agora
  cobriria só o dinheiro que passa pela gaveta — o boleto pago pelo banco
  continuaria invisível — e criaria uma taxonomia que o financeiro provavelmente
  refaria. O que o caixa já entrega pronto: valor, data, autor, sessão e motivo
  em texto. O financeiro acrescenta significado a um registro que já existe, em
  vez de recriá-lo. `movimentacoes_financeiras` já tem `tipo` ENTRADA/SAÍDA e
  `origem`, então contas a pagar entram como origem nova no mesmo livro.
- **NF-e.** Sprint dedicada, sem data. Não bloqueia a adega.
- **Refatorar o `ProductSearch.vue` além do commit A.** Mudar estrutura e
  comportamento no mesmo momento é trocar o pneu com o carro andando.

---

## 11. Coisas que não podem ser esquecidas

- **Master é quem tem CARGO CHAMADO "Master"** — `is_master = (cargo.nome.lower() ==
  "master")`. Não é checkbox nem conta única.
- **Visão gerencial vem do NOME do cargo**: contém "gerente" ou "administrador" → vê
  os dados de todos. Um cargo "Gerente de Caixa" daria visão total sem querer.
- **Relatórios não filtra por funcionário.** Quem tiver a permissão vê o faturamento
  da empresa, o ranking e a comissão de todos. A proteção é não marcar a permissão.
- **Cada funcionário precisa do PRÓPRIO login.** Credencial compartilhada faz o
  relatório de caixa dizer o mesmo nome em todas as linhas — e aí não há como saber
  quem fechou faltando.
- **Reinicie o backend depois de atualizar.** Código novo com processo antigo já
  custou duas rodadas de diagnóstico.
