# Backup em nuvem — plano de implementação (lado ERP)

Contrato do servidor: `erp-backup-contrato.md` (repositório da plataforma web).
Este documento cobre **o que o ERP escreve**, não o que o servidor faz.

**Fase 1 — banco.** Fechada, pronta para virar código. É o que está detalhado aqui.
**Fase 2 — imagens.** Depende de duas decisões de fora (ver o fim). Shape conhecido,
implementação não iniciada.

---

## 1. Escopo da fase 1

Entra: envio automático e manual do **banco de dados**, tela de status, histórico.
Não entra: imagens, **restauração**.

A restauração fica de fora por um motivo técnico, não por prazo: trocar o arquivo
SQLite com o engine segurando ele aberto exige derrubar o sidecar e aplicar a troca
antes do `create_all` no boot seguinte. É um projeto à parte, e restauração meia-boca
destrói banco de cliente. Backup sem restauração já entrega valor — o arquivo fica
na nuvem e é recuperável manualmente com suporte.

---

## 2. Arquivos

| Arquivo | O quê |
|---|---|
| `app/db/models/backup_log.py` | novo — tabela de registro |
| `app/db/crud/backup_log.py` | novo — consultas |
| `app/schemas/backup.py` | novo — payloads do contrato + respostas locais |
| `app/services/backup.py` | novo — empacotamento e orquestração |
| `app/api/v1/endpoints/backup.py` | novo — rotas locais |
| `app/api/v1/api.py` | inclui o router |
| `app/core/tarefas.py` | loop + reconciliação no lifespan |
| `alembic/versions/<hash>_backup_log.py` | novo — `down_revision = "e2f3a4b5c6d7"` |
| `test/test_backup.py` | novo |

---

## 3. Tabela `backup_log`

```
id, tipo, origem, status, upload_id, tamanho_bytes, checksum_sha256,
erro_codigo, erro_mensagem, criado_em, enviado_em, confirmado_em
```

`status` é uma máquina de **três** estados, e o do meio é o que importa:

| Estado | Quando é gravado | Por quê |
|---|---|---|
| `EMITIDO` | logo após o `url-upload` responder `ENVIAR` | há uma vaga reservada no servidor |
| `ENVIADO` | assim que o `PUT` devolve 2xx, **antes** do `confirmar` | o arquivo já está no bucket |
| `CONFIRMADO` | após o `confirmar` responder | ciclo fechado |
| `FALHOU` | qualquer erro, ou descarte na reconciliação | |

Sem o `ENVIADO`, a reconciliação no boot não consegue distinguir "morreu durante o
PUT" (nada subiu) de "morreu depois do PUT" (subiu, só o registro se perdeu) — e são
tratamentos opostos. É um campo a mais numa tabela que já seria criada.

**Migration:** guardar por `inspector.has_table("backup_log")`, porque o `create_all`
roda **antes** das migrations no startup (`app/core/tarefas.py`) e a tabela já vai
existir quando a migration rodar. Modelo a seguir: `965c71a2da9a`.

---

## 4. O ciclo, passo a passo

### 4.1 Antes de tudo: `/erp/validar`

O contrato (C.5) recomenda renovar o token **antes** de abrir o ciclo, não no meio.
Elimina a classe inteira de erro "401 no confirmar". Barato: uma chamada.

### 4.2 Consultar `/erp/backup/status`

Três coisas saem daqui, e nenhuma pode ser inferida localmente:

- `planoPermiteBackup` / `codigoBloqueio` — se `false`, aborta e registra. Trial e
  licença vencida não são erro: são estado normal, e a tela mostra o `motivoBloqueio`
  como veio.
- `enviadosHoje` / `limiteDiario` — **é a fonte da verdade do "já fiz hoje"**. O corte
  do dia é 00:00 `America/Sao_Paulo` no relógio do **servidor**; relógio errado em PC
  de loja é comum e as duas contagens divergiriam em silêncio. O `backup_log` local
  serve para diagnóstico e reconciliação, não para decidir cota.
- `tamanhoMaximoBytes` — ler daqui, nunca fixar 500 MB no código.

