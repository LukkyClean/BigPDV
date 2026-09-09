# Plano: fazer a NF-e sair de verdade

Documento de trabalho, escrito em 09/09/2026 a partir de dois sintomas reais na
loja e da leitura do código. A última seção é a que vai para o time do servidor
web.

Arquitetura, para não perder o fio:

```
ERP (FastAPI) → api.startbig.com.br → Focus NFe → SEFAZ
```

---

## 1. O que aconteceu, e por quê

### Sintoma A — "preenchi a IE e o aviso continua"

**Não é falha de gravação.** `indicador_ie` e `inscricao_estadual` são campos
diferentes, e o que está vazio é o primeiro. O backend salva os dois (o
`update_empresa` faz `setattr` genérico sobre `model_dump(exclude_unset=True)`).

O que está errado é tudo em volta:

1. A mensagem diz *"Acesse Configurações da Empresa > Dados Fiscais"* — e o
   campo está na MESMA tela, três centímetros acima do aviso. O texto foi
   escrito quando o aviso só existia no Centro Fiscal.
2. "Inscrição Estadual" e "Indicador de IE" são nomes quase iguais para coisas
   diferentes, sem uma linha de explicação. Quem não é contador erra.
3. O card mostra a frase da pendência, mas não leva ao campo.

Ou seja: o dado que falta é real, e a tela é que não ajuda a preencher.

### Sintoma B — "enviei o certificado e continua Não configurado"

Duas camadas, e as duas são defeito nosso.

**B1. A tela nunca recarrega.** `FiscalConfiguracoesView.vue` monta o modal
assim:

```vue
<FiscalCertificadoModal v-model:is-open="showCertificadoModal" />
```

O modal emite `uploaded` depois do upload — e **ninguém escuta**. Nada invalida
`fiscalKeys.configuracao()`, que tem `staleTime` de 30s. Mesmo com o `commit`
corrigido em `8960ee8`, o card continua dizendo "Não configurado" até o operador
sair da tela e voltar depois do stale. O upload funcionou; a tela mentiu.

**B2. O certificado não vai a lugar nenhum.** Em `services/empresa.py`, o passo
"5. Envio para a API Online" é literalmente:

```python
# 5. Envio para a API Online -- AINDA MOCK.
import time
time.sleep(0.5)
```

O `.pfx` é validado localmente (senha, validade, CNPJ do subject), os metadados
são gravados, e o arquivo morre na memória do processo. Não existe método de
certificado no `FiscalClientStartBig`, e o
`docs/contrato-api-fiscal-plataforma.md` não cita a palavra "certificado" em
nenhuma linha — nunca foi combinado com o servidor.

### Sintoma C — o que ninguém viu ainda: MEI não consegue emitir certo

`REGIME_TRIBUTARIO_OPTIONS` (frontend) oferece três opções:

```
Simples Nacional | Simples Nacional (Excesso de Sublimite) | Regime Normal
```

Não há **MEI**. E `crt_efetivo` dá prioridade ao rótulo do regime: só cai na
natureza jurídica quando o regime está vazio. Então, com "Simples Nacional"
escolhido, o CRT sai **1** — mesmo que a Natureza Jurídica esteja marcada como
MEI.

A SEFAZ exige **CRT 4** para MEI desde a NT 2021.004 (layout 4.00). A Focus usa
o mesmo domínio (`regime_tributario`: 1=Simples, 2=Simples com excesso,
3=Normal, **4=MEI**). Hoje, **um MEI não tem como sair com o CRT certo por esta
tela** — e a BIGTEC é MEI.

---

## 2. Como os sistemas profissionais fazem

Pesquisado para não inventarmos um caminho próprio.

**Bling, Tiny, Omie e ContaAzul** fazem todos a mesma coisa: o lojista sobe o
`.pfx` **dentro do próprio sistema**, junto com a senha, no painel de
configurações fiscais. O sistema é quem repassa o certificado ao emissor. O
lojista nunca abre a conta do gateway.

Conclusão: **o card do nosso Centro Fiscal está certo no conceito.** Ele promete
exatamente o que o mercado faz. O que falta é o cano por trás dele.

**A Focus** (nosso gateway, via plataforma) recebe assim:

