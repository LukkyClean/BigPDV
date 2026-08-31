# Plano de Implementação: Modernização do Módulo Fiscal (Dashboard e Fluxo de Emissão)

Este documento estabelece as especificações técnicas, arquiteturais e de interface para a implementação das melhorias no **Dashboard de Gestão Fiscal** e no **Fluxo de Emissão de Vendas (NF-e)** do sistema **BigPDV**. 

O objetivo é transformar a interface em uma central de ação rápida e segura, reduzindo a fricção operacional, eliminando cliques acidentais, permitindo resolução de pendências sem navegação entre módulos e suportando operações em lote.

---

## User Review Required

> [!IMPORTANT]
> **Edição Inline de NCM/CFOP:** A estratégia adotada atualizará diretamente o cadastro do produto através do endpoint existente `PUT /api/v1/produtos/{produto_id}/fiscal`. Isso garante que correções feitas na pré-visualização da nota corrijam o catálogo de forma definitiva para futuras vendas e recalculem os tributos na hora.

> [!IMPORTANT]
> **Emissão e Reemissão em Lote:** O consumo de numeração fiscal sequencial (`ultimo_numero_nfe + 1`) e envio para a API da Focus NFe exigem controle transacional cuidadoso. As emissões e reemissões em lote devem ser orquestradas de forma sequencial pelo backend ou controladas por fila no frontend para impedir condições de corrida na numeração de notas.

---

## Open Questions

Não há pendências bloqueantes. O item relativo à "modelagem de pesos" foi formalmente removido do escopo desta especificação conforme solicitado.

---

## Arquitetura Geral e Fases

O plano está estruturado em 3 fases complementares:
1. **Fase 1 — Ganhos Imediatos (Quick Wins):** Filtros dinâmicos nos cards, visibilidade de rejeições, menu de ações contextuais `(...)`, seleção segura com botão "Avançar" e enriquecimento do preview com CST/CSOSN e Formas de Pagamento.
2. **Fase 2 — Produtividade Operacional:** Edição inline de NCM/CFOP com duplo clique na pré-visualização e Drawer/Modal de resolução de pendências cadastrais sem sair da tela fiscal.
3. **Fase 3 — Operações em Lote:** Checkboxes e ações em lote no Centro Fiscal (reemissão e cancelamento) e emissão de múltiplas vendas selecionadas.

---

## Proposed Changes

---

### Backend (FastAPI & Schemas)

#### [MODIFY] [emissao_fiscal.py](file:///c:/dev/bigpdv/backend-fastapi/app/schemas/emissao_fiscal.py)
* **Objetivo:** Enriquecer o DTO de pré-visualização com CST/CSOSN e formas de pagamento da venda.
* **Alterações:**
  1. No schema `EmissaoPreviewItem`, adicionar o campo:
     ```python
     cst_csosn: Optional[str] = Field(None, description="CST de ICMS ou CSOSN do item")
     ```
  2. Criar novo schema para pagamentos no preview:
     ```python
     class EmissaoPreviewPagamento(BaseModel):
         nome: str
         codigo_sefaz: str
         valor: float
     ```
  3. No schema `EmissaoPreviewResponse`, incluir:
     ```python
     formas_pagamento: list[EmissaoPreviewPagamento] = []
     ```
  4. Adicionar schema para requisições em lote de emissão:
     ```python
     class EmissaoNFeBatchRequest(BaseModel):
         venda_ids: list[int] = Field(..., min_length=1, max_length=50)
     ```

#### [MODIFY] [emissao.py](file:///c:/dev/bigpdv/backend-fastapi/app/services/fiscal/emissao.py)
* **Objetivo:** Preencher CST/CSOSN e formas de pagamento na função de preview e fornecer suporte a reemissão/emissão em lote.
* **Alterações:**
  1. Em `preview_nfe_venda`:
     * Ao iterar `venda.itens` e montar `itens_preview`, buscar o código de situação tributária calculado em `resultado_calculo.itens[idx].icms_situacao_tributaria` (ou fallback para `item_venda.produto.fiscal.csosn` / `cst_icms`). Atribuir a `cst_csosn`.
     * Iterar `venda.pagamentos` e montar `formas_pagamento`:
       ```python
       formas_preview = [
           {
               "nome": pag.forma_pagamento.nome if pag.forma_pagamento else "Outros",
               "codigo_sefaz": pag.forma_pagamento.codigo_sefaz if pag.forma_pagamento else "99",
               "valor": float(pag.valor / 100),
           }
           for pag in venda.pagamentos
       ]
       ```
     * Incluir `"formas_pagamento": formas_preview` no dicionário de retorno de `preview_nfe_venda`.
  2. Implementar função `emitir_nfe_vendas_batch(db, venda_ids, empresa_id)`:
     * Itera sequencialmente pelos `venda_ids`, invoca `emitir_nfe_venda` para cada venda individual e coleta sucessos/falhas para retornar status estruturado.

