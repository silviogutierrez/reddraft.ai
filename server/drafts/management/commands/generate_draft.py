"""v2 draft generation: triage -> tracking link -> reply, using structured outputs."""

from __future__ import annotations

import json
import re
import sys
from typing import Any
from urllib.request import Request, urlopen

import anthropic
import praw
from django.conf import settings
from django.core.management.base import BaseCommand

from server.drafts.models import Draft, Subreddit

MODEL = "claude-sonnet-4-6"
MAX_VOICE_CHARS = 350_000

TRIAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["LINK", "ADVICE_ONLY", "REJECT"],
        },
        "reasoning": {"type": "string"},
        "confidence": {
            "type": "integer",
            "enum": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        },
        "extracted_params": {
            "type": "object",
            "properties": {
                "peptide": {"type": ["string", "null"]},
                "vial": {"type": ["string", "null"]},
                "vial_unit": {"type": ["string", "null"]},
                "dose": {"type": ["string", "null"]},
                "dose_unit": {"type": ["string", "null"]},
                "syringe": {"type": ["string", "null"]},
                "water": {"type": ["string", "null"]},
            },
            "required": [
                "peptide",
                "vial",
                "vial_unit",
                "dose",
                "dose_unit",
                "syringe",
                "water",
            ],
            "additionalProperties": False,
        },
        "upvotes_needed": {
            "type": ["integer", "null"],
        },
    },
    "required": [
        "action",
        "reasoning",
        "confidence",
        "extracted_params",
        "upvotes_needed",
    ],
    "additionalProperties": False,
}


def parse_reddit_url(url: str) -> tuple[str, str | None]:
    sub_match = re.search(r"/comments/([a-z0-9]+)", url)
    if not sub_match:
        raise ValueError(f"Could not extract submission ID from: {url}")

    submission_id = sub_match.group(1)

    com_match = re.search(r"/comments/[a-z0-9]+/[^/]*/([a-z0-9]+)", url)
    if not com_match:
        com_match = re.search(r"/comment/([a-z0-9]+)", url)

    comment_id = com_match.group(1) if com_match else None
    return submission_id, comment_id


def get_reddit() -> praw.Reddit:
    return praw.Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent="generate-draft/2.0",
        username=settings.REDDIT_USERNAME,
        password=settings.REDDIT_PASSWORD,
    )


def fetch_post(
    submission_id: str, comment_id: str | None = None
) -> dict[str, str]:
    reddit = get_reddit()
    post = reddit.submission(id=submission_id)

    post.comments.replace_more(limit=0)
    comments = []
    for c in post.comments[:15]:
        author = str(c.author) if c.author else "[deleted]"
        if author.lower() == settings.REDDIT_USERNAME.lower():
            continue
        comments.append(f"[score:{c.score}] u/{author}: {c.body}")

    result: dict[str, str] = {
        "title": post.title,
        "author": str(post.author) if post.author else "[deleted]",
        "subreddit": str(post.subreddit),
        "body": post.selftext,
        "score": str(post.score),
        "num_comments": str(post.num_comments),
        "url": f"https://www.reddit.com{post.permalink}",
        "comments": "\n\n".join(comments),
        "target_comment": "",
        "target_comment_author": "",
    }

    if comment_id:
        comment = reddit.comment(id=comment_id)
        comment.refresh()
        result["target_comment"] = comment.body
        result["target_comment_author"] = (
            str(comment.author) if comment.author else "[deleted]"
        )

        parent_chain = []
        current = comment
        for _ in range(5):
            parent = current.parent()
            if isinstance(parent, praw.models.Comment):
                parent_author = (
                    str(parent.author) if parent.author else "[deleted]"
                )
                parent_chain.append(f"u/{parent_author}: {parent.body}")
                current = parent
            else:
                break
        if parent_chain:
            result["parent_chain"] = "\n---\n".join(reversed(parent_chain))

    return result


