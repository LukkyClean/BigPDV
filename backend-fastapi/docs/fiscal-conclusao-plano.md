# Plano: fechar a parte fiscal (NF-e + NFC-e)

Escrito em 11/09/2026, depois de dois dias de emissão em homologação. Sucede a
§3 e a §5 do `fiscal-onboarding-plano.md` (09/09), que ficaram para trás em
pontos importantes: uma nota nossa chegou na SEFAZ, o certificado passou a ser
enviado, e a consulta deixou de inventar rejeição. A §4 daquele documento (o
que cabe à plataforma) continua valendo e é referenciada daqui.

O foco continua o que o dono decidiu em 09/09: **NF-e e NFC-e**. NFS-e fica
fora até haver decisão comercial sobre municípios.

Arquitetura, para não perder o fio:

```
ERP (FastAPI) → api.startbig.com.br → Focus NFe → SEFAZ
```

---

## 0. O que "pronto" significa

Sem isto o plano não tem fim. A parte fiscal está pronta quando, **numa loja
real, em produção**, o lojista consegue sozinho:

| # | Critério de aceite | Hoje |
|---|---|---|
| P1 | Emitir a NF-e de uma **venda** e ver AUTORIZADA, com DANFE e XML | nunca autorizou (homologação recusou por cadastro; corrigido em `dbfa434`, **não reprovado ainda**) |
| P2 | Emitir a NF-e das peças de uma **OS** | idem — mesmo motor, mesma prova pendente |
| P3 | Fechar uma venda no **caixa** e sair um cupom NFC-e com QR Code | **não existe gatilho no caixa** (§2) |
| P4 | Corrigir uma nota rejeitada e **reemitir** com um clique | cria linha e não transmite |
| P5 | **Cancelar** dentro da janela (24h NF-e / 30min NFC-e) | codado, não provado na SEFAZ |
| P6 | **Inutilizar** um número queimado | codado; rota da plataforma não existe (§4.4.4) |
| P7 | Entregar os **XMLs do mês ao contador** | não existe |
| P8 | Ser avisado **antes** de o certificado vencer | não existe |
| P9 | Nunca emitir nota real achando que testa | feito (`52270dc`, chip mostra o ambiente da plataforma) |

P1–P6 é o cano. P7–P8 é o dia a dia — sem eles a loja "emite" mas o contador
liga no dia 5.

---

## 1. Onde estamos (11/09/2026)

**Do lado do ERP** (branch `feat/fiscal-nfe`, HEAD `dbfa434`, 1318 pytest,
vue-tsc 0):

- Fases 0–3 do plano de 09/09 e a NF-e por OS: feitas.
- O gate de cadastro agora recusa **antes** de reservar número, e diz o campo.
  A NFC-e não exige endereço; a NF-e exige (`tipo_documento` atravessa o gate).
- Consulta distingue três desfechos (nunca transmitida / rejeitada / denegada)
  pelo `codigo` do corpo, e `status_focus` é gravado (migration `89eb6b730bb3`).
- PENDENTE saiu do bloqueio de "emissão em andamento" — o fantasma da reemissão
  não tranca mais a venda.
- Sidecar e instalador gerados em 10/09 18:11/18:16, **não instalados** — o
  `C:\StartBigERP\erp-api.exe` ainda é o de 12/08.

**Do lado da plataforma** (o que dá para inferir daqui):

- **§4.2 (tradução aninhado → plano) foi feita**: a `teste-56b6bf343d13` chegou
  na SEFAZ e voltou 422 nomeando campos do destinatário. Nada chega na SEFAZ
  sem tradução.
- `1afa82c` (códigos no 404) está commitado lá e **não deployado**.
- Certificado (§4.1): o ERP envia desde `5e9ec4f`. Se a rota existir, o card
  do Centro Fiscal mostra "Conectado à nuvem"; se mostrar "Validado, não
  enviado", ela ainda não subiu. **Conferir na tela, não adivinhar.**
- §4.2b (CNPJ no `/config`), §4.4 itens 1–6: sem notícia. O ERP se comporta
  bem na ausência de cada um (ver §5).

---

## 2. O achado: a NFC-e nunca foi ligada ao caixa

Tudo em volta existe, e cada parte acredita que a outra faz o disparo:

| Peça | Estado | Onde |
|---|---|---|
| Backend `emitir_nfce_venda` (gate, CSC, QR, tributos do XML, cancelamento em 30 min) | feito | `services/fiscal/emissao.py:574` |
| Composable `emitirNFCeVenda(vendaId, cpf, indPres)` | feito, **nunca chamado** | `shared/composables/useEmitirFiscal.ts:119` |
| Impressão do cupom ESC/POS com QR | feito, usado só na **reimpressão** | `sales/composables/flows/useNfcePrintFlow.ts` |
| Tela do Centro Fiscal (NFC-e) | feita; diz "a NFC-e nasce no caixa" | `fiscal/views/FiscalNFCeView.vue:11` |
| Caixa (`SaleModal/NotaFiscalSection.vue`) | só tem **"Emitir NF-e"** | linha 298 |

`git log -S"emitirNFCeVenda("` confirma: desde o commit que criou tudo isso
(`2445d40`) o composable nunca teve chamador. Não é regressão — é a peça que
faltou entre duas obras.

E o plano do PDV (`pdv-fiscal-e-nao-fiscal-plano.md`, §8) já tinha escrito a
regra que governa esta ligação:

> **Finalizar a venda não pode significar "imprimir".** Numa venda fiscal existe
> um estado entre finalizar e imprimir: aguardando autorização, rejeitada,
> contingência.

O Modo Balcão emenda a próxima venda dentro do `afterPrint`. A NFC-e entra
**antes** disso, e o cupom fiscal substitui o não fiscal — nunca sai os dois.

---

## 3. Inventário: feito × desligado × faltando

| Área | Feito | Desligado / meia-obra | Faltando |
|---|---|---|---|
| Cadastro do emitente | MEI, CNPJ só dígitos, gate unificado, ajuda no Indicador de IE | — | aviso de vencimento do certificado (P8) |
| Certificado | envio real, 3 estados no card | espera §4.1 para gravar CONECTADO | — |
| NF-e de venda | gate, número atômico, snapshot, 3 desfechos, polling | **sem teste ponta a ponta** com client falso (só reserva e `_aplicar_resultado` separados) | prova em homologação (P1) |
| NF-e de OS | adaptador, rateio, pagamentos proporcionais | — | prova em homologação (P2) |
| NFC-e | backend inteiro, impressão, reimpressão, tela | **sem gatilho no caixa** (§2) | `/nfce/emitir` + `qrcode`/`url_consulta` na plataforma (§4.4.2-3) |
| Reemissão | linha encadeada, limite de 5 (na cópia morta) | **duas implementações**; a ligada herda o número e não transmite | ligar (P4) |
| Cancelamento | janela, justificativa, modal | — | prova na SEFAZ (P5) |
| Inutilização | gaps, tela, controle | espera §4.4.4 | — |
| Consulta/reconciliação | 3 desfechos por código, `status_focus`, polling | — | — |
| Ambiente | chip lê a plataforma, divergência em vermelho | `FiscalAmbienteBadge.vue` morto | — |
| Contador | — | — | exportar XMLs do período (P7) |
| Correção de nota | editar venda + reemitir | — | Carta de Correção (CC-e) — decisão, §7 |

---

## 4. Fases

### Fase A — o cano fecha (a homologação autoriza)

Nada aqui é obra nova; é provar o que foi construído e ligar o que está solto.

| # | O quê | Onde | Custo |
|---|---|---|---|
| A1 | Deploy da plataforma (`1afa82c`), instalar o `setup.exe` de 10/09, **conferir o hash** do `erp-api.exe` (`f88914b0…`), consultar a `teste-56b6bf343d13` | VPS + loja | manhã |
| A2 | **Primeira NF-e de venda AUTORIZADA em homologação.** Venda com cliente de endereço completo. Se recusar, a mensagem agora aponta o campo — corrigir cadastro, não código | loja | 1 h se a §4.2 estiver inteira |
| A3 | NF-e de OS autorizada (mesma venda de teste, mesmo cliente) | loja | 30 min |
| A4 | **FEITA (11/09).** **Reemissão transmite.** Módulo novo `services/fiscal/reemissao.py`: valida, conta a cadeia (máx. 5), **despacha** ao `emitir_*` da origem com `tentativa_anterior_id`. Apagar as duas cópias antigas (`emissao.py:890`, `documento_fiscal.py:214`). Endpoint ganha `BackgroundTasks`. Toast pelo status real | ERP | 1 sessão |
| A5 | **FEITA (11/09)** — `test/api/v1/test_emissao_ponta_a_ponta.py`, 9 testes. **Teste ponta a ponta de `emitir_nfe_venda`** com client falso (padrão de `test_fiscal_configuracoes.py:343`): gate → reserva → payload → client → `_aplicar_resultado`. Hoje a costura só foi provada em homologação. Vem junto com A4 porque a reemissão precisa dele | ERP | dentro de A4 |
| A6 | Cancelar a nota de A2 dentro da janela e ver CANCELADA (P5) | loja | 15 min |