**Tolerar campos ausentes.** A fase 1 entra em produção **antes** do deploy do servidor,
então `codigoBloqueio` e `tamanhoMaximoBytes` podem não vir na resposta. Sem
`codigoBloqueio`, usar o `motivoBloqueio` como texto; sem `tamanhoMaximoBytes`, assumir
500 MB. Os dois passam a ser aproveitados sozinhos quando o deploy sair.

### 4.3 Empacotar

```
VACUUM INTO '<temp>/banco.sqlite'     → cópia consistente de banco vivo E compactada
zip(banco.sqlite, ZIP_LZMA)           → banco é texto: comprime 5-10x
tamanho = os.path.getsize(zip)        → exato, é o que entra na assinatura
```

`VACUUM INTO` faz numa chamada o que o plano original fazia em duas (`sqlite3.backup`
+ vacuum separado) e não exige lidar com WAL na mão.

O caminho do banco vem de `settings.DATABASE_URL` / `engine.url.database` — **nunca**
chumbado, senão dev e release divergem em silêncio.

Tudo isso roda em `asyncio.to_thread`. O backend é single-worker: zipar no event loop
congela venda, OS e atendimento. Padrão já usado em `tarefas.py:119`.

### 4.4 `url-upload` → `PUT` → `confirmar`

Pedir a URL **imediatamente antes** do PUT: o TTL de 30 min começa a correr na
resposta do `url-upload`, não no início do envio.

No PUT:
- `content=<bytes>`, nunca um file object aberto — file object faz o httpx mandar
  `Transfer-Encoding: chunked` e omitir o `Content-Length`, que **faz parte da
  assinatura**. O sintoma é `403 SignatureDoesNotMatch`, que parece bug de credencial.
- **sem `Authorization`** — vai direto ao bucket.
- mandar os `headers` que vieram na resposta do `url-upload`, como vieram. Não chumbar
  `Content-Type`: se amanhã a assinatura passar a exigir um `x-amz-*`, o envio quebra
  com um 403 sem explicação.

`confirmar` **sempre**, nos dois desfechos. É o que devolve a vaga na hora; sem ele a
vaga fica presa até o cron varrer, em até ~70 min.

---

## 5. Tratamento de erro

Sempre pelo campo `codigo`, nunca por mensagem — os textos são escritos para o usuário
final e vão mudar.

| Situação | O que fazer |
|---|---|
| `PUT` 5xx / timeout | 2-3 tentativas na **mesma URL**, espera crescente. Não gasta vaga. |
| `PUT` 403 `SignatureDoesNotMatch` | **não repetir** — é bug nosso. Registrar e falhar. |
| `PUT` 403 após o TTL | janela estourada: `confirmar ok:false`, tenta no ciclo seguinte |
| `429 BACKUP_LIMITE_DIARIO` | não repetir hoje |
| `403 BACKUP_PLANO_INATIVO` | não repetir; exibir mensagem |
| `409 BACKUP_TAMANHO_SUSPEITO` | automático com <50% do último. Mensagem específica na tela pedindo confirmação manual — o usuário nunca vai deduzir isso sozinho |
| `409 ARQUIVO_AUSENTE` / `TAMANHO_DIVERGENTE`, `503 NAO_CONFIGURADO` | próximo ciclo |
| `401` no `confirmar` | `/erp/validar` e repetir o **mesmo** `uploadId` (idempotente) |

Nunca em loop: falhou, tenta no ciclo seguinte.

---

## 6. Agendamento

**Oportunista, não horário fixo.** O sidecar só roda na máquina servidor
(`lib.rs`, gated por `is_server`) e só com o app aberto — não há serviço do Windows.
Backup marcado para 02:00 nunca acontece: a loja desliga o PC. A regra é "a cada hora,
se o `/status` disser que ainda há vaga e o último sucesso tem mais de 24h, sobe agora".
Na prática roda pouco depois de abrir a loja.

Consequência para a tela: **tirar o campo "horário do backup"** do mock atual. Ele
promete um controle que a arquitetura não entrega.

- `asyncio.Lock` global: o loop e o botão manual podem disparar juntos e queimar as
  duas vagas do dia.
