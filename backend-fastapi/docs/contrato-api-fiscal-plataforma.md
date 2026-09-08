# Contrato da API fiscal — o que o ERP envia e espera

Documento para o time do servidor web (`api.startbig.com.br`). Tudo aqui foi
extraído do código do ERP, não de memória: os payloads são a saída real de
`app/services/fiscal/payload_builder.py`.

Arquitetura: **ERP → api.startbig.com.br → Focus NFe → SEFAZ**.

Autenticação: `Authorization: Bearer <token JWT da licença>` em todas as chamadas.

---

## 1. O que trava hoje, em ordem de gravidade

### 1.1 O Zod da emissão poda os campos fiscais — BLOQUEIA TUDO

`fiscal.controller.ts` valida o payload com um `z.object` sem `passthrough`.
Zod **remove silenciosamente** todo campo não declarado. O schema atual conhece
só um subconjunto, e o que ele descarta inclui campos **obrigatórios** da NF-e.

Consequência: mesmo com a rota existindo, a SEFAZ rejeita por falta de campo
obrigatório — e a mensagem faz parecer que o ERP montou a nota errada.

**Campos que hoje são descartados e sem os quais a nota não é autorizada:**

| campo | onde | por que é obrigatório |
|---|---|---|
| `emitente.inscricao_estadual` | emitente | IE do emitente é obrigatória na NF-e |
| `emitente.codigo_regime_tributario` | emitente | é o CRT; decide CSOSN × CST |
| `items[].icms_situacao_tributaria` | item | CST/CSOSN do ICMS |
| `items[].icms_origem` | item | origem da mercadoria (0–8) |
| `items[].pis_situacao_tributaria` | item | CST do PIS |
| `items[].cofins_situacao_tributaria` | item | CST do COFINS |
| `items[].unidade_comercial` | item | unidade (UN, KG, CX…) |
| `formas_pagamento[]` | raiz | grupo `pag` é obrigatório desde a NF-e 4.0 |
| `presenca_comprador` | raiz | `indPres` |
| `finalidade_emissao` | raiz | `finNFe` |
| `consumidor_final` | raiz | `indFinal` |
| `numero`, `serie` | raiz | numeração é controlada pelo ERP |
| `totais.*` | totais | base de cálculo e ICMS total |

**Correção sugerida:** `.passthrough()` no schema de `payload`, validando só o
que a plataforma realmente precisa ler (hoje: `emitente.cnpj`, para a
conferência contra a config). O resto é repasse para a Focus — validar de novo
aqui só cria um segundo lugar para desatualizar.

### 1.2 NFC-e não existe

Sem `POST /erp/fiscal/nfce/emitir`, sem mapeamento de `qrcode`. O ERP tem a
emissão, a impressão em ESC/POS e a reimpressão prontas, e todas ficam inertes.

### 1.3 Inutilização não existe

Sem `POST /erp/fiscal/nfe/inutilizar`. O ERP tem a tela e o controle de gaps de
numeração prontos.

---

## 2. Rotas

| método | rota | estado | corpo |
|---|---|---|---|
| POST | `/erp/fiscal/nfe/emitir` | existe | `{ref, payload}` |
| POST | `/erp/fiscal/nfce/emitir` | **falta** | `{ref, payload}` |
| GET | `/erp/fiscal/nfe/consultar?ref=` | existe | — |
| POST | `/erp/fiscal/nfe/cancelar` | existe | `{ref, justificativa}` |
| POST | `/erp/fiscal/nfe/inutilizar` | **falta** | `{ref, payload}` |
| GET | `/erp/fiscal/nfe/consumo` | existe | — (o ERP ainda não usa) |

---

## 3. Payload da NF-e (modelo 55)

Saída real do construtor, para uma emissão de teste em homologação:

```json
{
  "natureza_operacao": "VENDA DE MERCADORIA",
  "tipo_documento": 1,
  "finalidade_emissao": 1,
  "consumidor_final": 1,
  "presenca_comprador": 1,
  "numero": 1,
  "serie": 1,
  "emitente": {
    "cnpj": "12345678000199",
    "razao_social": "LOJA DE INFORMATICA LTDA",
    "nome_fantasia": "Loja Info",
    "inscricao_estadual": "123456789",
    "inscricao_municipal": null,
    "codigo_regime_tributario": 3,
    "regime_tributario": "Lucro Presumido",
    "endereco": {
      "logradouro": "RUA DAS FLORES", "numero": "100", "complemento": "SALA 2",
      "bairro": "CENTRO", "cidade": "SAO PAULO", "uf": "SP", "cep": "01001000"
    }
  },
  "destinatario": { "cpf": "00000000000", "nome": "..." },
  "items": [
    {
      "numero_item": 1,
      "codigo_produto": "TESTE001",
      "descricao": "...",
      "ncm": "00000000",
      "cfop": "5102",
      "unidade_comercial": "UN",
      "quantidade_comercial": 1.0,
      "valor_unitario_comercial": 1.0,
      "valor_bruto": 1.0,
      "icms_origem": "0",
      "icms_situacao_tributaria": "102",
      "codigo_barras_comercial": "SEM GTIN",
      "unidade_tributavel": "UN",
      "codigo_barras_tributavel": "SEM GTIN"
    }
  ],
  "formas_pagamento": [ { "forma_pagamento": "01", "valor_pagamento": 1.0 } ],
  "totais": {
    "valor_produtos": 1.0, "valor_desconto": 0.0, "valor_frete": 0.0,
    "valor_seguro": 0.0, "valor_outras_despesas": 0.0,
    "icms_base_calculo": 0.0, "icms_valor_total": 0.0, "valor_total": 1.0
  }
}
```

Numa venda real aparecem ainda, conforme o caso: `icms_aliquota`,
`icms_base_calculo`, `icms_valor`, `icms_modalidade_base_calculo`,
`pis_aliquota_porcentual`, `pis_base_calculo`, `pis_valor`,
`cofins_aliquota_porcentual`, `cofins_base_calculo`, `cofins_valor`,
`ipi_situacao_tributaria`, `ipi_codigo_enquadramento`, `modalidade_frete`,
`transportador`, `local_destino`, e o `destinatario` completo com endereço.

Nós já **expurgamos nulos** antes de enviar: nó vazio é rejeição na hora.

---

## 4. Payload da NFC-e (modelo 65)

Mesmo formato da NF-e, mais:

| campo | observação |
|---|---|
| `modelo` | `65` |
| `csc_id` | ID do CSC (ex.: `"000001"`) |
| `csc_token` | **SEGREDO.** É com ele que se monta o QR Code |
| `valor_troco` | troco em dinheiro |
| `presenca_comprador` | só `1` (presencial) ou `4` (entrega a domicílio) |
| `destinatario` | **opcional** — a maioria das vendas de balcão não tem CPF |

⚠️ **`csc_token` não pode entrar em log.** Vazado, permite forjar QR Code em
nome da loja. O ERP já o censura nos próprios logs (`_CHAVES_SENSIVEIS` em
`client_startbig.py`); o servidor precisa fazer o mesmo.

**Alternativa melhor, se quiserem:** guardar o CSC na `EmpresaFiscalConfig`,
junto do `focusEmpresaToken`, e parar de recebê-lo do ERP. Menos segredo em
trânsito, um lugar só para configurar. Se seguirem por aí, avisem que a gente
tira do payload.

---

## 5. Payload da inutilização

```json
{ "modelo": 55, "serie": 1, "ano": 2026,
  "numero_inicial": 10, "numero_final": 12,
  "justificativa": "..." }
```

---

## 6. Resposta

O ERP aceita duas grafias por campo (a da Focus e a normalizada). O que a
plataforma devolve hoje **bate**, com uma falta:

| campo | aceito pelo ERP como | hoje |
|---|---|---|
| `status` | `autorizado` / `processando` / `cancelado` / outro | ✅ |
| `chave_acesso` | `chave_acesso`, `chave_nfe` | ✅ |
| `protocolo` | `protocolo`, `numero_protocolo` | ✅ |
| `numero`, `serie` | — | ✅ |
| `url_pdf` | `url_pdf`, `caminho_danfe` | ✅ |
| `url_xml` | `url_xml`, `caminho_xml_nota_fiscal` | ✅ |
| `codigo_sefaz` | `codigo_sefaz`, `status_sefaz` | ✅ |
| `mensagem_sefaz` | `mensagem_sefaz`, `message` | ✅ |
| `qrcode` | `qrcode`, `qrcode_url` | ❌ **falta** |
| `url_consulta` | `url_consulta`, `url_consulta_nf` | ❌ **falta** |

Sem `qrcode`, o cupom da NFC-e sai sem QR Code — e cupom sem QR Code não vale.

**Sobre `denegado`:** hoje ele cai no balde `erro`. São coisas diferentes —
denegada é decisão da SEFAZ sobre o contribuinte, e o lojista precisa saber
disso. Se puderem devolver `denegado` como status próprio, o ERP passa a
distinguir.

---

## 7. Idempotência

Confirmado: `X-Idempotency-Key` é ignorado, e quem protege é a **`ref`**.

O ERP está alinhado a isso:

- A ref é **estável por venda**: `venda-{numero_venda}`, `nfce-{numero_venda}`.
- Reemissão usa ref nova (`venda-123-retry-45`) — e só é permitida sobre
  documento **confirmadamente** rejeitado ou denegado.
- Falha de comunicação **nunca** vira rejeição: o documento fica
  `INDETERMINADA`, que não é reemitível, até a reconsulta resolver.
- Formato: só `A-Za-z0-9._-`, bem abaixo de 50 caracteres.

Podem manter o header ignorado; não dependemos dele.

Sobre a janela sem lock entre a consulta e o POST: para nós está de bom
tamanho, já que a Focus trata `ref` como única. Se quiserem fechar, um lock por
`(licencaId, ref)` resolveria.

---

## 8. Ambiente

Decidido pela plataforma, por cliente (`EmpresaFiscalConfig.ambiente`), e o ERP
não manda nada — está correto assim.

⚠️ **Ponto de atenção operacional:** o ERP tem uma chave "Homologação/Produção"
na tela, que hoje só trava a emissão **localmente**. Um lojista pode ver
"Homologação" na tela enquanto a plataforma está em produção, e emitir nota
real achando que testava.

Duas saídas, e qualquer uma serve:
1. A plataforma devolver o ambiente vigente em alguma resposta (o `/consumo`
   serviria), para o ERP exibir a verdade em vez do palpite local; ou
2. Nós escondermos essa chave e passarmos a exibir "definido pela plataforma".

Digam qual preferem que eu ajusto do nosso lado.

---

## 9. Módulo NFE na licença

Confirmado: `modulos` é array de strings dentro do JWT RS256.

- `FINANCEIRO` é base e entra sozinho.
- `NFE` precisa ser vinculado ao plano ou concedido como extra.
- O ERP **nega por padrão** para NFE: licença sem resposta ou com lista vazia
  não libera. Para os demais módulos, lista vazia libera (regra antiga).

**Pergunta em aberto:** o ERP chama `/licenca/conectar` a cada 5 minutos e
guarda o token que voltar. Esse endpoint remoeda o token com os módulos do
momento, ou devolve o mesmo até `proximaValidacaoEm`? Disso depende a
concessão do NFE aparecer na loja em 5 minutos ou em até 7 dias.

---

## 10. Ordem sugerida

1. `.passthrough()` no payload da emissão — sem isso, nada mais importa.
2. Mapear `qrcode` e `url_consulta` na resposta.
3. `POST /erp/fiscal/nfce/emitir`.
4. `POST /erp/fiscal/nfe/inutilizar`.
5. Responder a pergunta do item 9 e decidir o item 8.

Com o passo 1, dá para emitir NF-e em homologação e validar a cadeia inteira.