Achado ao fazer A4: o botão "Corrigir e Reemitir NF-e" do drawer de detalhes
estava **morto** — emitia o id do próprio documento e a view gravava o mesmo
id. Só o "Salvar e Reemitir" do modal de edição chamava a mutação. Ligado no
mesmo commit; DENEGADA saiu do botão, da tabela e da edição (decisão §7.1,
seguida a recomendação).

**A4 é a única mudança de código desta fase.** Detalhe que já está decidido:
número sempre novo (é o que os `emitir_*` fazem; o buraco se resolve com
inutilização). O que falta decidir está na §7.1 (DENEGADA).

⚠️ PyArmor: `emissao.py` está com 53 KB, na beira do teto de bytecode do trial.
A4 **encolhe** o arquivo (~40 linhas a menos) e põe a novidade num módulo
pequeno. Se o `build:sidecar` reclamar de licença mesmo assim, é o teto
(`project_pyarmor_teto_bytecode`), não defeito.

### Fase B — NFC-e no caixa

A fase que falta inteira. Do lado do ERP é uma ligação; do lado da plataforma
são duas rotas (§4.4.2-3) sem as quais o cupom sai sem QR — e cupom sem QR não
vale.

| # | O quê | Onde | Custo |
|---|---|---|---|
| B1 | **Decidir o gatilho** (§7.2): botão "Emitir NFC-e" no fechamento, ou automático quando a loja marcou "caixa fiscal". Recomendação abaixo | dono | — |
| B2 | **FEITA (11/09, `8d3d0da`).** Ligar `emitirNFCeVenda` no fechamento da venda, **antes** do `afterPrint`. Estados visíveis: verificando → autorizada (imprime cupom fiscal) / rejeitada (imprime não fiscal? — §7.3) / indeterminada (não imprime, manda ao Centro Fiscal) | `SaleModal`, `useNfcePrintFlow` | 1–2 d |
| B3 | **FEITA** (já existia em `FiscalFechamentoSection`, só faltava montar). CPF na nota: campo já existe no composable (`documentoConsumidor`); pôr na tela do fechamento, opcional, com a máscara e o DV que o gate já valida | `SaleModal` | dentro de B2 |
| B4 | **FEITA** (idem). `indicador_presenca` no fechamento (balcão × entrega) — o composable já grava antes de emitir; a tela precisa perguntar só quando a venda tem entrega | `SaleModal` | dentro de B2 |
| B5 | **FEITA.** Modo Balcão: a próxima venda só abre depois do desfecho fiscal (regra de ouro) | `useModoBalcao` ou equivalente | dentro de B2 |
| B6 | Primeira NFC-e autorizada em homologação, cupom impresso com QR lido pelo celular | loja | 1 h, **depende da §4.4.2-3** |
| B7 | Cancelar dentro dos 30 min e ver CANCELADA | loja | 15 min |

Achados ao fazer a Fase B (11/09): o bloco fiscal do fechamento
(`FiscalFechamentoSection`) também existia e nunca tinha sido montado; e o
"Emitir NF-e" do modal da venda batia num stub 501 — passou a emitir de
verdade. A NF-e não espelhava em `venda_nota_fiscal` (só a NFC-e, e só na
emissão): `espelho_nota.py` virou o único lugar que copia, chamado por emissão,
reemissão, consulta e cancelamento. Decisões §7.2 e §7.3: seguidas as
recomendações (o padrão do bloco é "Emitir Fiscal" quando certificado e CSC
estão prontos — o operador troca com um clique; o comprovante gerencial de
loja com módulo sai marcado DOCUMENTO NÃO FISCAL).

**Recomendação para B1:** botão, não automático — pelo menos até a segunda
loja. O automático transforma cada instabilidade da SEFAZ numa fila parada no
caixa; o botão deixa o operador fechar não fiscal e emitir depois pelo Centro
Fiscal (o backend permite: a venda fica FINALIZADA sem documento ativo). Quando
houver contingência de verdade, aí se automatiza.

### Fase C — o que a plataforma deve (checklist, não obra nossa)

Cada item com o comportamento do ERP **enquanto falta**, para ninguém confundir
ausência com defeito.

