# Conclave — System Architecture

## 1. High-Level Architecture Overview

Conclave is structured as a decoupled, multi-tier asynchronous architecture supporting HTTP REST and WebSocket connections.

```
                  ┌────────────────────────────────────────┐
                  │                Clients                 │
                  │   (Terminal TUI Client / Web App)      │
                  └──────────────────┬─────────────────────┘
                                     │
                   HTTP/REST (HTTPS) │ WebSockets (WSS)
                                     ▼
                  ┌────────────────────────────────────────┐
                  │       ASGI Application Gateway         │
                  │         (Uvicorn / Daphne)             │
                  └──────────────────┬─────────────────────┘
                                     │
                    ┌────────────────┴───────────────────┐
                    ▼                                    ▼   
    ┌───────────────────────────────┐ ┌───────────────────────────────┐
    │ Django REST Framework         │ │ Django Channels               │
    │ - SubDomainMiddleware         │ │ - WebSocketScopeMiddleware    │
    │ - Global Auth & Discovery     │ │ - ChatConsumer (Async)        │
    │ - Workspace Management        │ │ - Redis Presence Sync         │
    │ - History & Pagination        │ │ - Group Broadcasts            │
    └───────────────┬───────────────┘ └───────────────┬───────────────┘
                    │                                 │   
                    ├─────────────────┬───────────────┤
                    ▼                 │               ▼
    ┌───────────────────────────────┐ │ ┌───────────────────────────────┐
    │ PostgreSQL                    │ │ │ Redis                         │
    │ - Shared Schema               │ │ │ - Channels Pub/Sub Layer      │
    │ - Row-Level Security (RLS)    │ └►│ - User Presence Key/Values    │
    │ - UUID Primary Keys           │   │ - Ephemeral Caching           │
    └───────────────────────────────┘   └───────────────────────────────┘
```

---

## 2. Core Components

### A. Client Layer (TUI & Web)
- **TUI Client:** Terminal interface built with Python/Textual or Go/Bubbletea. Communicates over HTTPS for state initialization and persistent WebSockets for live chat streaming.

### B. ASGI Server & Routing
- **Entrypoint (`Conclave/asgi.py`):** Uses `ProtocolTypeRouter` to direct incoming traffic:
  - `http` traffic $\rightarrow$ Django WSGI/ASGI application pipeline with `SubDomainMiddleware`.
  - `websocket` traffic $\rightarrow$ `WebSocketScopeMiddleware` $\rightarrow$ `URLRouter` $\rightarrow$ `ChatConsumer`.

### C. Multi-Tenancy & Context Resolution Pipeline
Tenancy is resolved dynamically on every request:

```
Incoming Request: acme.conclave.app/chats/rooms/
│
▼
[SubDomainMiddleware / WebSocketScopeMiddleware]
│
├─► Extracts subdomain: "acme"
├─► Queries Tenant model for "acme"
├─► Injects tenant_id into ContextVar: _current_tenant_id
▼
[PostgreSQL Session Configuration]
│
└─► EXECUTE: SELECT set_config('app.current_tenant', '<tenant_uuid>', true);

```

All queries executed within that request transaction inherit the tenant isolation policy via PostgreSQL Row-Level Security.

### D. Real-Time Engine (Django Channels + Redis)
- **Channel Layer:** `channels_redis.core.RedisChannelLayer` distributes WebSocket payloads across distributed ASGI worker nodes.
- **Group Isolation:** Room broadcast groups are named strictly using the room's UUID: `chat_<room_uuid>`. This eliminates naming collisions when multiple workspaces have channels with the same name (e.g., `#general`).
- **Presence Engine:** User online state is maintained in Redis using key patterns (`user:<user_id>:is_online` and `room:<room_id>:user:<user_id>:online`) with expiration TTLs.

---

## 3. Data Flow Diagrams

