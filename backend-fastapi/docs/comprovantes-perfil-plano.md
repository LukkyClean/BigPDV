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

Perfil de comprovante = **suporte × densidade/blocos × documento**.

```
suporte      cupom58 · cupom80 · A5 (meia folha) · A4
densidade    basico · normal · completo
blocos       cliente · endereco · documento · objeto · fotos · observacoes ·
             diagnostico · itens · pagamento · termos · assinaturas
documento    os_entrada · os_entrega   (venda_recibo na fase final)
```

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
  os_entrada: { suporte: 'A5',      densidade: 'normal', blocos: [...] },
  os_entrega: { suporte: 'cupom80', densidade: 'basico', blocos: [...] },
}
```

### Presets são derivados, não armazenados

"Resumido" e "Completo" são botões que setam os toggles. A tela mostra
"Personalizado" quando a combinação não bate com nenhum preset. Nada de campo
`preset` salvo no banco — campo salvo dessincroniza dos toggles na primeira edição.

### O limite honesto

**Bloco que já existe no catálogo** → segmento novo só declara. Zero Vue.
**Bloco que ninguém inventou ainda** → escreve uma vez e ele entra no catálogo,
disponível para todos os segmentos daí em diante.

Foi exatamente o que aconteceu com `imagem_na_entrada`: a serigrafia precisou, virou
capacidade declarável, e hoje qualquer segmento pode pedir. O custo por segmento tende
a zero, mas o primeiro de cada **tipo novo de conteúdo** tem custo. Isso é inevitável;
a alternativa seria um motor de layout genérico, e aí voltamos a construir plataforma.

E a densidade resolve a constante de 42mm: ela deixa de ser número chumbado e passa a
ser consequência do perfil — `basico` sem foto, `normal` com foto pequena, `completo`
com foto grande.

---

## 5. Decisões tomadas

| Decisão | Escolha | Por quê |
|---|---|---|
| Suporte declarado pelo segmento é padrão ou regra? | **padrão** (lojista troca) | Regra parece organizada no papel, mas existe a oficina que só tem A4 e a serigrafia que comprou térmica. Não vale brigar com cliente por decisão de arquitetura. |
| Toggles valem por formato (cupom vs A4) ou um conjunto só? | **um conjunto só** | dois conjuntos dobram tela e manutenção; o cupom já é naturalmente condensado. Se aparecer caso real, divide depois com evidência. |
| Armazenamento: colunas booleanas ou JSON? | **colunas booleanas explícitas** | booleano tipado é coberto por Pydantic e `vue-tsc`. JSON não é, e a primeira chave escrita errada só aparece na impressão do cliente. |
| Defaults | **reproduzem exatamente a saída de hoje** | ninguém pode ter o comprovante alterado por uma atualização. Ver §7. |
| Editor de template pelo usuário | **não existe** | produto, não plataforma |
| Escolha de fonte e tamanho | **não existe** | é o botão que quebra layout e gera chamado. Se preciso, `densidade` resolve o caso real. |

---

## 6. Fases

Cada fase é entregável sozinha e reversível.

### Fase 0 — descobrir o que come a página
Abrir o template e medir quais blocos consomem a segunda folha. **Pode resolver a
queixa do cliente sem nenhuma configuração nova** — e aí melhora para todos, inclusive
quem nunca vai abrir a tela. Precedente: a ficha de vistoria da oficina foi
reorganizada em duas colunas exatamente assim.
*Risco: nenhum. Não escreve código de feature.*

### Fase 1 — catálogo de blocos
Nomear cada bloco do template atual e extrair a lista. Só organização; nenhum
comportamento muda. É o alicerce de todo o resto.
*Risco: nenhum.*

### Fase 2 — suporte de papel
Acrescentar `A5` ao mapa do `@page` em `imprimirComPagina` e fazer o template
respeitar a largura. Entrega "meia folha", que é metade da queixa original.
*Risco: baixo, frontend puro.*

### Fase 3 — perfil no registry
Cada segmento declara o perfil dos seus dois documentos. Defaults reproduzindo a saída
atual. O template passa a ler o perfil em vez das constantes.
*Risco: baixo — os blocos já são condicionais. Testar nos 3 segmentos.*

### Fase 4 — sobrescrita pela empresa
Colunas em `configuracoes_os` + migration + schema + seção nova na tela de Ordens de
Serviço, com **Entrada** e **Entrega** separados.
*Risco: médio. Mexe no backend → exige `build:sidecar` no deploy.*

### Fase 5 — preview ao vivo
`OSPrintTemplate.vue` recebendo uma OS de exemplo, renderizado reduzido ao lado dos
controles, atualizando a cada clique.

É o que separa esta tela da tela de 1998: configuração de impressão sem preview é
tentativa e erro gastando papel. E como a queixa do cliente é sobre **tamanho**, ver a
folha encolher ao desligar blocos ataca o problema direto.
*Risco: baixo (só leitura), custo o mais alto das fases.*

### Fase 6 — recibo de Venda
Mesmo desenho aplicado a `ConfiguracaoVendas` e ao template de venda, com o padrão já
provado na OS.

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
