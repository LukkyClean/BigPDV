# Módulo Frontend: Order Service (Ordens)

> Contexto técnico completo para desenvolvedores e assistentes de IA.

---

## Visão Geral

O módulo `order-service/ordens` gerencia o ciclo de vida das Ordens de Serviço no frontend da aplicação StartBig. Ele conecta a interface do usuário à API REST do backend, cobrindo criação, edição, gerenciamento de itens, upload de fotos, finalização com pagamentos e cancelamento.

O módulo é **feature-completo em infraestrutura**: schemas, services, mutations e queries estão todos implementados. A camada de formulário (form composables + context) encapsula a lógica VeeValidate + Zod e é consumida pelos componentes via `provide/inject`.

---

## Estrutura de Pastas

```
frontend/src/modules/order-service/ordens/
├── composables/
│   ├── form/
│   │   ├── useOSCreate.form.ts              ✅ Form de criação de OS (campos + FieldArray itens)
│   │   ├── useOSUpdateGeral.form.ts         ✅ Form de atualização geral (status, prioridade, texto)
│   │   ├── useOSUpdateObjeto.form.ts         ✅ Form de atualização de objeto
│   │   ├── useOSItem.form.ts                ✅ Form de add/edit de item (modo create/update)
│   │   ├── useOSFinalizar.form.ts           ✅ Form de finalização (solução + FieldArray pagamentos)
│   │   └── useOSCancelar.form.ts            ✅ Form de cancelamento (motivo)
│   └── request/
│       ├── useOrderServiceGet.queries.ts    ✅ Queries: lista paginada, detalhe, stats
│       ├── useOrderServiceCreate.mutate.ts  ✅ Mutations: criar OS, adicionar item
│       ├── useOrderServiceUpdate.mutate.ts  ✅ Mutations: atualizar, objeto, item,
│       │                                          finalizar, cancelar, reabrir
│       ├── useOrderServiceDelete.mutate.ts  ✅ Mutation: deletar item
│       └── relationship/
│           ├── useOSRelationshipGet.queries.ts  ✅ Queries: clientes, funcionários
│           ├── useOSClientSearch.queries.ts     ✅ Query de busca de cliente c/ debounce
│           ├── useOSPaymentMethods.queries.ts   ✅ Query de formas de pagamento
│           └── useOSPhotoMutate.mutate.ts       ✅ Mutations: upload/delete de foto
│
├── context/
│   └── useForm.context.ts                   ✅ Provider + Consumer (provide/inject)
│
├── constants/
│   ├── core.constant.ts                     ✅ Query keys, stale times, valores padrão
│   └── ordemServico.constants.ts            ✅ Status/prioridade display, UI config
│
├── schemas/
│   ├── orderService.schema.ts               ✅ Schema base (campos compartilhados)
│   ├── orderServiceMutate.schema.ts         ✅ Schemas de escrita: Create, Update, Ready, Cancel
│   ├── orderServiceQuery.schema.ts          ✅ Schemas de leitura: Read, Pagination, Stats
│   ├── enums/
│   │   └── osEnums.schema.ts               ✅ Status, Prioridade, TipoItem, TipoEquip, Medida, Bandeira
│   └── relationship/
│       ├── osItem.schema.ts                ✅ Create / Read / Update de itens
│       ├── osObjeto.schema.ts               ✅ Create / Read / Update de objetos
│       ├── osPayment.schema.ts             ✅ Create / Read de pagamentos
│       ├── osPhoto.schema.ts               ✅ Read de fotos
│       ├── customer/
│       │   ├── customer.schema.ts          ✅ Leitura de clientes PF e PJ (union type)
│       │   ├── enums/
│       │   │   ├── customerEnum.type.ts    ✅ TipoCliente (PF/PJ)
│       │   │   └── genderEnum.type.ts      ✅ Gênero
│       │   └── relationship/
│       │       └── address.schema.ts       ✅ Endereço do cliente
│       └── employee/
│           └── employee.schema.ts          ✅ Leitura de funcionários
│
├── services/
│   ├── orderServiceGet.service.ts           ✅ GET: lista, detalhe, stats
│   ├── orderServiceCreate.service.ts        ✅ POST: criar OS, adicionar item
│   ├── orderServiceUpdate.service.ts        ✅ PUT: atualizar, objeto, item,
│   │                                               finalizar, cancelar, reabrir
│   ├── orderServiceDelete.service.ts        ✅ DELETE: item
│   └── relationship/
│       ├── osRelationshipGet.service.ts     ✅ GET: clientes, funcionários
│       ├── osPhotoMutate.service.ts         ✅ POST/DELETE: fotos
│       └── osPaymentMethods.service.ts      ✅ GET: formas de pagamento
│
├── types/
│   ├── requests.type.ts                     ✅ Interfaces de payload para as mutations
│   └── context.type.ts                      ✅ Interfaces dos 6 segmentos de formulário
│
├── components/
│   ├── OSTable.vue                          ✅ Tabela de listagem com filtros e ações rápidas
│   ├── OSStats.vue                          ✅ Cards de estatísticas (total, abertas, finalizadas, ticket médio)
│   ├── OSPrintTemplate.vue                  ✅ Template de impressão (ENTRADA / SAIDA / CANCELAMENTO)
│   ├── OSClienteSearchModal.vue             ✅ Modal de busca/seleção de cliente
│   ├── OSCancelModal.vue                    ✅ Modal de cancelamento (standalone, gerencia própria API)
│   ├── OSFinalizarModal.vue                 ✅ Modal de finalização (standalone, gerencia própria API)
│   ├── OSFormModal.vue                      ✅ Modal principal de criação/edição (provider do contexto)
│   └── form/                               ✅ Sub-componentes do OSFormModal
│       ├── OSFormHeader.vue                 ✅ Header com número da OS e botões de ação
│       ├── OSFormFooter.vue                 ✅ Footer com total e botão FINALIZAR
│       ├── OSClientCard.vue                 ✅ Card de dados do cliente e datas
│       ├── OSControlsCard.vue               ✅ Card de status, técnico, prioridade, previsão
│       ├── OSObjetoTab.vue               ✅ Aba de dados do objeto (v-model ObjetoForm)
│       ├── OSDiagnosticoTab.vue             ✅ Aba de diagnóstico técnico e galeria de fotos
│       ├── OSServicesTab.vue                ✅ Aba de serviços/peças com resumo financeiro
│       ├── OSFotoGallery.vue                ✅ Galeria de fotos com upload/delete via mutations
│       ├── OSItemFormModal.vue              ✅ Modal de add/edit de item (dumb: emite save)
│       ├── OSReopenOptionsModal.vue         ✅ Modal de opções de reabertura (TEXT_ONLY / FULL)
│       └── OSObjetoSelectModal.vue     ✅ Modal de seleção de objeto do histórico
│
└── docs/
    └── order-service.md                     ✅ Esta documentação
```

