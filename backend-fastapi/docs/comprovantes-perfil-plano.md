# Comprovantes por perfil — plano de implementação

Como fazer o comprovante de OS deixar de ser **desenhado** e passar a ser **declarado**.

Este documento cobre os comprovantes de **Ordem de Serviço** (entrada e entrega). O
recibo de **Venda** usa o mesmo desenho e entra numa fase final, depois do padrão
estar provado na OS.

---

## 1. O problema real

A queixa que chegou foi "o recibo é grande demais, às vezes sai em duas folhas". Essa
é a ponta visível. O problema de fundo é outro:

**O comprovante é o último lugar do sistema onde um segmento novo cobra trabalho de
Vue.** Todo o resto já obedece a regra de crescimento do projeto — segmento novo
acrescenta declaração no registry e mais nada. O comprovante não: cada segmento quer
um tamanho de papel e um nível de detalhe diferente, e hoje isso se resolve editando
o template à mão.

A prova está dentro do próprio template, em `OSPrintTemplate.vue`:

> *90mm empurrava termos e assinaturas para a segunda folha; 55mm ainda deixava o
> rodapé transbordar sozinho. 42mm fecha a via.*

"Caber na folha" é uma constante ajustada na mão. Cada segmento novo refaz essa briga,
e a briga é sempre a mesma.

**Objetivo:** segmento novo declara `suporte`, `densidade` e `blocos`. Sem abrir o Vue.

---

## 2. Estado atual (o que já está pronto e não sabíamos)

Os dois eixos que interessam **já estão parametrizados**. Só não estão expostos.

| Peça | Situação |
|---|---|
| `shared/utils/print.utils.ts` → `imprimirComPagina` | injeta `@page{size}` com `'80mm auto'` ou `'A4'`. **Papel novo = mais um valor no mapa.** |
| `shared/services/escpos.ts` | `COLUNAS = {'58':32,'80':48}`, `DOTS = {'58':384,'80':576}`. Quebra de linha e alinhamento já são genéricos por bobina. |
| `OSPrintTemplate.vue` (573 linhas) | **já é todo seccionado por `v-if`**: cliente, endereço, objeto, atributos do segmento, observações, fotos, diagnóstico, itens, pagamento, termos. |
| `order-service/shared/segmento/textosImpressaoOS.ts` | já é pacote de textos **por segmento**, com assistência técnica como padrão. É o lugar natural do perfil. |
| `db/models/configuracao_os.py` | 4 campos (prazo entrega, garantia, abandono, taxa). **Nenhum de impressão** — espaço livre. |
| `shared/stores/impressao.store.ts` | config **por máquina** (`localStorage`): impressora, porta, formato, automático. |

O trabalho é **ligar condições que já existem** a um perfil declarado. Não é
reescrever o template.

---

## 3. Referências do ecossistema

Pesquisa feita para não inventar corte que o mercado já resolveu. O consenso valida o
desenho abaixo — os quatro separam as mesmas três coisas.

| Sistema | Mecanismo | O que aproveitamos |
|---|---|---|
| **Odoo** | `report.paperformat` é um registro próprio (tamanho, margens, orientação) | papel é conceito **separado** do conteúdo e reutilizável entre documentos |
| **Frappe / ERPNext** | *Print Format* é registro, com builder de blocos liga/desliga | catálogo finito de blocos, sem código do usuário |
| **Dynamics 365 BC** | "Report Selection" (documento → layout) + layout por cliente | mapeamento por **tipo de documento** e **sobrescrita em camadas** |
| **POS de varejo** (Square, Shopify) | lista de chaves liga/desliga | o modelo mínimo que resolve 90% do balcão |

### O que NÃO copiar

Todos têm um escape hatch onde o usuário escreve template de verdade: herança por
xpath (Odoo), HTML/Jinja custom (Frappe), Freemarker (NetSuite).

**Fica fora, pela mesma razão já decidida na arquitetura de segmentos: StartBig é
produto, não plataforma.** No dia em que o lojista escrever o template, todo chamado
de suporte vira "o comprovante dele quebrou e ninguém sabe por quê" — porque o
template deixou de ser nosso. Os grandes bancam isso porque têm consultores vivendo
disso; não é o nosso modelo.

Também fica fora o caminho do software vertical pequeno (o SHOficina, que originou a
conversa): uma lista de modelos chumbados. A lista dele já mostra a falha —
`40 Col. Completo c/logo + Cond. Celulares` são quatro decisões coladas num nome só, e
`A5 resumido com logo` não existe porque ninguém codou essa linha ainda.

---

## 4. O modelo

### 4.0 O invariante de conteúdo (decidido pelo dono, 12/08/2026)

**Não existe opção que remova informação do comprovante.** Aparecem SEMPRE, em
qualquer empresa e qualquer segmento, na OS e na Venda:

- dados da empresa
- dados do cliente, **incluindo endereço**
- os itens discriminados (produto ou serviço)
- o resumo exato do pagamento

Isso existe para **proteger o cliente** e não é assunto de preferência do lojista.

