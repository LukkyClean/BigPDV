# Renovação de assinatura — o que a API web precisa entregar

Contrato entre o ERP instalado na loja e a `api.startbig.com.br`, para o cliente
renovar a assinatura de dentro do sistema (PIX e cartão).

Escrito a partir do que o ERP **já faz hoje** (`app/services/licenca.py`). O lado
local será construído contra este contrato; a web pode ser feita depois, na
ordem que convier.

---

## 1. A parte que já existe — não construa de novo

O ERP **já sabe receber "mais 30 dias"**. De hora em hora, `renovar_licenca_background`
chama `POST /licenca/validar` e grava o que vier:

```python
licenca.token             = resposta.token
licenca.data_vencimento   = resposta.dataVencimento    # ← o desbloqueio entra aqui
licenca.proxima_validacao = resposta.proximaValidacaoEm
licenca.grace_period      = resposta.gracePeriodDias
```

**Consequência prática:** assim que a web mudar a `dataVencimento` no banco dela,
o sistema da loja destrava sozinho. Não existe — e não deve existir — um endpoint
de "liberar cliente". A liberação é efeito de `/licenca/validar` já responder com
a data nova.

O que falta na web é apenas **cobrar** e **avisar que caiu**.

---

## 2. O fluxo completo

| # | Quem | O quê |
|---|------|-------|
| 1 | ERP | Pede a cobrança (`POST /licenca/renovacao/cobranca`) |
| 2 | Web | Cria a cobrança no PSP e devolve o copia-e-cola |
| 3 | ERP | Mostra o QR na tela (gera a imagem a partir do copia-e-cola) |
| 4 | Cliente | Paga pelo banco |
| 5 | PSP | Webhook para a web |
| 6 | **Web** | **Estende a licença** e **depois** marca a cobrança como `PAGA` |
| 7 | ERP | Consulta o status a cada ~5s e vê `PAGA` |
| 8 | ERP | Chama `POST /licenca/validar` (endpoint que já existe) |
| 9 | ERP | Grava a `dataVencimento` nova e destrava o sistema |

O passo 6 é o único ponto onde a ordem importa — ver invariante **I2**.

---

## 3. Endpoints a implementar

Padrão dos existentes, para não destoar: JSON em **camelCase**, datas em
**ISO-8601 UTC**, valores monetários em **centavos (inteiro)**.

### 3.1 `GET /licenca/planos`

Para o app mostrar preço e período sem nada chumbado no código.

```json
{
  "planos": [
    {
      "codigo": "MENSAL",
      "nome": "Mensal",
      "valorCentavos": 9900,
      "dias": 30,
      "metodos": ["PIX", "CARTAO"]
    }
  ]
}
```

### 3.2 `POST /licenca/renovacao/cobranca`

Cria a cobrança PIX.

**Request**

```json
{
  "chave": "<chave de ativação descriptografada>",
  "hwid": "<hardware id da máquina>",
  "metodo": "PIX",
  "plano": "MENSAL"
}
```

**Response `201`**

```json
{
  "cobrancaId": "b3f1...",
  "metodo": "PIX",
  "pixCopiaECola": "00020126580014BR.GOV.BCB.PIX...",
  "qrCodeBase64": null,
  "valorCentavos": 9900,
  "descricao": "StartBig — plano mensal",
  "diasAdicionados": 30,
  "expiraEm": "2026-08-22T14:30:00Z"
}
```

> **Só o `pixCopiaECola` é obrigatório.** O app já desenha o QR a partir do BR Code
> (`PixQrCode.vue`), então `qrCodeBase64` pode vir `null` para sempre. Se um dia vier
> preenchido, o app usa a imagem do servidor.

**Erros** — `{ "codigo": "...", "mensagem": "..." }` com HTTP 4xx:

| codigo | Quando |
|---|---|
| `PLANO_INVALIDO` | plano não existe |
| `LICENCA_NAO_ENCONTRADA` | chave/hwid não batem |
| `LICENCA_BLOQUEADA` | bloqueio administrativo — pagar não resolve |
| `METODO_INDISPONIVEL` | PIX ainda não habilitado nesta conta |

### 3.3 `GET /licenca/renovacao/cobranca/{cobrancaId}`

Consulta de status. Query: `chave`, `hwid`.

**Response `200`**

```json
{
  "cobrancaId": "b3f1...",
  "status": "PENDENTE",
  "pagoEm": null,
  "dataVencimento": null
}
```

