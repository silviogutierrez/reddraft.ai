from datetime import datetime, timezone

from django.http import HttpRequest

from server.drafts.models import Draft, Subreddit
from server.rpc import Pick, Router

rpc = Router()


class UpdateDraftStatusForm(Pick):
    draft_id: int
    status: Draft.Status
    edited_reply: str = ""
    edit_notes: str = ""
    buy_upvotes: bool = False


@rpc()
def update_draft_status(
    request: HttpRequest, form: UpdateDraftStatusForm
) -> dict[str, bool]:
    draft = Draft.objects.get(pk=form.draft_id)
    draft.status = form.status
    draft.reviewed_at = datetime.now(timezone.utc)
    draft.buy_upvotes = form.buy_upvotes

    if form.edited_reply.strip():
        draft.edited_reply = form.edited_reply.strip()
    if form.edit_notes.strip():
        draft.edit_notes = form.edit_notes.strip()

    draft.save()
    return {"ok": True}


class SaveDraftEditsForm(Pick):
    draft_id: int
    draft_reply: str = ""
    edited_reply: str = ""
    edit_notes: str = ""
    notes: str = ""
    buy_upvotes: bool = False


@rpc()
def save_draft_edits(
    request: HttpRequest, form: SaveDraftEditsForm
) -> dict[str, bool]:
    draft = Draft.objects.get(pk=form.draft_id)
    draft.draft_reply = form.draft_reply.strip()
    draft.edited_reply = form.edited_reply.strip()
    draft.edit_notes = form.edit_notes.strip()
    draft.notes = form.notes.strip()
    draft.buy_upvotes = form.buy_upvotes
    draft.save()
    return {"ok": True}


class SaveSubredditForm(Pick):
    name: str
    banned: bool = False
    post_via: Subreddit.PostVia = Subreddit.PostVia.SELF
    daily_limit: int = 3
    weekly_limit: int = 10
    competitors: str = ""
    notes: str = ""


@rpc()
def save_subreddit(
    request: HttpRequest, form: SaveSubredditForm
) -> dict[str, bool]:
    Subreddit.objects.update_or_create(
        name=form.name.strip(),
        defaults={
            "banned": form.banned,
            "post_via": form.post_via,
            "daily_limit": form.daily_limit,
            "weekly_limit": form.weekly_limit,
            "competitors": form.competitors.strip(),
            "notes": form.notes.strip(),
        },
    )
    return {"ok": True}


class DeleteSubredditForm(Pick):
    name: str


@rpc()
def delete_subreddit(
    request: HttpRequest, form: DeleteSubredditForm
) -> dict[str, bool]:
    Subreddit.objects.filter(name=form.name).delete()
    return {"ok": True}


class AddDraftForm(Pick):
    subreddit: str
    post_title: str
    post_url: str
    draft_reply: str
    post_author: str = ""
    post_body: str = ""
    notes: str = ""
    alert_raw: str = ""
    matched_keyword: str = ""


@rpc()
def add_draft(
    request: HttpRequest, form: AddDraftForm
) -> dict[str, int | str]:
    if Draft.objects.filter(post_url=form.post_url).exists():
        existing = Draft.objects.get(post_url=form.post_url)
        return {"error": "duplicate", "existing_id": existing.pk}

    draft = Draft.objects.create(
        subreddit_name=form.subreddit,
        post_title=form.post_title,
        post_url=form.post_url,
        post_author=form.post_author,
        post_body=form.post_body,
        draft_reply=form.draft_reply,
        notes=form.notes,
        alert_raw=form.alert_raw,
        matched_keyword=form.matched_keyword,
    )
    return {"id": draft.pk, "status": "pending"}