A consequência é uma propriedade de segurança que vale mais que a flexibilidade
perdida: **nenhuma combinação de configurações produz uma via legalmente pobre.**
Ninguém desliga os itens e descobre meses depois que não consegue provar o que
entregou. O sistema não permite.

> Registro de percurso: a primeira versão deste plano propunha densidade
> `basico/normal/completo` **removendo blocos** (CPF, endereço, observações). Estava
> errado, e o corte certo veio do dono: o conteúdo é fixo, o que muda é a forma.

### 4.1 O que varia

Perfil de comprovante = **suporte × densidade**, por documento.

```
suporte      cupom58 · cupom80 · A5 (meia folha) · A4
densidade    normal (o de hoje) · compacto
logo         com · sem
documento    os_entrada · os_entrega · venda_recibo
```

Densidade é **a mesma informação renderizada diferente**. Hoje cada bloco é um card
com borda, barra de cabeçalho, ícone e `mb-4` de respiro. No compacto vira linha
corrida, rótulo inline, duas ou três colunas, sem moldura — mesmos dados, muito menos
papel.

Duas densidades, não três: três é fácil de escrever e caro de manter afinado.

### 4.2 Como a densidade se implementa

Dois caminhos, a decidir na execução:

1. **Classe no container** — `.print-container.compacto`, com o CSS de impressão
   redefinindo espaçamentos e bordas. Barato; o template quase não muda. Risco:
   briga de especificidade com as utilitárias do Tailwind, resolvida com
   `!important` — que o `print-a4.css` já usa, então não é corpo estranho.
2. **Classes condicionais no template** — `:class="dens('mb-4','mb-1')"`. Explícito,
   sem briga de CSS, mas mexe em muita linha.

Recomendação: começar por (1).

**No cupom térmico a densidade é outra coisa.** Lá não há CSS — são bytes. Compactar é
menos linha em branco e rótulo abreviado. Mesmo conceito, implementação separada em
`osToEscPos` / `saleToEscPos`.

### Três camadas de decisão

Cada uma no seu lugar natural, e a separação importa:

| Camada | Decide | Onde vive | Alcance |
|---|---|---|---|
| **Segmento** | o padrão sensato | registry (`textosImpressaoOS.ts` e vizinhos) | código |
| **Empresa** | sobrescreve o padrão | `configuracoes_os` (banco) | todos os terminais |
| **Máquina** | só **onde** imprimir | `localStorage` | aquele PC |

Conteúdo é decisão **da empresa**, nunca da máquina. Se morasse no `localStorage`, a
mesma OS sairia diferente no balcão e na oficina conforme quem configurou cada PC —
bug silencioso e chato de diagnosticar. A tela de Impressão continua cuidando só de
impressora, porta e formato disponível naquele PC.

### Declaração de um segmento novo

O alvo. Isto é tudo o que um segmento novo deveria precisar:

```ts
serigrafia: {
  os_entrada: { suporte: 'A5',      densidade: 'normal',   logo: true },
  os_entrega: { suporte: 'cupom80', densidade: 'compacto', logo: true },
}
```

### O limite honesto

Com o conteúdo fixo (§4.0), o custo por segmento novo cai bastante: quase tudo é
escolher suporte e densidade. Sobra um caso que ainda pede código: **conteúdo que
nenhum segmento tinha pedido antes**.

Foi o que aconteceu com `imagem_na_entrada` — a serigrafia precisou da arte na via,
virou capacidade declarável, e hoje qualquer segmento pode pedir. Escreve-se uma vez e
entra no catálogo para todos. A alternativa seria um motor de layout genérico, e aí
voltamos a construir plataforma.

E a densidade resolve a constante de 42mm da foto: deixa de ser número chumbado no
template e passa a ser consequência do perfil.

---

## 5. Decisões tomadas

| Decisão | Escolha | Por quê |
|---|---|---|
| Suporte declarado pelo segmento é padrão ou regra? | **padrão** (lojista troca) | Regra parece organizada no papel, mas existe a oficina que só tem A4 e a serigrafia que comprou térmica. Não vale brigar com cliente por decisão de arquitetura. |
| O que é configurável? | **só a forma** (suporte, densidade, logo) | §4.0 — conteúdo é proteção do cliente, não preferência do lojista |
| Quantas densidades? | **duas** (normal, compacto) | três é fácil de escrever e caro de manter afinado |
| Armazenamento | **colunas explícitas** (enum curto + booleano) | tipado é coberto por Pydantic e `vue-tsc`. JSON não é, e a primeira chave escrita errada só aparece na impressão do cliente. |
| Defaults | **reproduzem exatamente a saída de hoje** | ninguém pode ter o comprovante alterado por uma atualização. Ver §7. |
| Editor de template pelo usuário | **não existe** | produto, não plataforma |
| Escolha de fonte e tamanho | **não existe** | é o botão que quebra layout e gera chamado. Se preciso, `densidade` resolve o caso real. |

---

## 6. Fases

Cada fase é entregável sozinha e reversível.

### Fase 0 — descobrir o que come a página ✅ FECHADA (12/08/2026)

**Resultado: não há ganho de graça. É volume de informação mesmo.**

