# Plano: cadastro de produto inteligente (e no padrão do mercado)

Escrito em 12/09/2026, na `feat/fiscal-nfe` (HEAD `dd6f86b`). Nasceu de uma
tentativa simples: **cadastrar um produto e mandar para a SEFAZ**. O caminho
existe de ponta a ponta desde 11/09 (`fiscal-conclusao-plano.md`), mas o
primeiro passo — o formulário — não está pronto para ele.

**Revisado no mesmo dia**, depois de duas coisas:

1. O dono não entendeu o campo do CSOSN ("não achei o 102, não entendi"). Se ele
   não entende, nenhum lojista entende.
2. A pesquisa de como Bling, Omie, TagPlus e Tiny resolvem isso (§3, com fonte).
   A resposta do mercado não é "explicar melhor o 102" — é **não perguntar o 102
   no produto**. Isso mudou o eixo do plano e a ordem das fases.

Escopo: o formulário de **produto** (cadastro e edição) e a camada de tributação
que fica atrás dele. Fora de escopo: cadastro de **serviço** (`servico_fiscal`),
que recebe o mesmo tratamento depois.

**Nada começa a ser codado antes de as decisões da §4 estarem aceitas.**

---

## 0. O que "pronto" significa

| # | Critério de aceite | Hoje |
|---|---|---|
| P1 | Cadastrar um produto novo e **emitir a nota dele sem reabrir o cadastro** | impossível — criação não salva fiscal (§2.A1) |
| P2 | O lojista **nunca escolhe um código fiscal** para vender o que vende todo dia | escolhe, entre 10 opções em linguagem de lei (§2.B11) |
| P3 | O que a SEFAZ recusaria é **recusado no cadastro**, nomeando o campo | só o gate de emissão recusa (§2.B4) |
| P4 | NCM **encontrável por descrição**, não digitado de cabeça | `<input>` de 8 dígitos (§2.B5) |
| P5 | Cadastrar 30 produtos parecidos **não** é preencher 30 vezes o mesmo fiscal | é (§2.B6) |
| P6 | Nenhum campo na tela que o banco **descarta em silêncio** | "Localização no Estoque" é descartado (§2.C8) |
| P7 | O que entra **volta igual** ao reabrir o produto | IBS/CBS perde a casa decimal (§2.C9) |
| P8 | A lista de produtos mostra **quem está pronto para nota** e quem não | só o drawer de pendências, e só NCM |
| P9 | O dono consegue **mandar o catálogo fiscal para o contador** e trazer de volta | não existe |
| P10 | **Campo que não se aplica ao regime da empresa não aparece na tela** | aparecem CST e CSOSN juntos (§2.B7) |
| P11 | Quem **não** emite nota continua cadastrando produto em 4 campos | vale hoje, e é cláusula de não-regressão |

P11 não é detalhe: três segmentos rodam em loja real e nenhum deles emite nota
ainda. Toda inteligência deste plano vive **dentro** do `v-if="nfeDisponivel"`.

---

## 1. Onde estamos

A emissão funciona (homologação). O cadastro é o gargalo, em dois sentidos: ele
não salva o que a emissão precisa, e pede ao lojista decisões que não são dele.

---

## 2. Os furos (12/09/2026)

### A — o que impede o teste de hoje

**A1. A criação não salva nada fiscal.** `transformToCreateRequest`
(`useProductForm.ts:296`) não monta o bloco `fiscal` — só o caminho de update
monta (linha 348 em diante). E a seção fiscal, em modo criação, mostra apenas um
aviso pedindo para salvar e voltar depois (`DadosFiscaisSection.vue:145`). O
fluxo real hoje:

```
Cadastrar Produto → fechar → achar o produto na lista → abrir em edição
→ preencher 8 campos fiscais → Salvar Alterações → só então emitir
```

Entre os dois passos o produto aparece em `produtos_sem_ncm`
(`services/pendencias_globais.py:32`) e derruba o resumo do Centro Fiscal.

**A2. Nenhum default onde a resposta é quase sempre a mesma.** Origem nasce
vazia; unidade tributável nasce vazia — e o `validators.py:204` **já documenta**
que tirou esse campo da exigência porque `uTrib = uCom` é o correto no varejo
fracionado. O formulário pede à mão um campo que o backend decidiu resolver
sozinho.

