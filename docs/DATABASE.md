# Note: This is AI-generated based on models.py

# Database Design

## Database Technology

* PostgreSQL
* Django ORM

## Overview

Conclave uses a shared-database, shared-schema multi-tenant architecture.

Tenant isolation is enforced at the application layer using tenant context derived from the request subdomain.

All tenant-specific queries must be filtered by the resolved tenant identifier.

Users exist globally and may belong to multiple tenants.

## ER Diagram

See `docs/diagrams/er-diagram.dbml`.

### Relationship Summary

* One User can create multiple Tenants.
* One User can belong to multiple Tenants.
* One Tenant can have multiple Users.
* The `Profile` model acts as a junction table between `User` and `Tenant`.
* Tenant-specific user information is stored in `Profile`.

---

## Tables

### User

Purpose: Stores global account information and authentication data.

This entity exists outside tenant boundaries and serves as the global identity provider for the application.

#### Key Fields

* `id` — UUID primary key
* `email` — unique login identifier
* `name` — display name

#### Authentication

* Email-based authentication
* JWT tokens issued after successful login

#### Indexes

* Primary key index on `id`
* Unique index on `email`

#### Constraints

* `email` must be globally unique
* `email` cannot be null
* Users may belong to multiple tenants

---

### Tenant

Purpose: Represents an isolated workspace identified by a unique subdomain.

Each tenant contains its own members, settings, and resources.

#### Key Fields

* `id` — UUID primary key
* `name` — unique tenant identifier
* `created_by` — owner of the tenant
* `creation_date`
* `last_update`

#### Indexes

* Primary key index on `id`
* Unique index on `name`
* Foreign key index on `created_by`

#### Constraints

* `name` must be globally unique
* `created_by` must reference an existing user
* Deleting the creator deletes the tenant

#### Tenant Resolution

Incoming requests are mapped to a tenant using the request subdomain.

Example:

```text
acme.example.com → Tenant(name="acme")
```

---

### Profile

Purpose: Stores tenant-specific membership information.

Although named `Profile` in the codebase, this model functions as a membership table connecting users and tenants.

A single user can have different identities and permissions across tenants.

Examples:

* Different usernames per tenant
* Different roles per tenant
* Tenant-specific metadata

#### Key Fields

* `user`
* `tenant`
* `username`
* `role`
* `tags`
* `invited_by`
* `accepted_by`

#### Indexes

* Foreign key index on `user`
* Foreign key index on `tenant`
* Foreign key index on `invited_by`
* Foreign key index on `accepted_by`

#### Constraints

* Unique `(user, tenant)` pair
* Unique `(username, tenant)` pair

#### Business Rules

* A user cannot join the same tenant more than once.
* Usernames are unique within a tenant.
* The same username may exist across different tenants.
* Roles are scoped to a tenant.
* Tags are tenant-specific.

---

## Relationships

```text
User (1) ────────< Tenant

User (M) ────────< Profile >──────── (M) Tenant

User (1) ────────< Profile.invited_by

User (1) ────────< Profile.accepted_by
```

### Cardinality

* User → Tenant (creator): One-to-Many
* User ↔ Tenant (membership): Many-to-Many through `Profile`
* User → Profile (inviter): One-to-Many
* User → Profile (acceptor): One-to-Many

---

## Tenant Isolation Strategy

Conclave uses logical tenant isolation.

All tenant-specific operations require the current tenant context to be resolved before accessing data.

The following rules apply:

* Tenant context is derived from the request subdomain.
* Cross-tenant data access is prohibited.
* Membership validation is required before accessing tenant resources.
* Authorization decisions are performed using the `Profile` model.

Example:

```text
Request: acme.example.com/members/

1. Resolve tenant "acme"
2. Verify requesting user belongs to tenant
3. Filter records by tenant_id
4. Return tenant-scoped data only
```

---

## Future Considerations

* Evaluate UUIDv7 support for improved index locality and insertion performance.
* Add explicit indexes for frequently queried fields if usage patterns require them.
* Define a formal role system with enumerated values.
* Consider database-level row security if stronger tenant isolation becomes necessary.
* Evaluate soft deletion for tenants and memberships.
* Introduce audit logging for membership lifecycle events.

```
```
