# PDV — onde paramos (20/08/2026)

Ponto de retomada. Branch `feat/pdv`, último commit `df6de7f`.

> ✅ **A ÁRVORE ESTÁ LIMPA.** As fases 1, 2 e 3 foram dirigidas no app em
> 20/08/2026 e saíram em **três commits separados**: `637c264` (Modo Balcão),
> `cfa5799` (teclado e leitor) e `df6de7f` (terminais). A dívida do dia 17 está
> paga e o `git bisect` volta a servir.

---

## 1. O que o teste no app revelou (20/08)

O roteiro não passou de primeira, e o que ele achou pagou a manhã:

- **`<SaleModal />` estava montado DUAS vezes** — uma no `MainLayout` e outra no
  `SalesView`. Como o estado da venda é global (refs de módulo), o mesmo `Esc`
  era tratado duas vezes: a primeira fechava a modal de cima, a segunda via a
  flag já em `false` e fechava o PDV inteiro. Era o bug do `F3 → Esc →
  Ctrl+Enter`.
- **O `Esc` não enxergava o sub-modal de pagamento** e fechava a Finalizar Venda
  por cima dele, levando junto os pagamentos já lançados.
- **Não havia tecla para finalizar a venda.** O "segundo Enter" estava escrito no
  plano e nunca tinha sido ligado no botão. Agora existe — e espera a tecla
  anterior ser SOLTA, senão o mesmo Enter que confirma o pagamento clica em
  Finalizar e o troco some junto com o modal.
- **O Tab só anda para frente** e o foco nasce no meio do grid de pagamento: as
  três formas de cima eram inalcançáveis pelo teclado. Agora as setas andam pelo
  grid.
- **A lista de atalhos mentia em três linhas** (`Ctrl+Enter` não finaliza, `F2`
  é da lista de vendas, `F6` só age com o pagamento aberto). Corrigida contra o
  código, e ganhou o que faltava: `Enter`, setas e o grid de pagamento.

Lição que vale registrar: **as duas correções mais caras do dia — modal
duplicada e hierarquia do Esc — não seriam achadas por teste automatizado
nenhum.** Foram achadas dirigindo a janela.

## 1.1 O que ainda NÃO foi provado no app

- **Fase 3 inteira** (Terminais): nome que sobrevive ao logout, papel
  Retaguarda, coluna Terminal no relatório.
- **O leitor de verdade**: itens 6 e 7 do roteiro (código inexistente e código
  repetido em 2 produtos).
- A venda de 3 garrafas cronometrada, contando saídas voluntárias do teclado.

---

## 2. O que foi feito em 17/08

### Fase 1 — Modo Balcão *(fechada, falta só a prova)*
- `scripts/check-balcao.mjs`: guard de build que trava a chave dentro de 4
  arquivos autorizados e impede inverter o padrão desligado. **Testado que ele
  falha quando deve** (arquivo intruso e padrão invertido).
- ⚠️ O guard protege **arquitetura, não comportamento**. "Tem guard" não é "tem
  teste do Modo Balcão" — o ON/OFF continua sendo verificação manual.

### Fase 2 — O caminho de teclado *(codada, 6 commits lógicos num blob só)*
- **`tentarAdicionarProduto`**: porta única para leitor, clique, teclado e a
  modal. É **assíncrona** e espera a decisão do modal de estoque antes de
  resolver. Devolve `added | not_found | ambiguous | blocked | cancelled | error`
  em vez de `false` com cinco significados.
- **Cinco silêncios** consertados, incluindo o `catch { return false }` que
  transformava queda de rede em "não aconteceu nada".
- **Destaque determinístico**: `highlightedIndex` nasce em 0 e o watch volta para
  0. Herda de graça o ranking de código exato que o backend já calcula.
- **Flush do debounce** quando o leitor não morde — a lista aparece na hora, não
  300 ms depois.
- **Estoque zerado passou a ler `permitir_venda_estoque_zerado`**, no mesmo
  limiar do backend. Não é mudança de regra: a tela ignorava a configuração da
  loja e errava nos dois sentidos.
- **F3** abre a tela de quantidade; ela ganhou o teclado que nunca teve.
- Removidos `quantityInputRef` e `addItemToSale` (mortos).

### Fase 3 — Terminais persistentes *(codada + 12 testes)*
- Tabela `terminais` (durável) separada de `terminais_conectados` (presença).
  Migration `a1b2c3d4e5f6`, que copia o que já foi digitado na tabela antiga.
- **457 pytest** (eram 445). O teste mais importante: terminal não configurado
  nunca perde a trava de caixa.
- Tela em Configurações › Computadores da Loja.
- O relatório passou a ler o nome do **cadastro**, não da presença — era por isso
  que a coluna Terminal ficava vazia nos turnos antigos.