**A3. Quantidade inicial obrigatória ≥ 1** (`product.schema.ts:40`), com default
0 no próprio formulário. Não se cadastra catálogo antes de comprar a mercadoria —
e a configuração `permitir_venda_estoque_zerado` existe, o que faz a regra do
formulário contradizer a configuração da loja.

**A4. `codigo_produto` aceita 100 no front e 50 no backend.** Zod `max(100)`
(`product.schema.ts:17`), coluna `String(100)` (`produto.py:33`), e
`ProdutoCreate.codigo_produto` `max_length=50` (`schemas/produto.py:15`). SKU de
60 caracteres passa na tela e volta 422.

### B — o que falta de inteligência

**B11. O furo central: o formulário pede uma decisão que não é do produto.**
O campo CSOSN oferece 10 códigos em linguagem de lei
(`fiscal.constants.ts:17`) — `102 - Tributada sem permissão de crédito` — e
**7 deles o motor não calcula** (suportados: `101`, `102`, `500` em
`tax_engine/constants.py:24`). O lojista pode escolher um código que será
recusado depois, e o código que ele deveria escolher está escrito numa frase que
não significa nada para quem vende mouse. Pior: é a **mesma** resposta para
todos os produtos da loja, perguntada produto a produto. A §3 mostra que nenhum
sistema profissional faz isso.

**B4. O formulário não conhece as amarrações que a SEFAZ cobra.** O backend
conhece todas (`validators.py:204–280`):

| Regra já escrita no backend | O formulário avisa? |
|---|---|
| CEST obrigatório quando o CST/CSOSN indica substituição tributária | não |
| CST 20 exige redução de base de cálculo | não |
| CST 20 exige `cBenef` em SP, PR, RS, SC e GO | o campo aparece, sem exigir |
| CST/CSOSN fora do que o motor calcula | não |
| NCM/CFOP/CEST com contagem de dígitos errada | sim (é o único que o Zod cobre) |

**B5. NCM é texto livre.** Sem busca por descrição, sem conferir se o código
existe, sem sugerir CEST a partir dele. `BASE_NCM` e `BASE_CEST` estão declarados
como fontes no motor (`derivacao/types.py:34`) e não implementados.

**B6. Cada produto é preenchido do zero.** Não há cópia, nem aplicação em lote,
nem edição em massa. O drawer que existe
(`FiscalResolucaoProdutosDrawer.vue`) pede NCM e CFOP na mão, produto por
produto, e ignora os outros seis campos obrigatórios.

**B7. O regime é adivinhado por texto.** `regime_tributario.includes('Simples
Nacional')` (`DadosFiscaisSection.vue:75`). Sem regime preenchido, a tela mostra
**CST e CSOSN ao mesmo tempo** e aceita os dois — combinação que não existe em
nota nenhuma.

### C — dado perdido

**C8. Campo fantasma: "Localização no Estoque".** Está na tela
(`DadosProdutoSection.vue:195`), no Zod, nos dois payloads e no dicionário de
campos legíveis do histórico (`services/produto.py:156`). A coluna está
**comentada** no model (`produto.py:42`) e no schema (`schemas/produto.py:26`).
O lojista digita "Corredor A, Prateleira 3", salva com sucesso, e o dado é
descartado sem erro nenhum. (O Tiny tem esse campo na edição em massa — §3.)

**C9. IBS/CBS perde a casa decimal ao reabrir.** Grava `Math.round(valor * 100)`
e lê `Math.round(valor / 100)` (`useProductForm.ts:266`): 5,5 % salva 550 e volta
6. ICMS, PIS e COFINS não têm esse `round` — o defeito é só do par IBS/CBS.

**C10. Duas listas de unidade divergentes.** A comercial é hard-coded na seção
(`DadosProdutoSection.vue:36`: G, ML, CM, PC) e a tributável é
`UNIDADE_PRODUTO_OPTIONS` (`fiscal.constants.ts:54`: M2, PAR, sem G e sem PC).

---

## 3. O achado duplo

### 3.1 A derivação fiscal existe e não tem fio

Mesmo padrão da NFC-e que não estava ligada ao caixa (§2 do
`fiscal-conclusao-plano.md`): obra feita dos dois lados, falta a costura.

