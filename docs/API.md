# Conclave API Reference

## 1. Authentication & Identity (Root Domain)

### `POST /auth/signup/`
Registers a new user and returns JWT tokens.
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword",
    "name": "Alex"
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "name": "Alex"
    },
    "access_token": "jwt...",
    "refresh_token": "jwt..."
  }
  ```

### `POST /auth/login/`
Authenticates an existing user.
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword"
  }
  ```

### `POST /auth/token/refresh/`
Refreshes an expired access token.
- **Request Body:**
  ```json
  {
    "refresh": "jwt..."
  }
  ```

### `GET /auth/me/` (or `GET /profile/me/`)
Returns the authenticated user's profile and workspaces.

---

## 2. Workspace Management (Root Domain)

### `GET /tenant/mine/`
List all workspaces the authenticated user belongs to or owns.

### `GET /tenant/search/?q=tech`
Search public workspaces.

### `POST /tenant/`
Create a new workspace.
- **Request Body:**
  ```json
  {
    "name": "acme",
    "is_public": true
  }
  ```

### `POST /tenant/join/`
Join a public workspace or submit a request to a private workspace.
- **Request Body:**
  ```json
  {
    "tenant_name": "acme"
  }
  ```

---

## 3. Workspace Operations (Subdomain Scoped: `acme.conclave.app`)

### `GET /`
Workspace overview, member count, and room count.

### `GET /members/`
List workspace members with realtime `is_online` status indicators.

### `POST /invite/`
Invite a user by email to the current workspace.

### `GET /chats/rooms/`
List all chat channels and direct messages in the current workspace.

### `POST /chats/rooms/`
Create a new chat room/channel.
- **Request Body:**
  ```json
  {
    "name": "engineering",
    "type": "TENANT_CHATS"
  }
  ```

### `POST /chats/dm/<uuid:target_user_id>/`
Get or create a 1-on-1 Direct Message room.

### `GET /chats/rooms/<uuid:room_id>/messages/?limit=50&before=2026-08-16T12:00:00Z`
Fetch chronological message history for terminal viewports with cursor pagination.

### `GET /chats/rooms/<uuid:room_id>/read-states/`
Get unread badge count and last read message ID.

---

## 4. WebSocket Streaming Protocol

**Connection URL:**
`ws://acme.conclave.app/ws/chat/?token=<JWT_ACCESS_TOKEN>&room_id=<ROOM_UUID>`

### Client to Server Payloads:

1. **Send Message:**
   ```json
   {
     "type": "message_send",
     "message": "Hello from the TUI!"
   }
   ```
2. **Mark Message as Read:**
   ```json
   {
     "type": "mark_read",
     "message_id": "message-uuid"
   }
   ```
3. **Typing Indicator:**
   ```json
   { "type": "typing_start" }
   { "type": "typing_stop" }
   ```

### Server to Client Events:

1. **New Message:**
   ```json
   {
     "type": "message_send",
     "id": "uuid",
     "room_id": "uuid",
     "sender_id": "uuid",
     "sender_name": "Alex",
     "sender_username": "alex",
     "content": "Hello from the TUI!",
     "sent_at": "2026-08-16T12:00:00Z"
   }
   ```
2. **User Presence:**
   ```json
   {
     "type": "presence",
     "user_id": "uuid",
     "user_name": "Alex",
     "status": "online"
   }
   ```
3. **Typing Event:**
   ```json
   {
     "type": "typing",
     "user_id": "uuid",
     "user_name": "Alex",
     "typing": true
   }
   ```