def load_few_shot_examples() -> tuple[str, str]:
    posted_rows = (
        Draft.objects.filter(status=Draft.Status.POSTED)
        .exclude(edited_reply="")
        .order_by("-id")[:15]
    )

    posted_xml = []
    for r in posted_rows:
        parts = [
            f'<posted_example id="{r.pk}" subreddit="{r.subreddit_name}">',
            f"  <post_title>{r.post_title}</post_title>",
            f"  <post_body>{r.post_body or ''}</post_body>",
            f"  <original_draft>{r.draft_reply}</original_draft>",
            f"  <final_reply>{r.edited_reply}</final_reply>",
            f"  <edit_notes>{r.edit_notes or ''}</edit_notes>",
            "</posted_example>",
        ]
        posted_xml.append("\n".join(parts))

    rejected_rows = (
        Draft.objects.filter(status=Draft.Status.REJECTED)
        .exclude(edit_notes="")
        .order_by("-id")[:30]
    )

    rejected_xml = []
    for r in rejected_rows:
        parts = [
            f'<rejected_example id="{r.pk}" subreddit="{r.subreddit_name}">',
            f"  <post_title>{r.post_title}</post_title>",
            f"  <post_body>{r.post_body or ''}</post_body>",
            f"  <draft>{r.draft_reply}</draft>",
            f"  <rejection_notes>{r.edit_notes}</rejection_notes>",
            "</rejected_example>",
        ]
        rejected_xml.append("\n".join(parts))

    return "\n\n".join(posted_xml), "\n\n".join(rejected_xml)


def get_banned_subreddits() -> set[str]:
    return set(
        Subreddit.objects.filter(banned=True).values_list("name", flat=True)
    )


