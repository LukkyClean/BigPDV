# PDV fiscal e não fiscal — plano de implementação

> **Decisão do dono (20/08/2026):** o PDV tem duas categorias. O **não fiscal** é
> o produto e funciona sozinho, completo. O **fiscal** é um andar em cima, que só
> acende se o cliente tiver o recurso no plano.
> **Branch:** `feat/pdv`, em cima de `62b61c3`.
> **Continua:** `pdv-caixa-plano.md`, `pdv-profissional-plano.md`, `pdv-onde-paramos.md`.
> **Primeiro cliente:** adega de bebidas — hoje **não fiscal**.

---

## 0. Onde este plano se encaixa (e por que A/B em vez de 1-5)

**Existe outra lista de fases, e ela não acabou.** O `pdv-profissional-plano.md`
tem as fases 1 a 5 do balcão profissional:

| Fase | O que era | Estado em 20/08/2026 |
|---|---|---|
| 1 | Modo Balcão | ✅ commitada e provada no app (`637c264`) |
| 2 | caminho de teclado e leitor | ✅ commitada e provada no app (`cfa5799`) |
| 3 | terminais persistentes | ✅ commitada (`df6de7f`) — **falta provar no app** |
| 4 | **instalar na adega** — `build:sidecar`, instalador, build ID no `/api/health` | ⛔ **aberta** |
| 5 | permissões | ⛔ aberta |

Por isso a numeração **aqui é A1–A3 e B1–B3**: "fase 4" já tem dono, e duas listas
com o mesmo número é o tipo de confusão que faz alguém entregar a coisa errada.

> **Recomendação de ordem: a fase 4 daquele plano vem ANTES da trilha A daqui.**
>
> Três motivos, e o terceiro é o que pesa:
> 1. O que foi commitado hoje **não vale nada até rodar na loja** — código provado
>    no `npm run dev` não é código provado no app instalado.
> 2. O **build ID no `/api/health`** ainda não existe. Sem ele, todo diagnóstico
>    daqui para a frente começa por "que versão está rodando aí?" — e a resposta
>    hoje é um chute.
> 3. O **sidecar está atrasado desde a fase 0.5**. Quanto mais tempo passa, maior
>    o salto de uma vez só — e é exatamente esse tipo de salto que quebra loja.
>
> Entrada de mercadoria é para uma loja que **já está usando o sistema**. Hoje a
> adega não está.

---

## 1. A regra que organiza tudo

Três palavras que o sistema já usa e que **não são sinônimos**. Confundi-las é o
jeito mais rápido de fazer um cliente pagante perder acesso ao que comprou:

| Palavra | Quem decide | Onde mora | Exemplo |
|---|---|---|---|
| **recurso** | a StartBig — *o cliente pagou por isso* | licença (token assinado) | `nfe` |
| **configuração** | o lojista — *o cliente ligou isso* | `configuracao_*` por empresa | `emitir_nfce_na_venda` |
| **segmento** | o cadastro — *que tipo de loja é* | `empresas.segmento` | `pdv` |

**O recurso PERMITE; a configuração MANDA.** Uma loja com plano fiscal pode
operar não fiscal por uma semana (certificado vencido, contingência, o contador
pediu) sem perder o plano — e uma loja sem o recurso nunca vê a chave.

Não é teoria nova: é o mesmo desenho já provado no caixa — *segmento semeia,
configuração manda* — com um andar a mais em cima.

---

## 2. O levantamento (20/08/2026)

