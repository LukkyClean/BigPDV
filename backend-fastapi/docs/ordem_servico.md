# Módulo: Ordem de Serviço (OS)

> Contexto técnico completo para desenvolvedores e assistentes de IA.

---

## Visão Geral

Uma **Ordem de Serviço (OS)** representa o ciclo de vida completo de um atendimento técnico: desde a entrada do equipamento, passando pelo diagnóstico e execução do serviço, até a finalização com pagamento.

### Responsabilidades do módulo

- Abertura de OS com equipamento e itens de serviço
- Gerenciamento de itens (adicionar, atualizar, remover)
- Upload e remoção de fotos de diagnóstico
- Atualização de dados do equipamento e troca de cliente
- Transições de status com regras de negócio
- Finalização integrada com registro de pagamentos múltiplos
- Catálogo global de Formas de Pagamento

---

## Mapa de Arquivos

```
app/
├── api/v1/endpoints/
│   ├── ordem_servico.py        → 14 endpoints REST da OS (itens, fotos, status)
│   └── forma_pagamento.py      → 4 endpoints CRUD do catálogo de formas de pagamento
│
├── services/
│   ├── ordem_servico.py        → Regras de negócio (criação, atualização, status, pagamentos)
│   └── ordem_servico_foto.py   → I/O de arquivos (upload/delete de fotos em disco)
│
├── db/
│   ├── crud/
│   │   ├── ordem_servico.py    → Queries SQLAlchemy (OS, itens, fotos, pagamentos)
│   │   └── forma_pagamento.py  → Queries SQLAlchemy do catálogo de formas de pagamento
│   └── models/
│       ├── ordem_servico.py              → Tabela ordens_servico
│       ├── ordem_servico_equipamento.py  → Tabela ordem_servico_equipamentos
│       ├── ordem_servico_item.py         → Tabela ordem_servico_itens
│       ├── ordem_servico_pagamento.py    → Tabela ordem_servico_pagamentos
│       ├── ordem_servico_foto.py         → Tabela ordem_servico_fotos
│       └── forma_pagamento.py            → Tabela formas_pagamento
│
├── schemas/
│   ├── ordem_servico.py        → Todos os schemas Pydantic da OS
│   └── forma_pagamento.py      → Schemas do catálogo de formas de pagamento
│
└── static/uploads/ordens-servico/{os_id}/  → Fotos de diagnóstico
```

---

## Modelo de Dados

### Relacionamentos

```
OrdemServico (ordens_servico)
├── funcionario_id → FK Funcionario (nullable)
├── equipamento_id → FK OrdemServicoEquipamento (obrigatório)
│   └── cliente_id → FK Cliente (PF ou PJ, polimórfico)
├── itens[]        → OrdemServicoItem (cascade delete)
│   ├── produto_id → FK Produto (nullable, SET NULL on delete)
│   └── servico_id → FK Servico (nullable, SET NULL on delete)
├── pagamentos[]   → OrdemServicoPagamento (cascade delete)
│   └── forma_pagamento_id → FK FormaPagamento
└── fotos[]        → OrdemServicoFoto (cascade delete)
```

### Convenções importantes

| Convenção | Detalhe |
|---|---|
| **Valores monetários** | Sempre em centavos (integer). Ex: R$ 450,00 = `45000` |
| **Identificador público** | `numero_os` (ex: `OS-2026-000001`) — use nas URLs |
| **ID interno** | `id` (integer) — uso somente interno |
| **Soft delete** | Campo `ativo` na OS. Cancelamento via endpoint `/cancelar` |
| **Cascade** | Itens, pagamentos e fotos são deletados junto com a OS |

---

## Estados da OS — State Machine

```
         ┌──────────────────────────────────────────────┐
         │               update (manual)                │
         ▼                                              │
       ABERTA ──► EM_ANDAMENTO ──► AGUARDANDO_PECAS ────┘
         │              │                  │
         │              ▼                  ▼
         │    AGUARDANDO_APROVACAO  AGUARDANDO_RETIRADA
         │              │                  │
         │              └──────┬───────────┘
         │                     ▼
         │                FINALIZADA ◄──── /finalizar (pagamento integral)
         │                     │
         └──────────► CANCELADA │
                          │     │
                          └──►──┘
                            /reabrir → EM_ANDAMENTO
                            (limpa pagamentos e data_finalizacao)
```