| § | Rota / campo | Enquanto falta, o ERP… | Destrava |
|---|---|---|---|
| 4.1 | `POST /erp/fiscal/certificado` | grava `VALIDADO_LOCAL` e a tela explica | Fase A inteira (a Focus não emite sem certificado na empresa) |
| 4.2b | `cnpj` no `GET /erp/fiscal/config` | mostra "não informado", nunca divergência | diagnóstico de "CNPJ não autorizado" |
| 4.4.1 | `.passthrough()` no schema | campos podados → SEFAZ rejeita por falta de campo | Fase A |
| 4.4.2 | `qrcode` + `url_consulta` na resposta | cupom sem QR — **não imprime** | Fase B |
| 4.4.3 | `POST /erp/fiscal/nfce/emitir` | 404 → recusa local, sem número queimado | Fase B |
| 4.4.4 | `POST /erp/fiscal/nfe/inutilizar` | 501, tela de gaps funciona só como registro | P6 |
| 4.4.5 | `denegado` como status próprio | já resolvido do nosso lado via `status_focus` | — |
| 4.4.6 | `/licenca/conectar` remoeda o token? | concessão do NFE pode levar até 7 dias para aparecer | comercial |
| 4.3 | `db:push` (`idempotencia_fiscal`, `cscConfigurado`) | idempotência não protege contra duplicata em retry | Fase A |

Conferir com o time da plataforma **antes** da Fase B qual desses já subiu.
A `teste-56b6bf343d13` prova só a 4.2 e a 4.4.1 (os campos chegaram na SEFAZ).

### Fase D — o dia a dia (o contador e o certificado)

Sem isto a loja emite e a operação quebra no primeiro mês.

| # | O quê | Onde | Custo |
|---|---|---|---|
| D1 | **FEITA (11/09, `3667afc`).** **Aviso de vencimento do certificado.** `certificado_validade` já é gravado; falta virar pendência em `pendencias_globais` com 30 e 7 dias, e no card do Centro Fiscal. Certificado vencido = loja parada sem aviso | backend + card | ½ d |
| D2 | **FEITA (11/09, `209717c`).** **Exportar XMLs do período.** Botão "XMLs do mês" no Centro Fiscal → ZIP com autorizadas + canceladas + inutilizações, nomeado pela chave. O `baixar_xml` do client já existe; falta o laço e o ZIP. É o que o contador pede todo dia 5 | backend (endpoint) + botão | 1 d |
| D3 | **FEITA.** Apagar `FiscalAmbienteBadge.vue` | frontend | — |

O filtro por período e status que o D2 precisa **já existe** no
`GET /fiscal/documentos` (`data_inicio`, `data_fim`, `status`, `tipo`); o ZIP
reusa a mesma consulta.

### Fase E — produção

Só depois de A e B fecharem em homologação. É checklist, e quase nada é código.

1. Plataforma: `ambiente = 1` na `EmpresaFiscalConfig` da loja, certificado e
   **CSC de produção** (o de homologação não vale) cadastrados.
2. Série e **numeração inicial** conferidas com o contador — se a loja já emitiu
   por outro sistema, o contador continua de onde parou, não do 1.
3. Trava local (`ambiente_emissao`) coerente com a plataforma; o chip tem que
   ficar verde, não vermelho.
4. `npm run build:sidecar` + instalador + hash conferido na loja.
5. **Primeira nota real com o contador do lado**, de valor baixo, e o
   cancelamento dela dentro da janela — prova que os dois lados funcionam em
   produção antes de o caixa depender disso.
6. Módulo na licença: lista **completa** `["FINANCEIRO","NFE"]`; só `["NFE"]`
   derruba a Gestão Financeira.

---

### Estado em 11/09/2026, fim do dia

Tudo que não depende de ninguém está **feito e commitado** (`f692be9`,
`3667afc`, `8d3d0da`, `209717c`): 1348 pytest, vue-tsc 0, sidecar e
instalador gerados. O que resta é **prova em loja** (A1–A3, A6, B6–B7) e a
**plataforma** (Fase C). A Fase E é checklist.

## 5. Ordem e custo

| Ordem | Fase | Custo (ERP) | Depende de |
|---|---|---|---|
| 1 | A1–A3, A6 (provar) | 1 dia de loja | plataforma: 4.1, 4.2, 4.4.1, db:push |
| 2 | A4+A5 (reemissão) | 1 sessão | — |
| 3 | D1 (certificado vence) | ½ d | — |
| 4 | B2–B5 (NFC-e no caixa) | 1–2 d | decisão §7.2 |
| 5 | B6–B7 (provar NFC-e) | ½ dia de loja | plataforma: 4.4.2, 4.4.3 |
| 6 | D2–D3 (contador) | 1 d | — |
| 7 | E (produção) | 1 dia de loja + build | tudo acima |

