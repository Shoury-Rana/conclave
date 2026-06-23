import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from core.managers import UserManager


class User(AbstractUser):       # No applied, as this is global ACL
    username = None
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False) # TODO: Use uuid7 and indexes for performance, confirm whether it is supported yet or not.
    email = models.EmailField(unique=True)

    name = models.CharField(null=False, blank=False)

    tenants_joined = models.ManyToManyField('Tenant', through='Profile', through_fields=('user', 'tenant'))

    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []


# Basically each user can belong to multiple tenants,
# hence we will connect User and Tenants with each other
# using FK, but also add this profile 'through' model
# inbetween them, so that we can store data separately for
# each User and each Tenant it belongs
class Profile(models.Model):        # No applied, as this is global ACL
    user = models.ForeignKey('User', related_name='user', related_query_name='user', on_delete=models.CASCADE)
    tenant = models.ForeignKey('Tenant', related_name='tenant', related_query_name='tenant', on_delete=models.CASCADE)

    username = models.CharField(max_length=64, null=False, blank=False)
    role = models.CharField(max_length=64, null=True, blank=True)
    tags = models.JSONField(null=True, blank=True)
    invited_by = models.ForeignKey('User', related_name='invited', related_query_name='invited', on_delete=models.CASCADE, null=True, blank=True)
    accepted_by = models.ForeignKey('User', related_name='accepted', related_query_name='accepted', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'tenant'], name='unique_constraint_user_tenant'),
            models.UniqueConstraint(fields=['username', 'tenant'], name='unique_constraint_username_tenant')
        ]


class Tenant(models.Model):         # No applied, as this is global ACL
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    name = models.CharField(max_length=64, unique=True, null=False, blank=False)
    created_by = models.ForeignKey('User', related_name='creator', related_query_name='creator', on_delete=models.CASCADE)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)