### Regras por transição

| De → Para | Endpoint | Restrição |
|---|---|---|
| Qualquer → FINALIZADA | `PUT /finalizar` | sum(pagamentos) == valor_total |
| Qualquer → CANCELADA | `PUT /cancelar` | Não pode estar já CANCELADA |
| FINALIZADA/CANCELADA → EM_ANDAMENTO | `PUT /reabrir` | Limpa pagamentos e solucao |
| Transições manuais | `PUT /` (campo `status`) | Bloqueia FINALIZADA e CANCELADA |

---

## Cálculo Financeiro

```
valor_bruto = sum(item.quantidade × item.valor_unitario para cada item)
valor_total = max(0, valor_bruto - desconto)
```

- `valor_bruto` e `valor_total` são recalculados automaticamente quando:
  - Itens são adicionados, atualizados ou removidos
  - O campo `desconto` é alterado (via `PUT /` ou no corpo de `/finalizar`)

- **Validação na finalização**: `sum(pagamentos.valor) == valor_total`
  - Se a soma divergir, retorna `409 CONFLICT`

---

## Endpoints Completos

**Base URL**: `/api/v1/ordens-servico`

### OS — CRUD e Status

| Método | Path | Body | Response | Descrição |
|---|---|---|---|---|
| `POST` | `/` | `OrdemServicoCreate` | `OrdemServicoRead` | Criar OS com equipamento e itens |
| `GET` | `/` | query params | `OrdemServicoQuery` | Listar OS paginado com filtros |
| `GET` | `/stats` | — | `OrdemServicoStats` | Contadores e ticket médio |
| `GET` | `/{os_number}` | — | `OrdemServicoRead` | Buscar OS completa pelo número |
| `PUT` | `/{os_number}` | `OrdemServicoUpdate` | `OrdemServicoRead` | Atualizar campos da OS |
| `PUT` | `/{os_number}/equipamento` | `OSEquipamentoUpdate` | `OrdemServicoRead` | Atualizar equipamento/cliente |
| `PUT` | `/{os_number}/finalizar` | `OrdemServicoFinalizar` | `OrdemServicoRead` | Finalizar com pagamentos |
| `PUT` | `/{os_number}/cancelar` | `OrdemServicoCancelar` | `OrdemServicoRead` | Cancelar OS |
| `PUT` | `/{os_number}/reabrir` | — | `OrdemServicoRead` | Reabrir OS finalizada/cancelada |

### Itens

| Método | Path | Body | Response | Descrição |
|---|---|---|---|---|
| `POST` | `/{os_number}/itens` | `OSItemCreate` | `OrdemServicoRead` | Adicionar item |
| `PUT` | `/{os_number}/itens/{item_id}` | `OSItemUpdate` | `OrdemServicoRead` | Atualizar item |
| `DELETE` | `/{os_number}/itens/{item_id}` | — | `204` | Remover item |

### Fotos

| Método | Path | Body | Response | Descrição |
|---|---|---|---|---|
| `POST` | `/{os_number}/fotos` | `UploadFile` | `OSFotoRead` | Upload de foto |
| `DELETE` | `/{os_number}/fotos/{foto_id}` | — | `204` | Remover foto |

### Formas de Pagamento

**Base URL**: `/api/v1/formas-pagamento`

| Método | Path | Body | Response | Descrição |
|---|---|---|---|---|
| `GET` | `/` | — | `List[FormaPagamentoRead]` | Listar todas |
| `POST` | `/` | `FormaPagamentoCreate` | `FormaPagamentoRead` | Criar |
| `PUT` | `/{fp_id}` | `FormaPagamentoUpdate` | `FormaPagamentoRead` | Atualizar |
| `DELETE` | `/{fp_id}` | — | `204` | Desativar (soft delete) |

---

## Schemas de Entrada e Saída

### Criação (`OrdemServicoCreate`)

