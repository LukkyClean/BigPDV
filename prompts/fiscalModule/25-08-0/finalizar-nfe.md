# Relatório: Fluxo de Emissão de NF-e — Como Funciona e o que a API Web Deve Fazer

## Visão Geral da Arquitetura

```
┌──────────┐     ┌──────────────┐     ┌────────────────┐     ┌───────────┐     ┌───────┐
│ Frontend │ ──► │ Backend      │ ──► │ API StartBig   │ ──► │ Focus NFe │ ──► │ SEFAZ │
│ (Vue 3)  │     │ (FastAPI)    │     │ (api.startbig) │     │ (proxy)   │     │ (UF)  │
└──────────┘     └──────────────┘     └────────────────┘     └───────────┘     └───────┘
                       │
                       ├── Validações (completude fiscal)
                       ├── Cálculo tributário (FiscalTaxEngine)
                       ├── Montagem do payload (JSON)
                       ├── Controle de numeração (série + número)
                       └── Registro em banco (DocumentoFiscal)
```

**Estado atual**: BigPDV → Mock Client (simula tudo localmente). A API StartBig (`FiscalClientStartBig`) está como placeholder com `NotImplementedError`.

---

## Passo a Passo Completo da Emissão

### PASSO 1 — Frontend: Usuário Inicia Emissão

**Arquivo**: `frontend/src/modules/fiscal/views/FiscalNFeView.vue`

O usuário acessa `/fiscal/nfe` e tem duas opções:
- **"Emitir NF-e"** (botão primary) → Abre `FiscalEmitirNFeModal.vue`
- **"Emitir Teste"** (botão ghost, só em homologação) → Abre `FiscalEmitirTesteModal.vue`

#### Fluxo do modal de emissão real (`FiscalEmitirNFeModal.vue`):
1. Busca vendas FINALIZADAS via `useSalesListQuery` (`GET /api/v1/vendas/?status=FINALIZADA&search=...`)
2. Exibe lista com: número da venda, valor total, nome do cliente, data
3. Usuário seleciona uma venda → tela de confirmação com resumo
4. Clique em "Emitir NF-e" → chama `useFiscalEmitirNfeMutation`
5. Mutation faz `POST /api/v1/fiscal/emitir/nfe` com body `{ venda_id: 123 }`
6. Em caso de sucesso: toast + invalida queries (atualiza tabela de documentos)
7. Em caso de erro (422): toast com mensagem de pendências

#### Fluxo do modal de teste (`FiscalEmitirTesteModal.vue`):
1. Confirmação simples (sem seleção de venda)
2. `POST /api/v1/fiscal/emitir/teste/nfe` (sem body)

---

### PASSO 2 — Backend: Dependency `requer_modulo_fiscal`

**Arquivo**: `backend-fastapi/app/core/depends.py:249-284`

Antes de qualquer endpoint fiscal, esta dependency executa:
1. Extrai `empresa_id` do token JWT do usuário
2. Busca `EmpresaFiscalSettings` no banco
3. Se não existir: **auto-cria** com `ambiente_emissao=2` (homologação)
4. Retorna o token para o endpoint continuar

**Resultado**: Garante que sempre existe configuração fiscal para a empresa.

---

### PASSO 3 — Backend: Verificação de Completude (só emissão real)

**Arquivo**: `backend-fastapi/app/services/fiscal/validators.py`

O endpoint `emitir/nfe` chama `verificar_completude_venda(db, venda_id, empresa_id)` que valida:

#### Emitente (empresa):
- CNPJ preenchido e válido
- Regime tributário definido
- Inscrição Estadual (se indicador IE = 1)
- Endereço completo: logradouro, número, bairro, cidade, UF, CEP
- EmpresaFiscalSettings existe
- ~~Certificado digital configurado~~ (temporariamente desativado)

#### Destinatário (cliente da venda):
- CPF (PF) ou CNPJ (PJ) preenchido e válido

