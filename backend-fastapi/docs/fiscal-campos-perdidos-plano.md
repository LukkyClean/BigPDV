# O campo que some no caminho — causa, lista e plano

Escrito em 12/09/2026, depois da primeira tentativa real de emissão numa loja
(MEI, NF-e de R$ 1,00, homologação). A nota **chegou na SEFAZ** e voltou com
rejeição de **schema**:

```
87:0: ERROR: Element '{...}IPINT': This element is not expected.
Expected is one of ( CNPJProd, cSelo, qSelo, cEnq )
```

A investigação passou por uma acusação errada à plataforma antes de chegar na
causa, que era **nossa**: um nome de campo trocado. O erro de diagnóstico ficou
registrado na §1 de propósito — ele é a lição mais cara do dia.

---

## 1. A causa — e eu errei ao apontá-la

**Versão publicada primeiro (ERRADA), mantida aqui de propósito:** acusei o
`z.object` sem `passthrough` da plataforma de podar o `ipi_codigo_enquadramento`,
citando o §1.1 do `contrato-api-fiscal-plataforma.md` (09/09/2026).

**O que estava errado:** o `passthrough` **já existia** desde 08/09 (commit
`f6dd064` na VPS, `fiscal.schema.ts:111-118`, via `z.looseObject` — o nome do
`.passthrough()` no Zod 4). Eu inferi "corrigiram por lista" a partir de um
documento de diagnóstico desatualizado, em vez de ler o código de lá. A própria
evidência que usei desmentia a tese: CFOP, CSOSN e `formas_pagamento` nunca
estiveram em lista nenhuma e chegaram à SEFAZ — o que só acontece COM
passthrough.

**A causa real, confirmada na documentação da Focus:** o nome do campo estava
errado **no ERP**.

| A Focus espera | O ERP enviava |
|---|---|
| `ipi_situacao_tributaria` | `ipi_situacao_tributaria` ✅ |
| **`ipi_codigo_enquadramento_legal`** | **`ipi_codigo_enquadramento`** ❌ |

Faltava o `_legal`. A Focus ignorou o campo desconhecido, montou o `<IPINT>`
sem o `<cEnq>` e a SEFAZ recusou por schema. **Nenhum campo sumiu no caminho** —
saiu daqui com nome que ninguém do outro lado entende.

Fonte: documentação da Focus, *Campos que devem ser utilizados por situação
tributária — IPI*, que descreve `ipi_codigo_enquadramento_legal` como
"obrigatório quando informado IPI", aceitando `999` quando não aplicável.

### 1.1 Onde a plataforma DE FATO pode descartar campo

Resposta do time da VPS, conferida no código de lá: não é o Zod, é o tradutor
`focus-payload.mapper.ts`. Ele achata `emitente{}`, `destinatario{}` e
`transportador{}` por tabela de nomes (`achatarGrupo`) — chave fora do `MAPA_*`
some. **Raiz, `items[]` e `totais{}` sobem intactos.**

Consequência para a lista da §2: o risco de poda existe só nos campos aninhados
nesses três grupos. Os seis condicionais que eu havia apontado como em risco
(CEST, redução de base, cBenef, crédito do CSOSN 101, tipo de integração) são de
item ou de raiz — **nenhum corre esse risco**.

E consequência maior: como `items[]` sobe intacto, **os nomes de campo de item
que o ERP usa precisam bater exatamente com a API da Focus**. O IPI provou que
um nome errado passa despercebido até a SEFAZ recusar. Auditar os demais nomes
de item e de raiz contra a documentação da Focus virou tarefa — ver §3.2, item E.

## 2. O que o ERP envia hoje — lista para conferir na VPS

Gerada do código em 12/09/2026 (`test_contrato_payload_campos.py`), não de
memória. São **66 campos**.

Depois da resposta do time da VPS (§1.1), a pergunta para cada um deixou de ser
"o Zod declara?" e passou a ser **duas**:

- **Aninhado em `emitente` ou `destinatario`?** Então: *o `MAPA_*` do tradutor
  tem essa chave?* O que não estiver, some.
- **Em `items[]`, `totais{}` ou na raiz?** Sobe intacto — então: *o nome bate
  EXATAMENTE com o da API da Focus?* Foi aqui que o IPI se perdeu.

### Raiz da nota
```
modelo                 natureza_operacao      tipo_documento
local_destino          modalidade_frete       finalidade_emissao
consumidor_final       presenca_comprador     numero
serie                  valor_troco
```

### Emitente
```
emitente.cnpj                         emitente.razao_social
emitente.nome_fantasia                emitente.inscricao_estadual
emitente.inscricao_municipal          emitente.codigo_regime_tributario
emitente.regime_tributario
emitente.endereco.logradouro          emitente.endereco.numero
emitente.endereco.complemento         emitente.endereco.bairro
emitente.endereco.cidade              emitente.endereco.uf
emitente.endereco.cep
```