- Loop desligado em dev, senão a máquina de desenvolvimento queima a cota do cliente.

---

## 7. Reconciliação no boot

Roda **cedo e barata**, antes da licença validar. O caminho comum não chama a API.

| Pendência | Ação |
|---|---|
| `ENVIADO` | o arquivo está no bucket: `confirmar ok:true` com o mesmo `uploadId`. Corrige o `copiaAtual`, que senão descreveria a cópia anterior |
| `EMITIDO`, com envio mais novo já confirmado do mesmo tipo | descarte local. Nem toca na API |
| `EMITIDO`, sem envio mais novo, recente | `confirmar ok:false` — devolve a vaga na hora |
| `EMITIDO` antigo | descarte local: o cron do servidor já marcou `FALHOU` |

O critério principal é **"existe envio mais novo confirmado deste tipo"**, não idade.
A idade é rede de segurança. Motivo: a janela de órfã do servidor é derivada do TTL
(`TTL/60 + 30`), então se um dia o TTL subir, qualquer constante de tempo que a gente
chumbe aqui fica errada. O sinal de "outro envio sobrescreveu a chave" — que é o que a
ressalva B.4 realmente protege — está no `backup_log` local, com precisão.

---

## 8. Endpoints locais

Todos **Master-only** na matriz de permissões. O de restauração, quando existir,
entrega uma URL assinada com o banco inteiro da empresa: CPF, clientes, faturamento.

| Rota | O quê |
|---|---|
| `GET /api/v1/backup/status` | repassa o `/status` + o último registro local |
| `POST /api/v1/backup/executar/banco` | dispara manual (`origem: "MANUAL"`) |
| `POST /api/v1/backup/testar` | verificação não-destrutiva — ver abaixo |
| `GET /api/v1/backup/historico` | lê o `backup_log` |

### 8.1 `POST /backup/testar` — a verificação que vale mais que a restauração

Baixa pelo `url-download`, abre o arquivo num temporário, roda `PRAGMA integrity_check`,
confere que as tabelas esperadas existem e têm linhas, **descarta**. Não encosta no banco
vivo, não gasta cota de upload, não tem passo destrutivo.

Valida a cadeia inteira de ponta a ponta — empacotamento, envio, armazenamento, download,
integridade — e é a diferença entre "o servidor respondeu 200" e "o arquivo que está lá
abre". Rodando uma vez por mês, o cliente descobre que o backup está quebrado num dia
comum, e não no dia em que o HD morreu.

Nota: o `checksumSha256` guardado pelo servidor é o hash do **manifesto**, não dos bytes
do zip — foi assim de propósito, para o dedupe ser estável. Ele não serve para verificar
download. Para o banco isso não faz falta: o `PRAGMA integrity_check` prova mais do que um
hash provaria (um zip pode ter hash correto e conter um banco corrompido desde a origem).
Para imagens, a verificação é o `manifest.json` dentro do próprio pedaço.

---

## 9. Frontend

`configuracoes/.../backup-dados/BackupDados.vue` é **casca 100% estática** hoje:
o toggle é uma `div`, frequência e horário são texto fixo, os três botões estão
`disabled`. Precisa: service, TanStack Query no `/status`, botão manual **desabilitado
quando `enviadosHoje >= limiteDiario`** (com o motivo escrito — nunca deixar o usuário
clicar e comer um 429), e o histórico.

Ao mostrar o histórico, deixar explícito que é **diário de eventos, não lista de
restauração**. Existe uma cópia por tipo, e só. Prometer escolha de versão que não
existe é o pior defeito possível numa tela de backup.

---

## 10. Testes (`test/test_backup.py`)

Servidor mockado (`respx`). Nenhum teste toca a API real — a cota é de 2/dia e é do
cliente.

1. `VACUUM INTO` produz banco íntegro (`PRAGMA integrity_check`) com escrita concorrente
2. fluxo feliz: status → url-upload `ENVIAR` → PUT → confirmar `ok:true`
3. o PUT sai com `Content-Length` exato, **sem** `Authorization`, com os headers do passo 2
4. PUT 500 → `confirmar ok:false`, linha `FALHOU`, vaga devolvida
5. `403 SignatureDoesNotMatch` → **não** repete
6. `429` → não repete no mesmo dia
7. `409 TAMANHO_SUSPEITO` → mensagem específica
8. `401` no confirmar → valida e repete o mesmo `uploadId`
9. reconciliação: `ENVIADO` vira `confirmar ok:true`; `EMITIDO` com envio mais novo é
   descarte local sem tocar na API