```
POST https://api.focusnfe.com.br/v2/empresas
Authorization: Basic <token>:        (token como usuário, senha em branco)

{
  "nome": "...", "cnpj": "12345678000123",
  "regime_tributario": 1,             // 1|2|3|4 — 4 = MEI
  "inscricao_estadual": "...", "inscricao_municipal": "...",
  "email": "...",
  "logradouro": "...", "numero": "...", "bairro": "...",
  "municipio": "...", "uf": "PR", "cep": "80210000",
  "arquivo_certificado_base64": "MIIj4gIBAzCCI54GCSqGSIb3...",
  "senha_certificado": "...",
  "habilita_nfe": true
}
```

Resposta relevante: `id`, `certificado_valido_ate`, `habilita_nfe`,
`token_producao`.

Dois detalhes que mudam o desenho:

- A API de empresas da Focus **opera só em produção** (há `dry_run=1` para
  simular sem persistir). Ambiente de homologação × produção é decisão **por
  emissão**, não do cadastro.
- `habilita_nfe` precisa estar `true`. Empresa cadastrada mas não habilitada não
  emite — e é um candidato direto à mensagem "CNPJ do emitente não autorizado".

E o payload de emissão da Focus é **plano**, com a `ref` na query string:

```
POST /v2/nfe?ref=venda-123
{ "cnpj_emitente": "...", "nome_emitente": "...", "logradouro_emitente": "...",
  "municipio_emitente": "...", "uf_emitente": "...", "cep_emitente": "...",
  "inscricao_estadual_emitente": "...", "regime_tributario_emitente": 1,
  "nome_destinatario": "...", "cpf_destinatario": "...",
  "items": [ { "numero_item": 1, ... } ] }
```

O ERP manda **aninhado** (`emitente.cnpj`, `destinatario.cpf`,
`totais.valor_total`) e a `ref` **no corpo**. Alguém tem que traduzir — ver §4.

---

## 3. Plano do lado do ERP

### Fase 0 — parar de mentir (nada depende da plataforma) — **FEITA**

Tudo aqui é defeito de tela e sai sozinho.

| # | O quê | Onde |
|---|---|---|
| 0.1 | A view escutar `@uploaded` e invalidar `fiscalKeys.configuracao()` | `FiscalConfiguracoesView.vue` |
| 0.2 | Trocar o texto "Acesse Configurações da Empresa > Dados Fiscais" — o campo já está na tela | `validators.py:56`, `verificacao_fiscal.py:87` |
| 0.3 | Botão de voltar no Centro Fiscal / tela do certificado | `FiscalLayout.vue` |
| 0.4 | `mock_ativo` mente: a resposta calcula `FISCAL_MOCK_ENABLED or ambiente == 2`, mas a factory só olha `FISCAL_MOCK_ENABLED`. A tela mostra "(mock)" em homologação enquanto o envio é **real** | `endpoints/fiscal.py`, `FiscalAmbienteBadge.vue:31` |
| 0.5 | Ajuda nos campos: uma linha explicando Indicador de IE (1 contribuinte, 2 isento, 9 não contribuinte) e a diferença para a Inscrição Estadual | `TaxDataSection.vue` |
| 0.6 | Recolocar `check:sidecar` no `npm run build` — saiu em `ad032ff` (22/07), dentro de um commit sobre o formulário de vistoria | `frontend/package.json` |

### Fase 1 — o cadastro que a Focus exige — **FEITA** (`5e4f934`)

Sem isto, o cadastro passa no nosso gate e a Focus recusa.

- **1.1 MEI no seletor de regime.** Acrescentar `MEI` a
  `REGIME_TRIBUTARIO_OPTIONS` e ao `_ROTULO_PARA_CRT` (já mapeado). Decidir a
  migração dos MEIs que hoje estão como "Simples Nacional" — não dá para
  adivinhar pelo cadastro, então é pergunta na tela, não migration cega.
- **1.2 CNPJ só dígitos na saída.** `_montar_emitente` manda `empresa.documento`
  cru. Normalizar na borda (nunca no banco).
- **1.3 Bloquear emissão de emitente sem CNPJ.** Se `documento` tem 11 dígitos,
  é CPF: hoje ele vai no campo `cnpj` e a recusa vem de longe, com mensagem que
  não ajuda.
- **1.4 Unificar as duas implementações de `verificar_emitente`**
  (`fiscal/validators.py` e `verificacao_fiscal.py`). Hoje contam a mesma coisa
  com textos diferentes; o card da Empresa usa uma e o gate usa a outra.

### Fase 2 — o cano do certificado — **FEITA do nosso lado**