| Peça | Estado hoje |
|---|---|
| `shared/config/planos.ts` | **constante fixa** `PLANO_ATUAL = 'START'`, `nfe: false`. Frontend puro |
| `recursoDisponivel('nfe')` | usado em 2 lugares: `FiscalView` e `EmpresaForm` |
| `FiscalView.vue` | tela de bloqueio com CTA de upgrade — pronta, esperando o recurso |
| `EmpresaFiscalSettings` | **modelo completo** (séries NF-e/NFC-e, CSC, certificado A1, prefeitura) e **zero** serviço/endpoint/tela |
| `configuracoes_licenca` | `limite`, `data_vencimento`, `token`, `public_key`, `bloqueada` — **nenhuma noção de recurso** |
| `ValidarResponse` (API StartBig) | não devolve recursos |
| `produto` | **sem NCM, CFOP, CSOSN/CST, origem, unidade tributável** |
| `fornecedores.cnpj` | existe, `String(14)`, **unique** |
| `movimentacoes_estoque` | livro-razão único, com `origem` + FKs opcionais da causa |
| Movimentação de Estoque (tela) | ajuste manual, produto por `<select>` — não bipa |

**O achado que define a fase B1:** hoje o "plano" é uma linha de TypeScript. Ele
esconde a interface e não tranca nada. Para um recurso que é vendido, esconder
não é trancar.

---

## 3. Fase B1 — o direito de usar

**Custo:** 1 a 2 dias. **Risco:** baixo. **Bloqueia todo o resto.**

### 3.1 A verdade mora no token da licença

A API StartBig já emite um **token JWT** que o app renova sozinho, e o app já
guarda a `public_key` para conferir assinatura. Os recursos entram ali, como
claim:

```
recursos: ["nfe"]
```

Por que ali e não numa coluna do banco local: **o banco local é do cliente.** Uma
coluna `tem_nfe` é editável por quem tem acesso à máquina; um claim assinado, não.
E não custa infraestrutura nova — o canal já existe e já é renovado de hora em hora.

### 3.2 O padrão é seguro, e é isso que destrava a obra

`recursos` ausente = `[]` = **não fiscal**. Isso é o que permite construir tudo
agora, antes de a API mudar: enquanto o servidor não mandar nada, todo cliente
(inclusive as 3 lojas em produção) continua exatamente como está.

Para desenvolvimento, um `RECURSOS_FORCADOS` no `.env` que **só é lido quando
`APP_ENV != production`** — sem isso não há como testar o caminho fiscal antes de
o servidor existir, e "não dá para testar" é como uma fase morre.

### 3.3 O backend tranca; o frontend só esconde

Uma dependency `requer_recurso("nfe")`, no molde do `check_permission` que já
existe, em **todo** endpoint fiscal. Botão escondido não é trava: a rota continua
viva, exatamente como a rota `/servicos` continuava viva quando o menu sumiu
(achado do plano do caixa, seção "esconder a OS são 5 superfícies").

### 3.4 O frontend não muda de forma

`planos.ts` já foi escrito prevendo este dia — o comentário no topo dele diz
"este arquivo é o único ponto a trocar". A assinatura `recursoDisponivel('nfe')`
continua idêntica; muda só a fonte, de constante para o que veio em
`GET /licenca/status`. **Nenhum call site é tocado.**

> **Prova:** com `recursos` vazio, o app inteiro se comporta como hoje — mesma
> tela, mesmo menu, mesmos endpoints. Com `nfe` ligado à mão no `.env` de dev, a
> `FiscalView` deixa de mostrar o bloqueio. Nada no meio.

### 3.5 Dependência externa (e o que fazer se ela demorar)

Alguém precisa mexer na API StartBig para o token carregar `recursos`. **Isso não
bloqueia nada aqui**: com o padrão seguro, a **trilha A inteira** roda sem o
servidor mudar uma linha. Só a fase B3 depende de verdade.

---

## 4. Fase A1 — o seletor de produto único

**Custo:** 2 dias. **Risco:** baixo (se a ordem for respeitada).

Hoje a mesma bipada tem **três respostas diferentes** conforme a tela — e é isso,
mais do que a tela que não bipa, que faz o operador desconfiar do sistema.

O `leitorCodigoBarras.util.ts` já é a camada certa e está pronta (termo → único /
nenhum / ambíguo, exigindo `codigo_barras` ou `sku` literal). O que falta é
separar o resto em dois:

```
leitorCodigoBarras.util.ts   ← resolução      (existe, está bom)
SeletorDeProduto.vue         ← busca, debounce+flush, lista, setas, Enter   [extrair]
cada tela                    ← o que fazer com o produto escolhido
```

O `ProductSearch` da venda **sabe demais**: ele chama `tentarAdicionarProduto(saleId)`.
É por isso que não dá para reaproveitá-lo como está. O componente extraído
**resolve e emite**; quem decide o que fazer é a tela — é assim que ERPNext
(`scan_barcode` em toda transação) e Odoo funcionam.

**Ordem de adoção, por risco crescente:**

1. **Movimentação de Estoque** — nenhuma das 3 lojas usa no dia a dia. Estreia aqui.
2. **`F3` Adicionar Produto** — hoje tem o bug de debounce que a venda já não tem.
3. **A venda** — por último, porque é a que está em produção.

> **Prova medida:** o mesmo código bipado nas três telas produz a mesma resposta
> (adiciona / "nenhum produto" / "2 produtos com esse código"). Comparar com o
> arquivo do `git show HEAD`, não deduzir.

---

## 5. Fase A2 — entrada de mercadoria (não fiscal)

**Custo:** 3 a 4 dias. **Risco:** médio — encosta em custo médio.

### 5.1 Entrada é um DOCUMENTO, não um ajuste

É assim em SAP (*Goods Receipt* contra a ordem de compra), Odoo (*Receipts*),
ERPNext (*Purchase Receipt*) e em todo ERP brasileiro. O ajuste manual continua
existindo — mas como **exceção auditada** (quebra, perda, inventário), que é
exatamente o que a tela de Movimentação de Estoque já é hoje.

```
entradas_mercadoria         cabeçalho: fornecedor, origem, chave, número, série,
                            data de emissão, valor total, status, quem lançou
entradas_mercadoria_item    linhas: produto, descrição/código/EAN do fornecedor,
                            quantidade, custo unitário
```

`origem`: `MANUAL | CHAVE_DANFE | XML` — a mesma coluna-origem do livro de estoque
e do livro financeiro. **Confirmar a entrada escreve no livro único**
(`movimentacoes_estoque`, com FK do documento); nunca mexer em quantidade direto.

**Rascunho não é luxo:** conferir uma nota de 40 itens não termina numa sentada, e
uma entrada pela metade não pode ter mexido no estoque.

### 5.2 A chave do DANFE, bipada

Os 44 dígitos do código de barras do DANFE são lidos **localmente**, sem internet
e sem certificado:

```
23 | 2608 | 07272825005335 | 55 | 001 | 000224631 | 1 | 00224632 | 6
UF   AAMM   CNPJ do emitente  mod  série   número    tp   cNF      DV
```

Isso preenche o **cabeçalho inteiro**: fornecedor (pelo CNPJ, que já é `unique` em
`fornecedores`), número, série e data. Não achou o CNPJ → oferece cadastrar o
fornecedor com ele já preenchido.

⚠️ **Validar o dígito verificador (módulo 11) é obrigatório.** É o que separa
"bipou certo" de "bipou torto" — sem isso, um dígito errado vira uma nota
fantasma no sistema, e ninguém descobre até a conferência do mês.

⚠️ **A chave NÃO traz os itens.** Está escrito aqui porque é a pergunta que sempre
volta: os 44 dígitos são um identificador, e os produtos moram no XML, no servidor
da SEFAZ.

### 5.3 Os itens, bipando

`SeletorDeProduto` (fase A1) + quantidade + custo unitário — que é o número que
alimenta o custo médio e, por tabela, o CMV e o relatório de lucro.

**Produto sem EAN cadastrado:** a primeira bipada oferece gravar aquele código no
produto. É assim que o catálogo se conserta sozinho, item a item, em vez de exigir
um mutirão de cadastro antes de o leitor servir para alguma coisa.