10. lock: manual durante o automático não abre segundo ciclo

---

## 11. Fase 2 — imagens

Direção definida pelo lado web, implementação do servidor **ainda não feita**:

```
produtos.zip        espelho, chave fixa, sobrescrito
os-2026-06.zip      mês fechado — sobe uma vez, depois é PULAR
os-2026-07.zip      mês corrente — único que sobe todo dia
```

O envio diário para de crescer com a idade da instalação. Notas do lado ERP:

- **O espelho não é só `produtos/`.** As pastas são `produtos`, `empresa`, `usuarios` e
  `ordens-servico`. `empresa` (logo) e `usuarios` (avatar) são pequenas e mutáveis —
  vão no espelho junto com produtos. Só `ordens-servico` é write-once.

  ⚠ A D.1 do contrato descreve `imagens.zip` como "fotos de **produto** (catálogo)".
  Seguir isso ao pé da letra deixaria **o logo da empresa e os avatares sem backup
  nenhum** — e o logo sai no cupom e no A4 impresso. O servidor não olha o conteúdo do
  zip, então não há mudança de contrato: é decisão nossa, e é esta.
  `imagens.zip` = `produtos` + `empresa` + `usuarios`.
- **Particionar pela `data_criacao` da linha em `ordem_servico_fotos`**, não pelo mtime
  do arquivo: copiar a pasta entre máquinas reseta mtime e jogaria o histórico inteiro
  num mês só. Fallback para mtime em arquivo órfão.
- **Não particionar pela data da OS**: o sistema permite reabrir OS, e foto anexada hoje
  a uma OS de maio reabriria um mês fechado.
- Partição é **transporte, não armazenamento**: os caminhos dentro do ZIP continuam
  `ordens-servico/<id>/<arquivo>`. Restaurar é extrair os N zips sobre a mesma pasta.
- `ZIP_STORED` para imagens: já são WebP, deflate rende 1-3% e custa CPU à toa.
- Checksum sobre **manifesto** (caminho + tamanho + mtime em segundos inteiros,
  ordenado), nunca sobre os bytes do ZIP. O servidor trata o campo como opaco. Ganho:
  o checksum fica pronto antes de zipar, então comparando com
  `copiaAtual.<pedaço>.checksumSha256` dá para pular sem zipar nada.

### ⚠ Buraco em aberto: a virada do mês

O mês corrente sobe todo dia; o fechado nunca mais. Na virada, o último upload de julho
aconteceu **durante** julho e não contém as fotos tiradas depois dele. Se em 1º de agosto
o ERP passa a considerar julho fechado, essas fotos **nunca chegam à nuvem** — e o
`PULAR` esconde isso, porque o checksum de referência é o do upload incompleto.

Regra necessária: um mês só é considerado fechado depois de **um envio bem-sucedido
realizado já dentro do mês seguinte**. Precisa valer também quando a loja fica dias sem
abrir o sistema na virada.

Corolário: se pedaço fechado nunca é reenviado, também nunca é reparado. Precisa de uma
saída manual ("reenviar histórico") para o caso de o objeto no bucket corromper.

### Depende de fora

1. Servidor implementar a partição (coluna `periodo`, `url-download` devolvendo N,
   `copiaAtual` virando lista, `DIAS_FORCA_IMAGENS` só no pedaço corrente, cota separada
   para primeiro envio de pedaço fechado).
2. O tamanho real de `uploads/` no cliente em produção — decide se isso é para este mês
   ou para o trimestre.

---

## 12. Pendências gerais

- `limiteDiario.imagens: 2` no `/status` real, após o deploy do servidor.
- Copiar `erp-backup-contrato.md`, `erp-portas-de-entrada.md` e `integracao-erp-local.md`
  para `backend-fastapi/docs/`.