`status` ∈ `PENDENTE` | `PAGA` | `EXPIRADA` | `CANCELADA`.

Quando `PAGA`, devolva também `pagoEm` e a `dataVencimento` nova — só para o app
poder dizer "renovado até 21/09" imediatamente; a fonte da verdade continua sendo
o `/licenca/validar`.

### 3.4 `POST /licenca/renovacao/checkout` — cartão

O cartão **já funciona na web**, então o app não processa nada: ele abre o
navegador na URL que este endpoint devolver.

**Request**

```json
{ "chave": "...", "hwid": "...", "metodo": "CARTAO", "plano": "MENSAL" }
```

**Response `201`**

```json
{ "url": "https://startbig.com.br/checkout/b3f1...", "expiraEm": "2026-08-22T14:30:00Z" }
```

A URL precisa já carregar a identidade da licença — o cliente não pode ter que
descobrir qual conta é a dele depois de clicar. Se o checkout atual não aceitar
parâmetro, uma URL fixa resolve por enquanto; o app só chama `openUrl()`.

---

## 4. Invariantes — o que não pode ser quebrado

**I1. A cobrança tem que funcionar com a licença VENCIDA.**
É o caso principal: quem precisa pagar é justamente quem está vencido. Se os
endpoints de cobrança exigirem licença válida, o cliente fica preso sem conseguir
pagar. Só `LICENCA_BLOQUEADA` (bloqueio administrativo) deve recusar.

**I2. Estenda a licença ANTES de marcar `PAGA`.**
O app trata `PAGA` como "pode revalidar agora". Se a cobrança virar `PAGA` antes
de a `dataVencimento` mudar, o app chama `/licenca/validar`, recebe a data velha,
mostra "ainda vencido" e o cliente que acabou de pagar vê o sistema travado.

**I3. Criar cobrança duas vezes não pode gerar duas cobranças.**
Dois cliques, ou o operador reabrindo a tela, devem receber **a mesma** cobrança
pendente. Chave de idempotência sugerida: `licencaId + plano + status=PENDENTE`.

**I4. Nunca confie no cliente para estender a licença.**
O ERP local não escreve `data_vencimento` por conta própria — só grava o que vem
assinado do servidor. Se algum endpoint aceitar "estender" a pedido do app,
renovar assinatura vira "editar o SQLite".

**I5. Só marque `PAGA` depois da confirmação do PSP.**
Nunca com base em o cliente ter clicado "já paguei".

**I6. Datas em ISO-8601 UTC** (`2026-08-22T14:30:00Z`). O ERP assume UTC quando a
data vem sem fuso.

**I7. Valores em centavos, inteiros.** É o padrão do sistema inteiro.

**I8. Responda em menos de 5 segundos.** O app usa timeouts curtos com o servidor
de licença. Se a criação no PSP for lenta, crie primeiro o registro local e
devolva o copia-e-cola quando tiver — não segure a resposta.

**I9. `chave` + `hwid` são a credencial.** Mesmo par usado pelos endpoints já
existentes. Vale rate limit por licença.

---

## 5. O que o ERP faz de cada lado

**Já pronto (não depende da web):**

- Receber e gravar `dataVencimento` nova → destrava sozinho
- Desenhar QR a partir de um copia-e-cola PIX (`pixBrCode.ts`, `PixQrCode.vue`)
- Abrir o navegador numa URL (`openUrl`)

**Será construído contra este contrato:**

- Tela de cobrança (Cartão | PIX), só para o master
- Estado "somente renovação": com a licença vencida o usuário **loga**, mas o
  sistema fica inativo e apenas a cobrança funciona
- Proxy local dos três endpoints acima + revalidação forçada
- Degradação: enquanto a web responder 404, o botão PIX aparece como
  indisponível — sem tela quebrada

---

## 6. Em aberto — decidir na web

1. **URL do checkout de cartão** — endpoint `3.4` ou URL fixa?
2. **Preço e plano** — só mensal? qual valor em centavos?
3. **PSP do PIX** — Mercado Pago, Asaas, Efí? (não muda nada no ERP; só na web)
4. **Trial** — o `GET /licenca/status` já tem o campo `trial`, hoje nunca
   preenchido. Se a web passar a mandar, o app pode tratar quem nunca assinou
   diferente de quem está renovando.