### Correções de bugs que apareceram no caminho
- **A barra do caixa mostrava R$ 0,00 com a gaveta cheia.** O backend mandava
  "oculto" como o número `0`. Agora manda `null` e a tela diz que está oculto.
  O teste que existia **afirmava o bug** (`== 0`) e foi corrigido.
- **Foco não chegava na busca de produto.** Endurecido: tenta, confere se o foco
  ficou (`document.activeElement`), e tenta de novo no quadro seguinte.
- **O login quebrava (500)** com o cadastro de terminal: `try/except` sem
  rollback envenena a sessão do SQLAlchemy e quem quebra é o commit, depois.
  Agora é `begin_nested()`.

---

## 3. O QUE FALTA

### 3.1 Provar as fases 1–3 no app *(bloqueia tudo)*
Seção 1. É o próximo passo, não há alternativa.

### 3.2 Fase 4 — Instalar na adega *(meio dia)*
```
build do código → build do SIDECAR → instalador → versão identificável
→ instalação → reinício do backend → smoke test
```
- ⚠️ **O sidecar está desatualizado desde a fase 0.5.** Instalador gerado sem
  `npm run build:sidecar` leva o backend velho, e o sintoma chega como "segmento
  pdv recusado" ou "relatório mostrando zeros".
- **Build ID no `/api/health`** — item obrigatório, ainda **não feito**. Hoje o
  endpoint devolve `{"status":"ok"}` e o backend não sabe qual build é. O lugar
  de resolver é o `build-sidecar.mjs`, que carimba SHA + timestamp num arquivo
  que entra no bundle. Melhor retorno por linha do plano inteiro.
- ⚠️ Não mandar as fases 4 e 5 do plano do caixa no mesmo instalador para as três
  lojas que já rodam.

### 3.3 Fase 5 — Permissões *(projeto próprio, o maior)*
Nada começado. `view`/`manage`/`delete` não valem: a fechadura só confere se você
tem *alguma* chave. Precisa de migração de compatibilidade **antes** da semântica
nova (sai num instalador só — `aplicar_migracoes()` roda no startup). Falta
também redefinir senha de funcionário. **Limite explícito: não refatorar o
sistema de permissões inteiro.**

### 3.4 Faxina pendente
- As colunas `nome` e `papel` de `terminais_conectados` ficaram **mortas** depois
  da fase 3. Não removidas de propósito (evitar rebuild de sidecar só para isso).
  Saem numa migration própria quando a fase 3 estiver rodando na loja.
- **`npm run lint` está quebrado** no repositório: ESLint 9 procura
  `eslint.config.js` e só existe o formato antigo. É anterior a hoje, mas o
  `CLAUDE.md` manda rodar esse comando.

---

## 4. DECISÕES EM ABERTO (nenhuma bloqueia o teste)

**(a) As duas telas de produto continuam existindo?**
A busca inline (rápida, bipável, sempre +1) e a modal Adicionar Produto
(quantidade e desconto). Deixei as duas funcionando e obedecendo à mesma regra,
justamente para não decidir por você. Se a resposta for "só a inline", dá para
apagar a modal depois sem desfazer nada.

**(b) Se o F3 continuar abrindo a busca do navegador**, duas saídas:
- desligar os aceleradores de busca do WebView2 na configuração do Tauri
  (resolve na raiz, vale para o `Ctrl+F` também);
- trocar a tecla — F7, F8 e F9 estão livres e sem ação nativa no Chromium.

**(c) Fechamento cego**: ligado, a barra nunca mostra o dinheiro (é o que faz a
conferência ser conferência). Desligado, a barra vira o reflexo real da gaveta.
Numa loja onde você é o próprio caixa, o cego só atrapalha.

---

## 5. Divergências do backend que ficaram registradas, não corrigidas

- **Orçamento não lê `permitir_venda_estoque_zerado`.** `services/venda.py`
  consulta a chave; `services/orcamento.py` (`:106` e `:151`) recusa sempre. A
  tela espelha cada um separadamente — aplicar a mesma regra nos dois faria o
  orçamento prometer o que o servidor nega. Unificar mexe em regra de venda das
  três lojas e não entra aqui.
- **Categoria na sangria** (fornecedor, retirada do dono, despesa fixa) fica para
  o **módulo financeiro**. Decidido em 17/08: uma categoria agora cobriria só o
  que passa pela gaveta e criaria uma taxonomia que o financeiro refaria.

---

## 6. Coisas que não podem ser esquecidas

- **Reinicie o backend depois de mexer em Python.** Já custou duas rodadas de
  diagnóstico ("código novo com processo antigo").
- **Master é quem tem CARGO CHAMADO "Master"**; visão gerencial vem do NOME do
  cargo conter "gerente" ou "administrador".
- **Cada funcionário precisa do PRÓPRIO login**, senão o relatório de caixa diz o
  mesmo nome em todas as linhas.
- **Relatórios não filtra por funcionário**: quem tem a permissão vê a comissão de
  todos.
