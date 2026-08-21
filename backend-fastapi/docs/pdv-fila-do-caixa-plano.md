# PDV — Fila do caixa (atendente monta, caixa recebe)

> Escrito em 21/08/2026, na branch `feat/pdv`.
>
> - **Fase 1 — implementada** em 21/08/2026.
> - **Fase 2 — planejada**, não implementada.

## O problema

Numa loja com mais de uma pessoa, quem atende o cliente e quem recebe o dinheiro
não são a mesma pessoa. Hoje o StartBig não suporta essa divisão: com
`exigir_caixa_aberto` ligado, o atendente **não consegue nem começar** a venda
sem ter um turno de caixa aberto no nome dele.

O resultado prático é ou todo mundo abrir caixa (e aí a gaveta não bate com
ninguém), ou o atendente usar a máquina do caixa (e aí a fila para).

## O que JÁ funciona — e não precisa ser construído

Vale registrar, porque é metade do caminho:

- Uma venda `ATIVA` fica na lista e **qualquer operador pode abri-la e
  finalizá-la**.
- Ao finalizar, **o dinheiro cai no turno de quem recebeu**, não de quem vendeu.
  Garantido por `exigir_caixa_aberto_para_vender`, que cobra o turno do
  `operador_funcionario_id`, e por `registrar_pagamentos_de_venda`.
- **A comissão continua com o vendedor**, porque `venda.funcionario_id` é um
  campo separado de quem operou o checkout.
- Existe teste travando isso:
  `test_dinheiro_cai_no_turno_de_quem_recebe_e_nao_de_quem_vendeu`.

Ou seja: o modelo de dados já separa vendedor de recebedor. Falta destravar a
entrada e dar visibilidade à fila.

## Decisões tomadas com o dono (21/08/2026)

1. **A trava do caixa fica só na finalização.** Qualquer máquina pode começar
   uma venda sem turno aberto.
2. **A fila do caixa é um estado explícito**, não uma convenção verbal.

---

## Fase 1 — A trava sai da criação — FEITA

Pequena, independente, e entrega valor sozinha. Pode ir para a loja antes da
Fase 2.

### O que muda

Remover a chamada de `exigir_caixa_aberto_para_vender` em
[`services/venda.py:84`](../app/services/venda.py) (`create_sale`). A de
[`venda.py:296`](../app/services/venda.py) (`finish_sale`) **fica**.

Isso não abre buraco no controle da gaveta, e o próprio comentário do código já
diz por quê:

> A trava existe TAMBEM na finalizacao, e la e a garantia de verdade — e o
> momento do dinheiro. Aqui e para o operador saber ANTES de montar o carrinho
> inteiro, em vez de descobrir no checkout com o cliente esperando.

A da criação é **cortesia**, não garantia.

### O que precisa vir junto

Sem a trava na criação, quem está **sozinho** na loja monta o carrinho inteiro e
só descobre no checkout que precisa abrir o caixa — que é exatamente o atrito
que aquela linha evitava. Substituir por um aviso não bloqueante na tela de
vendas: uma faixa dizendo "Caixa fechado — você poderá montar vendas, mas não
finalizá-las", com o botão de abrir ali.

`SalesView.vue` já tem `vendaBloqueada`; ele deixa de desabilitar "Nova venda" e
passa a alimentar essa faixa.

### Efeito colateral bem-vindo: o beco da retaguarda fecha

Hoje uma máquina marcada como `RETAGUARDA` **esconde a barra do caixa**
([`CaixaBar.vue:158`](../../frontend/src/modules/sales/caixa/components/CaixaBar.vue))
mas **continua sendo cobrada** por `exigir_caixa_aberto` — nem o frontend nem o
backend olham o papel do terminal nessa hora. O operador fica sem o botão de
abrir caixa E com "Nova venda" bloqueado, sem saída.

O modelo já prometia o contrário:

> `'PDV'` abre caixa e é cobrado por `exigir_caixa_aberto`; `'RETAGUARDA'` não.
> — [`db/models/terminal_conectado.py:45`](../app/db/models/terminal_conectado.py)

Com a Fase 1 a promessa passa a valer sem código específico de terminal.

### Testes da Fase 1

- Venda **nasce** sem turno aberto, com as duas chaves ligadas (hoje falha).
- Venda **não finaliza** sem turno — o teste que já existe, que precisa
  continuar verde.
- Máquina retaguarda monta venda normalmente.

---

## Fase 2 — A fila do caixa — planejada

### Decisão de arquitetura: coluna, não status novo

`VendaStatus` tem três valores (`ATIVA`, `FINALIZADA`, `CANCELADA`) e o código
filtra por igualdade em vários lugares — `db/crud/venda.py` na listagem e em
`get_sales_status`, que alimenta os cards ATIVAS / FINALIZADAS / CANCELADAS.

Acrescentar `AGUARDANDO_PAGAMENTO` obrigaria a revisar **toda** comparação de
status do módulo, e uma esquecida faz a venda sumir de uma contagem sem erro
nenhum. Três lojas em produção dependem dessas telas.

**Em vez disso: uma coluna nova em `vendas`.**

```python
enviada_ao_caixa_em: Mapped[Optional[datetime]] = mapped_column(
    DateTime, nullable=True,
    doc="Quando o atendente mandou a venda para a fila do caixa. NULL = em montagem",
)
```

O status continua `ATIVA` nos dois casos. Nada que hoje filtra status muda de
comportamento. A coluna é aditiva e nullable — loja que atualiza e não usa a
funcionalidade não vê diferença.