---

## Fluxo de Dados

```
Componente Vue
    │
    │ useOSForm()          ← inject do contexto
    ▼
useForm.context.ts         ← provide/inject singleton por árvore
    │
    │ instancia 6 segmentos via useOSCreateForm(), useOSUpdateGeralForm(), ...
    ▼
composables/form/*.form.ts
    │
    │ VeeValidate useForm() + defineField() + useFieldArray()
    │ TanStack useMutation() → onSubmit()
    ▼
composables/request/*.mutate.ts
    │
    │ useMutation({ mutationFn: service, onSuccess: toast + invalidate })
    ▼
services/*.service.ts
    │
    │ axios.post / .put / .delete
    ▼
API REST /api/v1/ordens-servico/...
    │
    │ resposta → queryClient.invalidateQueries()
    ▼
composables/request/*.queries.ts   ← refetch automático via TanStack Query
    │
    ▼
Componente atualiza com os novos dados
```

---

## Responsabilidades por Camada

| Camada | Arquivo(s) | Responsabilidade |
|--------|-----------|--------------------|
| **Schema** | `schemas/*.schema.ts` | Validação Zod + inferência de tipos TypeScript. Nenhuma lógica de negócio. |
| **Types** | `types/requests.type.ts` | Interfaces de payload para mutations (agrupam `osNumber` + dados). |
| **Types** | `types/context.type.ts` | Interfaces dos contextos de formulário por segmento. |
| **Constants** | `constants/core.constant.ts` | Query keys, stale times, valores padrão dos formulários. |
| **Constants** | `constants/ordemServico.constants.ts` | Mapeamento status → label/cor, configurações de UI. |
| **Service** | `services/*.service.ts` | Chamadas Axios tipadas. Sem tratamento de erros (delegado ao TanStack Query). |
| **Queries** | `composables/request/*.queries.ts` | `useQuery` com cache, stale time, filtros reativos e debounce. |
| **Mutations** | `composables/request/*.mutate.ts` | `useMutation` com toast de sucesso/erro e `invalidateQueries`. |
| **Form** | `composables/form/*.form.ts` | VeeValidate forms segmentados, submit handlers, transformação de dados. |
| **Context** | `context/useForm.context.ts` | `provide/inject` singleton: instancia todos os segmentos e expõe o contexto. |
| **Component** | `components/` | Consome `useOSForm()` para acessar segmentos específicos. |