### Item (`items[]`) — onde a poda dói mais
```
numero_item              codigo_produto           descricao
quantidade_comercial     valor_unitario_comercial valor_bruto
unidade_comercial        codigo_barras_comercial  ncm
cfop                     icms_origem              unidade_tributavel
codigo_barras_tributavel icms_situacao_tributaria
valor_frete              valor_seguro             valor_outras_despesas_acessorias
valor_desconto
icms_modalidade_base_calculo   icms_base_calculo   icms_aliquota   icms_valor
pis_situacao_tributaria        pis_base_calculo    pis_aliquota_porcentual    pis_valor
cofins_situacao_tributaria     cofins_base_calculo cofins_aliquota_porcentual cofins_valor
```

**Condicionais** (só aparecem quando o caso pede, e some com a mesma facilidade):
```
cest                                              (produto com ST)
icms_reducao_base_calculo                         (CST 20)
icms_codigo_beneficio_fiscal_reducao_base_calculo (CST 20 em SP/PR/RS/SC/GO)
icms_aliquota_aplicavel_calculo_credito           (CSOSN 101)
icms_valor_credito_aproveitado                    (CSOSN 101)
tipo_integracao                                   (pagamento em cartão)
```

### Pagamento e totais
```
formas_pagamento[].forma_pagamento    formas_pagamento[].valor_pagamento
totais.valor_produtos   totais.valor_frete   totais.valor_seguro
totais.valor_outras_despesas             totais.valor_desconto
totais.icms_base_calculo                 totais.icms_valor_total
totais.valor_total
```

### Destinatário
Varia com o tipo de cliente (PF, PJ, consumidor no balcão) e por isso ficou
fora da lista fechada: `nome`, `cpf`/`cnpj`, `indicador_ie`, `inscricao_estadual`
e o grupo `endereco` (`logradouro`, `numero`, `complemento`, `bairro`, `cidade`,
`uf`, `cep`). **A NF-e exige o endereço; a NFC-e não.**

Junto de `emitente`, é o grupo que o tradutor da plataforma achata por tabela de
nomes — então é aqui que a auditoria importa.

### Como auditar sem emitir nada

O `traduzirPayloadParaFocus` da VPS é função pura. Em vez de esperar uma emissão
para descobrir o que sobrevive, basta passar por ele os exemplos versionados:

```
backend-fastapi/docs/payloads/nfe-regime-normal.json     (cenário rico)
backend-fastapi/docs/payloads/nfe-simples-nacional.json  (o caso das lojas)
```

O primeiro é **máximo de propósito** — item comum, item com ST (CEST), item com
CST 20 (redução de base + cBenef), pagamento em cartão (tipo_integracao) e
destinatário PF com endereço completo. Um exemplo mínimo auditaria só o caminho
feliz e deixaria de fora justamente os campos raros, que são os que ninguém
percebe faltando.

Gerados e mantidos por `test_payload_exemplo_auditoria.py`: mexer no payload sem
regerar quebra o teste, então o exemplo nunca envelhece em silêncio — que foi
exatamente o que aconteceu com o contrato de 09/09.

### Fora do payload de propósito
`ipi_situacao_tributaria` e `ipi_codigo_enquadramento` — removidos em
12/09/2026. Quando voltarem, o segundo tem de se chamar
**`ipi_codigo_enquadramento_legal`**, que é o nome da API da Focus. O grupo IPI é **opcional** no layout e este sistema não calcula
IPI (comércio e serviços). Informar "não tributado" era declarar um grupo que
não temos como garantir bem formado só para comunicar um zero. Voltam quando
houver cliente indústria, calculados de verdade e com `cEnq` na ordem do
schema.

---

## 3. O plano

### 3.1 Na plataforma (VPS)

**NÃO mexer no Zod** — o `passthrough` já está lá e não é a causa. Combinado
com o time de lá:

1. **Gravar o payload TRADUZIDO** a cada emissão. É o último salto antes da
   Focus, logo o único lugar que mostra exatamente o que ela recebeu. Hoje o
   `FocusNfeService.emitir` loga só a `ref`.
2. Conferir os campos aninhados de `emitente` e `destinatario` (§2) contra os
   três `MAPA_*` do tradutor. Item, raiz e totais não precisam.

