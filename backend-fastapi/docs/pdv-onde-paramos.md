# PDV — onde paramos (15/08/2026)

Ponto de retomada. Branch `feat/pdv`, árvore limpa, tudo commitado.

---

## O que está PRONTO

Fases 0 a 5 do plano, mais três coisas pedidas depois. Suíte saiu de **410 → 445
testes**, `vue-tsc` em zero o tempo todo.

| # | fase | commit |
|---|---|---|
| 0 | baseline congelado | `af49009` |
| 0.5 | fuso: o dia do relatório é o da loja | `182ca3f` |
| 1 | schema (caixa + livro do dinheiro) | `894388c` |
| 2 | backend do caixa atrás da chave | `1650ea0` |
| 3 | caixa dentro do PDV | `e54054c` |
| 4 | leitor de código de barras | `50ffb9a` |
| 5 | segmento `pdv` e o sumiço da OS | `84db7e8` |
| + | sangria em Segurança; venda não começa sem caixa | `bbf40a3` |
| + | Relatórios › Caixa (quem fechou faltando/sobrando) | `3efd255` |
| + | correção: relatório não pode dizer "Bateu certo" sem dado | `1b83ca3` |

**Verificado no app de verdade**, não só em teste: menu sem "Serviços" numa loja
`pdv`, barra do caixa, trava recusando a finalização, e a diferença de −R$ 10
aparecendo com o nome de quem fechou.

---

## POR ONDE COMEÇAR AMANHÃ

Três frentes, em ordem de recomendação.

### 1. Tela de Terminais *(pequena, fecha o cenário "servidor + 2 caixas")*

As colunas `nome` e `papel` existem em `terminais_conectados` desde a fase 1,
mas **não há tela para preenchê-las**. Duas consequências:

- a coluna **Terminal** do relatório de caixa aparece vazia
- sem `papel = RETAGUARDA`, **o PC do dono é tratado como caixa** — com
  "Exigir caixa aberto" ligado, a máquina dele vai pedir abertura de turno

Com um PC só não incomoda. Com o segundo, incomoda no primeiro dia.

A máquina já se cadastra sozinha no login (por HWID) — falta só nomear e marcar
o papel.

### 2. Fase 6 — instalar na adega

`npm run build:sidecar` → instalador → instalar → ligar as chaves lá.

**O sidecar está desatualizado** desde a fase 0.5, quando o backend mudou.

> **Não mande as fases 4 e 5 no mesmo instalador** para as três lojas que já
> rodam. Se algo quebrar, você precisa saber se foi o leitor ou o sumiço da OS.
> Para a **adega** tanto faz — é instalação nova, recebe tudo junto.

### 3. Permissões de verdade *(projeto próprio, o maior dos três)*

Ver a seção abaixo. É o que destrava o cargo "Supervisor".

---

## O problema das permissões, explicado

Você cria um cargo e marca **só "Visualizar"** em Vendas, esperando que a pessoa
olhe mas não apague. **Ela apaga.**

O sistema não pergunta *"pode EXCLUIR em Vendas?"*. Pergunta *"tem ALGUMA
permissão em Vendas?"* — e "Visualizar" já responde que sim:

```python
# app/api/v1/endpoints/venda.py
module_permission = ["venda", "view_sales", "manage_sales", "delete_sales"]

# app/core/depends.py
if any(permissoes.get(p) is True for p in perms):
    return usuario_token          # basta UMA
```

É uma porta com três chaves na parede — olhar, editar, excluir — cuja fechadura
só confere se você tem *alguma* chave. Qualquer uma abre tudo.

Vale para produtos também: `POST /produtos/` exige `"produto"`, a mesma chave do
GET.

**Isso é pior que não ter a granularidade:** a tela dá a sensação de ter limitado
alguém que continua podendo tudo.

### O que falta para o cargo "Supervisor" existir

1. **Fazer as três colunas valerem** — escrita exige `manage_*`, exclusão exige
   `delete_*`.
2. **Redefinir senha de funcionário** — hoje só existe `PATCH /usuarios/me/senha`
   (cada um troca a própria). Ninguém redefine a de outro, nem o master. Se o
   operador esquecer a senha, não há caminho no sistema.

### O RISCO de mexer nisso

Apertar a permissão pode **trancar gente nas três lojas que já rodam**. Se lá
existe um cargo com só "Visualizar" marcado e a pessoa trabalha normalmente hoje,
no dia da atualização ela para de conseguir trabalhar.

Precisa de migração de compatibilidade: quem já tem `view_*` ganha `manage_*`,
para ninguém acordar sem acesso. A regra nova vale para cargos criados dali em
diante.

---

## Coisas que a gente descobriu e não pode esquecer

- **Master é quem tem CARGO CHAMADO "Master"** — `is_master = (cargo.nome.lower()
  == "master")`. Não é checkbox nem conta única.
- **Visão gerencial vem do NOME do cargo**: contém "gerente" ou "administrador" →
  vê os dados de todos. Um cargo "Gerente de Caixa" daria visão total sem querer.
- **Relatórios não filtra por funcionário.** Quem tiver a permissão vê o
  faturamento da empresa, o ranking e a **comissão de todos**. A proteção é não
  marcar a permissão. A única parte protegida sozinha é a seção de Caixa, que
  exige visão gerencial.
- **Cada funcionário precisa do PRÓPRIO login.** Compartilhar credencial faz o
  relatório de caixa dizer o mesmo nome em todas as linhas — e aí não há como
  saber quem fechou faltando.
- **Reinicie o backend depois de atualizar.** Duas vezes hoje o sintoma foi
  código novo com processo antigo: o segmento `pdv` recusado no cadastro, e o
  relatório de caixa mostrando zeros.
