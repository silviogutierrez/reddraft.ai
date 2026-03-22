from django.contrib import admin

from upstream.admin import EmailUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(EmailUserAdmin):
    pass
