import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from core.managers import UserManager


class User(AbstractUser):  # No RLS applied, as this is global ACL
    username = None
    id = models.UUIDField(
        default=uuid.uuid4, primary_key=True, editable=False
    )  # TODO: Use uuid7 and indexes for performance, confirm whether it is supported yet or not.
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    tenants_joined = models.ManyToManyField(
        "Tenant", through="Profile", through_fields=("user", "tenant")
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return f"{self.name} <{self.email}>"


class Tenant(models.Model):  # No RLS applied, as this is global ACL
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    name = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(
        User,
        related_name="creator",
        related_query_name="creator",
        on_delete=models.CASCADE,
    )
    is_public = models.BooleanField(default=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# Basically each user can belong to multiple tenants,
# hence we will connect User and Tenants with each other
# using FK, but also add this profile 'through' model
# inbetween them, so that we can store data separately for
# each User and each Tenant it belongs
class Profile(models.Model):  # No RLS applied, as this is global ACL
    user = models.ForeignKey(
        User,
        related_name="profiles",
        related_query_name="profiles",
        on_delete=models.CASCADE,
    )
    tenant = models.ForeignKey(
        Tenant,
        related_name="members",
        related_query_name="members",
        on_delete=models.CASCADE,
    )
    username = models.CharField(max_length=64)
    role = models.CharField(max_length=64, default="member")
    tags = models.JSONField(null=True, blank=True, default=list)
    invited_by = models.ForeignKey(
        User,
        related_name="invited_members",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    accepted_by = models.ForeignKey(
        User,
        related_name="accepted_members",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "tenant"], name="unique_constraint_user_tenant"
            ),
            models.UniqueConstraint(
                fields=["username", "tenant"], name="unique_constraint_username_tenant"
            ),
        ]

    def __str__(self):
        return f"{self.username} ({self.tenant.name})"


class TenantInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    tenant = models.ForeignKey(
        Tenant, related_name="invitations", on_delete=models.CASCADE
    )
    invited_user = models.ForeignKey(
        User, related_name="invitations_received", on_delete=models.CASCADE
    )
    invited_by = models.ForeignKey(
        User, related_name="invitations_sent", on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class TenantJoinRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    tenant = models.ForeignKey(
        Tenant, related_name="join_requests", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User, related_name="join_requests", on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