---

## 6. Fase A3 — a memória do fornecedor

**Custo:** 1 dia. **Risco:** baixo.

```
produto_fornecedor    fornecedor_id, produto_id, codigo_fornecedor, ean_fornecedor
```

O código do fornecedor quase nunca é o seu. Bling e Tiny resolvem isso casando os
itens na primeira nota e **memorizando** — da segunda em diante entra quase
sozinho. Vale para a entrada bipada e é **pré-requisito** da entrada por XML.

---

## 7. Fase B2 — entrada por XML

**Custo:** 3 dias. **Risco:** médio.

Duas coisas que costumam ser confundidas, e a diferença decide o preço:

| | Precisa de certificado? | É emissão? |
|---|---|---|
| **Importar o arquivo XML** que o fornecedor mandou | **Não** | Não |
| **Buscar automático na SEFAZ** (`NFeDistribuicaoDFe`) | **Sim** (e-CNPJ A1) | Não |
| Emitir NF-e / NFC-e | Sim | **Sim** |

Cada item do XML traz `cEAN` — o código de barras do produto. Quando o fornecedor
preenche direito, o de-para é **automático**; quando vem `SEM GTIN` (comum), cai
no de-para manual da fase A3, que memoriza.

> **DECIDIDO pelo dono (20/08/2026): o import de XML é RECURSO PAGO.** A regra da
> casa é uma só — **o que envolve nota fiscal está no plano fiscal**, sem exceção
> por conveniência técnica.
>
> Fica registrado que a recomendação técnica era outra (o import não emite nada e
> não exige certificado), e que a decisão comercial prevalece. A consequência
> prática, que **não** é um problema: o caminho não fiscal continua **completo**
> sem o XML — a entrada se faz bipando a chave do DANFE e os itens. O XML acelera
> quem paga; ele não é a única forma de dar entrada.

---

## 8. Fase B3 — a venda fiscal (fronteira)

**Não é nossa.** A emissão vive em `origin/feat/fiscal-module`, com outro
programador. O que é nosso é **não fechar a porta**.

Duas coisas do nosso lado:

**(a) O cadastro de produto não tem os campos fiscais.** Falta NCM, CFOP, CSOSN/CST,
origem da mercadoria e unidade tributável. Isso é cadastro — nosso — e é a peça
que trava tudo se ficar para o fim. Só aparece para quem tem o recurso
(`requer_recurso('nfe')`), então não polui a tela de ninguém.

**(b) A regra de ouro, e ela precisa estar escrita ANTES de a emissão chegar:**

> **Finalizar a venda não pode significar "imprimir".**

Numa venda fiscal existe um estado **entre** finalizar e imprimir: aguardando
autorização, rejeitada pela SEFAZ, contingência offline. Hoje o Modo Balcão emenda
a próxima venda dentro do `afterPrint` — o que está certo para o não fiscal e
**não pode virar a única saída**. Custo de respeitar isso agora: zero. Custo de
descobrir depois: refazer o fluxo de finalização com o PDV já na rua.

---

## 9. Ordem, custo e risco

**Decisão do dono (20/08/2026): terminar o não fiscal inteiro, e só depois
ajustar para o fiscal.** Não é uma fila só — são duas trilhas, e a segunda não
começa antes de a primeira estar rodando na adega.

**Trilha A — não fiscal (é o produto, e entrega sozinha):**

| Fase | O que entrega | Custo | Risco | Depende de |
|---|---|---|---|---|
| **A1** | seletor de produto único, bipável | 2 d | baixo | — |
| **A2** | entrada como documento + chave do DANFE | 3–4 d | médio | A1 |
| **A3** | memória do fornecedor (de-para) | 1 d | baixo | A2 |

No fim da fase A3 a adega dá entrada numa nota inteira sem mouse, e o custo médio
passa a vir do que foi pago de verdade. **É um produto completo — não é meia
funcionalidade esperando o fiscal.**

