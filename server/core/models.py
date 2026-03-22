import uuid

from django.db import models

from upstream.user import AbstractEmailUser


class Model(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def is_new(self) -> bool:
        return self.pk is None


class User(AbstractEmailUser, Model):
    pass