---

## Segmentos de Formulário

O formulário da OS é dividido em **6 segmentos independentes**, cada um mapeando para um endpoint específico do backend:

| Segmento | Composable | Endpoint | Schema |
|----------|-----------|----------|--------|
| `criar` | `useOSCreateForm` | `POST /ordens-servico/` | `OrderServiceCreateSchema` |
| `atualizarGeral` | `useOSUpdateGeralForm` | `PUT /ordens-servico/{n}` | `OrderServiceUpdateSchema` |
| `atualizarObjeto` | `useOSUpdateObjetoForm` | `PUT /ordens-servico/{n}/objeto` | `OsObjetoUpdateSchema` |
| `item` | `useOSItemForm` | `POST/PUT /ordens-servico/{n}/itens[/{id}]` | `OsItemCreateSchema` |
| `finalizar` | `useOSFinalizarForm` | `PUT /ordens-servico/{n}/finalizar` | `OrderServiceReadySchema` |
| `cancelar` | `useOSCancelarForm` | `PUT /ordens-servico/{n}/cancelar` | `OrderServiceCancelSchema` |

### Campos por segmento

**`criar`** (POST /ordens-servico/)
- Campos gerais: `prioridade`, `defeito_relatado`, `diagnostico`, `observacoes`, `desconto`, `garantia`, `data_previsao`, `senha_aparelho`, `acessorios`, `condicoes_aparelho`
- Vínculos: `cliente_id`, `funcionario_id`
- Objeto nested: `objeto_tipo_equipamento`, `objeto_marca`, `objeto_modelo`, `objeto_numero_serie`, `objeto_imei`, `objeto_cor`
- FieldArray: `itens[]` (tipo, nome, unidade_medida, quantidade, valor_unitario)

**`atualizarGeral`** (PUT /ordens-servico/{n})
- Todos os campos opcionais: `status`, `prioridade`, `defeito_relatado`, `diagnostico`, `solucao`, `observacoes`, `desconto`, `garantia`, `data_previsao`, `senha_aparelho`, `acessorios`, `condicoes_aparelho`, `funcionario_id`
- `populateForm(os: OrderServiceReadDataType)` — carrega os dados atuais da OS
- **Atenção**: datas vêm do backend em formato ISO — converter para `YYYY-MM-DD` ao popular campos `type="date"`

**`atualizarObjeto`** (PUT /ordens-servico/{n}/objeto)
- `tipo_equipamento`, `marca`, `modelo`, `numero_serie`, `imei`, `cor`, `cliente_id`
- `cliente_id` permite troca do cliente vinculado ao objeto
- `populateForm(objeto: OsObjetoUpdateSchemaDataType)` — carrega os dados atuais

**`item`** (POST ou PUT /ordens-servico/{n}/itens[/{id}])
- `tipo`, `nome`, `unidade_medida`, `quantidade`, `valor_unitario`
- `editingItemId: Ref<number | null>` — controla o modo (null = criar, id = editar)
- `setEditingItem(id, data)` — ativa modo edição e popula o form
- Na submissão em modo edição, apenas os campos do `OsItemUpdateSchema` são enviados

**`finalizar`** (PUT /ordens-servico/{n}/finalizar)
- `solucao` (obrigatório, mín. 5 chars), `observacoes`, `desconto`
- FieldArray: `pagamentos[]` (forma_pagamento_id, valor, parcelas, bandeira_cartao, detalhes)
- Regra: `sum(pagamentos.valor) == os.valor_total` — validação no backend (409 se divergir)

**`cancelar`** (PUT /ordens-servico/{n}/cancelar)
- `motivo` (opcional, máx. 500 chars)

---

## Padrão provide/inject — Como Usar

### Componente pai (OSFormModal)