| Peça | Estado | Onde |
|---|---|---|
| `derivar_produto(ctx)` — CST/CSOSN, origem, CST PIS/COFINS e CFOP **coerente com a situação** | feito | `derivacao/__init__.py:62` |
| Contexto do cadastro (UF, CRT, tipo de atividade) | feito | `derivacao/resolver_db.py:37` |
| `GET /fiscal/sugestao/produto` — não exige o plano fiscal, não persiste nada | feito | `endpoints/fiscal.py:569` |
| `useSugestoesFiscais` — aplica, marca o que veio de sugestão, expõe a fundamentação | feito, **nenhum importador** | `modules/fiscal/composables/useSugestoesFiscais.ts` |
| Formulário consumindo isso | **não existe** | — |

Cada campo sugerido já vem com `fonte`, `confianca`, `fundamentacao` (o texto do
"por quê?") e `exige_confirmacao`, que marca onde errar produz **nota aceita e
errada**. A regra está na docstring do módulo e é a que este plano obedece:

> O pior desfecho de uma automação fiscal não é a nota rejeitada — é a nota
> ACEITA E ERRADA. Rejeição custa cinco minutos; recolhimento a menor custa
> multa, juros e responsabilidade do lojista.

### 3.2 Como os sistemas profissionais resolvem (pesquisado em 12/09/2026)

Quatro sistemas, quatro páginas de ajuda oficiais, **a mesma arquitetura**: a
tributação **não mora no produto**. Mora um nível acima, e o produto só aponta
para ela.

| Sistema | Onde a tributação mora | O que fica no produto |
|---|---|---|
| **TagPlus** | "Tributação Padrão" **por NCM** — CFOP, CST/CSOSN, alíquotas de ICMS/PIS/COFINS/IPI e bases | só o NCM e a origem |
| **Omie** | regra **por NCM**, desdobrável por UF e por tipo de cliente | a tela "Recomendações Fiscais do Produto" pede origem, tipo do produto, CEST (com filtro por NCM), unidade tributável, EAN tributável — **CSOSN e CFOP não aparecem lá** |
| **Bling** | "Natureza de Operação" (a tributação do tipo de operação) + "Grupos de produtos" para agrupar quem tem a mesma regra | NCM, CEST, origem |
| **Tiny** | edição em massa como ferramenta de primeira linha | NCM, CEST, origem, unidade, **localização**, marca, fornecedor — aplicáveis a vários produtos de uma vez |

Três detalhes que valem mais que o resto:

1. **O catch-all é padrão de mercado.** O TagPlus tem o NCM `00000099`
   = "TODOS NCMs" e orienta: empresa do Simples Nacional normalmente usa **uma
   única tributação padrão para todos os produtos**. A documentação do Mais PDV
   diz literalmente que o sistema **já vem com 102** e, se a loja é compra e
   revenda simples, "pode deixar 102".
2. **O CEST é filtrado pelo NCM** (Omie). Ninguém digita CEST de cabeça.
3. **Todos mandam alinhar com o contador uma vez** — não produto a produto. O
   sistema oferece estrutura e padrão; a decisão fiscal é confirmada no começo.

A conclusão que interessa: o nosso formulário não está difícil de entender por
falta de texto de ajuda. Ele está **no lugar errado**. Perguntar o CSOSN em cada
produto é pedir 40 vezes a resposta que a loja dá uma vez.

### 3.3 O formulário do TikTok Shop (trazido pelo dono em 12/09)

O dono cadastrou produtos lá e achou simples. Vale copiar a forma. A tela
inteira, para emitir NF-e, tem **doze campos — oito obrigatórios**:

| Obrigatório | Opcional |
|---|---|
| NCM, Natureza da operação, CST de PIS e COFINS, Origem, CSOSN, Unidade de medida | CEST, Ex TIPI, RECOPI, nº da Ficha de Conteúdo de Importação (FCI), Alíquota de imposto aproximada, Dados adicionais do produto |

O que essa tela ensina, em ordem de importância:

1. **Ela mostra CSOSN e não CST.** A empresa é do Simples, então o campo do
   regime normal nem existe na tela. O conjunto de campos é montado a partir do
   **cadastro da empresa** — é exatamente o que o dono pediu: "o sistema tem que
   entender pela configuração da empresa quais campos são necessários".
2. **Não existe campo de CFOP.** No lugar dele, **Natureza da operação** — em
   português. Nós já derivamos a natureza a partir do CFOP
   (`derivacao/cfop.py:166`) e já a gravamos no documento
   (`venda_nota_fiscal.py:40`): dá para mostrar a natureza e guardar o CFOP por
   baixo, sem inventar nada.