O levantamento mapeou o template inteiro e levantou um suspeito de layout — a regra
`.print-container .border { page-break-inside: avoid }` no `print-a4.css`, cujo
seletor pega *todo* elemento com borda (todos os cards), fazendo um bloco que não cabe
pular inteiro de página e deixar vão em branco. **O dono confirmou que não é o caso**:
a segunda folha vem cheia, é conteúdo.

Fica registrado como achado lateral: se algum dia aparecer segunda folha *quase
vazia*, esse seletor é o primeiro lugar a olhar.

Consumidores de espaço mapeados, em ordem: espaçamento acumulado (padding `1cm` +
`mb-4`/`mb-6`/`mb-8` empilhados + `margin-top: 2rem` do rodapé, fácil passar de 4cm só
de respiro) · os textos legais de tamanho fixo (Termo de Garantia, Condições de
Entrada, com `leading-relaxed` e `text-justify`) · o QR do PIX (30mm + `mb-6`) · a
tabela de itens, que cresce sem limite.

**Conclusão que orienta o resto:** o caminho é densidade de layout, não remoção de
conteúdo.

### Fase 1 — catálogo de blocos ✅ FECHADA (12/08/2026)

Extraído do template:

**Nos dois documentos** — cabeçalho da loja (logo, dados, nº da OS, datas) · faixa do
título · card do cliente (nome, CPF/CNPJ, telefone, endereço, código) · card do objeto
(marca, modelo, identificador, cor, atributos do segmento) · assinaturas · rodapé

**Só entrada** — defeito relatado · observações e acessórios · fotos/arte · condições
de entrada + prazo de retirada

**Só entrega** — diagnóstico e solução · itens com garantia por item · lista de
pagamentos · resumo financeiro (subtotal, desconto, deslocamento, juros, adiantamento,
total) · QR do PIX · termo de garantia ou declaração de entrega

Todos permanecem **sempre presentes** (§4.0). O catálogo serve para saber o que a
densidade precisa saber compactar, não o que ligar e desligar.

### Fase 2 — suporte de papel
Acrescentar `A5` ao mapa do `@page` em `imprimirComPagina` e fazer o template
respeitar a largura. Entrega "meia folha".
*Risco: baixo, frontend puro.*

### Fase 3 — densidade compacta
A variante `compacto` do layout: cards viram linha corrida, rótulo inline, mais
colunas, sem moldura. Decidir entre classe no container e classes condicionais
(§4.2). **É a fase que resolve a queixa** — as anteriores só preparam.
*Risco: médio. É onde o comprovante muda de cara; testar nos 3 segmentos.*

### Fase 4 — perfil no registry
Cada segmento declara suporte e densidade dos seus documentos. Defaults reproduzindo
a saída atual.
*Risco: baixo.*

### Fase 5 — sobrescrita pela empresa
Colunas em `configuracoes_os` + migration + schema + seção nova na tela de Ordens de
Serviço, com **Entrada** e **Entrega** separados.
*Risco: médio. Mexe no backend → exige `build:sidecar` no deploy.*

### Fase 6 — recibo de Venda
O mesmo CSS de densidade aplicado ao template de venda, e as mesmas colunas em
`ConfiguracaoVendas`.

**Deixou de ser projeto à parte.** Com o conteúdo fixo e só a forma variando, o
mecanismo é idêntico ao da OS — é aplicação, não desenho novo. Pode inclusive andar
junto da Fase 3 se o CSS sair genérico o bastante.

### Fase 7 — preview ao vivo
`OSPrintTemplate.vue` recebendo uma OS de exemplo, renderizado reduzido ao lado dos
controles, atualizando a cada mudança.

É o que separa esta tela da tela de 1998: configuração de impressão sem preview é
tentativa e erro gastando papel. E como a queixa é sobre **tamanho**, ver a folha
encolher ao trocar a densidade ataca o problema direto.
*Risco: baixo (só leitura), custo o mais alto das fases.*

---

## 7. Invariantes

Regras que não se negociam durante a execução:

1. **Nenhuma loja pode ter o comprovante alterado por uma atualização.** Todos os
   defaults nascem reproduzindo a saída atual, byte a byte no que for possível. Quem
   não abrir a tela nunca percebe que ela existe.
2. **Migration guardada pela presença** da coluna/tabela — o `create_all()` roda
   **antes** das migrações no startup (ver `core/tarefas.py` e CLAUDE.md).
3. **Testar nos três segmentos** antes de cada deploy. Informática e oficina estão em
   produção; impressão é código compartilhado, então mexer nela alcança as duas.
4. **Conteúdo nunca vai para o `localStorage`.** É decisão de empresa.
5. Consertar regressão em loja custa sidecar + instalador + deslocamento, não
   `git revert`.

---

## 8. Fora de escopo

Registrado para não voltar como "e se a gente também...":

- editor de template pelo usuário (qualquer forma: HTML, xpath, expressões)
- escolha de fonte e corpo de fonte
- lista de modelos chumbados
- posicionamento de campos ("posição do nº da OS")
- conteúdo específico de segmento como *modelo* na lista — isso é declaração no
  registry, que é o mecanismo que já temos