```vue
<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useOSFormProvider, useOSFormPendingState } from '../context/useForm.context'
import type { OrderServiceReadDataType } from '../schemas/orderServiceQuery.schema'

// CRÍTICO: chamar ANTES de qualquer await — Vue exige provide() síncrono
const osNumber = computed(() => props.ordemServico?.numero_os ?? null)
const isCreateMode = computed(() => !props.ordemServico)

const form = useOSFormProvider({
  osNumber,
  isCreateMode,
  onCreateSuccess: () => { /* fechar modal, imprimir ENTRADA */ },
  onUpdateSuccess: () => { /* feedback de sucesso */ },
  onItemSuccess:   () => { isItemModalOpen.value = false },
  onFinalizarSuccess: () => { isFinalizarModalOpen.value = false },
  onCancelarSuccess:  () => { /* atualizar estado da página */ },
})

// Indicador global de loading (qualquer segmento em progresso)
const isPending = useOSFormPendingState(form)

// Carregar dados para modo edição
watch(() => props.ordemServico, (os) => {
  if (os) {
    form.atualizarGeral.populateForm(os)
    form.atualizarObjeto.populateForm(os.objeto)
  } else {
    form.criar.resetForm()
  }
}, { immediate: true })
</script>
```

### Componente filho (seção do formulário)

```vue
<script setup lang="ts">
import { useOSForm } from '../context/useForm.context'

// Acessa apenas o segmento necessário
const { criar } = useOSForm()
</script>

<template>
  <form @submit="criar.onSubmit">
    <select v-model="criar.prioridade.value">
      <option value="BAIXA">Baixa</option>
      <option value="NORMAL">Normal</option>
      <option value="ALTA">Alta</option>
      <option value="URGENTE">Urgente</option>
    </select>
    <span v-if="criar.errors.value['prioridade']">
      {{ criar.errors.value['prioridade'] }}
    </span>

    <textarea v-model="criar.defeito_relatado.value" />

    <!-- FieldArray de itens -->
    <div v-for="(item, idx) in criar.itens.value" :key="item.key">
      <input v-model="item.value.nome" />
      <button type="button" @click="criar.handleRemoveItem(idx)">Remover</button>
    </div>
    <button type="button" @click="criar.handleAddItem()">Adicionar item</button>

    <button type="submit" :disabled="criar.isPending.value">Salvar</button>
  </form>
</template>
```

### Componente filho — seção de item (add/edit em modo edição)

```vue
<script setup lang="ts">
import { useOSForm } from '../context/useForm.context'
import type { OsItemReadSchemaDataType } from '../schemas/relationship/osItem.schema'

const { item } = useOSForm()

function editarItem(osItem: OsItemReadSchemaDataType) {
  item.setEditingItem(osItem.id, {
    nome: osItem.nome,
    unidade_medida: osItem.unidade_medida,
    quantidade: osItem.quantidade,
    valor_unitario: osItem.valor_unitario,
  })
}
</script>
```

### Modais standalone (sem provider externo)

`OSCancelModal`, `OSFinalizarModal` e `OSClienteSearchModal` são **autônomos** — não dependem do context do `OSFormModal`. Eles instanciam seus próprios composables internamente:

```typescript
// OSFinalizarModal: instancia o composable diretamente
const osNumberRef = computed(() => props.osNumero)
const finalizarForm = useOSFinalizarForm({
  osNumber: osNumberRef,
  onSuccess: () => emit('finalized', { shouldPrint }),
})

// OSCancelModal: usa a mutation diretamente
const cancelMutation = useCancelOrderServiceMutation()
```

---

## Queries Disponíveis

```typescript
import {
  useOrderServiceQueryAll,    // Lista paginada com filtros
  useOrderServiceQueryUnique, // OS única por numero_os
  useOrderServiceQueryStats,  // Contadores e ticket médio
} from '../composables/request/useOrderServiceGet.queries'

import {
  useOsCustomersGet,   // Clientes para seleção em formulários
  useOsEmployeesGet,   // Funcionários para seleção em formulários
} from '../composables/request/relationship/useOSRelationshipGet.queries'

import { useOSClientSearch } from '../composables/request/relationship/useOSClientSearch.queries'
// useOSClientSearch(isOpen): { searchQuery, clientes, isLoading, lastCreatedId }

import { useOsPaymentMethodsGet } from '../composables/request/relationship/useOSPaymentMethods.queries'
// useOsPaymentMethodsGet(): { formasPagamento, isLoading }
```

### Parâmetros de listagem (`useOrderServiceQueryAll`)

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `searchQuery` | `Ref<string>` | Busca por numero_os, nome do cliente, razão social |
| `activeStatusFilterQuery` | `Ref<OsEstadoKey \| undefined>` | Filtro por estado: um status do fluxo (vira `status`) ou um desfecho SEM_REPARO/CONDENADO (vira `situacao_equipamento`) |
| `activePriorityFilterQuery` | `Ref<boolean>` | Ordena por prioridade (URGENTE → BAIXA) |