3. **Todo campo tem um "?" do lado.** Doze campos, doze ajudas. É o item mais
   barato desta lista inteira e o que mais muda a sensação de "eu entendo esta
   tela".
4. **Metade fica em branco e emite assim mesmo.** Campo opcional é opcional de
   verdade, e a tela não finge que é tudo obrigatório.

Campos que eles têm e nós **não** temos no `produto_fiscal`: Ex TIPI, FCI,
RECOPI, alíquota aproximada e `infAdProd` (dados adicionais que saem impressos
na nota). Nenhum é obrigatório para o caso do varejo comum — entram como lista
de espera, não na Fase 1.

E a diferença que precisa ficar dita: o TikTok é **marketplace**, não ERP. Ele
não tem onde guardar uma regra por NCM, então repete os 8 campos em cada
produto. Nós temos. A Fase 2 mantém a simplicidade da tela dele e ainda tira o
CSOSN do produto — a tela fica **menor** que a do TikTok, não igual.

---

## 4. Decisões

**D0. A tributação vira regra da loja, não campo do produto.** Três níveis, com
precedência igual à do TagPlus:

```
produto (exceção)  →  regra por NCM  →  tributação padrão da loja
```

- **Tributação padrão da loja**: uma vez, na configuração fiscal. Nasce
  preenchida pelo motor de derivação que já existe (CSOSN 102 / CST 00, CFOP
  5102, PIS/COFINS 49) e é confirmada pelo dono — de preferência junto com o
  contador.
- **Regra por NCM**: para o produto que foge (ST, monofásico, isento). Quem tem
  dez pneus cria uma regra e os dez obedecem.
- **Exceção no produto**: os 21 campos de hoje continuam existindo, como
  override, atrás de "tributação específica deste produto".

**D1. No cadastro do produto, só o que é do produto.** NCM (buscável), origem
(padrão 0), CEST (só quando o NCM indicar ST), unidade tributável (= comercial).
CSOSN, CFOP e CST de PIS/COFINS **saem da tela do produto** — exatamente como no
Omie. O lojista deixa de ver o 102.

**D2. O fiscal nasce com o produto, numa transação.** `ProdutoCreate` ganha
`fiscal: Optional[...]` e o endpoint grava os dois juntos. *Alternativa
recusada:* `POST /produtos` seguido de `PUT /produtos/{id}/fiscal` — duas
chamadas deixam o produto criado e o fiscal perdido quando a segunda falha, que é
o estado que estamos consertando.

**D3. Sugerir nunca preenche onde errar sai caro.** `exige_confirmacao` não
auto-aplica; `confianca: ambigua` exige escolha entre as `alternativas`. Campo
sugerido ganha marca e o "por quê?" ao lado; editar à mão tira a marca, e
sugestão nunca sobrescreve o que o usuário digitou.

**D4. A regra fiscal mora no backend, num lugar só.** Não se reescreve em Zod o
que `validators.py` já sabe: extrai-se de `verificar_produto_fiscal` uma função
pura sobre um rascunho e expõe-se um dry-run que a tela chama. O gate de emissão
passa a usar a mesma função — se divergirem, o cadastro aprova o que a emissão
recusa, a pior combinação possível.

**D5. NCM embarcado, não consultado online.** A loja tem internet ruim e o app já
é offline-first. A tabela entra como **dado semeado no banco**, nunca como
literal Python (T1), e a busca por descrição reusa `core/busca.py` — que já faz
acentos, palavras soltas e erro de digitação.

**D6. Onde o código fiscal ainda aparecer, aparece com etiqueta de gente.**
`102 · Venda normal — o imposto vai na guia do Simples`. E a lista separa os três
códigos que o motor calcula; os outros ficam atrás de "ver todos", com aviso de
que o sistema ainda não calcula. Isso vale para a tela de tributação padrão e
para o modo de exceção, não mais para o cadastro comum.

**D6b. Quem decide os campos da tela é o cadastro da empresa.** Um **mapa de
obrigatoriedade** derivado do regime, do CRT e da atividade — servido pelo
backend, não escrito em `v-if` espalhado. Regra: campo que não se aplica **não
aparece** (não aparece cinza, não aparece desabilitado). Simples Nacional vê
CSOSN e não vê CST ICMS nem alíquota de ICMS; regime normal vê o contrário; FCI
só aparece com origem importada; CEST só com ST. É o comportamento da tela do
TikTok (§3.3) e resolve de uma vez o furo B7, em que os dois campos apareciam
juntos.