def build_triage_prompt(
    post: dict[str, str],
    voice: str,
    product: str,
    humanizer: str,
    peptides_catalog: str,
    posted_examples: str,
    rejected_examples: str,
    *,
    third_party: bool = False,
) -> str:
    if third_party:
        disclosure_rule = (
            'Do NOT say "I built this", "I made this", "Disclosure: I\'m the creator", or anything similar. '
            "You are posting from a third-party account. Just drop the link naturally without any ownership claim."
        )
        third_party_note = "\nNOTE: This is a banned subreddit. The reply will be posted from a third-party account. Do NOT include any ownership claims."
    else:
        disclosure_rule = 'Vary the disclosure phrasing: "I built this", "I made this", "Disclosure: mine", etc.'
        third_party_note = ""

    target_section = ""
    if post.get("target_comment"):
        target_section = f"""
TARGET COMMENT (you are replying to THIS comment, not the post directly):
<target_comment>
Author: u/{post['target_comment_author']}
{post['target_comment']}
</target_comment>
"""
        if post.get("parent_chain"):
            target_section += f"""
PARENT COMMENT CHAIN (for context, oldest first):
<parent_chain>
{post['parent_chain']}
</parent_chain>
"""

    return f"""You are analyzing a Reddit post to decide how to reply as u/brosterdamus (Silvio).

VOICE GUIDE (how to write):
<voice>
{voice}
</voice>

ANTI-AI WRITING GUIDE (patterns to avoid — your output MUST pass as human-written):
<humanizer>
{humanizer}
</humanizer>

PRODUCT DOCUMENTATION (what the calculator does, URL parameters, peptide keys):
<product>
{product}
</product>

PEPTIDE CATALOG (all supported peptides, blends, compounds, vial sizes, dose presets — this is the source of truth for valid ?peptide= URL parameter values):
<peptides_catalog>
{peptides_catalog}
</peptides_catalog>

PEPTIDE KNOWLEDGE (use these facts, do NOT make up dosing info):
<facts>
- Retatrutide starting dose is 2mg weekly per clinical trials, though 1mg is also fine to start with. Pin once a week, titrate up as needed.
- Tirzepatide starting dose is 2.5mg weekly.
- Semaglutide starting dose is 0.25mg weekly.
- Cagrilintide doses vary wildly per person, some respond at 0.25mg, others need 2mg+.
</facts>

CRITICAL VOICE RULES (violations = instant rejection):
- Use informal shorthand: "subq" not "subcutaneous", "bac water" not "bacteriostatic water", "tirz" not "tirzepatide" (when referencing casually), "reta" not "retatrutide" (same), "sema" not "semaglutide" (same). Use full names only on first mention or in a calculator link context.
- Reference other commenters as /u/username, not "Someone mentioned" or by name.
- Do NOT use em dashes (—). Use commas, periods, or parentheses instead.
- Do NOT use self-deprecating hedges like "grain of salt", "for what it's worth", "take it or leave it".
- Occasionally drop an article ("add 1ml bac water" not "add 1ml of bac water"), use a run-on sentence, or leave something lowercase that "should" be capitalized. Real reddit posts aren't grammatically perfect. Don't overdo this, just let it happen naturally once or twice.
- Do not use emoji.
- Do not open with "Great question!" or "Hope this helps!" or any greeting.
- Do not use bold (**text**) excessively. One or two bolds max per reply, if any.
- {disclosure_rule}

APPROVED REPLIES (these passed review — learn from the style, tone, and edits):
<posted_examples>
{posted_examples}
</posted_examples>

REJECTED REPLIES (these were rejected — the rejection_notes explain why):
<rejected_examples>
{rejected_examples}
</rejected_examples>

REDDIT POST TO ANALYZE:
<post>
Subreddit: r/{post['subreddit']}
Title: {post['title']}
Author: u/{post['author']}
Score: {post['score']}

{post['body']}
</post>
{target_section}
EXISTING COMMENTS (for context — do not repeat what others have already said):
<comments>
{post['comments']}
</comments>
{third_party_note}
TASK: Analyze this post and decide how to reply.

- LINK: The post involves dosing, reconstitution, mixing math, syringe calculations, or any scenario where the peptide calculator (joyapp.com/peptides/) would be useful. Choose LINK even if the question has already been answered — we are pitching the calculator as a helpful tool. Extract all inferable calculator URL parameters. Use peptide keys from the catalog (e.g., retatrutide, tirzepatide, wolverine, glow, klow, custom). Default syringe to "1" if not mentioned. For the water param: set it ONLY if the poster has ALREADY reconstituted (mixed water into the vial). If they're asking how much water to add, or planning to add water, or thinking about it, leave water as null so the calculator auto-picks the optimal amount.
- ADVICE_ONLY: The post is about peptides/GLP-1s but the calculator isn't relevant (side effects, progress, general advice, diet, stacking without math). We'll reply with helpful advice and no link.
- REJECT: The post has nothing to do with peptides, is a meme, or replying would be inappropriate/spammy.

Also provide:

- confidence (1-10): How confident are you that this reply can be posted automatically WITHOUT human review? This is the bar:
  - 9-10: Slam dunk. Simple reconstitution math or straightforward dosing question. We know the exact answer. No nuance, no empathy needed, no risk of being wrong. The voice is easy to nail (short, factual). Post looks fresh with few or no existing answers.
  - 7-8: Very likely fine. Clear question we can answer well, but minor risk factors: slightly tricky voice (needs empathy or nuance), or the post already has decent answers so ours might look redundant.
  - 5-6: Needs review. We can probably help, but: the question is ambiguous, or we'd need to make assumptions about their setup, or the topic requires careful phrasing (medical concerns, stacking advice), or the thread is old/crowded.
  - 3-4: Risky. The post is only tangentially relevant, or we'd be stretching to include a link, or there's high risk of getting the voice wrong (emotional topic, complex situation).
  - 1-2: Almost certainly needs edits or should be skipped. Borderline spam territory, very hard voice, or we're not sure of the facts.

- upvotes_needed: how many upvotes our comment would need to become the top comment in the thread. Look at the existing comment scores. If the top comment has score N, we need N+1 upvotes. If there are no comments yet, return 0. Return null if REJECT."""