#### Itens (produtos da venda):
- Nenhum item avulso (todos devem ter produto vinculado)
- Cada produto deve ter `ProdutoFiscal` com:
  - NCM preenchido
  - CFOP padrão preenchido
  - Unidade tributável preenchida
  - Origem da mercadoria preenchida
  - CST ICMS (Lucro Presumido/Real) OU CSOSN (Simples Nacional)
  - Se CST 20: `reducao_base_icms` obrigatório
  - CST PIS e CST COFINS (warning se ausente, usa "01" como default)

#### Pagamentos:
- Ao menos 1 pagamento registrado
- Cada forma de pagamento deve ter `codigo_sefaz` preenchido (01=Dinheiro, 03=Crédito, 04=Débito, 17=PIX, etc.)

Se houver pendências → HTTP 422 com lista detalhada de problemas.

**A emissão de teste PULA esta etapa** (usa dados fictícios hardcoded).

---

### PASSO 4 — Backend: Cálculo Tributário (FiscalTaxEngine)

**Diretório**: `backend-fastapi/app/services/fiscal/tax_engine/`

#### 4.1 Resolução de Alíquotas (`resolver.py`)

Converte dados ORM em DTOs puros:
1. Obtém a UF do emitente (endereço da empresa)
2. Verifica se é Simples Nacional (regime tributário)
3. **Trava interestadual**: se UF do cliente ≠ UF do emitente → erro `OperacaoInterestadualError`
4. Para cada item da venda, resolve alíquotas com prioridade:
   - **Override no produto** (`ProdutoFiscal.aliquota_icms`) → usa se preenchido
   - **Default da UF** (`AliquotaUF.aliquota_icms_interna`) → fallback
5. Converte centavos (int) → Decimal (reais)
6. Retorna `list[ItemEntrada]` + `DadosNota`

#### 4.2 Rateio Proporcional (`rateio.py`)

Distribui valores da nota (frete, seguro, outras despesas, desconto) proporcionalmente entre os itens:
- Peso de cada item = `valor_bruto / soma_todos_brutos`
- Centavo de diferença vai para o item de maior valor (garante que soma = total)

#### 4.3 Cálculo de ICMS (`calculators/icms.py`)

Por CST/CSOSN:
- **CST 00** (Tributação normal): `base = valor_bruto + frete + seguro + despesas - desconto` → `valor = base × alíquota/100`
- **CST 20** (Redução de base): `base_reduzida = base × (1 - redução/100)` → `valor = base_reduzida × alíquota/100`
- **CST 40/41** (Isento): base=0, valor=0
- **CST 60** (ST cobrada anteriormente): base=0, valor=0
- **CSOSN 101** (Simples com crédito): calcula `valor_credito = base × aliquota/100`
- **CSOSN 102** (Simples sem crédito): base=0, valor=0
- **CSOSN 500** (ST cobrada anteriormente): base=0, valor=0

#### 4.4 Cálculo de PIS/COFINS (`calculators/pis_cofins.py`)

- CST 01/02 (tributado): `base = valor_bruto + frete + seguro + despesas - desconto`
  - **STF Tema 69** (flag configurável): `base -= valor_icms` (exclui ICMS da base)
  - PIS: `valor = base × alíquota/100`
  - COFINS: `valor = base × alíquota/100`
- CST 04-09 (isento/suspenso): base=0, valor=0

#### 4.5 Consolidação (`consolidador.py`)

Soma todos os valores por item e gera `TotaisNota`:
- `valor_total_produtos`, `valor_frete`, `valor_seguro`, `valor_outras_despesas`, `valor_desconto`
- `base_calculo_icms`, `valor_icms`, `valor_pis`, `valor_cofins`
- `valor_total_nota = produtos + frete + seguro + despesas - desconto`

**Resultado**: `ResultadoCalculo` com `itens: list[ImpostosItem]` + `totais: TotaisNota`