**D6c. Natureza da operação na tela, CFOP por baixo.** O lojista escolhe "Venda
de mercadoria"; o sistema guarda `5102`. Já existe derivação nos dois sentidos
(`derivacao/cfop.py:166`) e a coluna já existe no documento fiscal.

**D6d. "?" em todo campo fiscal.** Uma frase por campo, em português de loja,
com um exemplo. Doze campos, doze ajudas — é o item mais barato do plano.

**D7. Unidade é uma lista só**, e a tributável nasce igual à comercial.

**D8. Quantidade inicial 0 é válida.** Cadastrar catálogo antes de comprar é caso
real, e quem não quer tem a configuração de estoque.

**D9. "Localização no Estoque" é entregue, não removida.** Está na tela, nos
payloads e no histórico; o Tiny a tem na edição em massa. Coluna nullable em
`produtos`, com migration.

**D10. Quem decide CST vs CSOSN é o servidor** (o campo que volta na sugestão,
conforme o CRT lido por `obter_crt`). Fim do `includes('Simples Nacional')`. Sem
regime definido, a tela pede para definir o regime.

**D11. O contador recebe planilha, não login.** Decisão do dono: acesso próprio
para o contador é boa ideia **mas só quando existir a versão web**. Hoje o dono
ou o administrador exporta um arquivo e manda. Formato: **CSV UTF-8 com BOM e
separador `;`**, que o Excel em português abre com dois cliques e não exige
dependência nova no sidecar (não há openpyxl nem xlsx no projeto — conferido).
A mesma planilha volta por importação. Se o contador reclamar do formato, `.xlsx`
entra depois, medindo o custo no PyArmor/PyInstaller antes.

**D12. Nada disso aparece para quem não emite.** Tudo sob `nfeDisponivel`, e o
teste de não-regressão é cadastrar produto com o módulo fiscal desligado e
comparar com o `git show HEAD` — medido, não deduzido.

---

## 5. Fases

### Fase 1 — o cano do cadastro *(destrava o teste na SEFAZ)*

Não mexe em arquitetura: faz o que já existe funcionar de uma vez.

> **Estado em 12/09/2026: Fase 1 COMPLETA no código** — 1.1 a 1.11 feitos.
> 1.370 pytest (20 novos: `test_produto_cadastro_fiscal.py` e
> `test_campos_produto.py`), vue-tsc 0, migration `p9q0r1s2t3u4`, head único.
>
> Três defeitos vieram de brinde, todos em produção hoje:
> `HTTPException` sem import fazia o 404 de "produto sem dados fiscais" virar
> 500; `ProdutoUpdate.codigo_barras` tinha teto 50 contra coluna de 100; e o
> `nota_fiscal` do `ProdutoUpdate` não existe no model — saiu.
>
> **Falta a prova no app** (P1): cadastrar e emitir sem reabrir o cadastro.
> Deploy na loja exige `npm run build:sidecar` (T8).

| # | O que muda | Arquivos |
|---|---|---|
| 1.1 | `fiscal` aceito no `POST /produtos`, na mesma transação (D2) | `schemas/produto.py`, `services/produto.py`, endpoint de produtos, `useProductForm.ts:296` |
| 1.2 | Seção fiscal habilitada na criação (cai o aviso "salve primeiro") | `DadosFiscaisSection.vue:145`, `ProductModal.vue:171` |
| 1.3 | Origem = 0 e unidade tributável = comercial como padrão (A2, D7) | `useProductForm.ts`, `DadosFiscaisSection.vue` |
| 1.4 | Quantidade inicial 0 permitida (D8) | `product.schema.ts:40` |
| 1.5 | `codigo_produto` com o mesmo teto nas três camadas (A4) | `schemas/produto.py:15` |
| 1.6 | Localização entregue, com migration (D9) | `models/produto.py:42`, `schemas/produto.py:26`, migration |
| 1.7 | Round-trip de IBS/CBS corrigido (C9) | `useProductForm.ts:266` |
| 1.8 | Listas de unidade unificadas (C10) | `fiscal.constants.ts:54`, `DadosProdutoSection.vue:36` |
| 1.9 | Rótulos de gente nos códigos que ainda aparecem (D6) | `fiscal.constants.ts` |
| 1.10 | Mapa de obrigatoriedade por regime: campo que não se aplica some (D6b, resolve B7) | endpoint novo em `fiscal.py`, `DadosFiscaisSection.vue` |
| 1.11 | "?" com uma frase em português em cada campo fiscal (D6d) | `DadosFiscaisSection.vue`, `fiscal.constants.ts` |