def build_reply_prompt_link(triage: dict[str, Any], tracking_code: str) -> str:
    params = triage["extracted_params"]

    url_parts = []
    for key in ["peptide", "vial", "vial_unit", "dose", "dose_unit", "syringe", "water"]:
        val = params.get(key)
        if val is not None:
            url_parts.append(f"{key}={val}")
    url_parts.append(f"t={tracking_code}")

    calculator_url = "https://www.joyapp.com/peptides/?" + "&".join(url_parts)

    return f"""Action confirmed: LINK.

The tracking code is: {tracking_code}

Write the reply. Use this pre-filled calculator URL:
{calculator_url}

For blends (wolverine, glow, klow), the peptide key IS the blend name, no need to list individual components in the URL.
WATER PARAM RULES:
- Include &water=X ONLY if the poster has ALREADY reconstituted (already mixed water into the vial). Example: "I added 2ml of bac water" = include &water=2.
- Do NOT include &water if they're asking how much water to add, planning to add water, or haven't mixed yet. When water is omitted, the calculator auto-picks the optimal water amount for the cleanest syringe draws.
- You can tell them to "click manual" to try different water amounts and compare.

STRICT RULES (violating ANY of these = instant rejection):
- Answer ONLY the specific question(s) asked. Do NOT volunteer extra advice, warnings, tips, or address topics the poster only mentioned in passing. If they asked about reconstitution math, answer that. Don't add paragraphs about side effects, injection technique, or dosing schedules they didn't ask about.
- 2-4 sentences max before the link.
- Do NOT just parrot what another commenter already said. Add your own value (the calculator).
- Do NOT use em dashes (the long dash character). Use commas, periods, or parentheses instead. This is the #1 reason drafts get rejected.
- No emoji, no greetings, no "Hope this helps!"
- Keep it casual and imperfect. Drop an article, use a run-on, leave something lowercase.

Output ONLY the reply text. No meta-commentary."""


def build_reply_prompt_advice() -> str:
    return """Action confirmed: ADVICE_ONLY.

Write the reply. No calculator link.

STRICT RULES (violating ANY of these = instant rejection):
- Answer ONLY the specific question(s) asked. Do NOT volunteer extra advice, warnings, tips, or address topics the poster only mentioned in passing. If they asked about side effects, answer that. Don't add dosing schedules, injection technique, or other topics they didn't ask about.
- 2-4 sentences max.
- Do NOT just parrot what another commenter already said. Add your own value.
- Do NOT use em dashes (the long dash character). Use commas, periods, or parentheses instead. This is the #1 reason drafts get rejected.
- No emoji, no greetings, no "Hope this helps!"
- Keep it casual and imperfect. Drop an article, use a run-on, leave something lowercase.

Output ONLY the reply text. No meta-commentary."""


def create_tracking_link(post_url: str, subreddit: str) -> str:
    payload = json.dumps(
        {
            "api_key": settings.TRACKING_API_KEY,
            "url": post_url,
            "subreddit": subreddit,
        }
    ).encode()

    req = Request(
        settings.TRACKING_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req) as resp:
        return json.loads(resp.read().decode())  # type: ignore[no-any-return]


def save_draft(
    post: dict[str, str],
    triage: dict[str, Any],
    reply: str | None,
    tracking_code: str | None,
) -> int:
    action_str = triage["action"]
    action_enum = Draft.Action[action_str]
    status = Draft.Status.REJECTED if action_str == "REJECT" else Draft.Status.PENDING
    upvotes_needed = triage.get("upvotes_needed")

    existing = Draft.objects.filter(post_url=post["url"]).first()

    if existing:
        existing.draft_reply = reply or ""
        existing.action = action_enum
        existing.confidence = triage["confidence"]
        existing.upvotes_needed = upvotes_needed
        existing.tracking_code = tracking_code or ""
        existing.triage_reasoning = triage["reasoning"]
        existing.notes = triage["reasoning"] if action_str == "REJECT" else ""
        existing.status = status
        existing.save()
        return existing.pk

    draft = Draft.objects.create(
        subreddit_name=post["subreddit"],
        post_title=post["title"],
        post_url=post["url"],
        post_author=post["author"],
        post_body=post["body"],
        draft_reply=reply or "",
        action=action_enum,
        confidence=triage["confidence"],
        upvotes_needed=upvotes_needed,
        tracking_code=tracking_code or "",
        triage_reasoning=triage["reasoning"],
        notes=triage["reasoning"] if action_str == "REJECT" else "",
        status=status,
    )
    return draft.pk