### Retorno de `useOrderServiceQueryStats`

```typescript
stats: {
  total: number
  abertas: number
  finalizadas: number
  ticket_medio: number   // ← em centavos; NÃO existe campo emAndamento
}
```

---

## Mutations Disponíveis

```typescript
// Criação
useCreateOrderServiceMutation()   // POST /ordens-servico/
useCreateItemOSMutation()         // POST /ordens-servico/{n}/itens

// Atualização
useUpdateOrderServiceMutation()   // PUT /ordens-servico/{n}
useUpdateObjetoOSMutation()        // PUT /ordens-servico/{n}/objeto
useUpdateItemOSMutation()         // PUT /ordens-servico/{n}/itens/{id}
useReadyOrderServiceMutation()    // PUT /ordens-servico/{n}/finalizar
useCancelOrderServiceMutation()   // PUT /ordens-servico/{n}/cancelar
useReopenOrderServiceMutation()   // PUT /ordens-servico/{n}/reabrir

// Deleção
useOrderServiceDeleteItem()       // DELETE /ordens-servico/{n}/itens/{id}

// Fotos
useUploadFotoOSMutation()         // POST /ordens-servico/{n}/fotos
useDeleteFotoOSMutation()         // DELETE /ordens-servico/{n}/fotos/{id}
```

---

## Tipos Exportados por Schema

### `orderServiceQuery.schema.ts`
```typescript
OrderServiceReadDataType       // OS completa com todos os relacionamentos
OrderServicePaginationDataType // Resposta paginada da listagem
OrderServiceParamsDataType     // Parâmetros de busca/filtro
OrderServiceStatsDataType      // { total, abertas, finalizadas, ticket_medio }
```

### `orderServiceMutate.schema.ts`
```typescript
OrderServiceCreateSchemaDataType
OrderServiceUpdateDataType
OsObjetoUpdateSchemaDataType
OrderServiceReadyDataType
OrderServiceCancelDataType
```

### `schemas/relationship/osItem.schema.ts`
```typescript
OsItemCreateSchemaDataType   // { tipo, nome, unidade_medida, quantidade, valor_unitario, item_id? }
OsItemUpdateSchemaDataType   // todos opcionais (exceto tipo)
OsItemReadSchemaDataType     // + id, ordem_servico_id, produto_id?, servico_id?, valor_total
```

### `schemas/relationship/osObjeto.schema.ts`
```typescript
OsObjetoUpdateSchemaDataType  // todos opcionais
OsObjetoReadSchemaDataType    // + id, cliente_id, ativo, datas
```

### `schemas/relationship/osPayment.schema.ts`
```typescript
OsPaymentCreateSchemaDataType  // { forma_pagamento_id, valor, parcelas, bandeira_cartao?, detalhes? }
```

### `schemas/enums/osEnums.schema.ts`
```typescript
OsStatusEnumDataType       // 'ABERTA' | 'EM_ANDAMENTO' | ...
OsPriorityEnumDataType     // 'BAIXA' | 'NORMAL' | 'ALTA' | 'URGENTE'
OsItemTypeEnumDataType     // 'PRODUTO' | 'SERVICO'
OsEquipTypeEnumDataType    // 'COMPUTADOR' | 'CELULAR' | ...
OsItemMeasureEnumDataType  // 'UN' | 'KG' | 'H' | ...
```

### `schemas/relationship/customer/customer.schema.ts`
```typescript
CustomerUnionReadSchemaDataType  // union: CustomerPFReadSchemaDataType | CustomerPJReadSchemaDataType
```

---

## Migração Old → New (Referência Rápida)

| Antigo (deletado) | Novo |
|---|---|
| `ordemServico.numero` | `ordemServico.numero_os` |
| `ordemServico.objeto` (string) | `ordemServico.objeto.tipo_equipamento` |
| `ordemServico.marca` | `ordemServico.objeto.marca` |
| `ordemServico.modelo` | `ordemServico.objeto.modelo` |
| `ordemServico.numero_serie` | `ordemServico.objeto.numero_serie` |
| `item.descricao` | `item.nome` |
| `item.servico_id` (FK lookup) | `item.tipo` (enum PRODUTO/SERVICO) + `item.nome` (texto livre) |
| Stats: `emAndamento` | removido — não existe no novo schema |
| Stats: — | `ticket_medio` (novo campo) |
| `OrdemServicoStatus` type | `OsStatusEnumDataType` |
| `OrdemServicoPrioridade` type | `OsPriorityEnumDataType` |
| `ClienteResumo` type | `CustomerUnionReadSchemaDataType` |
| `OrdemServicoFotoRead` type | `OsImageReadDataType` |
| `OrdemServicoRead` type | `OrderServiceReadDataType` |