**Prova:** pytest do POST com `fiscal` aninhado (inclusive fiscal inválido
derrubando o produto junto); e, no app, cadastrar um produto e **emitir sem
reabrir o cadastro**. O que conta é a segunda.

### Fase 2 — a tributação sai do produto *(o coração do plano)*

| # | O que muda |
|---|---|
| 2.1 | Tabela de **tributação padrão da loja** (1 por empresa), nascida da derivação e confirmada pelo dono |
| 2.2 | Tabela de **regra por NCM** (0..n), com o catch-all como padrão da loja |
| 2.3 | Resolução em cascata no momento da emissão: produto → NCM → padrão (D0) |
| 2.4 | Cadastro de produto enxuga para NCM + origem + CEST + unidade (D1); os 21 campos viram "tributação específica deste produto", recolhida |
| 2.5 | Tela de tributação padrão com os rótulos de gente e só os códigos que o motor calcula (D6) |

> **Estado em 12/09/2026: backend FEITO (2.1, 2.2, 2.3).** 1.386 pytest (16
> novos), head `q0r1s2t3u4v5`, vue-tsc 0.
>
> - Tabelas `tributacao_padrao` e `regra_tributaria_ncm`, nascendo **vazias**.
> - `fiscal_efetivo()` resolve a cascata e está ligado nos cinco pontos de
>   leitura: as quatro emissões (NF-e e NFC-e de venda, duas da OS), o
>   `tax_engine` e o gate de `validators.py`.
> - Endpoints de tributação padrão e de regras por NCM — ler é de qualquer
>   usuário, escrever é só master.
> - **A propriedade que permite subir isto**: sem linha nas tabelas novas,
>   `fiscal_efetivo()` devolve o próprio `produto.fiscal`, sem cópia. Há teste
>   dedicado, porque três lojas emitem hoje e nenhuma terá configuração.
>
> **12/09/2026, mais tarde: Fase 2 COMPLETA (2.1 a 2.5).**
>
> - `FiscalTributacaoModal.vue` + cartão em Configurações Fiscais: a loja
>   responde uma vez, com o botão "Sugerir para mim" — que é o **primeiro
>   chamador** do `useSugestoesFiscais`, escrito há semanas e nunca usado.
> - Cadastro de produto enxuto: com a tributação padrão configurada, CFOP e
>   CST/CSOSN saem da tela e viram "tributação específica deste produto",
>   recolhida. O lojista deixa de ver o 102.
> - **Nada some com valor dentro**: produto que já tem CFOP/CST próprios abre
>   a seção de exceção automaticamente, e o bloco de alíquotas só desaparece
>   quando não há nada salvo nele.
> - Sem tributação padrão, a tela é a de antes, inteira.

**Prova:** pytest da cascata (produto vence NCM, NCM vence padrão; campo vazio
não sobrescreve preenchido) e de que o payload da nota sai idêntico ao de hoje
para um produto que tinha tudo no cadastro — **medido com o arquivo do
`git show HEAD`**, não deduzido. No app: cadastrar produto novo informando
**só o NCM** e emitir.

**Migração dos produtos que já existem:** quem já tem `produto_fiscal`
preenchido continua valendo como exceção — nada se apaga. A tributação padrão é
criada com os valores mais frequentes do catálogo atual, mostrados para
confirmação.

### Fase 3 — validar no cadastro o que a SEFAZ cobra

- Função pura extraída de `verificar_produto_fiscal` sobre um rascunho (D4).
- Dry-run chamado no `blur` do que muda a regra e antes de salvar.
- Pendência aparece **no campo**, e o campo precisa estar renderizado (T4).
- O gate de emissão passa a chamar a mesma função.

**Prova:** pytest de que cadastro e emissão devolvem o mesmo conjunto de
pendências para o mesmo rascunho; no app, marcar ST e o CEST virar obrigatório na
hora.