O ERP já faz a chamada. Falta a rota do outro lado (§4.1) — até ela existir, o
404 volta como *indisponível* e o cadastro fica `VALIDADO_LOCAL`. No dia em que
a rota subir, **o mesmo código passa a gravar `CONECTADO_NUVEM` sem instalador
novo**.

⚠️ A correção do `commit` (`8960ee8`) tinha piorado a mentira: antes o upload não
gravava e o card ficava "Não configurado", acidentalmente honesto; depois passou
a gravar `CONECTADO_NUVEM` com o certificado parado na máquina. Agora existem
três estados, e o card mostra os três.

- **2.1** Trocar o `time.sleep(0.5)` por uma chamada real ao
  `POST /erp/fiscal/certificado`, mandando o `.pfx` em base64 + senha.
- **2.2** Guardar da resposta o que a plataforma devolver: validade, CNPJ
  conferido e status. **Nunca** guardar a senha nem o arquivo — hoje já não
  guardamos, e isso se mantém.
- **2.3** O card passa a refletir o estado remoto, não o local.
- **2.4** Falha de envio precisa aparecer como falha. Hoje o único jeito de o
  upload falhar é senha errada.

### Fase 3 — enxergar o outro lado — **FEITA**

- **3.1** Expor `consultar_config()` numa rota nossa e mostrar no Centro Fiscal
  o que a plataforma enxerga: ambiente, `tokenConfigurado`, `cscConfigurado`,
  `certificadoStatus`, `pendencias[]`.
- **3.2** Mostrar lado a lado **"CNPJ que o ERP manda" × "CNPJ que a plataforma
  tem"**. É o que encerra a dúvida de quem é o problema, sem abrir chamado.
- **3.3** A chavinha Homologação/Produção passa a exibir o ambiente **da
  plataforma**, não o palpite local — ou some. Hoje ela deixa emitir nota real
  achando que testa.

  Feito assim: o chip do Centro Fiscal mostra o ambiente **da plataforma**
  quando ela responde (e fica vermelho quando os dois discordam), e o seletor no
  modal passou a se chamar "trava deste computador", com um aviso de que mudar
  ali não muda na emissora. O campo local continua existindo porque é ele que
  arma o `emitir_teste`; o que sumiu foi a impressão de que ele decide.

  Achado ao revisar: `FiscalAmbienteBadge.vue` **nunca foi usado** — o chip é
  inline na view. É o componente onde vivia o `(mock)` do item 0.4, então
  aquela correção estava certa e invisível. O componente segue no repositório,
  morto.

### Fase 4 — o que fica para depois

- NF-e a partir de OS (hoje 501). Para oficina e serigrafia, é onde está o
  faturamento.
- NFS-e municipal.
- Reconciliação de numeração e inutilização em produção.

---

## 4. O que a plataforma web tem que fazer

Esta é a seção para o time do servidor.

### 4.1 Rota de certificado — **não existe e é o que trava**

```
POST /erp/fiscal/certificado
Authorization: Bearer <token da licença>

{ "arquivo_base64": "<.pfx em base64>", "senha": "..." }
```

A plataforma deve:

1. Validar o PKCS#12 com a senha e extrair CNPJ e validade.
2. Conferir que o CNPJ do certificado bate com o da ficha da licença. Se não
   bater, **recusar com essa frase** — é o erro mais provável em campo.
3. Criar ou atualizar a empresa na Focus (`POST /v2/empresas`), mandando
   `arquivo_certificado_base64`, `senha_certificado` e `habilita_nfe: true`.
4. Guardar `id`, `token_producao` e `certificado_valido_ate` na
   `EmpresaFiscalConfig`.
5. Responder `{ cnpj, valido_ate, status, habilitado }`.

A senha e o arquivo **não podem ser logados** nem devolvidos.

### 4.2 Tradução do payload — aninhado → plano

O ERP manda `emitente.cnpj`; a Focus quer `cnpj_emitente`. A `ref` vai no nosso
corpo e a Focus a quer na **query string**.

**A tradução tem que ser de vocês**, e não é preguiça nossa: se o ERP falar o
vocabulário da Focus, a plataforma deixa de ser intermediária e trocar de
gateway passa a exigir instalador novo em cada loja. Hoje trocar de gateway é um
deploy de vocês.