Guardar o **timestamp** em vez de um booleano custa o mesmo e dá a ordenação da
fila de graça (quem esperou mais aparece primeiro), além de permitir medir tempo
de espera depois, se algum dia interessar.

### Princípio: a coluna é sinal de lista, não regra de negócio

**A finalização ignora completamente `enviada_ao_caixa_em`.** O caixa pode
finalizar uma venda que nunca entrou na fila, e pode editar uma que entrou. A
coluna só organiza a lista.

Isso é o que mantém o risco baixo: nenhuma regra de dinheiro passa a depender de
um campo novo.

### Backend

| Item | Onde |
|---|---|
| Coluna `enviada_ao_caixa_em` | `db/models/venda.py` |
| Migration aditiva | `alembic/versions/` — decidir pela **presença** da coluna |
| `enviada_ao_caixa_em` no schema de leitura | `schemas/venda.py` |
| `POST /vendas/{id}/enviar-ao-caixa` | `api/v1/endpoints/venda.py` |
| `POST /vendas/{id}/devolver-para-montagem` | idem |
| Filtro `na_fila: bool` na listagem | `db/crud/venda.py` |
| Contagem da fila | junto de `get_sales_status` |

Regras dos dois endpoints:

- **Enviar** recusa venda sem itens (fila com carrinho vazio é ruído) e venda
  que não esteja `ATIVA`.
- **Enviar** é idempotente: reenviar não muda o timestamp original, senão o
  atendente perderia o lugar na fila sem querer.
- **Devolver** limpa a coluna. Qualquer operador pode — o atendente que se
  arrependeu e o caixa que viu problema.
- Permissão: a mesma de vender (`view_sales`). Não inventar permissão nova; o
  dono já decidiu quem opera venda.

### Alterar item tira a venda da fila

Se o atendente acrescentar um item depois de enviar, o caixa está olhando um
total que mudou embaixo dele. Então `add_item_to_sale`, `update_item_in_sale`,
`remove_item_from_sale` e a aplicação de desconto **limpam
`enviada_ao_caixa_em`** e a venda volta para "em montagem".

Custa um reenvio ao atendente e evita o caixa cobrar o valor errado. É a única
regra da Fase 2 que mexe em código de venda existente — e ela é aditiva
(atribuir `None` a uma coluna nova).

### Frontend

- **Botão "Enviar para o caixa"** no rodapé do `SaleModal`, ao lado de
  "Finalizar venda". Aparece **só** quando `controlar_caixa` está ligado — loja
  sem caixa não tem fila, e o botão seria ruído.
- **No Modo Balcão o botão não aparece**: ali é uma pessoa só, do começo ao fim.
- **Grupo "Aguardando pagamento (N)"** no topo da lista de vendas, ordenado por
  `enviada_ao_caixa_em` crescente.
- **Selo na linha** da venda que está na fila, com há quanto tempo espera.
- **Polling**: a lista já roda com `refetchInterval`
  (`core/config/queryIntervals.ts`) — é o único mecanismo que cruza terminais
  neste sistema, e é o que faz a fila aparecer na máquina do caixa sem F5.
  Conferir se o intervalo atual da lista serve; `REFETCH_REALTIME` é o usado
  onde a travessia entre terminais importa.
- **Chave de cache**: tudo pendurado no prefixo de `saleKeys`, e as duas
  mutations novas invalidam `saleKeys.lists()` e `saleKeys.status()`. Chave-irmã
  não é alcançada pelo TanStack.

### Testes da Fase 2

1. Enviar marca o timestamp; devolver limpa.
2. Reenviar **não** move o lugar na fila.
3. Enviar venda sem item é recusado.
4. Acrescentar item depois de enviar **tira** da fila.
5. O caixa finaliza uma venda da fila e **o dinheiro cai no turno dele** — é o
   teste que já existe, reencenado pelo caminho novo.
6. A comissão continua com o atendente (`venda.funcionario_id` intacto).
7. **Inércia**: com `controlar_caixa` desligado, nada muda — a coluna fica NULL
   e a lista se comporta como sempre. É o teste que decide se a fase pode ir
   para a loja.

---

## O que NÃO entra

- **Não** existe "venda finalizada esperando pagamento". Finalizar é registrar o
  dinheiro, num passo só. A fila acontece **antes** da finalização.
- **Não** há bloqueio de quem pode finalizar o quê. Qualquer operador com turno
  aberto pega qualquer venda da fila.
- **Não** há notificação/som para o caixa. O polling da lista basta; som é
  decisão de produto separada.
- **Não** mexer no `VendaStatus`.

## Riscos

| Risco | Mitigação |
|---|---|
| Regressão nas telas de venda das 3 lojas | Coluna aditiva, status intocado, teste de inércia |
| Fila esquecida com vendas velhas | O selo mostra o tempo de espera; limpeza fica para depois se incomodar |
| Atendente edita e o caixa não percebe | Editar tira da fila (regra acima) |
| Loja de um PC só perde o aviso antecipado | Faixa não bloqueante na Fase 1 |

## Ordem de execução

1. **Fase 1** — trava sai da criação + faixa de aviso + testes. Pode ir sozinha
   para a loja e já resolve o beco da retaguarda.
2. **Fase 2** — coluna, migration, endpoints, botão, grupo na lista, testes.

Ambas exigem `npm run build:sidecar` antes do instalador: as duas mexem no
backend.
