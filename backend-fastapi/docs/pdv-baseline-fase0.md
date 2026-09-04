# PDV — Fase 0: o "antes" congelado

> Registro do baseline contra o qual toda prova medida das fases seguintes será
> comparada. **Nenhum código foi alterado nesta fase.**
>
> Levantado em **15/08/2026, 11:37** (horário local).

---

## 1. Ponto de partida

| | |
|---|---|
| Branch | `feat/pdv` |
| Commit HEAD | `d43f072ef322c098238122405e8a33ecb0750c78` |
| Base da branch | `feat/segmento-serigrafia` (nunca `master`) |

**A árvore de trabalho NÃO estava limpa.** Havia uma alteração não commitada em
`frontend/src-tauri/src/network/discovery.rs`: um caractere `t` solto no fim do
arquivo, sem quebra de linha. É acidental (arquivo estava aberto no editor) e
**quebra a compilação do Rust**. Não foi feita por esta fase e não foi revertida sem
autorização — ver seção 5.

## 2. Suíte de testes — backend

```
410 passed, 93 warnings in 178.39s
```

Comando: `python -m pytest test/ -q` (venv ativado).

**Ressalva importante para leituras futuras:** existe um bug conhecido de fuso em
que o filtro de relatório recebe data local contra `criado_em` em UTC. Os testes de
`test_custo_estoque.py` são o detector disso — eles **passam de manhã e falham à
noite**. Esta corrida foi às 11:37, então passaram. Uma falha desses testes numa
corrida noturna **não é regressão desta branch**; é o bug de fuso já existente.

## 3. Type check — frontend

```
npx vue-tsc --noEmit   →   exit 0, nenhuma saída
```

Zero erros. Lembrando que `npm run build` **não** roda o `vue-tsc` (o commit f9ce039
o removeu do script), então esta verificação é manual e precisa ser repetida a mão.

## 4. Sidecar

```
npm run check:sidecar   →   ✓ sidecar em dia com o backend
```

Em dia no momento do baseline. **Vai ficar desatualizado assim que a fase 1 mexer no
backend** — é o esperado, e tem que ser regerado antes de gerar instalador.

## 5. Bancos de dados

São **dois bancos diferentes** e não podem ser confundidos:

| | dev | instalado (exe) |
|---|---|---|
| caminho | `backend-fastapi/start_big.db` | `%LOCALAPPDATA%\StartBigERP\data\start_big.db` |
| quem usa | `fastapi dev` (porta 8000) | app instalado (porta 8080-8083) |
| tamanho | 606.208 bytes | 593.920 bytes |
| modificado | 15/08/2026 | 30/07/2026 |
| revisão Alembic | `a1b2c3d4e5f7` (**head**) | `a4b5c6d7e8f9` |

Cópias do baseline (somente cópia — os originais não foram tocados) em
`scratchpad/baseline-fase0/`, com os nomes `dev_start_big.db` e
`instalado_start_big.db`.

### 5.1 O achado que mais importa para a fase 1

**O banco do exe está 9 migrations atrás do head.** A cadeia que falta nele:

```
a4b5c6d7e8f9  ← onde o banco do exe está
  → b7c8d9e0f1a2  custo no livro de estoque
  → c8d9e0f1a2b3  custo do item avulso na venda
  → d9e0f1a2b3c4  cor do tema da empresa
  → b1c2d3e4f5a6  chave pix da empresa
  → c2d3e4f5a6b7  forma de pagamento do adiantamento da OS
  → d3e4f5a6b7c8  medidas da sacola viram referencias
  → e4f5a6b7c8d9  configuracoes_backup
  → f1a2b3c4d5e6  configuracoes_backup
  → a1b2c3d4e5f7  apresentacao dos comprovantes de OS   ← head
```

Isso é **bom para o teste**: ele é um retrato realista de "loja desatualizada", que
é exatamente o caso que a migration da fase 1 precisa sobreviver. A migration nova
não pode assumir que o banco chega nela já no head.

Head único confirmado: `alembic heads` → `a1b2c3d4e5f7 (head)`. Não há segunda
cabeça aberta.

---

## 6. Como usar este baseline

- **Fase 1** — aplicar a migration sobre a cópia do banco do **exe** (o atrasado) e
  confirmar que sobe até o head sem erro e que o app abre e vende igual.
- **Fase 2** — comparar as linhas gravadas por uma venda finalizada com a chave
  desligada contra o comportamento aqui registrado: `venda`, `venda_pagamento` e
  `movimentacoes_estoque` idênticas, livro do dinheiro **vazio**.
- **Todas as fases** — `pytest` tem que continuar em **410 passed** (mais os testes
  novos de cada fase) e `vue-tsc` em **zero**.