Enquanto isso não existe, confiram **de onde o controller lê o CNPJ**. Se for
`payload.cnpj_emitente`, ele recebe `undefined`, compara com a ficha e recusa —
que é exatamente o "CNPJ do emitente não autorizado" que a loja está vendo. O
mapa completo campo a campo está em `contrato-api-fiscal-plataforma.md` §3.

### 4.2b Devolver o CNPJ da ficha no `GET /erp/fiscal/config`

Descoberto ao construir a fase 3. Hoje a resposta traz `ambiente`,
`configurado`, `tokenConfigurado`, `cscConfigurado`, `certificadoStatus` e
`pendencias[]` — mas **não traz o CNPJ que a plataforma tem cadastrado**.

Sem ele, a tela do Centro Fiscal mostra "o CNPJ que este sistema envia" e, do
outro lado, "a plataforma não informa". Justamente a comparação que encerraria a
dúvida do "CNPJ do emitente não autorizado" fica pela metade.

É um campo:

```json
{ "ambiente": 2, "configurado": true, "cnpj": "11222333000181", ... }
```

O ERP já aceita `cnpj` ou `cnpjEmitente`, com ou sem máscara — compara sempre em
dígitos. Enquanto não vier, o campo aparece como "não informado" e **nunca** como
divergência.

### 4.3 Conferências que valem mesmo que 4.2 seja a causa

- **CNPJ na `EmpresaFiscalConfig`: só dígitos, sem máscara.**
- **`habilita_nfe: true` na Focus.** Empresa cadastrada e não habilitada não
  emite.
- **`regime_tributario` = 4 para MEI.** Mandar 1 para um MEI produz nota aceita
  e errada — o pior desfecho.
- **`ambiente`** na ficha (2 = homologação), e certificado/CSC cadastrados para
  esse mesmo ambiente. CSC de homologação não vale em produção.
- **`db:push`** pendente desde 08/09: tabela `idempotencia_fiscal` e coluna
  `cscConfigurado`.
- **Conceder módulo exige a lista completa**: `["FINANCEIRO","NFE"]`. Só
  `["NFE"]` derruba a Gestão Financeira da loja.

### 4.4 Já pedido e ainda aberto (de `contrato-api-fiscal-plataforma.md`)

1. `.passthrough()` / looseObject no schema do payload.
2. Mapear `qrcode` e `url_consulta` na resposta — sem QR Code o cupom não vale.
3. `POST /erp/fiscal/nfce/emitir`.
4. `POST /erp/fiscal/nfe/inutilizar`.
5. Devolver `denegado` como status próprio, em vez de cair no balde `erro`.
6. Responder: o `/licenca/conectar` remoeda o token com os módulos do momento,
   ou devolve o mesmo até `proximaValidacaoEm`? Disso depende a concessão do
   NFE aparecer na loja em 5 minutos ou em 7 dias.

---

## 5. Ordem sugerida

1. ~~**Fase 0**~~ — feita.
2. ~~**Fase 1**~~ — feita (`5e4f934`).
3. ~~**Fase 3**~~ — feita. O Centro Fiscal passou a mostrar o outro lado.
4. **§4.2** do lado de vocês — **é o que trava a emissão hoje**, e é uma leitura
   de código para descobrir de onde o controller lê o CNPJ.
5. **§4.2b** — um campo na resposta do `/config`, e a comparação de CNPJ fecha.
6. ~~**Fase 2**~~ — feita do lado do ERP; espera a §4.1 para deixar de gravar
   `VALIDADO_LOCAL`.

**Do lado do ERP não sobra nada que possamos fazer sozinhos.** Fases 0, 1, 2 e 3
estão implementadas; a 2 só termina com a §4.1, e a fase 4 (NF-e por OS, NFS-e)
é escopo novo, não conserto.

## 6. Fontes

- [Focus NFe — criar empresa](https://doc.focusnfe.com.br/reference/criar_empresa.md)
- [Focus NFe — emitir NF-e](https://doc.focusnfe.com.br/reference/emitir_nfe.md)
- [Focus NFe — vincular certificado A1](https://focusnfe.com.br/blog/como-vincular-o-certificado-digital-modelo-a1-a-empresa-cadastrada/)
- [Certificado A1 em Bling, Tiny e Conta Azul](https://validarcertificadodigital.com.br/blog/certificado-digital-bling-tiny-conta-azul)
- [Instalação do A1 no Bling](https://www.vprmarketing.com.br/como-instalar-o-certificado-digital-a1-no-bling-erp)
