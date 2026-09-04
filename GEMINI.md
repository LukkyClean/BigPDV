# Diretrizes do Projeto BigPDV

## 1. Ambiente Backend (FastAPI / Python) & Execução de Testes

### 1.1. Ativação do Ambiente Virtual (.venv)
- O ambiente virtual Python do backend localiza-se em `backend-fastapi/.venv`.
- No Windows (PowerShell), **nunca** chame comandos globais `python` ou `pytest` diretamente.
- Utilize sempre o executável direto da virtualenv:
  ```powershell
  # A partir de c:\dev\bigpdv\backend-fastapi:
  .venv\Scripts\python.exe -m pytest <caminho_do_teste> -v
  ```

### 1.2. Padrões do Ambiente de Testes (`pytest` / `TestClient`)
- **Diretório de Execução**: `c:\dev\bigpdv\backend-fastapi`
- **Fixtures Padrão**: Utilize as fixtures `client`, `db_session` e `header_with_token`.
- **Precondições & Seeds Obrigatórios**:
  - **Sequência de Vendas**: Ao criar vendas em testes, sempre invoque `_seed_contador_venda(db_session)` antes de finalizar vendas para garantir a numeração correta.
  - **Módulo Fiscal**: Testes que chamam endpoints protegidos por `requer_modulo_fiscal` precisam de registro em `EmpresaFiscalSettings` no banco (`db_session.add(EmpresaFiscalSettings(...))`).
  - **Schema de Pagamento**: Ao chamar `/finalizar`, os objetos do array `pagamentos` devem conter obrigatoriamente:
    ```python
    {
        "forma_pagamento_id": fp_id,
        "valor": valor,
        "juros_valor": 0,
        "juros_responsavel": "LOJA",
        "parcelado": False,
        "qtd_parcelas": None,
    }
    ```

---

## 2. Validação do Frontend (Vue 3 / Vite)

- **Diretório de Execução**: `c:\dev\bigpdv\frontend`
- **Comando de Validação**:
  ```powershell
  npm run build
  ```
  *(Executa validações completas de tokens, paleta de cores, modelos de impressão, QR Code PIX e compilação TypeScript/Vite)*.