```json
{
  "prioridade": "NORMAL",
  "defeito_relatado": "Tela preta após queda",
  "cliente_id": 1,
  "funcionario_id": 1,
  "equipamento": {
    "tipo_equipamento": "CELULAR",
    "marca": "Samsung",
    "modelo": "Galaxy S23",
    "numero_serie": "SN123",
    "imei": "352415001234567"
  },
  "itens": [
    { "tipo": "PRODUTO", "nome": "Tela S23", "unidade_medida": "UN", "quantidade": 1, "valor_unitario": 45000 },
    { "tipo": "SERVICO", "nome": "Mão de obra", "unidade_medida": "UN", "quantidade": 1, "valor_unitario": 12000 }
  ]
}
```

### Finalização (`OrdemServicoFinalizar`)

```json
{
  "solucao": "Substituição do módulo frontal",
  "desconto": 0,
  "pagamentos": [
    { "forma_pagamento_id": 1, "valor": 45000, "parcelas": 1 },
    { "forma_pagamento_id": 2, "valor": 12000, "parcelas": 1 }
  ]
}
```

> `sum(pagamentos.valor)` = 57000 deve == `os.valor_total` = 57000 ✓

### Resposta (`OrdemServicoRead`) — campos principais

```
id, numero_os, status, prioridade
valor_bruto, valor_total, desconto
data_criacao, data_atualizacao, data_finalizacao, data_previsao
ativo, garantia
cliente (ClienteRead)
funcionario (FuncionarioRead | null)
equipamento (OSEquipamentoRead)
itens (OSItemRead[])
pagamentos (OSPagamentoRead[])   ← populado após finalização
fotos (OSFotoRead[])             ← populado conforme uploads
```

---

## Filtros de Listagem (`GET /`)

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `search` | `string` | Busca por numero_os, nome PF, razão social PJ |
| `status` | `OrdemServicoStatus` | Filtra por status específico |
| `priority_sort` | `boolean` | Ordena por prioridade (URGENTE → BAIXA) |
| `page` | `int` | Página atual (padrão: 1) |
| `limit` | `int` | Itens por página (padrão: 20, máx: 100) |

---

## Upload de Fotos

- **Diretório**: `static/uploads/ordens-servico/{os_id}/{uuid}.{ext}`
- **Nomenclatura**: UUID v4 para evitar colisões
- **Acesso**: `GET /static/uploads/ordens-servico/{os_id}/{arquivo}` (via StaticFiles)
- **Delete**: Remove arquivo físico + tenta limpar diretório vazio
- **Validação de ownership**: O foto_id é validado contra o os_number na rota

---

## Padrão de Transação

Todas as escritas seguem o padrão:

```
Endpoint → _handle_db_transaction(db, service_fn, *args)
              ↓
           Service (regras de negócio)
              ↓
           CRUD: db.add/delete/flush/refresh (SEM commit)
              ↓
           _handle_db_transaction: commit ou rollback
```

O `_handle_db_transaction` em `app/core/depends.py`:
- Executa o service
- Faz `db.commit()` em caso de sucesso
- Faz `db.rollback()` em caso de `HTTPException`, `ValueError` ou erro inesperado

---

## Enums Relevantes

### `OrdemServicoStatus`
`ABERTA` | `EM_ANDAMENTO` | `AGUARDANDO_PECAS` | `AGUARDANDO_APROVACAO` | `AGUARDANDO_RETIRADA` | `FINALIZADA` | `CANCELADA`

### `OrdemServicoPrioridade`
`BAIXA` | `NORMAL` | `ALTA` | `URGENTE`

### `OrdemServicoItemTipo`
`PRODUTO` | `SERVICO`

### `TipoEquipamento`
`COMPUTADOR` | `NOTEBOOK` | `CELULAR` | `TABLET` | `IMPRESSORA` | `MONITOR` | `PRINTER` | `SCANNER` | `OUTROS`

---

## Notas para Desenvolvimento Futuro

1. **Notificações**: Ao mudar status (especialmente AGUARDANDO_RETIRADA), seria natural enviar notificação ao cliente.
2. **Relatório de OS**: Geração de PDF com os dados da OS para impressão (número, cliente, serviços, valor).
3. **Histórico de status**: Atualmente não há log de transições. Uma tabela `ordem_servico_historico` poderia registrar cada mudança.
4. **Garantia automática**: O campo `garantia` é livre (string). Poderia ser calculado automaticamente como data a partir da finalização.
5. **Estoque**: Ao adicionar um item do tipo PRODUTO, poderia baixar automaticamente o estoque do produto.