**Total de código do nosso lado: ~5 dias.** O resto é prova em loja e espera
da plataforma. A ordem põe primeiro o que **não depende de ninguém** sempre que
a plataforma estiver atrasada: A4, D1, B2–B5 e D2 podem ser feitos enquanto se
espera a 4.4.2-3.

A trilha inteira sai **desta branch** (`feat/fiscal-nfe`), e o instalador do
cliente sai sempre da linhagem da oficina (`project_branch_oficina_isolada`) —
conferir o merge antes da Fase E.

---

## 6. O que NÃO entra

- **NFS-e** — municipal, sem rota na plataforma, sem decisão comercial. A
  `FiscalNFSeView` continua dizendo "em breve".
- **Contingência offline de NFC-e** — exige assinar o XML na loja, e o
  certificado vive na plataforma por desenho. Quando a SEFAZ cai, a Focus
  enfileira (`processando`) e o polling resolve; o caixa fecha não fiscal e
  emite depois. É limitação conhecida, não tarefa.
- **Entrada por XML e manifestação do destinatário** — trilha B do plano do
  PDV, recurso pago, outro projeto.
- **E-mail/WhatsApp do DANFE ao cliente** — o `url_pdf` já vem da plataforma; o
  operador pode baixar e mandar. Automatizar é feature, não fechamento.

---

## 7. Decisões em aberto (são do dono)

1. **DENEGADA continua reemitível?** O commit `dbfa434` concluiu que "reenviar
   não adianta" e tirou DENEGADA do balde de REJEITADA — mas o botão do drawer e
   os dois backends ainda aceitam. **Recomendação: cortar** (422 + botão some).
   Hoje o clique gasta um número e volta denegada de novo. Contra: denegação
   por IE irregular do destinatário (302) se resolve corrigindo o cliente — e
   isso continua possível pelo "Emitir NF-e" direto na venda.

2. **NFC-e: botão ou automática?** Recomendação em B1: botão. Muda para
   automática quando a loja pedir, por chavinha na configuração, nunca por
   padrão.

3. **Venda com NFC-e rejeitada: imprime o cupom não fiscal?** Recomendação:
   sim, e a venda fica FINALIZADA sem documento ativo — o operador resolve no
   Centro Fiscal. Detalhe: o cupom não fiscal de hoje **não tem aviso nenhum**
   (a linha "SEM VALOR FISCAL" é a do cupom NFC-e em homologação,
   `nfceToEscPos.ts:218`); numa loja fiscal ele precisa ganhar uma, senão o
   cliente sai com um papel que parece cupom fiscal e não é. Entra no B2. A
   alternativa (trancar o caixa até resolver) é o que os PDVs antigos fazem e é
   o que faz a loja odiar o fiscal.

4. **Carta de Correção (CC-e)?** Serve para erro que não muda valor nem
   destinatário (endereço, descrição). Hoje o caminho é cancelar (24h) e
   reemitir. Sem CC-e, erro descoberto no dia seguinte não tem saída — mas é
   rota nova na plataforma **e** tela nova. Recomendação: **não agora**;
   registrar como próxima fase depois da E.

---

## 8. Riscos

- **A prova de A2 pode revelar recusa nova.** Cada rodada em homologação até
  agora achou um campo (CPF fictício, endereço, `modalidade_frete`). O gate
  cobre o que a SEFAZ já apontou; o que ela ainda não apontou, não. Orçar A2
  como iteração, não como evento.
- **Código compartilhado com as 3 lojas em produção.** `SaleModal` e o fluxo de
  impressão são do PDV que roda na informática, oficina e serigrafia. B2 mexe
  neles: a prova tem que ser **medida** (antes × depois), e o não fiscal tem que
  continuar idêntico para quem não tem o módulo (`project_informatica_producao`).
- **A reemissão hoje herda o número** (`documento_fiscal.py:236`). Enquanto A4
  não sair, ligar "transmitir" nessa cópia produziria Rejeição 204 na primeira
  tentativa. Não ligar nada antes de trocar a implementação.
- **PyArmor trial.** Cada arquivo grande do fiscal (`emissao.py`,
  `payload_builder.py`, `client_startbig.py`) está perto do teto. Novidade vai
  em módulo novo; refactor que engorda um deles quebra o sidecar.
- **Deploy em duas pontas.** Loja e plataforma não sobem juntas. Todo item da
  Fase C tem comportamento definido na ausência — manter isso é o que permite
  qualquer ordem de deploy.
