"""Process F5Bot alert emails, create drafts in the queue."""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from django.core.management.base import BaseCommand

from server.drafts.models import Draft

ACCOUNT = "ava@joyapptracker.com"

AUTOMOD_SUBS = {"BodyOptimization", "BiohackingU"}


def gws_env() -> dict[str, str]:
    return {**os.environ, "GOOGLE_WORKSPACE_CLI_ACCOUNT": ACCOUNT}


def run_gws(args: list[str]) -> str:
    result = subprocess.run(
        ["gws", *args],
        capture_output=True,
        text=True,
        timeout=30,
        env=gws_env(),
    )
    return result.stdout.strip()


def extract_email_body(payload: dict[str, Any]) -> str:
    """Walk Gmail MIME payload tree to find and decode the text/plain body."""
    if "parts" in payload:
        for part in payload["parts"]:
            result = extract_email_body(part)
            if result:
                return result
    elif payload.get("mimeType") == "text/plain" and payload.get("body", {}).get(
        "data"
    ):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode()
    return ""


def get_email_header(headers: list[dict[str, str]], name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def search_f5bot_emails(max_results: int = 20) -> list[dict[str, Any]]:
    raw = run_gws(
        [
            "gmail",
            "users",
            "messages",
            "list",
            "--params",
            json.dumps(
                {
                    "userId": "me",
                    "q": "from:f5bot is:unread",
                    "maxResults": max_results,
                }
            ),
        ]
    )
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"Failed to parse message list: {raw[:200]}")
        return []

    message_ids = [m["id"] for m in data.get("messages", [])]
    if not message_ids:
        return []

    emails: list[dict[str, Any]] = []
    for msg_id in message_ids:
        msg_raw = run_gws(
            [
                "gmail",
                "users",
                "messages",
                "get",
                "--params",
                json.dumps(
                    {
                        "userId": "me",
                        "id": msg_id,
                        "format": "full",
                    }
                ),
            ]
        )
        if not msg_raw:
            continue
        try:
            msg = json.loads(msg_raw)
        except json.JSONDecodeError:
            continue

        headers = msg.get("payload", {}).get("headers", [])
        emails.append(
            {
                "id": msg["id"],
                "threadId": msg.get("threadId", msg["id"]),
                "subject": get_email_header(headers, "Subject"),
                "from": get_email_header(headers, "From"),
                "body": extract_email_body(msg.get("payload", {})),
            }
        )

    return emails


def parse_f5bot_alert(body: str) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []

    sections = re.split(r'(?=Keyword:\s*")', body)

    for section in sections:
        if not section.strip().startswith("Keyword:"):
            continue
        alert: dict[str, str] = {}

        kw_match = re.search(r'Keyword:\s*"([^"]+)"', section)
        if kw_match:
            alert["matched_keyword"] = kw_match.group(1)

        sub_match = re.search(
            r"Reddit (?:Comments|Posts) \(/r/([^/]+)/\):\s*(.+?)(?:\n|<)", section
        )
        if sub_match:
            alert["subreddit"] = sub_match.group(1)
            title_raw = sub_match.group(2).strip()
            title_raw = re.sub(r"\s+by\s+\S+\s*$", "", title_raw)
            title_raw = title_raw.strip("'\"\u2018\u2019\u201c\u201d")
            alert["post_title"] = title_raw

        url_match = re.search(r"https://f5bot\.com/url\?u=([^&\s>]+)", section)
        if url_match:
            alert["post_url"] = urllib.parse.unquote(url_match.group(1))

        author_match = re.search(
            r"['\u2018\u2019].*?['\u2018\u2019]\s+by\s+(\S+)", section
        ) or re.search(r"\nby\s+(\S+)", section)
        if author_match:
            alert["post_author"] = author_match.group(1)

        body_match = re.search(
            r"https://f5bot\.com/url\S+\n(.+?)(?:\n\nDo you have comments|\n\nKeyword:|\n\n[\U0001f4f8\U0001f30e\U0001f4c9\u26a1\u2705\U0001f449\U0001f680*]|\nWant to advertise|$)",
            section,
            re.DOTALL,
        )
        if body_match:
            alert["post_body"] = body_match.group(1).strip().replace("*", "")

        if alert.get("subreddit") and alert.get("post_url"):
            alerts.append(alert)

    return alerts


def is_automod_noise(alert: dict[str, str]) -> bool:
    return alert.get("post_author") == "AutoModerator"


def is_already_joyapp(alert: dict[str, str]) -> bool:
    body = (alert.get("post_body") or "").lower()
    return "joyapp.com" in body


def extract_reddit_thread_url(url: str) -> str:
    match = re.match(r"(https://www\.reddit\.com/r/[^/]+/comments/[^/]+/[^/]*/)", url)
    if match:
        return match.group(1)
    return url


def extract_post_id(url: str) -> str | None:
    match = re.search(r"/comments/([a-z0-9]+)", url)
    return match.group(1) if match else None


