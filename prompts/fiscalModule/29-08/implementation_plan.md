# Plano de Implementação: Validação de Vendas Incompletas e Bloqueio de Emissão Dupla (Opção A)

Este plano detalha a implementação técnica das soluções da **Opção A** para os dois desafios do fluxo de emissão fiscal no BigPDV:
1. **Bloqueio explícito de vendas incompletas antes da emissão**, com validação em lote (batch) ativada apenas quando o módulo fiscal estiver habilitado, exibindo feedback visual imediato e toast formatado com as pendências.
2. **Bloqueio rigoroso de múltipla emissão da mesma venda**, transformando o retorno silencioso em erro explícito HTTP 409 (Conflict) no backend, acompanhado de badges visuais de status e desabilitação no frontend.

---

## User Review Required

> [!IMPORTANT]
> **Comportamento na Finalização do PDV**: A validação fiscal que roda ao finalizar a venda (`finish_sale`) é apenas informativa/classificatória e **NÃO deve bloquear a conclusão da venda física no caixa de balcão** (o cliente na loja física pode pagar e levar a mercadoria mesmo sem informar CPF para NF-e). O bloqueio estrito ocorre **no momento de selecionar para emissão da NF-e**.
> Caso você deseje que a própria finalização da venda no PDV seja impedida quando houver pendência fiscal (quando o módulo fiscal estiver ativo), confirme essa preferência. O plano abaixo adota o padrão de **não travar o caixa da loja física**, travando exclusivamente a **emissão fiscal**.

> [!NOTE]
> **Regra de Reemissão (Rejeição SEFAZ)**: Vendas com documento fiscal em status `REJEITADA` ou `DENEGADA` **não** são bloqueadas como duplicatas, pois o sistema permite até 5 retentativas de correção/reemissão encadeada via Centro Fiscal.

---

## Arquitetura e Fluxo da Solução

```
[ Finalização no PDV ]
       │
       ▼ (Se Módulo Fiscal Ativo)
[ Avalia Conformidade Fiscal da Venda ] ──► Registra status inicial em VendaNotaFiscal (Opcional/Cache)
       │
       ▼
[ Usuário abre Modal "Emitir NF-e" ]
       │
       ▼
[ GET /vendas/verificar-fiscal-batch?ids=... ] (Protegido por requer_modulo_fiscal)
       │
       ├─► Para cada venda finalizada:
       │     1. Verifica se já possui DocumentoFiscal ativo (PROCESSANDO / AUTORIZADA)
       │     2. Executa verificar_completude_venda() (Emitente, Destinatário, Itens, Pagamentos)
       │
       ▼
[ Frontend renderiza lista de seleção enriquecida ]:
       ├── 🟢 NF-e Autorizada   ──► Bloqueada para nova emissão (Botão inativo / Toast informativo)
       ├── 🔵 Processando SEFAZ ──► Bloqueada (Aguardando retorno)
       ├── ⚠️ Incompleta        ──► Bloqueada (Clique dispara Toast Formatado com pendências)
       └── ✅ Apta para Emissão ──► Habilitada (Clique avança para Pré-visualização da NF-e)
       │
       ▼ (Se tentar forçar emissão de venda já emitida)
[ POST /fiscal/emitir/nfe ] ──► Backend retorna HTTP 409 Conflict com detalhes da nota existente
```

---

## Proposed Changes

Separado por camada e componentes, ordenados pelas dependências lógicas.

---

### Backend (FastAPI + SQLAlchemy)

#### 1. Schemas de Verificação Fiscal e Batch
#### [MODIFY] [`app/schemas/verificacao_fiscal.py`](file:///c:/dev/bigpdv/backend-fastapi/app/schemas/verificacao_fiscal.py)
- Adicionar schema `StatusFiscalVendaItem`:
  - `venda_id: int`
  - `numero_venda: Optional[int]`
  - `apta: bool`
  - `documento_fiscal_ativo: Optional[dict]` (id, status, numero_documento, serie)
  - `pendencias: list[PendenciaFiscal]`