#### [MODIFY] [fiscal.py](file:///c:/dev/bigpdv/backend-fastapi/app/api/v1/endpoints/fiscal.py)
* **Objetivo:** Expor endpoint de emissão em lote.
* **Alterações:**
  1. Adicionar endpoint `POST /emitir/nfe-batch`:
     * Recebe payload `EmissaoNFeBatchRequest`.
     * Executa `emitir_nfe_vendas_batch`.
     * Agenda polling assíncrono para os documentos que entrarem em `PROCESSANDO`.

---

### Frontend — Módulo Fiscal

#### [MODIFY] [fiscal.types.ts](file:///c:/dev/bigpdv/frontend/src/modules/fiscal/types/fiscal.types.ts)
* **Objetivo:** Atualizar os tipos TypeScript para refletir as novas propriedades do preview.
* **Alterações:**
  1. Adicionar `cst_csosn?: string` em `EmissaoPreviewItem`.
  2. Criar `EmissaoPreviewPagamento`:
     ```typescript
     export interface EmissaoPreviewPagamento {
       nome: string;
       codigo_sefaz: string;
       valor: number;
     }
     ```
  3. Adicionar `formas_pagamento: EmissaoPreviewPagamento[]` em `EmissaoPreviewResponse`.

#### [MODIFY] [FiscalStats.vue](file:///c:/dev/bigpdv/frontend/src/modules/fiscal/components/listagem/FiscalStats.vue)
* **Objetivo:** Tornar os cards de resumo clicáveis e utilizáveis como filtros rápidos.
* **Alterações:**
  1. Adicionar props:
     ```typescript
     interface Props {
       resumo: DocumentoFiscalResumo | undefined;
       isLoading: boolean;
       activeStatus?: DocumentoFiscalStatus | null;
     }
     ```
  2. Adicionar emit: `defineEmits<{(e: 'select-status', status: DocumentoFiscalStatus | null): void}>()`.
  3. Envolver cada `BaseStatsCard` em um container clicável com `role="button"`, cursor pointer e classes visuais de destaque quando `activeStatus` for igual ao status do card (ex: anel/borda e leve elevação).
  4. Clique em um card já ativo emite `null` (comportamento de toggle para desmarcar).

#### [MODIFY] [FiscalDocumentosTable.vue](file:///c:/dev/bigpdv/frontend/src/modules/fiscal/components/listagem/FiscalDocumentosTable.vue)
* **Objetivo:** Integrar filtros dinâmicos externos, visibilidade de rejeições, menu de ações `(...)`, checkboxes e barra de ações em lote.
* **Alterações:**
  1. **Sincronização de Filtro:**
     * Aceitar prop `modelValueStatus?: DocumentoFiscalStatus | null` com `v-model:status`.
  2. **Exibição do Motivo da Rejeição:**
     * Na célula do destinatário (`<td>`): se `doc.status === 'REJEITADA'`, renderizar logo abaixo do texto de origem um bloco discreto em vermelho:
       ```html
       <div v-if="doc.status === 'REJEITADA' && (doc.motivo_rejeicao || doc.mensagem_sefaz)" 
            class="flex items-center gap-1 mt-1 text-[11px] text-red-600 truncate max-w-xs"
            :title="doc.motivo_rejeicao || doc.mensagem_sefaz">
         <AlertCircle :size="12" class="shrink-0 text-red-500" />
         <span class="truncate">{{ doc.motivo_rejeicao || doc.mensagem_sefaz }}</span>
       </div>
       ```
  3. **Menu de Ações Contextuais (...):**
     * Substituir a fileira horizontal de botões por um menu dropdown contextual (`BaseDropdown` ou popover acionado por `MoreVertical`).
     * Exibir apenas as opções válidas para o status daquela linha:
       * `AUTORIZADA`: Imprimir DANFE, Baixar XML, Cancelar NF-e, Ver Detalhes.
       * `REJEITADA` / `DENEGADA`: Reemitir Documento, Ver Motivo Completo, Ver Detalhes.
       * `PROCESSANDO` / `PENDENTE`: Consultar SEFAZ, Ver Detalhes.
       * `CANCELADA`: Imprimir DANFE, Baixar XML, Ver Detalhes.
  4. **Checkboxes e Ações em Lote:**
     * Adicionar checkbox no cabeçalho para marcar/desmarcar todos os itens da página atual.
     * Adicionar checkbox em cada linha da tabela.
     * Manter estado reativo `selectedDocIds = ref<number[]>([])`.
     * Quando `selectedDocIds.length > 0`, exibir barra flutuante inferior com:
       * Contador de notas selecionadas.
       * Botão **"Reemitir Selecionadas"**: Habilitado somente se todas as selecionadas forem `REJEITADA` ou `DENEGADA`.
       * Botão **"Cancelar Selecionadas"**: Habilitado somente se todas as selecionadas forem `AUTORIZADA`. Abre o modal de cancelamento em lote.
       * Botão para desmarcar todas.