**Trilha B — fiscal (só quando a A estiver na rua):**

| Fase | O que entrega | Custo | Risco | Depende de |
|---|---|---|---|---|
| **B1** | recursos na licença, ponta a ponta | 1–2 d | baixo | — |
| **B2** | import de XML **(recurso pago)** | 3 d | médio | B1 + A3 |
| **B3** | campos fiscais do produto + gancho da emissão | 2 d | médio | B1 |

A fase B1 encabeça a trilha B, e não a A, porque **o não fiscal não precisa de
trava nenhuma**: ele é o que todo cliente tem. A trava só existe para separar
quem pagou — e ninguém pagou ainda.

⚠️ **Uma coisa da trilha B vale desde agora, e é de graça:** a regra de ouro da
seção 8 (*finalizar a venda não pode significar "imprimir"*). Respeitar isso
enquanto se mexe na venda custa zero; descobrir depois custa refazer a
finalização com o PDV na rua.

---

## 10. O que NÃO entra

- **Emissão** de NF-e / NFC-e / NFS-e — outro programador, outra branch.
- **Gestão do certificado digital A1** — vem junto com a emissão.
- **Contas a pagar a partir da entrada** — é do módulo financeiro; a entrada só
  precisa nascer com FK suficiente para ligar depois.
- **Manifestação do destinatário** (evento SEFAZ) — depende de certificado.
- **Inventário / contagem cíclica** — projeto próprio.

---

## 11. Decisões em aberto

1. ~~**Import de XML: fiscal ou não fiscal?**~~ **RESOLVIDO em 20/08/2026:
   recurso PAGO.** Regra da casa: o que envolve nota fiscal está no plano fiscal.
   Consequência no cronograma: a **fase B2 passa a depender da fase B1**, e o
   não fiscal se fecha na fase A3.

2. ~~**O dono da adega tem ou pretende ter e-CNPJ (A1)?**~~ **RESOLVIDO em
   20/08/2026: segue a mesma regra — busca automática na SEFAZ é recurso pago,
   e o certificado não entra agora.** Primeiro o não fiscal fica pronto; o
   fiscal se ajusta depois.

3. **PREMISSA ASSUMIDA (não é decisão fechada): bipar a chave do DANFE fica no
   NÃO fiscal.** É o único ponto de fronteira que a regra "nota fiscal = pago"
   não resolve sozinha, então fica escrito o raciocínio: ler 44 dígitos de um
   papel **não emite nada, não consulta a SEFAZ e não usa certificado** — é só
   identificar o documento que veio junto com a mercadoria, como quem digita o
   número da nota no teclado, só que sem errar. Se ela fosse paga, a entrada do
   plano não fiscal voltaria a ser 100% digitada à mão e a fase A2 perderia o
   motivo de existir.

   Isso é **uma linha de gate**: se a decisão for o contrário, muda em um lugar
   e nada do resto se desfaz.
4. **Quem mexe na API StartBig** para o token carregar `recursos`? Sem isso, o
   fiscal nunca acende em cliente nenhum — mas agora isso **não bloqueia nada**:
   é a primeira pergunta da trilha B, e a trilha A não depende dela.

---

## 12. Riscos

- **A entrada de mercadoria mexe no custo médio**, que alimenta o CMV e o
  relatório de lucro das 3 lojas em produção. Prova **medida** (antes × depois com
  o arquivo do `git show HEAD`), nunca deduzida.
- **O seletor de produto é código compartilhado da venda.** Por isso a venda é a
  última a adotar, e só depois de as outras duas telas estarem rodando.
- **A API de licença é externa.** O padrão seguro (`recursos` ausente = não fiscal)
  é o que impede que um atraso lá vire um app quebrado aqui.
- **A trilha B inteira não viaja no mesmo instalador** das 3 lojas que já rodam.
