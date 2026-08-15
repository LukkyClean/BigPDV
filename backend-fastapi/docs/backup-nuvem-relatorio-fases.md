# Backup em nuvem — relatório das fases

**Sistema:** StartBig ERP · **Data:** 27 de julho de 2026
**Documento de referência técnica:** `backup-nuvem-plano.md` (plano de implementação)
**Contrato do servidor:** `erp-backup-contrato.md`, repositório da plataforma web (`eca757b`)

---

## 1. O que este projeto entrega

Backup automático dos dados de cada cliente para a nuvem da StartBig, com recuperação
possível em caso de perda da máquina.

Hoje o cliente não tem backup nenhum. O banco de dados e as fotos vivem em
`%LOCALAPPDATA%\StartBigERP\` — sobrevivem à atualização do sistema e à desinstalação,
mas não sobrevivem ao HD queimar, ao PC ser roubado ou ao ransomware. A tela de
"Backup dos Dados" existe nas Configurações, mas é uma casca visual: os botões estão
desabilitados e não há nada por trás.

### O que é salvo, e o que cada parte significa

| Parte | Conteúdo | Tamanho típico |
|---|---|---|
| **Banco de dados** | 39 tabelas: clientes, produtos, estoque, vendas, ordens de serviço, orçamentos, pagamentos, funcionários, configurações | dezenas de MB |
| **Fotos de catálogo** | imagens de produto, logo da empresa, avatares | pequeno e estável |
| **Fotos de ordem de serviço** | registro do equipamento na entrada, acompanhamento, conclusão | cresce para sempre |

A distinção mais importante do projeto: **o banco não contém as fotos.** Ele guarda o
caminho do arquivo (`ordens-servico/482/a3f9.webp`), não os bytes da imagem. Por isso
são backups separados — e por isso restaurar só o banco é uma operação legítima:
a loja volta a operar por inteiro, com as miniaturas quebradas até as fotos chegarem.

---

## 2. Como funciona, em uma página

O ERP conversa com a API da StartBig em quatro passos, autenticado com o mesmo token
de licença que já usa hoje:

1. **Consulta cota** — `GET /erp/backup/status` diz se o plano permite, quantos envios
   restam hoje e o que já está na nuvem.
2. **Pede autorização** — `POST /erp/backup/url-upload` devolve um link temporário de
   escrita, ou responde `PULAR` se nada mudou desde o último envio.
3. **Envia** — `PUT` do arquivo direto no armazenamento, sem passar pela API.
4. **Confirma** — `POST /erp/backup/confirmar`, sempre, tenha dado certo ou errado.

O envio roda **automaticamente**, uma vez por dia, e há um botão manual para o usuário
forçar quando quiser.

### Duas limitações estruturais, ditas de frente

**O backup só acontece com o sistema aberto.** Quem envia é o backend embutido no app,
e ele só existe na máquina configurada como servidor da loja. Não há serviço do Windows
rodando em segundo plano. Loja que passa uma semana sem abrir o sistema passa uma semana
sem backup. Por isso o agendamento é oportunista — "passaram 24 horas do último envio?
sobe agora" — e não um horário fixo. Backup marcado para as 2 da manhã nunca aconteceria:
a loja desliga o PC.

**Consequência para a tela:** o campo "horário do backup" do desenho atual sai. Ele
promete um controle que a arquitetura não entrega.

---

## 3. Fase 1 — Backup do banco de dados

**Estado: pronta para implementar. Não depende de nada externo.**

### Escopo

Envio automático e manual do banco, tela de acompanhamento, histórico de envios e um
botão de verificação que prova que o backup funciona.

### Como o banco é empacotado

O arquivo do banco não pode ser copiado com o sistema em uso — cópia simples de um
SQLite ativo produz backup corrompido se houver escrita no meio. Usamos o comando
`VACUUM INTO` do próprio SQLite, que numa única operação gera uma cópia íntegra **e**
compactada, removendo o espaço morto acumulado. Depois disso o arquivo é comprimido em
ZIP com LZMA. Banco é texto e número: comprime de 5 a 10 vezes.

Todo o empacotamento roda fora da linha principal de execução. O backend atende um
pedido por vez; comprimir no lugar errado congelaria venda, OS e atendimento enquanto
durasse.

### O registro de envios

Uma tabela nova, `backup_log`, acompanha cada envio em três estados: **emitido** (o
servidor reservou uma vaga), **enviado** (o arquivo chegou na nuvem) e **confirmado**
(o ciclo fechou). O estado do meio existe por um motivo prático: se faltar luz durante o
envio, na próxima abertura o sistema precisa saber se o arquivo chegou a subir ou não —
são situações opostas e o tratamento é diferente.

Essa tabela também alimenta a tela de histórico e permite diagnosticar por telefone o
que aconteceu na máquina do cliente.

### "Testar meu backup" — o item que vale mais que parece

Um botão que **baixa o backup da nuvem, abre o arquivo, verifica que é um banco válido
e íntegro, e joga fora.** Não toca no banco em uso, não restaura nada, não tem passo
destrutivo.

É o que separa "o servidor respondeu que recebeu" de "o arquivo que está lá abre".
Rodando uma vez por mês, o cliente descobre que o backup está quebrado num dia comum,
e não no dia em que o HD morreu.

Este item estava classificado como parte da restauração — uma fase sem dono nem data.
Foi movido para a fase 1 porque não depende de nada dela: reaproveita o download e a
verificação, e para por aí.

### Entregas da fase 1

- Tabela de registro e migração do banco
- Serviço de empacotamento e comunicação com a API
- Rotas locais: status, executar, testar, histórico — todas restritas ao usuário Master
- Tarefa automática diária e reconciliação de envios interrompidos
- Tela de Backup funcional, com botão desabilitado e motivo escrito quando não há vaga
- Dez testes automatizados, todos contra um servidor simulado — nenhum encosta na API
  real, porque a cota diária é do cliente

### Fora do escopo da fase 1

A restauração. Trocar o arquivo do banco enquanto o sistema o mantém aberto exige
derrubar o backend e aplicar a troca na inicialização seguinte — é um projeto próprio,
detalhado na fase 3. Restauração feita pela metade destrói banco de cliente, e backup
sem restauração já entrega valor: o arquivo está guardado e é recuperável com suporte.

---

## 4. Fase 2 — Backup das fotos

**Estado: desenho fechado dos dois lados. Aguarda o servidor entrar em produção.**

### O problema que essa fase resolve

Foto de ordem de serviço tem uma característica que muda tudo: **é escrita uma vez e
nunca mais alterada**, e a pasta só cresce. Uma oficina com 10 OS por dia e 4 fotos por
OS acumula cerca de 12 MB por dia — 360 MB em um ano.

Tratada como espelho, essa pasta seria reenviada por inteiro toda noite. Aos 400 MB, o
cliente subiria 400 MB por dia dos quais 99% seriam fotos de meses atrás que nunca mais
vão mudar — até bater no teto de 500 MB por pacote, quando o backup simplesmente pararia
de funcionar. Não é um problema que se resolve aumentando limites: com o teto em 2 GB,
passaria a subir 2 GB por noite.

### A solução: separar por ciclo de vida

| Pacote | O que leva | Com que frequência sobe |
|---|---|---|
| `imagens.zip` | fotos de produto, logo da empresa, avatares | todo dia — são poucas e mudam |
| `os-2026-05.zip` | fotos de OS de maio | uma vez na vida |
| `os-2026-06.zip` | fotos de OS de junho | uma vez na vida |
| `os-2026-07.zip` | fotos de OS do mês corrente | todo dia |

O envio diário passa a ser: banco + catálogo + o mês corrente. **Deixa de crescer com a
idade da instalação** — uma oficina com cinco anos de histórico envia por noite a mesma
coisa que uma com cinco meses.

### As três decisões que sustentam isso

**O mês de uma foto é a data de cadastro dela no banco.** Não a data da ordem de serviço
— este sistema permite reabrir OS, e uma foto anexada hoje a uma OS de maio faria um mês
já fechado voltar a mudar. E não a data do arquivo em disco — timestamp de arquivo não
sobrevive a cópia de pasta, então migrar o cliente para um PC novo reescreveria todas as
datas e o acervo inteiro seria reenviado, justamente no pior dia possível. A data
guardada no banco é a única que sobrevive a cópia, a restauração e a troca de máquina.

**Um mês é reenviado quando muda, não quando "ainda não subiu".** Parece a mesma coisa e
não é. Se o sistema pulasse meses por já terem sido enviados, as fotos dos últimos dias
de cada mês nunca chegariam à nuvem — o último envio de julho aconteceu durante julho e
não continha o que veio depois dele. Comparando conteúdo, isso se corrige sozinho no ciclo
seguinte, sem rotina especial de virada de mês e sem custo quando nada mudou.

**A verificação é feita antes de compactar.** O sistema compara uma assinatura do
conteúdo local com a que está na nuvem. Batendo, não compacta nada e não chama a API. No
funcionamento normal, o backup de fotos custa uma requisição e alguns milissegundos.

### O primeiro envio é o mais pesado

Um cliente que já tem dois anos de histórico precisa subir 24 pacotes, cada um uma única
vez. O servidor reserva uma cota separada e maior para esse caso (12 por dia contra 2 do
uso normal), justamente porque é a janela em que o acervo ainda está desprotegido. Se a
cota acabar, o envio continua no dia seguinte de onde parou — nenhum mês é perdido.

### Depende de

O servidor já tem a partição implementada, mas **em branch, ainda não executada uma única
vez em ambiente real**. A fase 2 do ERP não tem contra o que escrever até isso subir. A
decisão de quando subir é da direção, e está condicionada à separação entre ambiente de
teste e produção.

---

## 5. Fase 3 — Restauração

**Estado: documentada, sem responsável e sem data.**

É a fase que dá sentido às outras duas. Backup que ninguém sabe restaurar é fé, não
seguro. Está registrada aqui para ser um item planejado, e não a descoberta de daqui a
três meses.

### Por que não é trivial

**O sistema segura o arquivo do banco enquanto está aberto.** Sobrescrever com o ERP
rodando vai de erro claro a corrupção silenciosa. O caminho seguro é baixar e verificar
numa área temporária, marcar a operação como pendente, pedir para o usuário fechar o
programa, e fazer a troca na abertura seguinte, antes de qualquer conexão ser aberta. É
o único momento em que a troca é segura, e não exige do usuário nada além de reabrir o
sistema.

**A ordem importa, e a errada custa caro.** Fotos primeiro, banco por último, e o banco
antigo é **renomeado, nunca apagado**. "Restaurei e agora não abre nem o novo nem o
velho" é o único desfecho pior que não ter backup.

**A partição encareceu esta fase.** Em vez de um download, são vários — um por mês de OS
mais os dois espelhos —, cada link válido por 5 minutos, com repedido para o que faltar.
Foi o preço de não ter o backup diário crescendo para sempre; a conta chega aqui.

### Um ponto de máquina nova que já está resolvido

Quando o cliente troca de PC, os dados de licença guardados no banco estão criptografados
com a identificação da máquina antiga. Restaurados como estão, o sistema acusaria cópia
não autorizada — a restauração legítima e a pirataria passariam pelo mesmo teste.

A solução não afrouxa a proteção: a máquina nova faz o cadastro normal e recebe a
identificação dela própria; a restauração traz todos os dados **menos** a linha de
licença, que fica sendo a da máquina nova. O servidor, por sua vez, já libera o download
para qualquer máquina autenticada da mesma licença — o backup pertence ao cliente, não ao
equipamento.

---

## 6. Limites conhecidos

Registrados de propósito. Nenhum é impeditivo; todos são melhores conhecidos do que
descobertos.

| Limite | Efeito | Situação |
|---|---|---|
| Backup só com o sistema aberto | loja fechada não gera backup | estrutural — não há serviço em segundo plano |
| Teto de 500 MB por pacote | um mês de fotos que passe disso não sobe | com a partição, um mês não chega perto; se chegar, é sinal de volume anormal |
| Uma cópia por pacote, sem versões | não existe "restaurar o de terça" | decisão de custo do servidor |
| Retenção de 90 dias após a licença deixar de estar ativa | cliente que abandona o sistema perde o arquivo após 3 meses | há avisos por e-mail aos 75 e 83 dias; cliente ativo nunca perde |
| Envio automático menor que 50% do anterior é recusado | proteção contra perda de dados em massa | a saída é o botão manual, com mensagem específica na tela |
| Fotos de OS a 1920px | pasta cresce mais rápido do que precisaria | avaliado e mantido: foto de vistoria é prova do estado do equipamento na entrada, e degradar tem custo em discussão com cliente. A partição tirou a urgência |

---

## 7. Situação atual e próximos passos

| Item | Estado |
|---|---|
| Contrato do servidor | fechado e conferido contra o código, não contra a intenção |
| Fase 1 (banco) | plano detalhado pronto; aguarda autorização para começar |
| Fase 2 (fotos) — servidor | implementado em branch, nunca executado |
| Fase 2 (fotos) — ERP | aguarda o servidor entrar em produção |
| Fase 3 (restauração) | documentada, sem responsável |
| Medição do cliente em produção | pendente — decide a prioridade da fase 2 |

### O que falta decidir

**Autorizar o início da fase 1.** Nada nela depende do que está pendente: o backup do
banco funciona contra o servidor de hoje, com as cotas que já existem.

**Quando subir o servidor.** É o caminho crítico da fase 2, e a decisão está condicionada
à separação entre ambiente de teste e produção.

**Medir a pasta de fotos do cliente em operação.** Não muda o desenho — decide se a fase 2
é para este mês ou para o próximo trimestre, e se algum mês isolado se aproxima do teto.

**Dar dono à fase 3.** Não precisa ser agora, mas precisa ter data antes de o backup ser
anunciado ao cliente como garantia.
