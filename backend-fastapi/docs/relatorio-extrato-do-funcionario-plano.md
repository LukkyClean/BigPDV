# Relatórios — Extrato de serviços do funcionário

> **Implementado** em 21/08/2026, na branch `feat/pdv`.
>
> Dois ajustes em relação ao plano, decididos durante a implementação:
>
> - O critério do item é `!= REPROVADO`, e não `== APROVADO`. É o mesmo que a
>   consulta de CMV deste módulo já usa, e o resultado é idêntico: finalizar OS
>   com item PENDENTE já é barrado, então numa OS finalizada ele não existe.
> - O `valor_total` do extrato é **menor** que o `faturamento_os` do ranking
>   sempre que a OS tiver peça — e isso é correto, não divergência. O teste que
>   amarra os dois usa OS só de serviço.

## O que é

Um botão discreto no Ranking por funcionário que abre o **extrato do que aquela
pessoa fez** no período: quais serviços, em quais OS, quanto somam. Imprimível,
para o dono entregar em mãos.

O gesto já existe no sistema e é o modelo a seguir: a **folha de comissão**
(`ComissaoFolhaPrint.vue`) é gerada pelo dono, impressa e entregue ao
funcionário. Este extrato é a mesma ideia num nível mais fino — em vez do total
a pagar, o que foi feito para chegar nele.

## Decisões tomadas com o dono (21/08/2026)

1. **Só o Master gera e imprime.** A tela do funcionário não muda. Mantém a
   regra fechada hoje: relatório gerencial é do dono.
2. **Com valores.** Valor por serviço e total — é o que torna o papel útil para
   o funcionário conferir a comissão. A folha de comissão já mostra valores a
   ele, então não há segredo novo sendo aberto.
3. **Só serviços.** Peça é material da loja: entra no custo, não na produção do
   técnico. `ordem_servico_itens.tipo = SERVICO`.

## O que já existe — e não precisa ser construído

- `ordem_servico_itens` tem `tipo`, `nome`, `quantidade`, `valor_total`,
  `garantia_dias` e `status_aprovacao`.
- `ordens_servico` tem `funcionario_id` (o técnico), `numero_os`,
  `data_finalizacao` e o objeto/cliente.
- `RelatorioRanking` já devolve `funcionario_id` e `nome` por linha — é de onde
  o botão sai, sem consulta extra para saber quem listar.
- `imprimirComPagina('A4')` + `PrintFooter` + `useCompanyPrintInfo` são o
  encanamento de impressão, já usado pela folha de comissão e pelo financeiro.

**Serviço só existe em OS.** Venda no PDV carrega apenas produto (`CADASTRADO` /
`AVULSO`), sem `servico_id`. Isso simplifica o escopo e traz uma consequência: o
extrato **não faz sentido numa loja de PDV puro**, e a seção precisa sumir lá.

---

## Backend

### Endpoint

```
GET /api/v1/relatorios/extrato-funcionario
    ?funcionario_id=&inicio=&fim=
```

`Depends(get_current_master_user)` — 403 para quem não é Master, igual aos
outros quatro relatórios gerenciais. Não inventar permissão nova.

### Resposta

```python
class ExtratoServicoItem(BaseModel):
    """Um serviço executado, na OS em que foi executado."""
    numero_os: int
    data_finalizacao: date
    objeto: Optional[str]      # "Gol ABC-1234" — o que o segmento chamar de objeto
    cliente: Optional[str]
    servico: str               # ordem_servico_itens.nome
    quantidade: float
    valor_total: int           # centavos

class RelatorioExtratoFuncionario(BaseModel):
    inicio: date
    fim: date
    funcionario_id: int
    funcionario_nome: str
    qtd_os: int                # OS DISTINTAS, não linhas
    qtd_servicos: int
    valor_total: int
    itens: list[ExtratoServicoItem]
```

`qtd_os` conta OS distintas de propósito: uma OS com três serviços é **uma** OS
e três serviços. Somar linhas daria "3 OS" e o número não bateria com o ranking.

### Regras

- **Âncora é `data_finalizacao`**, como em todos os relatórios do módulo. O que
  foi concluído no período conta no período — igual a `get_os_finalizadas_periodo`.
- **Só OS finalizadas.** Serviço em OS aberta ainda pode mudar ou ser removido;
  extrato com linha que some depois é pior que extrato incompleto.
