# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

StartBig is an ERP / Point of Sale system built as a desktop application using Tauri with a Vue 3 frontend and FastAPI Python backend.

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
O banco fica em `%LOCALAPPDATA%\StartBigERP\data\start_big.db`, **fora** da pasta de
instalação — o desinstalador não o alcança, e os hooks NSIS só mexem em firewall.
No startup, `app/core/tarefas.py` roda `create_all()` e **depois** `aplicar_migracoes()`
(`upgrade("head")`). Migrations novas devem decidir pela presença do **schema antigo**,
não pela ausência do novo — senão o `create_all` já criou a tabela vazia e a migração
não roda (a `965c71a2da9a` faz isso certo e serve de modelo). Não há backup automático
antes de migrar.

⚠️ **Nunca renomeie o arquivo do banco.** O `create_all()` do startup não reclama de
um nome inexistente: ele cria um banco **vazio** ao lado do de verdade, e o sintoma
que chega é "o sistema não reconhece mais meu usuário e senha". Foi o que derrubou o
servidor da loja em 28/07/2026, quando o `7b8d129` trocou o nome para `startbig.db`
(sem underscore). Se um rename for inevitável, acrescente o nome antigo em
`LEGACY_DB_FILENAMES` (`app/core/config.py`) no mesmo commit.

### Papel da máquina (servidor × terminal) e endereço do backend
O papel fica em `%APPDATA%\br.com.startbig.erp\StartBigERP\system-config.json`
(`is_server`, `server_ip`, `server_port`, `configured`, `servico_instalado`, `data_dir`),
**por usuário do Windows**, escrito só por `src-tauri/src/network/config.rs`. Regras que
não podem regredir (incidente do cliente em 09/2026 — servidor virou terminal apontando
para o próprio IP de LAN, que mudava com o DHCP):
- `get_api_url` devolve **loopback** para servidor; `resolver_papel_efetivo` corrige o
  papel no startup quando o IP salvo é desta máquina **e** há backend/tarefa local
  (regra conjuntiva — nunca converter só pelo IP).
- `set_role_client` **recusa** IP desta máquina (`IP_LOCAL`); a auto-descoberta marca
  `local: true` e o wizard não auto-conecta a si mesmo.
- Servidor já configurado **nunca** volta ao wizard "Tipo de máquina" — vai para
  `erro-conexao` em modo servidor (reiniciar/reparar serviço).
- `backend.rs::ensure_backend` espera a tarefa `StartBigServer` (até 90 s) antes de subir
  sidecar, e o sidecar sempre recebe `--data-dir` (senão abre outro banco).
- Log persistente: `rede.log` ao lado do `system-config.json`; painel em
  Configurações › Rede e Conexão (`diagnostico_rede`).
- mDNS (`app/core/discovery.py`) anuncia todas as IPv4 locais via `ifaddr`, nunca
  `127.0.0.1`, e re-anuncia quando os IPs mudam (`atualizar_anuncio`, a cada 45 s).

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
