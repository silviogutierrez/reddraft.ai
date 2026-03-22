from django.contrib import admin

from .models import Draft, Subreddit


@admin.register(Subreddit)
class SubredditAdmin(admin.ModelAdmin[Subreddit]):
    list_display = ("name", "banned", "post_via", "daily_limit", "weekly_limit")
    list_filter = ("banned", "post_via")
    search_fields = ("name",)


@admin.register(Draft)
class DraftAdmin(admin.ModelAdmin[Draft]):
    list_display = (
        "id",
        "status",
        "subreddit_name",
        "post_title",
        "action",
        "confidence",
        "created_at",
    )
    list_filter = ("status", "action", "buy_upvotes")
    search_fields = ("subreddit_name", "post_title", "post_url", "draft_reply")
    readonly_fields = ("uuid", "created_at", "updated_at")