- **Só `tipo = SERVICO`.**
- **Item com `status_aprovacao` recusado fica de fora** — ele não foi executado.
  Conferir o enum antes; se "recusado" não existir como estado final, ignorar
  esta regra em vez de inventar.
- **Ordenação**: `data_finalizacao` crescente, depois `numero_os`. O papel é
  lido de cima para baixo como uma linha do tempo do mês.

### Onde o código mora

| Item | Onde |
|---|---|
| Consulta (join OS + itens + objeto/cliente) | `db/crud/relatorio.py` |
| Montagem e agregados | `services/relatorio.py` |
| Schemas acima | `schemas/relatorio.py` |
| Endpoint Master-only | `api/v1/endpoints/relatorios.py` |

---

## Frontend

### O botão

Uma coluna a mais na tabela do `RankingSection.vue`, com ícone (`FileText`) por
linha. O ranking já tem `funcionario_id` e `nome` — é o lugar natural: você está
justamente olhando a lista de pessoas.

```
Ranking por funcionário
  1  Michel    R$ 320,00   R$ 920,00   R$ 1.240,00   [↧]
  2  Alan      R$ 890,00   R$   0,00   R$   890,00   [↧]
```

Discreto: ícone sem rótulo, na cor de apoio, como as ações rápidas da tabela de
vendas.

### O modal

Abre com o extrato na tela e um botão **"Imprimir extrato"**. Reusa o fluxo da
folha de comissão verbatim — `mostrarFolha` + `nextTick` + `afterprint` com
fallback de 60s + `imprimirComPagina('A4')`.

O `ExtratoFuncionarioPrint.vue` segue `ComissaoFolhaPrint.vue`: `hidden
print:block`, teleportado para o body, cabeçalho com `useCompanyPrintInfo` e
`PrintFooter`.

### A folha

```
[logo]  EMPRESA LTDA
        Extrato de serviços · 01/08/2026 a 31/08/2026

        Funcionário: Michel

  DATA    OS     OBJETO / CLIENTE        SERVIÇO              QTD    VALOR
  12/08   1042   Gol ABC-1234 · João     Troca de óleo          1    R$  90,00
  12/08   1042   Gol ABC-1234 · João     Alinhamento            1    R$ 120,00
  14/08   1051   Uno XYZ-9876 · Maria    Revisão completa       1    R$ 340,00
  ...

  14 serviços em 9 OS                                  TOTAL  R$ 1.240,00
```

A OS repetida na segunda linha é proposital: o papel é conferido item a item, e
uma célula vazia obriga o leitor a subir para saber de qual OS aquilo é.

### Onde some

- Dentro do `v-if="isMaster"` que já envolve as seções gerenciais.
- Dentro do `v-if="usaOrdemServico"` — loja de PDV puro não tem serviço, e um
  botão que abre extrato sempre vazio é pior que botão nenhum.

---

## Testes

1. Serviço de OS finalizada do funcionário entra; o de outro funcionário, não.
2. Peça na mesma OS **não** entra.
3. OS ainda aberta não entra.
4. `qtd_os` conta OS distintas — três serviços numa OS dão `qtd_os = 1`.
5. O `valor_total` do extrato bate com o `faturamento_os` daquela pessoa no
   ranking, no mesmo período. **Este é o teste que importa**: dois relatórios
   que discordam do mesmo número destroem a confiança nos dois.
6. 403 para quem não é Master, com um cargo que TEM a permissão do módulo.
7. Período sem OS devolve extrato vazio com totais zerados, não erro.

## O que NÃO entra

- **Não** muda a tela do funcionário.
- **Não** entra peça, nem custo, nem comissão calculada — comissão já tem folha
  própria, e duplicar o cálculo em dois lugares é convidar os dois a divergirem.
- **Não** exporta CSV. A folha de comissão tem export; se fizer falta aqui,
  entra depois, com o mesmo `exportar()`.

## Riscos

| Risco | Mitigação |
|---|---|
| Extrato discordar do ranking | Teste 5 amarra os dois ao mesmo número |
| Loja de PDV vendo botão inútil | `v-if="usaOrdemServico"` |
| OS sem funcionário atribuído | Não aparece em extrato nenhum — é o mesmo comportamento do ranking; não inventar um "sem técnico" |

## Custo

Uma migration **não** é necessária: nada de novo é persistido, tudo sai de
`ordens_servico` e `ordem_servico_itens`. Mesmo assim o deploy exige
`npm run build:sidecar`, porque o backend ganha endpoint novo.