---

### PASSO 5 — Backend: Montagem do Payload

**Arquivo**: `backend-fastapi/app/services/fiscal/payload_builder.py`

Monta um dict JSON pronto para ser enviado à API. Estrutura:

```json
{
  "natureza_operacao": "Venda de Mercadoria",
  "tipo_documento": 1,
  "finalidade_emissao": 1,
  "consumidor_final": 1,
  "presenca_comprador": 1,
  "numero": 42,
  "serie": 1,

  "cnpj_emitente": "12345678000190",
  "razao_social_emitente": "Empresa X Ltda",
  "nome_fantasia_emitente": "Empresa X",
  "inscricao_estadual_emitente": "123456789",
  "regime_tributario_emitente": 1,
  "endereco_emitente": {
    "logradouro": "Rua A",
    "numero": "100",
    "bairro": "Centro",
    "cidade": "São Paulo",
    "uf": "SP",
    "cep": "01001000"
  },

  "cpf_destinatario": "12345678901",
  "nome_destinatario": "João Silva",

  "items": [
    {
      "numero_item": 1,
      "codigo_produto": "PROD001",
      "descricao": "Camiseta",
      "ncm": "61091000",
      "cfop": "5102",
      "unidade_comercial": "UN",
      "quantidade_comercial": "2.00",
      "valor_unitario_comercial": "50.00",
      "valor_bruto": "100.00",
      "icms_origem": "0",
      "icms_situacao_tributaria": "00",
      "icms_modalidade_base_calculo": 0,
      "icms_base_calculo": "100.00",
      "icms_aliquota": "18.00",
      "icms_valor": "18.00",
      "pis_situacao_tributaria": "01",
      "pis_base_calculo": "82.00",
      "pis_aliquota_porcentual": "1.65",
      "pis_valor": "1.35",
      "cofins_situacao_tributaria": "01",
      "cofins_base_calculo": "82.00",
      "cofins_aliquota_porcentual": "7.60",
      "cofins_valor": "6.23",
      "ipi_situacao_tributaria": "53",
      "ipi_codigo_enquadramento": "999",
      "valor_frete": "0.00",
      "valor_seguro": "0.00",
      "valor_desconto": "0.00",
      "valor_outras_despesas_acessorias": "0.00"
    }
  ],

  "formas_pagamento": [
    {
      "forma_pagamento": "17",
      "valor_pagamento": "100.00"
    }
  ],

  "valor_produtos": "100.00",
  "icms_base_calculo": "100.00",
  "icms_valor_total": "18.00",
  "valor_total": "100.00"
}
```

---

### PASSO 6 — Backend: Registro no Banco de Dados

**Arquivo**: `backend-fastapi/app/services/fiscal/emissao.py:131-152`

Antes de chamar a API, o sistema:
1. Gera uma `ref_api` única (UUID): `"doc-a1b2c3d4e5f6"`
2. Incrementa `fiscal_settings.ultimo_numero_nfe` (atômico, mesma transação)
3. Cria registro `DocumentoFiscal` com:
   - `tipo_documento`: "NFE"
   - `origem_tipo`: "VENDA"
   - `origem_id`: ID da venda
   - `status`: "PROCESSANDO"
   - `numero_documento`: próximo número sequencial
   - `serie`: série configurada
   - `ref_api`: referência única
   - `ambiente_emissao`: 1 (produção) ou 2 (homologação)
   - `valor_total`: total da venda em centavos
4. `db.flush()` garante que o registro existe antes da chamada HTTP

---

### PASSO 7 — Backend: Chamada ao Client Fiscal

**Arquivo**: `backend-fastapi/app/services/fiscal/http/client_factory.py`

A factory seleciona o client:
- `ambiente == 2` OU `FISCAL_MOCK_ENABLED=true` → `FiscalClientMock` (resposta local)
- `ambiente == 1` → `FiscalClientStartBig` (chamada à API web)