---

## Convenções Adotadas

| Convenção | Detalhe |
|-----------|---------|
| **Valores monetários** | Sempre em centavos (integer). Ex: R$ 450,00 = `45000` |
| **Identificador público** | `numero_os` (ex: `OS-2026-000001`) — usar nas chamadas de API e rotas |
| **ID interno** | `id` (integer) — uso somente interno (ex: para mutations de itens/fotos) |
| **Nomenclatura de arquivos** | `*.service.ts`, `*.mutate.ts`, `*.queries.ts`, `*.schema.ts`, `*.type.ts`, `*.form.ts` |
| **Query keys** | Centralizadas em `constants/core.constant.ts` como strings constantes |
| **Stale time** | 1 minuto para OS; pode ser aumentado se o domínio tolerar dados levemente stale |
| **Erros de API** | Tratados nas mutations com `useToast` e `getErrorMessage` |
| **Schemas Zod** | Exportam o schema, o `toTypedSchema` (para VeeValidate) e o tipo inferido |
| **Linguagem** | Português para variáveis, comentários, labels e mensagens de erro |

---

## Enums

### `OsStatusEnum`
```
ABERTA | EM_ANDAMENTO | AGUARDANDO_PECAS | AGUARDANDO_APROVACAO | AGUARDANDO_RETIRADA | FINALIZADA | CANCELADA
```

### `OsPriorityEnum`
```
BAIXA | NORMAL | ALTA | URGENTE
```

### `OsItemTypeEnum`
```
PRODUTO | SERVICO
```

### `OsEquipTypeEnum`
```
COMPUTADOR | NOTEBOOK | CELULAR | TABLET | IMPRESSORA | MONITOR | PRINTER | SCANNER | OUTROS
```

### `OsItemMeasureEnum`
```
UN | KG | G | L | ML | M | CM | M2 | M3 | H | D | MES | OUTROS
```

### `OsCardsFlagEnum`
```
MASTERCARD | VISA | ELO | OUTROS
```

---

## Decisões Arquiteturais

### 1. Formulários segmentados por operação (não um form único)
A OS tem múltiplos endpoints de escrita com schemas distintos. Usar um único form unificado seria frágil: validações conflitantes, dificuldade de reset parcial, estado UI acoplado. Cada endpoint tem seu próprio `useForm()`, schema e mutation.

### 2. `useFieldArray` deve ser chamado imediatamente após seu `useForm`
VeeValidate 4 usa `injectWithSelf` para vincular `useFieldArray` ao form mais recente via `vm.provides`. Como múltiplos `useForm()` são chamados no mesmo setup (dentro de `useOSFormProvider`), a ordem importa: `useFieldArray` de itens é chamado dentro de `useOSCreateForm` (vincula ao form de criação), e `useFieldArray` de pagamentos é chamado dentro de `useOSFinalizarForm` (vincula ao form de finalização).

### 3. Modo add/edit de item em um único composable
O `useOSItemForm` usa `OsItemCreateSchema` como schema de validação (superset). Na submissão, o handler verifica `editingItemId.value` e chama a mutation adequada (create ou update), extraindo apenas os campos aceitos pelo endpoint de update. Isso evita duplicar a lógica de form para o mesmo conjunto de inputs.

### 4. `provide/inject` como singleton por árvore de componentes
O padrão escolhido — `useOSFormProvider()` no pai + `useOSForm()` nos filhos — garante que todos os segmentos sejam instanciados uma única vez por instância do modal/página. Filhos acessam diretamente o segmento que precisam sem prop drilling. Diferente de refs globais (module-level), o contexto é isolado por instância de componente pai.

### 5. `onSuccess` callbacks no provider
O provider aceita callbacks por operação (`onCreateSuccess`, `onUpdateSuccess`, etc.) em vez de emitir eventos. Isso mantém o controle de fluxo (fechar modal, navegar, resetar) no componente pai, onde ele naturalmente pertence, sem acoplamento com o composable.

### 6. Modais standalone são self-contained
`OSCancelModal` e `OSFinalizarModal` gerenciam suas próprias chamadas de API internamente. Eles recebem `osNumero: string` como prop e não dependem do provider do `OSFormModal`. Isso permite usá-los de qualquer contexto (tabela de listagem, modal de edição, etc.).