### 3.2 No ERP — parar de descobrir isso por rejeição
| # | O que | Por quê |
|---|---|---|
| A | **Registrar o payload enviado** (hoje não é gravado em lugar nenhum) | Sem isso, toda investigação desse tipo é leitura de código e adivinhação. Foi o que custou esta tarde |
| B | **Teste de contrato** congelando os 66 campos | **FEITO** hoje (`test_contrato_payload_campos.py`): mexer no payload sem atualizar o contrato quebra o teste |
| C | **Eco da plataforma**: ela devolver, em modo diagnóstico, o payload como recebeu | Permite `diff` automático entre enviado e recebido — a prova que hoje não existe |
| D | Guardar a **rejeição estruturada** com o trecho do XML | Já existe parcialmente (status e motivo); falta o corpo |
| E | **Auditar os nomes de campo de item contra o XML AUTORIZADO** | **FEITO** hoje (`test_auditoria_nomes_no_xml.py`), esperando só o XML de uma emissão em homologação. Ver §3.4 |

O item A é o mais barato e o de maior retorno: com o payload gravado, o
diagnóstico de hoje teria durado um minuto.

### 3.3 Ordem
1. **Agora:** sidecar novo com o IPI fora → a loja emite. Guardar o JSON desta
   emissão antes de mandar (item A já entrou hoje).
2. **Esta semana:** o log do payload traduzido na VPS (§3.1) e a auditoria de
   nomes (item E). Os dois juntos fecham o buraco de verdade.
3. **Depois:** o IPI volta, calculado, com `ipi_codigo_enquadramento_legal`.

---

## 4. O que NÃO fazer

**Acusar o outro lado a partir de documento de diagnóstico, sem ler o código
de lá.** Foi o que eu fiz, e custou uma rodada de discussão: o `contrato-api-
fiscal-plataforma.md` descrevia o estado de 09/09 e o `passthrough` entrou em
08/09 — o documento nasceu desatualizado e eu o tratei como verdade corrente.

E **remendar campo a campo toda vez que a SEFAZ recusar**. O IPI foi corrigido
por mérito próprio (grupo opcional, imposto que não calculamos), mas a lição
que fica não é sobre IPI: é que **nome de campo errado é ignorado em silêncio
por toda a cadeia**, e só a SEFAZ reclama — tarde, e com mensagem que parece
falar de outra coisa.


---

## 3.4 O método certo para auditar nomes (correção do time da VPS)

Minha proposta era comparar o payload que o ERP envia com o que a plataforma
repassa à Focus. O time de lá apontou o furo, e ele é decisivo:

> O log lado a lado prova **transporte, não nomes**. Se o ERP mandar
> `ipi_codigo_enquadramento` e o log mostrar `ipi_codigo_enquadramento`
> chegando na Focus, o diff passa limpo — e o campo continua errado.

É exatamente o que aconteceu: o campo viajou intacto a vida inteira. Ninguém o
descartou. Ele simplesmente não significa nada para a Focus.

**Quem responde "a Focus entendeu?" é o XML autorizado.** Campo enviado que não
aparece lá foi ignorado em silêncio. A Focus devolve o XML em
`caminho_xml_nota_fiscal`, e o ERP já o lê (`client.baixar_xml`, com
`completa=1`).

Isso virou `test/services/fiscal/test_auditoria_nomes_no_xml.py`, que traz a
tabela **campo da API → tag do XML** para os 30 campos de item — a documentação
que faltava. Para rodar:

1. Emitir uma nota em **homologação** com o máximo de campos preenchidos.
2. Salvar o XML autorizado como `docs/payloads/xml-autorizado-homologacao.xml`.
3. Salvar o payload da emissão (do log `[FISCAL] payload NFE ref=...`) como
   `docs/payloads/payload-da-emissao.json`.
4. `pytest test/services/fiscal/test_auditoria_nomes_no_xml.py -s`

Sem os arquivos o teste é pulado. Com eles, a saída nomeia cada campo que não
deixou rastro no XML, e a lista de 30 se resolve de uma vez — sem depender de
documentação que se contradiz.

---

## 3.5 Veredito dos 25 campos aninhados (13/09/2026)

O time da VPS mandou as tabelas de chaves aceitas do `focus-payload.mapper.ts`.
Cruzadas com o que o ERP envia (`docs/payloads/nfe-regime-normal.json`):

| Grupo | Enviamos | Descartadas |
|---|---|---|
| `emitente` | 8 | **`regime_tributario`** |
| `emitente.endereco` | 7 | nenhuma |
| `destinatario` (PF) | 4 | nenhuma |
| `destinatario.endereco` | 7 | nenhuma |

**Só uma chave se perde, e o descarte é intencional e inofensivo:**
`regime_tributario` é o rótulo em texto ("Simples Nacional"); a Focus lê o CRT
numérico, que vai em `codigo_regime_tributario` — e esse chega. O ERP pode
parar de enviá-lo, mas não é urgente.

O `email` que eles levantaram como candidato **não se aplica**: o ERP não envia
email em nenhum dos dois grupos.

Ou seja: **o achatamento do tradutor não está tirando nada de que precisamos.**
O risco real estava, e continua, nos nomes de campo de item — §3.4.
