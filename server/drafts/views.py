from datetime import timedelta

from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from server.rpc import Pick, Template

from .models import Draft, Subreddit


class SubredditConfig(Pick):
    name: str
    banned: bool
    post_via: Subreddit.PostVia
    daily_limit: int
    weekly_limit: int
    competitors: str
    notes: str


class DraftSummary(Pick):
    id: int
    status: Draft.Status
    subreddit_name: str
    post_title: str
    post_author: str
    draft_reply: str
    edited_reply: str
    edit_notes: str
    matched_keyword: str
    created_at: str


TABS = {
    "pending": Draft.Status.PENDING,
    "approved": Draft.Status.APPROVED,
    "rejected": Draft.Status.REJECTED,
    "posted": Draft.Status.POSTED,
}


class QueuePage(Template):
    drafts: list[DraftSummary]
    tab: str
    counts: dict[str, int]
    subreddit_configs: dict[str, SubredditConfig]
    today_counts: dict[str, int]
    weekly_counts: dict[str, int]


def queue_page(request: HttpRequest) -> HttpResponse:
    tab = request.GET.get("tab", "pending")

    if tab == "all":
        drafts_qs = Draft.objects.all()
    elif tab in TABS:
        drafts_qs = Draft.objects.filter(status=TABS[tab])
    else:
        drafts_qs = Draft.objects.filter(status=Draft.Status.PENDING)
    drafts_qs = drafts_qs.order_by("-created_at")

    counts: dict[str, int] = {}
    for key, enum_val in TABS.items():
        counts[key] = Draft.objects.filter(status=enum_val).count()
    counts["all"] = sum(counts.values())

    sub_config: dict[str, SubredditConfig] = {}
    for sub in Subreddit.objects.all():
        sub_config[sub.name] = SubredditConfig(
            name=sub.name,
            banned=sub.banned,
            post_via=sub.post_via,
            daily_limit=sub.daily_limit,
            weekly_limit=sub.weekly_limit,
            competitors=sub.competitors,
            notes=sub.notes,
        )

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    today_counts: dict[str, int] = {}
    for row in (
        Draft.objects.filter(status=Draft.Status.POSTED, posted_at__gte=today_start)
        .values("subreddit_name")
        .annotate(cnt=Count("id"))
    ):
        today_counts[row["subreddit_name"]] = row["cnt"]

    weekly_counts: dict[str, int] = {}
    for row in (
        Draft.objects.filter(status=Draft.Status.POSTED, posted_at__gte=week_ago)
        .values("subreddit_name")
        .annotate(cnt=Count("id"))
    ):
        weekly_counts[row["subreddit_name"]] = row["cnt"]

    draft_summaries = [
        DraftSummary(
            id=d.pk,
            status=d.status,
            subreddit_name=d.subreddit_name,
            post_title=d.post_title,
            post_author=d.post_author,
            draft_reply=d.draft_reply,
            edited_reply=d.edited_reply,
            edit_notes=d.edit_notes,
            matched_keyword=d.matched_keyword,
            created_at=d.created_at.isoformat(),
        )
        for d in drafts_qs
    ]

    return QueuePage(
        drafts=draft_summaries,
        tab=tab,
        counts=counts,
        subreddit_configs=sub_config,
        today_counts=today_counts,
        weekly_counts=weekly_counts,
    ).render(request)


class DraftDetail(Pick):
    id: int
    status: Draft.Status
    subreddit_name: str
    post_title: str
    post_url: str
    post_author: str
    post_body: str
    draft_reply: str
    edited_reply: str
    edit_notes: str
    notes: str
    matched_keyword: str
    buy_upvotes: bool
    action: Draft.Action | None
    triage_reasoning: str
    tracking_code: str
    confidence: int | None
    upvotes_needed: int | None
    reviewed_at: str | None
    created_at: str


class SubredditInfo(Pick):
    name: str
    banned: bool
    post_via: Subreddit.PostVia
    daily_limit: int
    weekly_limit: int
    competitors: str
    notes: str


class DraftPage(Template):
    draft: DraftDetail
    sub_info: SubredditInfo | None
    today_count: int


def draft_page(request: HttpRequest, draft_id: int) -> HttpResponse:
    draft = Draft.objects.get(pk=draft_id)

    sub_info: SubredditInfo | None = None
    try:
        sub = Subreddit.objects.get(name=draft.subreddit_name)
        sub_info = SubredditInfo(
            name=sub.name,
            banned=sub.banned,
            post_via=sub.post_via,
            daily_limit=sub.daily_limit,
            weekly_limit=sub.weekly_limit,
            competitors=sub.competitors,
            notes=sub.notes,
        )
    except Subreddit.DoesNotExist:
        pass

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = Draft.objects.filter(
        subreddit_name=draft.subreddit_name,
        status=Draft.Status.POSTED,
        posted_at__gte=today_start,
    ).count()

    detail = DraftDetail(
        id=draft.pk,
        status=draft.status,
        subreddit_name=draft.subreddit_name,
        post_title=draft.post_title,
        post_url=draft.post_url,
        post_author=draft.post_author,
        post_body=draft.post_body,
        draft_reply=draft.draft_reply,
        edited_reply=draft.edited_reply,
        edit_notes=draft.edit_notes,
        notes=draft.notes,
        matched_keyword=draft.matched_keyword,
        buy_upvotes=draft.buy_upvotes,
        action=draft.action,
        triage_reasoning=draft.triage_reasoning,
        tracking_code=draft.tracking_code,
        confidence=draft.confidence,
        upvotes_needed=draft.upvotes_needed,
        reviewed_at=draft.reviewed_at.isoformat() if draft.reviewed_at else None,
        created_at=draft.created_at.isoformat(),
    )

    return DraftPage(
        draft=detail,
        sub_info=sub_info,
        today_count=today_count,
    ).render(request)


class SubredditRow(Pick):
    name: str
    banned: bool
    post_via: Subreddit.PostVia
    daily_limit: int
    weekly_limit: int
    competitors: str
    notes: str
    today_used: int
    weekly_used: int


class SubredditsPage(Template):
    subreddits: list[SubredditRow]


def subreddits_page(request: HttpRequest) -> HttpResponse:
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    today_counts: dict[str, int] = {}
    for row in (
        Draft.objects.filter(status=Draft.Status.POSTED, posted_at__gte=today_start)
        .values("subreddit_name")
        .annotate(cnt=Count("id"))
    ):
        today_counts[row["subreddit_name"]] = row["cnt"]

    weekly_counts: dict[str, int] = {}
    for row in (
        Draft.objects.filter(status=Draft.Status.POSTED, posted_at__gte=week_ago)
        .values("subreddit_name")
        .annotate(cnt=Count("id"))
    ):
        weekly_counts[row["subreddit_name"]] = row["cnt"]

    subs = Subreddit.objects.order_by("-banned", "name")
    rows = [
        SubredditRow(
            name=s.name,
            banned=s.banned,
            post_via=s.post_via,
            daily_limit=s.daily_limit,
            weekly_limit=s.weekly_limit,
            competitors=s.competitors,
            notes=s.notes,
            today_used=today_counts.get(s.name, 0),
            weekly_used=weekly_counts.get(s.name, 0),
        )
        for s in subs
    ]

    return SubredditsPage(subreddits=rows).render(request)