### Fase 4 — NCM e CEST pesquisáveis

- Tabela NCM semeada (D5) + busca por descrição via `core/busca.py`.
- Campo NCM vira busca ("mouse" → `8471.60.53`), aceitando o código digitado.
- CEST filtrado pelo NCM, como no Omie — sempre sugestão com
  `exige_confirmacao`, porque CEST errado é nota aceita e errada.
- `Fonte.BASE_NCM` e `Fonte.BASE_CEST` saem de declaração para implementação.
- Com a Fase 2 no lugar, o NCM passa a ser **a chave da tributação**: escolher o
  NCM certo passa a valer muito mais do que preencher campo.

### Fase 5 — a planilha do contador (P9)

- Exportar o catálogo fiscal em CSV (D11): SKU, nome, NCM, descrição do NCM,
  origem, CEST, a tributação que **vale** para aquele produto e de onde ela veio
  (padrão / NCM / exceção), mais uma coluna de pendência em português.
- Importar a mesma planilha de volta, com pré-visualização do que vai mudar
  antes de gravar.
- Edição em massa na tela (padrão Tiny): marcar produtos → aplicar NCM, origem,
  CEST, unidade, localização.

### Fase 6 — candidatos (decidir depois da primeira nota autorizada)

- **Importar o XML da NF-e de compra** e cadastrar o produto com o NCM que o
  fornecedor já classificou. É o caminho mais curto para um catálogo correto.
- **Acesso do contador** ao módulo fiscal — decisão do dono: quando existir a
  versão web.
- **Cálculo de ST com MVA** (CST 10/70, a loja como substituto). Hoje o motor
  cobre quem *recebeu* com ST (CST 60 / CSOSN 500), não quem *calcula*.

---

## 6. Armadilhas (todas já nos morderam, menos a T9)

**T1. PyArmor morre acima de ~18 KB de bytecode por módulo.** A tabela NCM
**não** pode virar literal Python — quebraria o `build:sidecar` e só apareceria
na hora de gerar instalador. Entra como arquivo de dados lido em runtime
(declarado no `run.spec`) ou seed de migration.

**T2. `create_all()` roda antes das migrations.** As migrations das fases 1.6 e 2
precisam decidir pela presença do **schema antigo**, não pela ausência do novo —
modelo é a `965c71a2da9a`.

**T3. `v-model.number` é inerte em componente.** Campo numérico novo via
`BaseInput` entrega string, o Zod reprova e o vee-validate aborta calado.

**T4. Erro em campo que a tela não renderiza mata o submit em silêncio.** É o bug
do complemento da empresa, em produção até hoje. Com a Fase 2 recolhendo campos
numa seção fechada, o risco **aumenta**: pendência de campo escondido tem de
abrir a seção.

**T5. `''` de select escondido reprova no Zod.** Campos que só aparecem em certo
CST precisam tratar `''` como ausente.

**T6. Cache por prefixo canônico** (`shared/constants/entityKeys.ts`);
chave-irmã não é alcançada. A tributação padrão e as regras por NCM entram como
chaves novas e invalidam o catálogo.

**T7. Teste verde não prova a tela.** 1.350 pytest não viram os onze furos da §2.
A prova de cada fase inclui clicar.

**T8. Nada chega na loja sem `npm run build:sidecar`.** O backend muda nas fases
1, 2, 3, 4 e 5.

**T9. Excel come zero à esquerda.** Na planilha da Fase 5, NCM, CEST, CST e CFOP
precisam sair como **texto**, senão `00` vira `0` e `01012100` perde o zero — e o
contador devolve uma planilha que parece certa e está errada. Vale teste de
round-trip: exportar, reimportar, comparar byte a byte.

---

## 7. Em aberto

1. **Tabela NCM**: lista completa (~10 mil posições) no instalador, ou começar
   pelos segmentos que já rodam (informática, autopeças, serigrafia)?
2. **Ordem**: Fase 1 isolada esta semana, para o teste na SEFAZ sair logo, e a
   Fase 2 depois? (É a minha recomendação: a Fase 1 não atrapalha a Fase 2, e sem
   ela não há primeira nota.)
3. **Quem confirma a tributação padrão** na primeira vez: o dono sozinho, ou
   entra um passo de "mande para o contador conferir" antes de liberar a emissão?