### 7. Total de item: read vs create
- `OsItemReadSchemaDataType`: `valor_total` vem do backend (calculado no save)
- `OsItemCreateSchemaDataType`: não tem `valor_total` — calcular localmente: `quantidade * valor_unitario`

---

## Componentes

### Arquitetura da Camada de UI

```
OrdensServicoTab (views/)
├── OSStats              ← cards de estatísticas
├── OSTable              ← listagem com ações rápidas
├── OSClienteSearchModal ← standalone
├── OSFormModal          ← provider do contexto → filhos em form/
│   ├── OSFormHeader
│   ├── OSClientCard
│   ├── OSControlsCard
│   ├── OSObjetoTab
│   ├── OSDiagnosticoTab → OSFotoGallery
│   ├── OSServicesTab
│   ├── OSFormFooter
│   ├── OSFinalizarModal (standalone interno)
│   ├── OSItemFormModal  (dumb: emite save)
│   ├── OSReopenOptionsModal
│   └── OSObjetoSelectModal
├── OSCancelModal        ← standalone
└── OSPrintTemplate      ← oculto, ativado por window.print()
```

### Componentes de Listagem

#### `OSTable.vue`

Tabela principal de OS com busca, filtro por status e ações rápidas.

```typescript
// Props
ordensServico: OrderServiceReadDataType[]
isLoading?: boolean
totalPages?: number
currentPage?: number
totalItems?: number

// v-model
search: string
activeFilter: string | null

// Emits
view(os)     // abrir modal de visualização
edit(os)     // abrir modal de edição
finalizar(os)
cancelar(os)
reabrir(os)
print(os)    // imprimir SAIDA/CANCELAMENTO
'update:currentPage'(page: number)
```

#### `OSStats.vue`

Cards de estatísticas. Recebe shape `{ total, abertas, finalizadas, ticket_medio }`.

```typescript
stats: { total: number; abertas: number; finalizadas: number; ticket_medio: number }
loading?: boolean
```

### Modais Standalone

#### `OSClienteSearchModal.vue`

Busca de cliente para nova OS. Usa `useOSClientSearch(isOpen)` internamente.

```typescript
// Props
isOpen: boolean

// Emits
close: []
selectCliente: [cliente: CustomerUnionReadSchemaDataType]
```

#### `OSCancelModal.vue`

**Autônomo**: gerencia toda a lógica de cancelamento internamente via `useOSCancelarForm`.

```typescript
// Props
isOpen: boolean
osNumero: string | null
osDisplayNumber?: string

// Emits
close: []
cancelled: [{ shouldPrint: boolean }]
```

#### `OSFinalizarModal.vue`

**Autônomo**: gerencia finalização via `useOSFinalizarForm` + `useOsPaymentMethodsGet`.

```typescript
// Props
isOpen: boolean
osNumero: string | null
ordemServico: OrderServiceReadDataType | null

// Emits
close: []
finalized: [{ shouldPrint: boolean }]
```

### `OSFormModal.vue` — Modal Principal

É o **único `provide()` de contexto** do módulo. Deve ser instanciado com `useOSFormProvider({...})` como **primeira chamada síncrona** do `<script setup>`.

```typescript
// Props
isOpen: boolean
ordemServico?: OrderServiceReadDataType | null   // null = modo criação
selectedCliente?: CustomerUnionReadSchemaDataType | null
autoShowReopen?: boolean

// Emits
close: []
changeCliente: []   // usuário clicou em "Trocar" → parent abre OSClienteSearchModal
```

**Comportamentos internos:**
- **Modo criação**: popula `form.criar` com `resetForm()` ao abrir; ao submit, `form.criar.onSubmit()` chama o backend e imprime ENTRADA automaticamente
- **Modo edição**: chama `populateEditForm(os)` ao abrir — popula `atualizarGeral` e `atualizarObjeto`; `data_previsao` convertida de ISO → `YYYY-MM-DD`
- **Auto-save de objeto**: ao mudar de aba "Objeto" para outra aba (edit mode), `form.atualizarObjeto.onSubmit()` é chamado automaticamente
- **Reopen**: `TEXT_ONLY` → salva texto mas mantém status FINALIZADA; `FULL` → chama `useReopenOrderServiceMutation` e libera todos os campos
- **Adapter de objeto**: `objetoFormData` computed converte entre os campos individuais dos form contexts e o `ObjetoForm` esperado por `OSObjetoTab`
- **Itens (create mode)**: gerenciados via `form.criar.itens` FieldArray — `handleAddItem`, `handleRemoveItem`, `handleUpdateItem`
- **Itens (edit mode)**: novos itens via `useCreateItemOSMutation`; edição via `form.item.setEditingItem + onSubmit`; remoção via `useOrderServiceDeleteItem`