- Adicionar schema de resposta batch `ResultadoVerificacaoBatch`:
  - `resultados: dict[int, StatusFiscalVendaItem]` (mapeado por `venda_id`)
  - `total_aptas: int`
  - `total_incompletas: int`
  - `total_emitidas: int`

---

#### 2. Consultas e Agregações no Banco de Dados
#### [MODIFY] [`app/db/crud/fiscal.py`](file:///c:/dev/bigpdv/backend-fastapi/app/db/crud/fiscal.py)
- Criar função `get_documentos_ativos_por_vendas_batch(db: Session, numeros_venda: list[int]) -> dict[int, DocumentoFiscal]`:
  - Executa uma query única com `IN(numeros_venda)` buscando documentos com status em `['PROCESSANDO', 'PENDENTE', 'AUTORIZADA']`.
  - Retorna mapa indexado `{numero_venda: DocumentoFiscal}` evitando consultas N+1.

---

#### 3. Serviço de Verificação em Lote (Batch)
#### [MODIFY] [`app/services/verificacao_fiscal.py`](file:///c:/dev/bigpdv/backend-fastapi/app/services/verificacao_fiscal.py)
- Criar função `verificar_completude_vendas_batch(db: Session, venda_ids: list[int], empresa_id: int) -> ResultadoVerificacaoBatch`:
  - Carrega as vendas requisitadas com eager loading otimizado (`joinedload(cliente)`, `subqueryload(itens)`, `subqueryload(pagamentos)`).
  - Executa a verificação do Emitente uma única vez por lote (evita recalcular dados da empresa N vezes).
  - Consulta documentos fiscais ativos em lote via `get_documentos_ativos_por_vendas_batch`.
  - Para cada venda:
    - Se já possui documento fiscal `AUTORIZADA` ou `PROCESSANDO`, marca `apta = False` com indicador de documento ativo.
    - Se não possui documento ativo, avalia: Destinatário, Itens (proibição de avulso, NCM, CFOP, tributação) e Pagamentos (código SEFAZ).
    - Monta o `StatusFiscalVendaItem` consolidado.

---

#### 4. Endpoints da API de Vendas
#### [MODIFY] [`app/api/v1/endpoints/venda.py`](file:///c:/dev/bigpdv/backend-fastapi/app/api/v1/endpoints/venda.py)
- **Novo Endpoint**: `GET /api/v1/vendas/verificar-fiscal-batch`:
  - Protegido por `requer_modulo_fiscal` e permissões de venda.
  - Recebe lista de IDs via query parameter: `ids: list[int] = Query(...)`.
  - Limite máximo de segurança: até 50 vendas por chamada.
  - Retorna `ResultadoVerificacaoBatch`.

---

#### 5. Serviço de Emissão Fiscal (Bloqueio de Emissão Dupla)
#### [MODIFY] [`app/services/fiscal/emissao.py`](file:///c:/dev/bigpdv/backend-fastapi/app/services/fiscal/emissao.py)
- Modificar o trecho de idempotência em `emitir_nfe_venda(db, venda_id, empresa_id)`:
  - Substituir o retorno silencioso `return doc_ativo` por:
    ```python
    doc_ativo = crud.get_documento_ativo_por_venda(db, venda.numero_venda)
    if doc_ativo:
        if doc_ativo.status == "AUTORIZADA":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "codigo": "NF_JA_AUTORIZADA",
                    "mensagem": f"Esta venda já possui a NF-e nº {doc_ativo.numero_documento} (Série {doc_ativo.serie}) autorizada na SEFAZ.",
                    "documento_id": doc_ativo.id,
                    "chave_acesso": doc_ativo.chave_acesso,
                    "url_pdf": doc_ativo.url_pdf,
                },
            )
        elif doc_ativo.status in ("PROCESSANDO", "PENDENTE"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "codigo": "NF_EM_PROCESSAMENTO",
                    "mensagem": "Esta venda já possui uma emissão em andamento. Aguarde a confirmação da SEFAZ.",
                    "documento_id": doc_ativo.id,
                },
            )
    ```
  - Adicionar lock pessimista na checagem de concorrência (`with_for_update` na linha do documento ou na empresa fiscal settings) para blindar contra duplo clique simultâneo.

---

