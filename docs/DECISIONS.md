# Conclave — Architectural Decision Records (ADRs)

This document records the architectural and design decisions made in Conclave, along with the trade-offs and rationale.

---

## ADR 001: Multi-Tenancy via Shared Database + PostgreSQL Row-Level Security (RLS)

### Context
We needed a multi-tenant isolation strategy that supports hundreds of workspaces without incurring excessive infrastructure costs or operational complexity.

### Decision
Adopt a **shared-database, shared-schema** model enforced by **PostgreSQL Row-Level Security (RLS)** in tandem with Django request middleware.

### Alternatives Considered
- **Database-per-tenant:** High operational overhead; difficult connection pooling; costly for smaller workspaces.
- **Schema-per-tenant (Django Tenants):** Migration bottlenecks when running schema migrations across hundreds of tenant schemas.
- **Pure application-level filtering (WHERE tenant_id = x):** Susceptible to developer oversight where a missing filter leaks cross-tenant records.

### Consequences
- **Pros:** Low infrastructure overhead, centralized migrations, defense-in-depth isolation enforced at the database kernel level.
- **Cons:** Requires executing `set_config('app.current_tenant', ...)` per transaction, requiring careful handling in async Channels handlers.

---

## ADR 002: Subdomain-Based Tenant Routing with Header Fallbacks

### Context
Workspaces need clean namespace separation and distinct URLs while supporting both browser clients and CLI/terminal environments.

### Decision
Extract tenant names from the HTTP Host header subdomain (`<tenant>.conclave.app`). Provide fallback support for `X-Tenant` headers and query parameters (`?tenant=acme`) for local development, test suites, and terminal environments.

### Alternatives Considered
- **Path-based routing (`conclave.app/<tenant>/...`):** Complicates cookie isolation, routing tables, and URL nesting.
- **Token-embedded tenancy:** Prevents users from accessing public workspace landing pages prior to authenticating.

### Consequences
- **Pros:** Natural workspace boundaries, clean API URLs, friendly for multi-tab browser usage.
- **Cons:** Requires wildcard DNS and SSL certificates (`*.conclave.app`) in production.

---

## ADR 003: Deterministic Direct Messaging (DM) Rooms

### Context
Direct messaging between two workspace members could either be modeled as a distinct domain entity (`DirectMessage` table) or unified under the existing `ChatRooms` model.

### Decision
Reuse `ChatRooms` with `type = RoomTypes.DIRECT_MESSAGE` and construct deterministic room names:
$$\text{name} = \text{"dm_"} + \min(\text{user}_A, \text{user}_B) + \text{"_"} + \max(\text{user}_A, \text{user}_B)$$

### Alternatives Considered
- **Dedicated DirectMessage Table:** Doubles the codebase surface area (separate serializers, consumers, pagination logic, and WebSocket endpoints).

### Consequences
- **Pros:** Unifies message streaming, history pagination, read tracking, and WebSocket handlers across group channels and DMs.
- **Cons:** Querying "all my DMs" requires filtering room memberships with type `DIRECT_MESSAGE`.

---

## ADR 004: Stateless JWT Authentication for HTTP and WebSockets

### Context
Clients include terminal UIs, scripts, and web browsers. WebSockets cannot easily send custom HTTP headers during standard browser handshakes.

### Decision
Use **JSON Web Tokens (SimpleJWT)**. For WebSockets, allow token transmission via:
1. `?token=<jwt>` query parameter.
2. `Authorization: Bearer <jwt>` HTTP header.
3. `Sec-WebSocket-Protocol: access_token:<jwt>` subprotocol.

### Alternatives Considered
- **Session / Cookie Authentication:** Problematic for non-browser TUI clients and cross-subdomain API calls.

### Consequences
- **Pros:** Fully stateless, uniform authentication mechanism across REST and WebSockets.
- **Cons:** Token revocation requires maintaining a token blacklist in Redis/database.

---

## ADR 005: Redis for Ephemeral Presence and Channel Layer

### Context
Live chat requires sub-50ms message distribution and tracking who is currently online without placing write pressure on PostgreSQL.

### Decision
Use **Redis** as:
1. The backend for Django Channels (`channels_redis`).
2. An ephemeral key-value store for user presence (`user:<id>:is_online`) with automatic TTL expiration.

### Alternatives Considered
- **PostgreSQL `LISTEN` / `NOTIFY`:** Lacks built-in channel layer abstractions for Django Channels and increases database connection pressure.
- **Database polling for presence:** Generates excessive database write traffic for transient heartbeat updates.

### Consequences
- **Pros:** Extremely fast pub/sub, zero database overhead for presence/typing indicators.
- **Cons:** Requires running and monitoring a Redis instance alongside PostgreSQL.

---

## ADR 006: Chronological Timestamp Cursor Pagination for Terminal Viewports

### Context
Terminal UIs display messages in fixed line viewports (e.g., 50 lines). Users scroll up (`PageUp`) to load older messages. Standard `page=2` offset pagination suffers from page drift when new messages arrive.

### Decision
Implement cursor pagination using message timestamps:
`GET /chats/rooms/<id>/messages/?limit=50&before=2026-08-16T12:00:00Z`
The server fetches the latest 50 records older than the cursor and returns them in ascending chronological order.

### Alternatives Considered
- **Offset/Limit Pagination (`?page=2&page_size=50`):** Shifts existing offsets as new messages are inserted, leading to duplicate or skipped messages in TUI buffers.

### Consequences
- **Pros:** Immune to message drift; delivers predictable payload slices directly formatted for TUI renderers.
- **Cons:** Requires indexes on `(room_id, sent_at)` for optimal query performance.

---

## ADR 007: Server-Authoritative Sender Resolution

### Context
Initial consumer prototypes accepted `sender` in the client JSON payload, creating an impersonation vulnerability.

### Decision
The backend **must ignore** any client-supplied sender fields. The sender is resolved strictly from `self.user` in the authenticated WebSocket scope and mapped to the corresponding `RoomMembers` record.

### Consequences
- **Pros:** Prevents sender spoofing and ensures data integrity.
- **Cons:** Requires a database lookup on first connection to link the `User` to their workspace `Profile`.