#### [MODIFY] [FiscalNFeView.vue](file:///c:/dev/bigpdv/frontend/src/modules/fiscal/views/FiscalNFeView.vue)
* **Objetivo:** Conectar o estado do filtro selecionado nos cards do `FiscalStats` com o `FiscalDocumentosTable`.
* **Alterações:**
  1. Definir `filtroStatus = ref<DocumentoFiscalStatus | null>(null)`.
  2. Passar `:active-status="filtroStatus"` e `@select-status="filtroStatus = $event"` para `<FiscalStats />`.
  3. Passar `v-model:status="filtroStatus"` para `<FiscalDocumentosTable />`.

#### [MODIFY] [FiscalCancelarModal.vue](file:///c:/dev/bigpdv/frontend/src/modules/fiscal/components/detalhes/FiscalCancelarModal.vue)
* **Objetivo:** Suportar cancelamento de um ou múltiplos documentos com a mesma justificativa.
* **Alterações:**
  1. Alterar prop `documentoId: number | null` para `documentoIds: number[]`.
  2. Atualizar o texto informativo para indicar quando múltiplas notas serão canceladas simultaneamente (ex: "Cancelando 3 notas fiscais autorizadas").
  3. No envio, executar mutação de cancelamento para cada ID selecionado (ou chamar endpoint batch se implementado) com a justificativa única fornecida.

#### [NEW] [FiscalResolucaoProdutosDrawer.vue](file:///c:/dev/bigpdv/frontend/src/modules/fiscal/components/shared/FiscalResolucaoProdutosDrawer.vue)
* **Objetivo:** Permitir ao usuário preencher NCM, CEST e CFOP dos produtos com cadastro incompleto diretamente na tela fiscal.
* **Especificação do Componente:**
  1. Drawer lateral ou Modal de largura expandida contendo uma grade/tabela de produtos incompletos obtidos de `useFiscalPendenciasQuery`.
  2. Colunas da tabela:
     * Nome do Produto (leitura).
     * NCM (input com validação de 8 dígitos numéricos).
     * CEST (input com validação de 7 dígitos numéricos).
     * CFOP Padrão (input com validação de 4 dígitos numéricos).
  3. Botão "Salvar" individual por linha e botão geral "Salvar Todos":
     * Invoca `productService.updateFiscal(produtoId, dados)` para cada item modificado.
     * Ao salvar com sucesso, exibe toast e invalida as queries `fiscalKeys.pendencias()` e `fiscalKeys.resumo()`.
     * A barra de Saúde Fiscal é atualizada na hora sem sair do módulo.

#### [MODIFY] [FiscalPendenciasPanel.vue](file:///c:/dev/bigpdv/frontend/src/modules/fiscal/components/shared/FiscalPendenciasPanel.vue)
* **Objetivo:** Acionar o novo drawer de resolução de produtos em vez de navegar para `/products`.
* **Alterações:**
  1. Emitir evento `abrir-resolucao` ou alternar `showResolucaoDrawer = true` na seção de produtos com cadastro incompleto.
  2. Substituir o link externo de redirecionamento pelo acionamento do drawer em contexto.