def process_url(
    url: str,
    client: anthropic.Anthropic,
    voice: str,
    product: str,
    humanizer: str,
    peptides_catalog: str,
    posted_examples: str,
    rejected_examples: str,
    banned_subs: set[str],
    *,
    dry_run: bool = False,
) -> dict[str, Any] | None:
    submission_id, comment_id = parse_reddit_url(url)

    if not dry_run:
        existing = Draft.objects.filter(
            post_url__contains=f"/comments/{submission_id}/",
            status__in=[Draft.Status.POSTED, Draft.Status.APPROVED],
        ).first()
        if existing:
            print(
                f"  Skipping: already have draft #{existing.pk} ({existing.status}) for this post",
                file=sys.stderr,
            )
            return None

    print(
        f"Fetching post {submission_id}"
        + (f" comment {comment_id}" if comment_id else "")
        + "...",
        file=sys.stderr,
    )

    post = fetch_post(submission_id, comment_id)
    is_third_party = post["subreddit"] in banned_subs
    mode_label = " [3rd party]" if is_third_party else ""
    print(
        f"r/{post['subreddit']}{mode_label}: {post['title']} by u/{post['author']}",
        file=sys.stderr,
    )

    triage_prompt = build_triage_prompt(
        post,
        voice,
        product,
        humanizer,
        peptides_catalog,
        posted_examples,
        rejected_examples,
        third_party=is_third_party,
    )

    print("  Triage...", file=sys.stderr)
    triage_response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": triage_prompt}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": TRIAGE_SCHEMA,
            }
        },
    )

    tu = triage_response.usage
    print(
        f"  Triage tokens: {tu.input_tokens:,} in / {tu.output_tokens:,} out (${tu.input_tokens * 3 / 1_000_000 + tu.output_tokens * 15 / 1_000_000:.3f})",
        file=sys.stderr,
    )

    triage = json.loads(triage_response.content[0].text)
    upvotes = triage.get("upvotes_needed")
    upvotes_label = f", upvotes needed: {upvotes}" if upvotes is not None else ""
    print(
        f"  Action: {triage['action']} (confidence: {triage['confidence']}{upvotes_label})",
        file=sys.stderr,
    )
    print(f"  Reasoning: {triage['reasoning']}", file=sys.stderr)

    if triage["action"] == "REJECT":
        if dry_run:
            print("  [dry-run] Would reject, skipping DB save", file=sys.stderr)
            print(json.dumps(triage, indent=2))
        else:
            draft_id = save_draft(post, triage, reply=None, tracking_code=None)
            print(f"  Rejected -> draft #{draft_id}", file=sys.stderr)
        return triage

    tracking_code = None
    if triage["action"] == "LINK":
        if dry_run:
            tracking_code = "DRYRUN"
            print(
                "  [dry-run] Skipping tracking link creation, using placeholder code",
                file=sys.stderr,
            )
        else:
            print("  Creating tracking link...", file=sys.stderr)
            tracking_code = create_tracking_link(post["url"], post["subreddit"])
            print(f"  Tracking code: {tracking_code}", file=sys.stderr)

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": triage_prompt},
        {"role": "assistant", "content": triage_response.content[0].text},
    ]

    if triage["action"] == "LINK":
        assert tracking_code is not None
        turn2_prompt = build_reply_prompt_link(triage, tracking_code)
    else:
        turn2_prompt = build_reply_prompt_advice()

    messages.append({"role": "user", "content": turn2_prompt})

    print("  Generating reply...", file=sys.stderr)
    reply_response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=messages,
    )

    ru = reply_response.usage
    print(
        f"  Reply tokens: {ru.input_tokens:,} in / {ru.output_tokens:,} out (${ru.input_tokens * 3 / 1_000_000 + ru.output_tokens * 15 / 1_000_000:.3f})",
        file=sys.stderr,
    )

    reply = reply_response.content[0].text

    if dry_run:
        print("  [dry-run] Skipping DB save", file=sys.stderr)
        print(json.dumps(triage, indent=2))
        print(f"\n{reply}\n")
    else:
        draft_id = save_draft(post, triage, reply, tracking_code)
        print(f"  Saved -> draft #{draft_id}", file=sys.stderr)
        print(f"\n{reply}\n", file=sys.stderr)

    return triage


