# Análise e Melhoria do Prompt: Centro Fiscal - StartBig ERP

**Contexto:**
Estamos desenvolvendo a interface e a lógica de apresentação do "Centro Fiscal" (Módulo Fiscal) para o StartBig ERP (stack: FastAPI no backend e Vue 3 + Tauri no frontend). Este módulo atua como uma peça de encaixe opcional e integra-se à Focus NFe. Precisamos construir uma dashboard centralizada e profissional que dê ao usuário controle total sobre suas emissões e pendências, seguindo o Documento Técnico de Arquitetura do sistema.

**Objetivo:**
Criar o planejamento e o detalhamento técnico do **Centro Fiscal**. Este painel deve agregar o gerenciamento dos documentos emitidos e o painel de pendências proativas.

**Requisitos e Funcionalidades (O que deve ser planejado):**

1. **Gestão de Documentos Fiscais (`documento_fiscal`):**
   * Listar todas as notas geradas, mapeando sua origem polimórfica (Vendas e Ordens de Serviço).
   * Exibir status em tempo real (Autorizado, Rejeitado, Cancelado).
   * Permitir ações interativas: pré-visualização do DANFE, download do XML/PDF e reemissão de notas rejeitadas.
   * Exibir de forma explícita os motivos de rejeição retornados pela SEFAZ/Focus NFe.

2. **Painel de Pendências Fiscais (Fonte de dados: `verificar_completude_fiscal()`):**
   * Exibir estatísticas e listas de itens bloqueantes de forma não-intrusiva.
   * Mostrar de forma categorizada: Produtos ativos sem NCM, Serviços sem código municipal, Formas de pagamento sem código SEFAZ e Dados do emitente incompletos.
   * O painel deve ser apenas informativo, pois o bloqueio real ocorre no "Gate pré-envio" no momento da emissão da venda/OS.

3. **Regra de Exibição e Segurança:**
   * Garantir que o módulo `modules/fiscal/` no frontend só seja renderizado e acessível se o backend confirmar que o `empresa.fiscal_settings` está ativo para o tenant.

**Sua Tarefa:**
Aja como um Arquiteto de Software/Desenvolvedor Sênior. Entregue um planejamento estruturado de como esses componentes devem ser implementados no frontend (componentização no Vue) e no backend (endpoints FastAPI). 
Ao final do seu planejamento, **faça uma lista com todas as dúvidas ou pontos cegos sobre regras de negócio, UI/UX ou comportamentos do sistema que você precise que eu esclareça antes de começarmos a codar.**

***

## 3. Faças as perguntas abaixo para fechar o planejamento

1. **UX das Pendências:** Quando o usuário clica em "15 Produtos sem NCM" no painel, o sistema deve abrir um modal de correção rápida em lote (planilha/grid) ou deve redirecioná-lo para a tela de listagem de produtos com um filtro fiscal aplicado?
2. **Visualização do Documento:** Para a pré-visualização da NFe, você deseja renderizar o DANFE em um visualizador de PDF embutido dentro do app Tauri, ou abrir no visualizador padrão do sistema operacional?
3. **Métricas e Dashboards:** Além de "notas pendentes, concluídas e canceladas", você deseja visualizar totais financeiros tributados (ex: Total faturado no mês via NF) nesse Centro Fiscal, ou apenas a gestão operacional dos documentos?
4. **Fila de Processamento:** Se uma Venda tiver muitos itens ou a Focus NFe demorar a responder, o status da `documento_fiscal` ficará como "Processando". O Centro Fiscal deve ter *auto-refresh* (polling/WebSockets) para atualizar esse status na tela sem o usuário precisar recarregar a página?