### Frontend (Vue 3 + TanStack Query + Tailwind)

#### 1. Tipagem TypeScript
#### [MODIFY] [`frontend/src/modules/fiscal/types/fiscal.types.ts`](file:///c:/dev/bigpdv/frontend/src/modules/fiscal/types/fiscal.types.ts)
- Adicionar interfaces para a resposta batch:
  ```typescript
  export interface StatusFiscalVendaItem {
    venda_id: number;
    numero_venda: number | null;
    apta: boolean;
    documento_fiscal_ativo?: {
      id: number;
      status: DocumentoFiscalStatus;
      numero_documento?: number;
      serie?: number;
    } | null;
    pendencias: PendenciaFiscal[];
  }

  export interface ResultadoVerificacaoBatch {
    resultados: Record<number, StatusFiscalVendaItem>;
    total_aptas: number;
    total_incompletas: number;
    total_emitidas: number;
  }
  ```

---

#### 2. Serviços de Comunicação HTTP
#### [MODIFY] [`frontend/src/modules/fiscal/services/fiscal.service.ts`](file:///c:/dev/bigpdv/frontend/src/modules/fiscal/services/fiscal.service.ts)
- Adicionar método `verificarFiscalBatch(vendaIds: number[]): Promise<ResultadoVerificacaoBatch>` chamando `GET /vendas/verificar-fiscal-batch?ids=1,2,3`.

---

#### 3. Query Composable para Verificação em Lote
#### [NEW] [`frontend/src/modules/fiscal/composables/useFiscalVerificacaoBatchQuery.ts`](file:///c:/dev/bigpdv/frontend/src/modules/fiscal/composables/useFiscalVerificacaoBatchQuery.ts)
- Hook reativo TanStack Query que recebe a lista de vendas carregadas no modal.
- Executa a busca em lote somente quando o modal estiver aberto e o módulo fiscal estiver ativo (`recursoDisponivel('nfe')`).
- Mantém cache inteligente indexado por ID de venda (`staleTime: 30 segundos`).

---

#### 4. Utilitário de Formatação de Toasts Fiscais
#### [NEW] [`frontend/src/modules/fiscal/utils/formatadorPendenciasToast.ts`](file:///c:/dev/bigpdv/frontend/src/modules/fiscal/utils/formatadorPendenciasToast.ts)
- Função responsável por gerar a mensagem rica para o `useToast().warning` ou `error`:
  - Agrupa os erros por categoria com emojis amigáveis:
    - 🏢 **Dados da Empresa (Emitente)**
    - 👤 **Cliente / Destinatário**
    - 📦 **Itens & Produtos**
    - 💳 **Pagamento**
  - Formata linhas pontuadas (bullet points) destacando o nome do produto ou campo faltante.
  - Exemplo do resultado visual no toast:
    ```
    ⚠️ Venda #104 — Não pode ser emitida

    👤 Destinatário:
    • Cliente "Carlos Silva" não possui CPF cadastrado

    📦 Itens:
    • Produto "Cabo HDMI" sem NCM preenchido
    • Item "Instalação" é avulso (requer produto cadastrado)
    ```

---

#### 5. Modal de Seleção de Venda para Emissão
#### [MODIFY] [`frontend/src/modules/fiscal/components/emitir/FiscalEmitirNFeModal.vue`](file:///c:/dev/bigpdv/frontend/src/modules/fiscal/components/emitir/FiscalEmitirNFeModal.vue)
- Integrar `useFiscalVerificacaoBatchQuery` alimentado com os IDs das vendas visíveis.
- Renderizar cada venda com seu estado visual específico:
  1. **Venda com NF-e já autorizada**:
     - Badge verde `🟢 NF-e Emitida (Nº ${num})`.
     - Opacidade leve, cursor de ajuda.
     - Clique: Emite toast informativo: *"Esta venda já foi emitida (NF-e nº X). Acesse o Centro Fiscal para visualizar a DANFE/XML."*
  2. **Venda com NF-e em processamento**:
     - Badge azul `🔵 Processando na SEFAZ`.
     - Clique: Toast informativo solicitando aguardar o retorno da SEFAZ.
  3. **Venda com Pendências Fiscais (Incompleta)**:
     - Badge âmbar/vermelho `⚠️ Incompleta`.
     - Card com borda tracejada âmbar e texto secundário indicando a quantidade de pendências (ex: *"2 pendências cadastrais"*).
     - Botão desabilitado para avançar para o passo 2.
     - Clique: Dispara o toast formatado explicando exatamente o que falta corrigir.
  4. **Venda Apta**:
     - Badge verde suave `✅ Pronta para emitir`.
     - Clique: Avança normalmente para a pré-visualização (Passo 2).

