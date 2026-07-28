# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BigPDV is a Point of Sale (PDV) system built as a desktop application using Tauri with a Vue 3 frontend and FastAPI Python backend.

## Development Commands

### Frontend (from `frontend/` directory)
```bash
npm run dev            # Só o Vite (NÃO sobe o backend — suba-o à parte)
npm run build          # check:sidecar + vite build (NÃO faz type-check; ver abaixo)
npm run build:sidecar  # Regera o backend empacotado (PyArmor + PyInstaller)
npm run check:sidecar  # Falha se o sidecar estiver mais velho que o backend
npm run lint           # ESLint with auto-fix
npm run format         # Prettier formatting
npm run storybook      # Storybook component development (port 6006)
npm run tauri          # Tauri CLI commands
```

`npm run build` **não roda o `vue-tsc`** (o commit f9ce039 o removeu do script). Type
error não quebra o build nem o instalador — rode `npx vue-tsc --noEmit` à mão.

### Backend (from `backend-fastapi/` directory)
```bash
.\.venv\Scripts\activate                 # Windows
source .venv/bin/activate                # Linux/Mac

fastapi run app/main.py --port 8080      # para usar com `npm run tauri dev`
fastapi dev app/main.py                  # porta 8000 — para usar no navegador
pytest test/                             # Run tests
```

### ⚠️ Portas: dev na 8000, loja na 8080-8083 (separados de propósito)
| Como você roda | Backend procurado em | Origem |
|---|---|---|
| Navegador em `localhost:1420` | **8000** | fallback de `api/backendUrl.ts` |
| `npm run tauri dev` (janela) | **8000** | **chumbado** em `src-tauri/src/network/config.rs` (`#[cfg(debug_assertions)]`) — ignora o `system-config.json` |
| App instalado (release) | `config.server_port` (fallbacks **8080→8083**, senão aleatória) | `load_config()`; é a porta do sidecar |

Dev e app instalado usam faixas **separadas** (8000 vs 8080-8083) para não colidir
numa máquina que é loja **e** ambiente de dev ao mesmo tempo. Suba o backend de dev
com `fastapi dev app/main.py` (padrão 8000) — tanto navegador quanto `tauri dev` batem
na mesma porta. Se o login parecer quebrado, **cheque a porta antes do banco**.

### Sidecar (backend empacotado)
O instalador leva o backend como um `.exe`: `frontend/src-tauri/bin/erp-api-<target-triple>.exe`
(declarado em `tauri.conf.json` → `bundle.externalBin`). Ele **não é gerado pelo
`tauri build`** e **não está versionado** — cada máquina gera o seu:

```bash
cd frontend && npm run build:sidecar
```

Três passos, encadeados em `scripts/build-sidecar.mjs`:
1. **PyArmor** ofusca `app/` → `backend-fastapi/dist/` (`run.py` carrega daí quando `APP_ENV=production`)
2. **PyInstaller** (`run.spec`) empacota `run.py` + `dist/` + `alembic` → `.exe`
3. Copia para `bin/` com o *target triple* do `rustc` no nome

**Regere sempre que mexer no backend.** `npm run build` chama o `check:sidecar` e
falha se o sidecar estiver atrasado — em 16/07/2026 ele estava 6 dias velho, e um
instalador assim quebraria a oficina (contrato sem `capacidades` derruba Vistoria,
Revisões, aprovação e garantia) e o `/reconnect`.

Notas: o PyArmor está em licença **trial** (`pyarmor-trial`) — revisar antes de um
release comercial. O `dist/` é *build artifact* (gitignored), não a fonte.

### Atualização de cliente (o banco é preservado)
O banco fica em `%LOCALAPPDATA%\StartBigERP\data\pdv.db`, **fora** da pasta de
instalação — o desinstalador não o alcança, e os hooks NSIS só mexem em firewall.
No startup, `app/core/tarefas.py` roda `create_all()` e **depois** `aplicar_migracoes()`
(`upgrade("head")`). Migrations novas devem decidir pela presença do **schema antigo**,
não pela ausência do novo — senão o `create_all` já criou a tabela vazia e a migração
não roda (a `965c71a2da9a` faz isso certo e serve de modelo). Não há backup automático
antes de migrar.

## Architecture

### Frontend (`frontend/src/`)

**Module-based architecture** where each feature is a self-contained module:

```
modules/
├── auth/          # Login flow
├── home/          # Dashboard
├── mainLayout/    # Main app shell (sidebar, header, layout)
├── onboarding/    # Initial company setup wizard
└── employees/     # Employee management
```

Each module contains:
- `views/` - Page components
- `components/` - Module-specific components
- `routes.ts` - Auto-loaded by `router/index.ts` via glob import
- `services/` - API calls
- `composables/` - Vue composables
- `types/` - TypeScript types
- `schemas/` - Zod validation schemas
- `store/` - Pinia stores (module-specific)

**Shared code** (`shared/`):
- `components/ui/` - Reusable UI components (BaseButton, BaseInput, BaseSelect, etc.)
- `stores/` - Global stores (auth.store.ts)
- `composables/` - Global composables (useUser, useToast, useAppNavigation)
- `services/` - Global services

**Key patterns:**
- Routes are auto-discovered from `@/modules/**/routes.ts`
- TanStack Query for server state management
- Pinia for client state
- VeeValidate + Zod for form validation
- Axios instance in `api/axios.ts` with auth interceptors

### Backend (`backend-fastapi/app/`)

**Layered architecture:**

```
app/
├── api/v1/
│   ├── api.py         # Router aggregation
│   └── endpoints/     # Route handlers
├── core/
│   ├── config.py      # Pydantic settings from .env
│   ├── security.py    # Password hashing (bcrypt), JWT tokens
│   └── depends.py     # FastAPI dependencies
├── db/
│   ├── session.py     # SQLAlchemy engine and session
│   ├── base.py        # Base model class
│   ├── models/        # SQLAlchemy ORM models
│   └── crud/          # Database operations
├── schemas/           # Pydantic request/response schemas
└── services/          # Business logic
```

**Key entities:** Usuario, Funcionario, Cliente, Empresa, Produto, Servico, Fornecedor, Cargo, Endereco, Estoque

**Auth flow:** JWT tokens with blocklist for logout. Tokens stored as HTTP-only cookies.

### Tauri (`frontend/src-tauri/`)

Rust-based desktop shell using:
- `tauri-plugin-stronghold` - Secure storage
- `tauri-plugin-keyring` - System keychain integration
- `rust-argon2` - Password hashing

## API Endpoints

All endpoints under `/api/v1/`:
- `/auth` - Login/logout
- `/usuarios` - User management
- `/empresas` - Companies
- `/funcionarios` - Employees
- `/cargos` - Job positions
- `/clientes` - Customers
- `/fornecedores` - Suppliers
- `/produtos` - Products
- `/servicos` - Services
- `/enderecos` - Addresses

## Language

The codebase uses Portuguese for:
- Variable and function names
- Comments and documentation
- Database fields and API responses
- UI text

Maintain this convention when adding new code.