### Message Send Flow (WebSocket)
```
Client (Alex)               ChatConsumer               PostgreSQL          Redis Channel Layer     Client (Sam)
      │                          │                         │                       │                   │
      ├── 1. {"message_send"} ──►│                         │                       │                   │
      │                          │                         │                       │                   │
      │                          ├── 2. Resolve Profile ──►│                       │                   │
      │                          │     & Insert Message    │                       │                   │
      │                          │                         │                       │                   │
      │                          │◄─ 3. Message Saved ─────┘                       │                   │
      │                          │                                                 │                   │
      │                          ├── 4. group_send("chat_<room_uuid>", payload) ──►│                   │
      │                          │                                                 │                   │
      │                          │                                                 ├── 5. Broadcast ──►│
      │                          │                                                 │                   │
      │◄── 6. Echo message_send ─┴─────────────────────────────────────────────────┴───────────────────┘
```

### History Pagination Flow (REST)
```
Client (TUI)                                                   DRF View / Database
     │                                                                    │
     ├── GET /chats/rooms/<uuid>/messages/?limit=50&before=<timestamp> ──►│
     │                                                                    │── Queries Messages WHERE sent_at < timestamp
     │                                                                    │   ORDER BY sent_at DESC LIMIT 50
     │                                                                    │
     │                                                                    │── Inverts slice to chronological order
     │◄─ 200 OK [ [msg1, msg2, ..., msg50] ] ─────────────────────────────┘
```

---

## 4. Database Architecture & ER Model

```
┌─────────────────────────┐                ┌─────────────────────────┐
│          User           │                │         Tenant          │
├─────────────────────────┤                ├─────────────────────────┤
│ PK  id (UUID)           │ 1            * │ PK  id (UUID)           │
│     email (Unique)      ├────────────────┤     name (Unique)       │
│     name                │  (created_by)  │     is_public           │
└───────────┬─────────────┘                │     creation_date       │
            │ 1                            └───────────┬─────────────┘
            │                                          │ 1
            │                                          │
            │ *                                        │ *
┌───────────▼─────────────┐                ┌───────────▼─────────────┐
│         Profile         │                │        ChatRooms        │
├─────────────────────────┤                ├─────────────────────────┤
│ PK  id (BigInt)         │ 1            * │ PK  id (UUID)           │
│ FK  user_id             ├────────────────┤ FK  tenant_id           │
│ FK  tenant_id           │ (memberships)  │     name                │
│     username            │                │     type (BROADCAST/DM) │
│     role                │                └───────────┬─────────────┘
└───────────┬─────────────┘                            │ 1
            │ 1                                        │
            │                                          │
            │ *                                        │ *
┌───────────▼─────────────┐                ┌───────────▼─────────────┐
│       RoomMembers       │                │        Messages         │
├─────────────────────────┤                ├─────────────────────────┤
│ PK  id (UUID)           │ 1            * │ PK  id (UUID)           │
│ FK  room_id             ├────────────────┤ FK  room_id             │
│ FK  profile_id          │    (sender)    │ FK  sender_id           │
│ FK  last_read_message_id│                │     content             │
└─────────────────────────┘                │     sent_at             │
                                           └─────────────────────────┘
```

---

## 5. Security & Isolation Model

1. **Defense in Depth (Dual-Layer Isolation):**
   - **Application Layer:** DRF querysets explicitly filter by `tenant_id` resolved from `_current_tenant_id`.
   - **Database Layer (RLS):** PostgreSQL policies reject rows that do not match `current_setting('app.current_tenant')`.
2. **Server-Authoritative Identity:**
   - Clients cannot spoof message senders. The `ChatConsumer` extracts the sender identity strictly from the verified JWT `self.user` object and queries the corresponding workspace `Profile`.
3. **Deterministic Direct Message Rooms:**
   - 1-on-1 DM rooms use canonical naming conventions (`dm_<min_uuid>_<max_uuid>`) to prevent duplicate conversations between two members in the same workspace.

---

## 6. Scalability & Deployment Considerations

- **Stateless Web/WebSocket Nodes:** Any number of ASGI instances can run behind Nginx / Cloudflare.
- **Redis Pub/Sub:** All cross-process message dispatch is handled by Redis channel layers.
- **Connection Pooling:** For production workloads, deploy **PgBouncer** in `transaction` mode between Django and PostgreSQL to handle thousands of concurrent short-lived database transactions.