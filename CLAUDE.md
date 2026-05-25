# Development Guide & Agent Rules

This document is the source of truth for how the agent must organize code, place files, enforce testing standards, and ensure deployment safety. All changes are subject to code review.

## Tech Stack
- Python 3.10+
- NiceGUI 3.3.0 (>= 1.4, single-process with FastAPI)
- FastAPI 0.121.2
- SQLModel 0.0.27 (SQLAlchemy engine)
- PostgreSQL (psycopg2-binary)
- JWT auth (python-jose) + password hashing (passlib, bcrypt)
- Pydantic v2 + pydantic-settings
- Pytest + pytest-asyncio + Coverage.py
- Uvicorn (dev server via NiceGUI)

## Strict Agent Rules (Guardrails)
1. No new root files: never create new files at repo root unless a critical system config is required. All app code lives under src/ and tests live under tests/.
2. Strict folder logic: check Architecture before creating files. If a file is created in the wrong folder, delete it and recreate in the correct folder.
3. No direct UI-to-DB: UI pages must not query SQLModel sessions directly. UI must call repository functions.
4. Shared logic only: business logic and permission checks must live in repositories so UI and API reuse the same logic.
5. No HTTP calls to self: UI pages must not call local API endpoints via httpx/requests. Call repositories directly.
6. Permissions consistency: do not allow UI to bypass repository permission checks (avoid 401/403 mismatches).

## Clean Code & Modularization
- Atomic files (SRP): one file per page/component; avoid mega-files and split if a file exceeds ~250 lines.
- Explicit imports: avoid from module import *; keep imports explicit for traceability.
- Type hinting: required for all function signatures and repository methods.
- UI/logic separation: src/frontend/pages/ is layout-only; data transforms and filtering belong in repositories.
- Naming clarity: use descriptive names (avoid handler()); prefer on_login_button_click() or handle_user_registration().

## Strict File Organization
| File Type | Required Folder | Naming Rule |
| --- | --- | --- |
| Page UI | src/frontend/pages/ | [page_name]_page.py |
| Shared Components | src/frontend/components/ | [component_name].py |
| Layouts | src/frontend/layouts/ | [layout_name].py |
| API Endpoints | src/backend/endpoints/ | [module_name]_routes.py |
| Database Models | src/models/ | [entity].py |
| Business Logic | src/repositories/ | [module_name]_repo.py |
| DB Config/Seed | src/db/ | By function (init, session, seed) |
| Config/Security | src/core/ | config.py, security.py |

## Commands
- python app.py
- pip install -r requirements.txt
- cp .env.template .env

## Architecture Details
- app.py: entrypoint only; initializes DB, registers API routers, imports UI pages, and runs NiceGUI.
- Single-process app: NiceGUI UI and FastAPI share the same app instance.
- UI State: use app.storage.user for authentication state.
- DB Sessions:
  - UI code: with get_db_context() as db:
  - API code: db: Session = Depends(get_db)
- Security: all password hashing and JWT logic belongs in src/core/security.py.

## Workflow For Adding Features
1. Model: define SQLModel in src/models/.
2. Logic: implement data access and permissions in src/repositories/.
3. Component: create reusable UI parts in src/frontend/components/ when needed.
4. Page: create UI pages in src/frontend/pages/.
5. Register: import new pages/routers in app.py.

## Testing & Quality Assurance
- Definition of done: a feature is complete only when all related tests pass, linting is clean, and src/ docs are updated if needed.
- Test mirroring: tests/ must mirror the src/ structure (example: src/repositories/user_repo.py -> tests/repositories/test_user_repo.py).
- No regression: every bug fix must include a regression test that fails before the fix and passes after.
- Fail-fast and rollback: CI/CD must halt on test failure, and critical errors require rollback to the last stable Git commit.

## Best Practices
- Keep new features inside repositories and reuse from both UI and API.
- Prefer context-managed DB sessions and close them promptly.
- Raise HTTPException in repositories; UI pages should catch and show ui.notify messages.
- Keep pages small; if UI code appears more than twice, move it into components.
- Keep requirements.txt pinned and updated.
- Use absolute imports (e.g., from src.core.config import settings).
