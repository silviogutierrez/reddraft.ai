from enum import Enum

from django.db import models
from reactivated.fields import EnumField

from server.core.models import Model


class Subreddit(Model):
    class PostVia(Enum):
        SELF = "Self"
        CROWDREPLY = "CrowdReply"

    name = models.CharField(max_length=255, unique=True)
    banned = models.BooleanField(default=False)
    post_via = EnumField(enum=PostVia, default=PostVia.SELF)
    daily_limit = models.IntegerField(default=3)
    weekly_limit = models.IntegerField(default=10)
    competitors = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class Draft(Model):
    class Status(Enum):
        PENDING = "Pending"
        APPROVED = "Approved"
        REJECTED = "Rejected"
        POSTED = "Posted"
        SKIPPED = "Skipped"

    class Action(Enum):
        LINK = "Link"
        ADVICE_ONLY = "Advice Only"
        REJECT = "Reject"

    status = EnumField(enum=Status, default=Status.PENDING)
    subreddit_name = models.CharField(max_length=255)
    post_title = models.CharField(max_length=500)
    post_url = models.URLField(max_length=500, unique=True)
    post_author = models.CharField(max_length=255, blank=True)
    post_body = models.TextField(blank=True)
    draft_reply = models.TextField(blank=True)
    draft_reply_b = models.TextField(blank=True)
    draft_reply_c = models.TextField(blank=True)
    selected_variant = models.CharField(max_length=1, blank=True)
    edited_reply = models.TextField(blank=True)
    edit_notes = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    alert_raw = models.TextField(blank=True)
    matched_keyword = models.CharField(max_length=255, blank=True)
    buy_upvotes = models.BooleanField(default=False)
    action = EnumField(enum=Action, null=True, blank=True)
    triage_reasoning = models.TextField(blank=True)
    tracking_code = models.CharField(max_length=100, blank=True)
    confidence = models.IntegerField(null=True, blank=True)
    upvotes_needed = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"#{self.pk} {self.subreddit_name}: {self.post_title[:60]}"
