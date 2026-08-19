# Conclave — Project Overview

## 1. Executive Summary

**Conclave** is an open, high-performance, multi-tenant real-time chat platform engineered for developer teams, sysadmins, and communities. It combines strict tenant isolation, PostgreSQL Row-Level Security (RLS), stateless JWT authentication, and bi-directional WebSocket event streaming. 

While Conclave supports web clients, it is intentionally optimized for **Terminal User Interfaces (TUIs)** and CLI clients, offering low-overhead JSON REST endpoints, predictable cursor pagination, and reliable WebSocket event streaming.

---

## 2. Problem Statement

Existing enterprise and community messaging platforms suffer from several fundamental trade-offs:
1. **Bloated Client Footprint:** Mainstream platforms (Slack, Discord, Teams) rely on heavy Electron apps consuming gigabytes of memory and lack first-class keyboard-driven terminal interfaces.
2. **Weak or Complex Multi-Tenancy:** Multi-tenant systems often either compromise on data isolation (leaking cross-tenant data due to application bug slips) or introduce operational complexity (schema-per-tenant or database-per-tenant migrations).
3. **Impedance Mismatch with TUI Workflows:** Most APIs are built around rich web paradigms (nested WYSIWYG, infinite scroll DOM trees) rather than fixed-viewport terminal screens requiring deterministic message history and fast keyboard navigation.

Conclave solves this by pairing a **subdomain-isolated, RLS-backed backend** with a **predictable, terminal-optimized API surface**.

---

## 3. Target Audience & Personas

- **Engineers & DevOps Teams:** Users who live in terminal environments (tmux, vim, zsh) and want real-time communication without leaving their command line.
- **Multi-Workspace Organizations:** Companies and open-source networks needing isolated workspaces for distinct teams, projects, or clients within a single deployment.
- **System Administrators:** Operators seeking a lean, horizontally scalable chat backend with low infrastructure overhead (PostgreSQL + Redis + Django ASGI).

---

## 4. Core Use Cases

### A. Workspace & Tenant Discovery
- Users register once globally and can create or join multiple isolated workspaces.
- Workspaces can be **Public** (searchable and open to join) or **Private** (requiring an invitation or an owner-approved join request).
- Dynamic subdomain routing maps `acme.conclave.app` directly to the `acme` workspace.

### B. Channel & Direct Messaging
- **Broadcast / Channels:** Public or team-wide channels within a workspace (e.g., `#general`, `#devops`).
- **1-on-1 Direct Messages (DMs):** Deterministically resolved DM rooms between workspace members without duplicating channel infrastructure.
- **Message History & Viewport Scrolling:** Timestamp-based cursor pagination (`?limit=50&before=<timestamp>`) designed for terminal `PageUp` / scrollback buffers.

### C. Real-Time Streaming & Ephemeral State
- **Bi-directional WebSockets:** Sub-50ms message delivery across all connected workspace members.
- **Live User Presence:** Real-time online/offline indicators powered by Redis TTL keys.
- **Typing Indicators:** Lightweight transient events to display who is typing without database writes.
- **Read Receipts & Unread Badges:** Per-user last-read message tracking to compute accurate unread counts (`[#general (4)]`).

---

## 5. System Assumptions & Operational Constraints

| Dimension | Specification / Constraint |
|---|---|
| **Identity Model** | Global identity (`User`); tenant-scoped membership profile (`Profile`). |
| **Data Isolation** | Shared-database, shared-schema enforced via PostgreSQL Row-Level Security (RLS) + Django Middleware. |
| **Tenant Routing** | Primary: HTTP Host subdomain (`<tenant>.domain.com`). Fallback: `X-Tenant` header / `?tenant=` query param. |
| **Authentication** | Stateless JWT (Access + Refresh tokens with blacklisting on rotation). |
| **Realtime Transport** | ASGI WebSockets via Django Channels backed by Redis Channel Layer. |
| **Database Engine** | PostgreSQL 14+ (relies on PostgreSQL `set_config` and RLS policies). SQLite supported in dev/tests. |

---

## 6. Requirements Breakdown

### Functional Requirements
1. **Global Auth & Account Management:** User registration, credential authentication, JWT token refresh, and personal profile management.
2. **Multi-Tenant Workspace Lifecycle:** Workspace creation, search, public joining, invitations with email lookup, and join request approval/rejection workflows.
3. **Chat Room Management:** Creating channels, auto-joining creator, deterministic DM creation between workspace members.
4. **Message Delivery & History:** Storing messages with server-authoritative timestamps, fetching message history with limit/before pagination.
5. **Real-time Event Streaming:** WebSocket connections delivering messages, typing indicators, presence events, and read acknowledgments.

### Non-Functional Requirements
1. **Low Latency:** WebSocket broadcast latency under 50ms under typical loads.
2. **Security & Spoof Protection:** The backend authoritatively resolves the authenticated user and their workspace profile for all message creations.
3. **Tenant Boundary Guarantees:** Zero data leakage across tenants, guaranteed at both application middleware and database RLS layers.
4. **Stateless Scalability:** ASGI workers can scale horizontally behind a load balancer with Redis coordinating pub/sub state.