---

#### 6. Tratamento de Erro 409 no Fluxo de Emissão
#### [MODIFY] [`frontend/src/modules/fiscal/composables/useFiscalEmitirNfeMutation.ts`](file:///c:/dev/bigpdv/frontend/src/modules/fiscal/composables/useFiscalEmitirNfeMutation.ts)
- Capturar especificamente respostas com `status === 409`:
  - Se `detail.codigo === 'NF_JA_AUTORIZADA'`, exibir toast de aviso com o número da nota e link/ação para abrir o documento.
  - Invalidar imediatamente a query de documentos fiscais e a query batch para atualizar a UI.

---

## Verification Plan

### Testes Automatizados (Backend)

Executar suite de testes do backend via PowerShell:
```powershell
cd c:\dev\bigpdv\backend-fastapi
.\.venv\Scripts\activate
pytest test/test_fiscal_emissao.py test/test_verificacao_fiscal.py -v
```

1. **Teste de Verificação Batch**:
   - Criar 3 vendas de teste: (1) completa e apta, (2) com item avulso, (3) sem CPF no cliente.
   - Chamar `verificar_completude_vendas_batch` e validar o dicionário de retorno e categorização das pendências.
2. **Teste de Bloqueio de Emissão Dupla (Idempotência Estrita)**:
   - Emitir NF-e para venda finalizada -> status muda para `AUTORIZADA`.
   - Tentar emitir novamente a mesma venda -> verificar que o endpoint retorna HTTP 409 (Conflict) com código `NF_JA_AUTORIZADA`.
3. **Teste de Concorrência**:
   - Simular duas chamadas concorrentes de emissão para a mesma venda e validar que apenas uma obtém trava de processamento.

### Verificação Manual (Ponta a Ponta no Frontend)

1. **Cenário 1: Venda Incompleta no Modal de Emissão**
   - No PDV, finalizar uma venda para um cliente sem CPF, contendo um produto sem NCM ou um item avulso.
   - Acessar o menu **Fiscal > NF-e** e clicar em **Emitir NF-e**.
   - **Resultado Esperado**: A venda deve aparecer na lista marcada com badge `⚠️ Incompleta`. Ao clicar na venda, a tela de pré-visualização **não** deve abrir; em vez disso, um toast elegante e formatado deve surgir listando os itens faltantes (cliente sem CPF, produto sem NCM).
2. **Cenário 2: Venda Apta e Emissão Completa**
   - Finalizar uma venda com cliente identificado (CPF válido), produtos cadastrados com NCM/CFOP/origem e pagamento em Dinheiro/PIX.
   - Abrir o modal **Emitir NF-e**.
   - **Resultado Esperado**: A venda aparece com badge `✅ Pronta para emitir`. Ao clicar, abre o passo 2 com pré-visualização e cálculo tributário simulado.
3. **Cenário 3: Bloqueio de Emissão Dupla**
   - Confirmar a emissão da venda aprovada no Cenário 2.
   - Reabrir o modal **Emitir NF-e**.
   - **Resultado Esperado**: A venda agora exibe o badge `🟢 NF-e Emitida` e está bloqueada para seleção, impedindo qualquer tentativa de reemissão duplicada.
4. **Cenário 4: Gating de Módulo Fiscal Desativado**
   - Testar o comportamento com o módulo fiscal desligado no plano (`recursoDisponivel('nfe') === false`).
   - **Resultado Esperado**: O modal fiscal sequer é exibido, rotas protegidas retornam 403 e a operação de caixa do PDV segue seu fluxo normal sem interrupções.