def thread_already_in_queue(post_id: str) -> bool:
    return Draft.objects.filter(post_url__contains=f"/comments/{post_id}/").exists()


def fetch_op_text(url: str) -> dict[str, str] | None:
    thread_url = extract_reddit_thread_url(url)
    json_url = thread_url.rstrip("/") + ".json?limit=1"

    req = urllib.request.Request(
        json_url,
        headers={"User-Agent": "outreach/1.0 by brosterdamus"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        post = data[0]["data"]["children"][0]["data"]
        return {
            "op_title": post.get("title", ""),
            "op_body": post.get("selftext", ""),
            "op_author": post.get("author", ""),
            "op_url": f"https://www.reddit.com{post.get('permalink', '')}",
        }
    except Exception as e:
        print(f"  Failed to fetch OP text: {e}")
        return None


def push_to_queue(alert: dict[str, str]) -> Draft | None:
    post_id = extract_post_id(alert["post_url"])
    if post_id and thread_already_in_queue(post_id):
        print(f"  Thread already in queue: r/{alert['subreddit']}")
        return None

    op = fetch_op_text(alert["post_url"])
    time.sleep(1)

    if op:
        if "joyapp.com" in (op["op_body"] or "").lower():
            print(f"  OP already has joyapp link, skipping: r/{alert['subreddit']}")
            return None
        post_title = op["op_title"]
        post_body = op["op_body"]
        post_author = op["op_author"]
        post_url = op["op_url"]
        note_extra = f"F5Bot matched comment by u/{alert.get('post_author', '?')}."
    else:
        post_title = alert.get("post_title", "")
        post_body = alert.get("post_body", "")
        post_author = alert.get("post_author", "")
        post_url = alert["post_url"]
        note_extra = "Failed to fetch OP text, using F5Bot comment data as fallback."

    if Draft.objects.filter(post_url=post_url).exists():
        existing = Draft.objects.get(post_url=post_url)
        print(
            f"  Duplicate (existing #{existing.pk}): r/{alert['subreddit']}: {alert.get('post_title', '')[:60]}"
        )
        return None

    draft = Draft.objects.create(
        subreddit_name=alert["subreddit"],
        post_title=post_title,
        post_url=post_url,
        post_author=post_author,
        post_body=post_body,
        draft_reply="",
        matched_keyword=alert.get("matched_keyword", ""),
        notes=f"Auto-ingested from F5Bot alert. Keyword: {alert.get('matched_keyword', 'unknown')}. {note_extra}",
    )
    print(
        f"  Queued draft #{draft.pk} for r/{alert['subreddit']}: {alert.get('post_title', '')[:60]}"
    )
    return draft


def archive_email(message_id: str, thread_id: str | None = None) -> None:
    tid = thread_id or message_id
    run_gws(
        [
            "gmail",
            "users",
            "threads",
            "modify",
            "--params",
            json.dumps({"userId": "me", "id": tid}),
            "--json",
            json.dumps({"removeLabelIds": ["INBOX", "UNREAD"]}),
        ]
    )


class Command(BaseCommand):
    help = "Process F5Bot alert emails and create drafts"

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(
            f"F5Bot Email Processor — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.stdout.write(f"{'=' * 60}")

        emails = search_f5bot_emails()
        if not emails:
            self.stdout.write("No unread F5Bot emails found.")
            return

        self.stdout.write(f"Found {len(emails)} unread F5Bot email(s)")

        total_queued = 0
        total_skipped = 0
        total_alerts = 0

        for email in emails:
            subject = email.get("subject", "")
            body = email.get("body", "")
            msg_id = email.get("id", "")

            if (
                "f5bot" not in subject.lower()
                and "f5bot" not in email.get("from", "").lower()
            ):
                self.stdout.write(f"  Skipping non-F5Bot email: {subject[:60]}")
                continue

            alerts = parse_f5bot_alert(body)
            self.stdout.write(f"\n{subject[:70]} — {len(alerts)} alert(s)")

            for alert in alerts:
                total_alerts += 1

                if is_automod_noise(alert):
                    self.stdout.write(
                        f"  Skipping AutoMod post in r/{alert['subreddit']}"
                    )
                    total_skipped += 1
                    continue

                if is_already_joyapp(alert):
                    self.stdout.write(
                        f"  Already has joyapp link, skipping: r/{alert['subreddit']}"
                    )
                    total_skipped += 1
                    continue

                result = push_to_queue(alert)
                if result:
                    total_queued += 1

            thread_id = email.get("threadId", msg_id)
            if thread_id:
                archive_email(msg_id, thread_id=thread_id)
                self.stdout.write(f"  Archived email {msg_id[:12]}...")

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(
            f"Done: {total_alerts} alerts, {total_queued} queued, {total_skipped} skipped"
        )
        self.stdout.write(f"{'=' * 60}\n")