### Sub-componentes do OSFormModal

#### `OSFormHeader.vue`

Header escuro com número da OS e botões (ENTRADA, SAÍDA, REABRIR, SALVAR, FECHAR).

```typescript
osNumber: string | number  // ex: "OS-2024-001" — o componente extrai apenas o sequencial
osId?: number              // define se botão ENTRADA está habilitado
isFinalizada: boolean
isPending: boolean
reopenMode: 'NONE' | 'TEXT_ONLY' | 'FULL'
// emits: print, reprintExit, reopen, save, close
```

#### `OSFormFooter.vue`

Footer com total financeiro e botão FINALIZAR (visível apenas em edit mode não-finalizado).

```typescript
valorTotal: number   // em centavos
isFinalizada: boolean
isEditMode: boolean
reopenMode: 'NONE' | 'TEXT_ONLY' | 'FULL'
// emits: finalizar
```

#### `OSClientCard.vue`

Card de dados do cliente. Lida com union PF/PJ via type assertions.

```typescript
cliente?: CustomerUnionReadSchemaDataType | null
status?: OsStatusEnumDataType | null
dataCriacao?: string | Date
dataFinalizacao?: string | Date
isEditMode?: boolean
isFinalizada?: boolean
// emits: changeCliente
```

#### `OSControlsCard.vue`

Dois selects (Status, Técnico) + dois inputs (Prioridade, Previsão).

```typescript
status: OsStatusEnumDataType
funcionarioId: string
prioridade: OsPriorityEnumDataType
dataPrevisao: string
statusOptions: SelectOption[]
prioridadeOptions: SelectOption[]
funcionariosOptions: SelectOption[]
// emits: update:status, update:funcionarioId, update:prioridade, update:dataPrevisao
```

#### `OSObjetoTab.vue`

Aba de objeto. Usa `v-model` com objeto `ObjetoForm` (bridge do OSFormModal):

```typescript
interface ObjetoForm {
  objeto: string    // = tipo_equipamento no backend
  marca: string
  modelo: string
  numero_serie: string
  imei: string
  cor: string
  senha_aparelho: string
  acessorios: string
  defeito_relatado: string
  condicoes_aparelho: string
}
```

> **Atenção**: o campo `objeto` do `ObjetoForm` mapeia para `tipo_equipamento` nos schemas do backend. O adapter `objetoFormData` computed no `OSFormModal` faz essa conversão.

#### `OSDiagnosticoTab.vue`

Aba técnica com textarea de diagnóstico + `OSFotoGallery`.

```typescript
diagnostico: string
osNumero?: string      // undefined = create mode (gallery desabilitada)
fotos: OsImageReadDataType[]
isLocked: boolean
// emits: 'update:diagnostico', photoChange
```

#### `OSServicesTab.vue`

Lista de itens com totais financeiros.

```typescript
itens: (OsItemCreateSchemaDataType | OsItemReadSchemaDataType)[]
isLocked?: boolean
subtotal: number       // centavos
valorDesconto: number  // centavos
valorTotal: number     // centavos
valorEntrada?: number  // centavos
// emits: addItem, editItem(index), removeItem(index)
```

> `OsItemReadSchemaDataType` tem `valor_total` (do backend). `OsItemCreateSchemaDataType` não tem — calcular `quantidade * valor_unitario` localmente.

#### `OSFotoGallery.vue`

Galeria com upload e delete. Usa `useUploadFotoOSMutation` e `useDeleteFotoOSMutation`.

```typescript
osNumero: string
fotos: OsImageReadDataType[]
isLocked: boolean
```

#### `OSItemFormModal.vue`

Modal **dumb** de criação/edição de item. Não chama API — apenas emite os dados.

```typescript
// Props
isOpen: boolean
item?: OsItemCreateSchemaDataType | null   // null = nova entrada

// Emits
close: []
save: [item: OsItemCreateSchemaDataType]
```

---

## Referências

- Backend: `backend-fastapi/docs/ordem_servico.md`
- Padrão de formulário: `modules/employees/composables/useEmployeeForm.ts`
- Padrão de queries: `modules/employees/composables/useEmployeesQuery.ts`
- Padrão de modal state: `modules/employees/composables/useEmployeeModal.ts`
- Schemas compartilhados: `shared/schemas/payments/payment.schema.ts`, `shared/schemas/pagination/`