#### 7.1 Hoje: FiscalClientMock

Retorna imediatamente dados fictícios:
```python
{
    "status": "autorizado",
    "chave_acesso": "44 dígitos aleatórios",
    "protocolo": "15 dígitos aleatórios",
    "numero": payload["numero"],
    "serie": payload["serie"],
    "url_pdf": "https://mock.startbig.com.br/danfe/{ref}.pdf",
    "url_xml": "https://mock.startbig.com.br/xml/{ref}.xml",
    "codigo_sefaz": 100,
    "mensagem_sefaz": "Autorizado o uso da NF-e (HOMOLOGAÇÃO - SEM VALOR FISCAL)",
}
```

#### 7.2 Futuro: FiscalClientStartBig (o que a API web deve fazer)

**Contrato**: 3 métodos, cada um recebe parâmetros e retorna `EmissaoResultado`:

```python
class EmissaoResultado(TypedDict):
    status: str           # "autorizado" | "processando" | "erro" | "cancelado"
    chave_acesso: str     # 44 dígitos (chave de acesso da NF-e)
    protocolo: str        # Protocolo de autorização SEFAZ
    numero: int           # Número da NF-e (confirmado pela SEFAZ)
    serie: int            # Série da NF-e
    url_pdf: str          # URL do DANFE (PDF) para download
    url_xml: str          # URL do XML autorizado para download
    codigo_sefaz: int     # Código de retorno SEFAZ (100=autorizado, 135=cancelado, etc.)
    mensagem_sefaz: str   # Mensagem textual da SEFAZ
```

---

## O QUE A API WEB STARTBIG DEVE FAZER

### Endpoint 1: Emitir NF-e

```
POST /erp/fiscal/nfe/emitir
Content-Type: application/json
Authorization: Bearer <token_empresa>

Body: { "ref": "doc-a1b2c3d4e5f6", "payload": { ...payload completo... } }
```

