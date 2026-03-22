from __future__ import annotations

from typing import Any, ClassVar

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager["AbstractEmailUser"]):
    def create_user(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> AbstractEmailUser:
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> AbstractEmailUser:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

    def get_by_natural_key(self, username: str | None) -> AbstractEmailUser:
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})


class AbstractEmailUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=255, unique=True, verbose_name="email address")
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD: ClassVar[str] = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return self.email