#### [MODIFY] [FiscalEmitirNFeModal.vue](file:///c:/dev/bigpdv/frontend/src/modules/fiscal/components/emitir/FiscalEmitirNFeModal.vue)
* **Objetivo:** Implementar seleção segura com botão "Avançar", edição inline de NCM/CFOP com duplo clique, exibição de CST/CSOSN, bloco de Formas de Pagamento e suporte a emissão múltipla.
* **Alterações:**
  1. **Seleção Segura (Etapa 1):**
     * Remover a transição automática imediata para o preview no clique da linha.
     * Clicar em uma linha altera `vendaSelecionadaId.value = venda.id`, aplicando estilo visual de seleção (`bg-blue-50/70 border-brand-primary`).
     * Adicionar botão no rodapé: `"Avançar para Revisão"` (desabilitado se nenhuma venda apta estiver selecionada).
     * Somente ao clicar em "Avançar", disparar `previewMutation` e avançar para o `step = 2`.
  2. **Seleção Múltipla de Vendas (Etapa 1):**
     * Adicionar checkboxes nas linhas das vendas aptas.
     * Se `vendasSelecionadas.length > 1`:
       * O botão no rodapé muda para `"Emitir X Vendas em Lote"`.
       * Ao avançar, renderiza uma visualização de confirmação em lote (tabela com número da venda, cliente, total, e status apto).
       * Botão de confirmação dispara a emissão de todas as vendas selecionadas.
  3. **Edição Inline de NCM e CFOP (Etapa 2 - Preview):**
     * Nas colunas de CFOP e NCM da tabela de itens, permitir duplo clique:
       * Alterna a célula para um `<input>` compacto com máscara e foco automático.
       * `Enter` ou `blur` dispara a validação e salva via `productService.updateFiscal(item.produto_id, { ... })`.
       * Após salvar, executa `previewMutation.mutateAsync({ venda_id: venda.id })` para recarregar o preview e recalcular impostos automaticamente.
  4. **Inclusão de CST/CSOSN (Etapa 2 - Preview):**
     * Inserir nova coluna no cabeçalho: `<th>CST/CSOSN</th>` imediatamente após `<th>CFOP</th>`.
     * Exibir o código retornado pelo backend (`item.cst_csosn ?? '—'`) com estilização font-mono em badge suave.
  5. **Inclusão do Bloco de Forma de Pagamento (Etapa 2 - Preview):**
     * Logo abaixo do card de "Resumo Financeiro", adicionar o card "Forma de Pagamento":
       * Exibe lista das formas de pagamento vinculadas àquela venda (`previewData.formas_pagamento`), indicando o nome da forma e o valor formatado.

---

## Verification Plan

### Automated Tests
1. **Backend Tests (pytest):**
   * Testar cálculo tributário e resposta do endpoint de preview:
     ```bash
     cd c:\dev\bigpdv\backend-fastapi
     pytest tests/test_fiscal_preview.py -k "test_preview_nfe_includes_cst_and_pagamento"
     ```
   * Testar integridade da emissão em lote de vendas:
     ```bash
     pytest tests/test_fiscal_emissao.py -k "test_emissao_batch"
     ```

2. **Frontend Typecheck e Linter:**
   * Validar tipos e sintaxe dos componentes Vue modificados:
     ```bash
     cd c:\dev\bigpdv\frontend
     npm run build
     ```

### Manual Verification
1. **Filtro dos Cards:** Acessar `/fiscal/nfe`, clicar no card "Rejeitadas" e conferir se a tabela filtra automaticamente para notas rejeitadas. Clicar novamente no card e verificar se o filtro é limpo.
2. **Rejeição Visível:** Localizar uma nota com status `REJEITADA` e verificar se a mensagem da SEFAZ aparece de forma legível e elegante abaixo do nome do destinatário.
3. **Menu Contextual:** Clicar no menu `(...)` de uma nota autorizada e checar se apenas ações pertinentes (DANFE, XML, Cancelar) estão presentes.
4. **Seleção Segura e Botão Avançar:** Abrir o modal de "Emitir NF-e", clicar em uma venda da lista e constatar que a tela NÃO avança automaticamente. Clicar em "Avançar" no rodapé e checar a transição para a tela de pré-visualização.
5. **CST/CSOSN e Forma de Pagamento:** Na pré-visualização, verificar a presença da coluna `CST/CSOSN` na tabela de itens e o card de "Forma de Pagamento" abaixo do resumo financeiro.
6. **Edição Inline de NCM:** Dar duplo clique no campo NCM de um item no preview, alterar o valor, pressionar Enter e confirmar que o NCM foi salvo no produto e os tributos foram recalculados na hora.
7. **Resolução de Pendências em Contexto:** No popover de Saúde Fiscal, clicar em produtos com cadastro incompleto, constatar a abertura do Drawer na própria tela fiscal, preencher o NCM de um produto pendente, salvar e ver a barra de Saúde Fiscal subir sem redirecionamento de tela.