**Responsabilidades da API web**:
1. **Receber o payload JSON** do BigPDV (formato descrito no Passo 5)
2. **Converter para XML** no schema da NF-e (modelo 55) com namespace correto
3. **Assinar digitalmente** o XML com certificado A1 da empresa (PKCS#7 / X.509)
4. **Enviar à SEFAZ** (ou via Focus NFe como proxy) no ambiente correto (homologação/produção)
5. **Aguardar resposta** da SEFAZ (sincrônico ou assíncrono)
6. **Retornar `EmissaoResultado`** com:
   - `status: "autorizado"` se código SEFAZ = 100
   - `status: "processando"` se a SEFAZ ainda está processando
   - `status: "erro"` se rejeitado (código SEFAZ ≠ 100)
   - `chave_acesso`: 44 dígitos retornados pela SEFAZ
   - `protocolo`: protocolo de autorização
   - `url_pdf`: URL do DANFE gerado (a API deve gerar o PDF)
   - `url_xml`: URL do XML autorizado (a API deve armazenar o XML)
   - `codigo_sefaz`: código numérico (100, 204, 302, etc.)
   - `mensagem_sefaz`: mensagem textual do retorno

### Endpoint 2: Consultar NF-e

```
GET /erp/fiscal/nfe/consultar?ref=doc-a1b2c3d4e5f6
Authorization: Bearer <token_empresa>
```

**Responsabilidades da API web**:
1. Buscar o status atual da NF-e pela `ref` (referência interna)
2. Se ainda "processando": consultar SEFAZ e retornar status atualizado
3. Retornar `EmissaoResultado` com status atual

**Quando é chamado**: O BigPDV faz polling quando o documento está com status PROCESSANDO ou PENDENTE. O usuário clica "Consultar" na tabela de documentos.

### Endpoint 3: Cancelar NF-e

```
POST /erp/fiscal/nfe/cancelar
Content-Type: application/json
Authorization: Bearer <token_empresa>

Body: { "ref": "doc-a1b2c3d4e5f6", "justificativa": "Erro no pedido do cliente" }
```

**Responsabilidades da API web**:
1. Validar que a justificativa tem ≥ 15 caracteres (exigência SEFAZ)
2. Montar evento de cancelamento (XML de evento tipo 110111)
3. Assinar e enviar à SEFAZ
4. Retornar `EmissaoResultado` com `status: "cancelado"` e `codigo_sefaz: 135`

**Quando é chamado**: Apenas para documentos com status AUTORIZADA. O usuário abre o modal de cancelamento, digita a justificativa, e confirma.

---

## Fluxo de Reemissão (documento rejeitado)

Se a SEFAZ rejeitar a NF-e, o BigPDV:
1. Marca o documento como REJEITADA
2. O usuário pode clicar "Reemitir" na tabela
3. O sistema cria um NOVO `DocumentoFiscal` com `tentativa_anterior_id` apontando para o anterior
4. O novo documento inicia como PENDENTE
5. O sistema NÃO tenta emitir automaticamente — espera ação do usuário
6. Isso cria uma linked list de tentativas que pode ser consultada via `/documentos/{id}/historico`

---

## Resumo dos Status do Documento

| Status | Significado | Ações Disponíveis |
|--------|------------|-------------------|
| PENDENTE | Criado, não enviado | Consultar |
| PROCESSANDO | Enviado, aguardando SEFAZ | Consultar |
| AUTORIZADA | Aprovado pela SEFAZ | Cancelar, baixar PDF/XML |
| REJEITADA | Recusado pela SEFAZ | Reemitir |
| CANCELADA | Cancelado após autorização | - |
| DENEGADA | Denegado pela SEFAZ (definitivo) | Reemitir |

---

## Códigos SEFAZ mais comuns

| Código | Significado |
|--------|------------|
| 100 | Autorizado o uso da NF-e |
| 135 | Evento registrado e vinculado a NF-e (cancelamento OK) |
| 204 | Duplicidade de NF-e (já existe com essa chave) |
| 302 | Irregularidade fiscal do emitente |
| 539 | Duplicidade de evento |
| 999 | Erro não catalogado |

---

## Tabelas do Banco Envolvidas

| Tabela | Papel |
|--------|-------|
| `documento_fiscal` | Cada emissão/tentativa é uma linha. Status, chave, protocolo, URLs. |
| `empresa_fiscal_settings` | Ambiente (1/2), série NF-e, último número, certificado. 1:1 com empresa. |
| `produto_fiscal` | NCM, CFOP, CST/CSOSN, alíquotas. 1:1 opcional com produto. |
| `aliquota_uf` | Alíquotas padrão por UF (ICMS, PIS, COFINS). Fallback quando produto não tem override. |
| `venda_nota_fiscal` | Parâmetros de emissão por venda (natureza operação, finalidade). 1:1 opcional com venda. |
| `forma_pagamento` | Catálogo de formas de pagamento com `codigo_sefaz` (01, 03, 04, 17, etc.) |

---

## Checklist para Habilitar Emissão Real (Produção)

1. [ ] Implementar `FiscalClientStartBig` com os 3 métodos (`emitir_nfe`, `consultar_nfe`, `cancelar_nfe`)
2. [ ] Definir endpoints da API web StartBig (URL base, autenticação, formato request/response)
3. [ ] Implementar upload e gestão de certificado digital A1 (.pfx)
4. [ ] Reativar validação de certificado em `validators.py` (linha 48-49)
5. [ ] Setar `FISCAL_MOCK_ENABLED=false` e `ambiente_emissao=1` na empresa
6. [ ] Testar em homologação SEFAZ (ambiente=2 com API real, não mock)
7. [ ] Testar em produção com nota de R$ 1,00 e cancelar imediatamente
