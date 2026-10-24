# Conclave Backend

> A subdomain-isolated, multi-tenant real-time chat platform engineered specifically for **Terminal User Interfaces (TUIs)** and CLI clients.

---

## Problem Statement

Mainstream team communication platforms (Slack, Discord, Teams) are heavy, memory-intensive Electron apps that provide poor integration with keyboard-driven terminal workflows. Furthermore, multi-tenant architectures frequently struggle with a difficult trade-off:
- **Application-only filtering (`WHERE tenant_id = ...`)** is prone to developer slips that leak cross-tenant data.
- **Schema-per-tenant or Database-per-tenant** creates operational complexity, slow migrations, and heavy connection pooling overhead.
- **Standard offset pagination (`?page=2`)** suffers from offset drift when new messages arrive while a user is scrolling in a terminal screen buffer.

**Conclave** resolves this by combining **strict subdomain-based tenant routing**, **defense-in-depth PostgreSQL Row-Level Security (RLS)**, and a **terminal-tailored API & WebSocket streaming engine**.

---

## Architectural Highlights

- **Strict Subdomain Multi-Tenancy:** Ingress requests authoritatively resolve the workspace from the HTTP `Host` subdomain (e.g., `acme.conclave.app` or `acme.lvh.me:8000` in local dev).
- **PostgreSQL Row-Level Security (RLS):** Operates on a single shared-database and shared-schema. The middleware sets the session context `set_config('app.current_tenant', tenant_id, true)` in each transaction, ensuring isolation is enforced at the database kernel level.
- **TUI-Optimized Cursor Pagination:** Message history utilizes timestamp cursors (`?limit=50&before=<timestamp>`) returning reverse-chronological slices formatted for terminal viewports without message drift or skips.
- **Deterministic 1-on-1 Direct Messaging:** Unified under the room model with canonical naming (`dm_<min_uuid>_<max_uuid>`), avoiding duplicate tables or parallel WebSocket endpoints.
- **Sub-50ms Real-Time Event Engine:** Powered by Django Channels (ASGI) and Redis pub/sub. Tracks transient user presence (`user:<id>:is_online`) and typing indicators with automatic Redis TTL expiration, avoiding database write pressure.
- **Stateless Authentication:** JSON Web Tokens (SimpleJWT) authenticated uniformly across HTTP requests and WebSocket handshakes (`?token=`, `Authorization`, or `Sec-WebSocket-Protocol`).

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Language & Runtime** | Python 3.14+ |
| **Package Manager** | [`uv`](https://github.com/astral-sh/uv) |
| **Web & ASGI Framework** | Django 6.1, Django REST Framework 3.18, Django Channels 4.3 |
| **Realtime Transport** | ASGI WebSockets via Uvicorn & Redis Pub/Sub |
| **Database** | PostgreSQL 14+ (Row-Level Security) |
| **Cache & Presence** | Redis 7+ (`django-redis`, `channels-redis`) |
| **API Documentation** | OpenAPI 3.0 / Swagger UI (`drf-spectacular`) |

---

## Setup & Running with `uv`

### 1. Prerequisites
- [uv](https://docs.astral.sh/uv/) installed
- PostgreSQL 14+ running
- Redis 6+ running

### 2. Environment Configuration
Create a `.env` file in the backend root:
```env
SECRET_KEY=your-secure-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost,.lvh.me
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://lvh.me:5173
DATABASE_URL=postgres://postgres:password@localhost:5432/conclave_db
BASE_DOMAIN_LENGTH=2
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
```

### 3. Install Dependencies
```bash
uv sync
```

### 4. Database Migrations & RLS Policies
```bash
# Run Django migrations
uv run python manage.py migrate

# Apply PostgreSQL Row-Level Security policies to tenant models
uv run python manage.py apply_rls_policy_for_model core,chats
```

### 5. Start the Real-Time ASGI Server
```bash
uv run uvicorn Conclave.asgi:application --host 0.0.0.0 --port 8000 --reload
```

---

## API & WebSocket Endpoints

- **Interactive API Documentation:** `http://localhost:8000/api/schema/swagger-ui/`
- **Global Auth & Account Management:**
  - `POST /auth/signup/` — Register user & issue JWT
  - `POST /auth/login/` — Authenticate existing user
  - `GET /auth/me/` — Retrieve global profile & memberships
  - `POST /auth/token/refresh/` — Refresh access token
- **Global Workspace Operations:**
  - `POST /tenant/` — Create new workspace
  - `GET /tenant/mine/` — List owned & joined workspaces
  - `GET /tenant/search/?q=` — Search public workspaces
  - `POST /tenant/join/` — Join workspace or submit access request
- **Workspace-Scoped Operations (`http://<workspace>.lvh.me:8000`):**
  - `GET /` — Workspace overview
  - `GET /members/` — Workspace roster with live `is_online` status
  - `GET /chats/rooms/` — List channels & DMs with unread counts
  - `POST /chats/rooms/` — Create chat channel (`TENANT_CHATS`)
  - `POST /chats/dm/<target_user_id>/` — Get/create deterministic DM room
  - `GET /chats/rooms/<room_id>/messages/?limit=50&before=<timestamp>` — Cursor message history
- **WebSocket Streaming:**
  - `ws://<workspace>.lvh.me:8000/ws/chat/?token=<JWT>` — Live chat stream, typing events & presence

---

## Detailed Documentation

- [Architecture & Data Flows](docs/ARCHITECTURE.md)
- [System Overview & Requirements](docs/OVERVIEW.md)
- [API Reference & WebSocket Protocol](docs/API.md)
- [Database Schema & Multi-Tenancy Strategy](docs/DATABASE.md)
- [Architectural Decision Records (ADRs)](docs/DECISIONS.md)