class Command(BaseCommand):
    help = "Generate AI draft replies for Reddit posts"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("url", nargs="?", help="Reddit post or comment URL")
        parser.add_argument(
            "--batch",
            action="store_true",
            help="Process all pending drafts from DB",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Triage only, print JSON, don't save",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        url = options.get("url")
        batch = options.get("batch", False)
        dry_run = options.get("dry_run", False)

        if not url and not batch:
            self.stderr.write("Provide a Reddit URL or use --batch")
            return

        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            self.stderr.write("Error: Set ANTHROPIC_API_KEY in settings.py or environment")
            return

        data_dir = settings.DATA_DIR
        voice_file = data_dir / "voice.md"
        product_file = data_dir / "peptide-calculator-features.md"
        humanizer_file = data_dir / "humanizer.md"
        peptides_file = data_dir / "peptides.json"

        for path, name in [
            (voice_file, "voice.md"),
            (product_file, "peptide-calculator-features.md"),
            (humanizer_file, "humanizer.md"),
            (peptides_file, "peptides.json"),
        ]:
            if not path.exists():
                self.stderr.write(f"Error: {name} not found at {path}")
                return

        voice = voice_file.read_text()
        if len(voice) > MAX_VOICE_CHARS:
            voice = voice[:MAX_VOICE_CHARS]
            self.stderr.write(f"Truncated voice to {MAX_VOICE_CHARS:,} chars")
        product = product_file.read_text()
        humanizer = humanizer_file.read_text()
        peptides_catalog = peptides_file.read_text()
        posted_examples, rejected_examples = load_few_shot_examples()
        banned_subs = get_banned_subreddits()

        self.stderr.write(
            f"Context loaded: voice {len(voice):,} chars, "
            f"{len(posted_examples):,} chars posted examples, "
            f"{len(rejected_examples):,} chars rejected examples"
        )
        if banned_subs:
            self.stderr.write(
                f"Banned subreddits (third-party mode): {', '.join(sorted(banned_subs))}"
            )

        client = anthropic.Anthropic(api_key=api_key)

        if batch:
            pending = Draft.objects.filter(
                status=Draft.Status.PENDING, action__isnull=True
            ).order_by("id")
            self.stderr.write(f"Found {pending.count()} pending drafts to triage")

            for i, draft in enumerate(pending):
                self.stderr.write(f"\n[{i + 1}/{pending.count()}] #{draft.pk}")
                try:
                    process_url(
                        draft.post_url,
                        client,
                        voice,
                        product,
                        humanizer,
                        peptides_catalog,
                        posted_examples,
                        rejected_examples,
                        banned_subs,
                    )
                except Exception as e:
                    self.stderr.write(f"  Error: {e}")

            self.stderr.write(f"\nDone. Processed {pending.count()} drafts.")
        else:
            assert url is not None
            process_url(
                url,
                client,
                voice,
                product,
                humanizer,
                peptides_catalog,
                posted_examples,
                rejected_examples,
                banned_subs,
                dry_run=dry_run,
            )
