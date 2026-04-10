"""v3 draft generation: Agent SDK, Opus, 3 variants, no triage step."""

from __future__ import annotations

import asyncio
import json
import re
import sys
from typing import Any
from urllib.request import Request, urlopen

import praw
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    query,
)
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand

from server.drafts.models import Draft, Subreddit

MODEL = "claude-opus-4-6"

DRAFT_REPLY_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "reply": {"type": "string"},
            "includes_link": {"type": "boolean"},
            "skip_reason": {"type": ["string", "null"]},
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
        },
        "required": ["reply", "includes_link", "skip_reason", "extracted_params"],
        "additionalProperties": False,
    },
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
        user_agent="generate-draft/3.0",
        username=settings.REDDIT_USERNAME,
        password=settings.REDDIT_PASSWORD,
    )


def fetch_post(submission_id: str, comment_id: str | None = None) -> dict[str, str]:
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
                parent_author = str(parent.author) if parent.author else "[deleted]"
                parent_chain.append(f"u/{parent_author}: {parent.body}")
                current = parent
            else:
                break
        if parent_chain:
            result["parent_chain"] = "\n---\n".join(reversed(parent_chain))

    return result


def load_correction_history() -> tuple[str, str]:
    """Load ALL posted and rejected drafts as correction history."""
    posted_rows = (
        Draft.objects.filter(status=Draft.Status.POSTED)
        .exclude(edited_reply="")
        .order_by("-id")
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
        .order_by("-id")
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
    return set(Subreddit.objects.filter(banned=True).values_list("name", flat=True))


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


SYSTEM_PROMPT = """You are a Reddit reply assistant for u/brosterdamus (Silvio), who built a peptide reconstitution calculator at joyapp.com/peptides/.

Your job is to write helpful, natural-sounding Reddit replies that match Silvio's voice. For each post, you will either write a reply or explain why the post should be skipped.

OUTPUT RULES:
- If the post is clearly irrelevant (not about peptides/GLP-1s, is a meme, replying would be inappropriate or spammy), set skip_reason to a brief explanation and leave reply empty.
- Otherwise, write a reply in the "reply" field.
- Set includes_link to true if your reply contains a calculator link, false otherwise.
- Extract all inferable calculator URL parameters into extracted_params.

PEPTIDE KNOWLEDGE (use these facts, do NOT make up dosing info):
- Retatrutide starting dose is 2mg weekly per clinical trials, though 1mg is also fine to start with. Pin once a week, titrate up as needed.
- Tirzepatide starting dose is 2.5mg weekly.
- Semaglutide starting dose is 0.25mg weekly.
- Cagrilintide doses vary wildly per person, some respond at 0.25mg, others need 2mg+.

CRITICAL VOICE RULES (violations = instant rejection):
- Use informal shorthand: "subq" not "subcutaneous", "bac water" not "bacteriostatic water", "tirz" not "tirzepatide" (when referencing casually), "reta" not "retatrutide" (same), "sema" not "semaglutide" (same). Use full names only on first mention or in a calculator link context.
- Reference other commenters as /u/username, not "Someone mentioned" or by name.
- Do NOT use em dashes (the long dash character). Use commas, periods, or parentheses instead. This is the #1 reason drafts get rejected.
- Do NOT use self-deprecating hedges like "grain of salt", "for what it's worth", "take it or leave it".
- Occasionally drop an article ("add 1ml bac water" not "add 1ml of bac water"), use a run-on sentence, or leave something lowercase that "should" be capitalized. Real reddit posts aren't grammatically perfect. Don't overdo this, just let it happen naturally once or twice.
- Do not use emoji.
- Do not open with "Great question!" or "Hope this helps!" or any greeting.
- Do not use bold (**text**) excessively. One or two bolds max per reply, if any.

REPLY RULES:
- Answer ONLY the specific question(s) asked. Do NOT volunteer extra advice, warnings, tips, or address topics the poster only mentioned in passing.
- 2-4 sentences max before any link. Keep it concise.
- Do NOT just parrot what another commenter already said. Add your own value.
- If the calculator is relevant (dosing, reconstitution, mixing math, syringe calculations), include a pre-filled calculator link.
- If the calculator is not relevant (side effects, progress, general advice, diet, stacking without math), reply with helpful advice and no link.

WATER PARAM RULES:
- Include &water=X in the URL ONLY if the poster has ALREADY reconstituted (already mixed water into the vial). Example: "I added 2ml of bac water" = include &water=2.
- Do NOT include &water if they're asking how much water to add, planning to add water, or haven't mixed yet. When water is omitted, the calculator auto-picks the optimal water amount for the cleanest syringe draws.
- You can tell them to "click manual" to try different water amounts and compare.

CALCULATOR URL FORMAT:
- Base URL: https://www.joyapp.com/peptides/
- Add query parameters for values you can infer: ?peptide=KEY&vial=SIZE&vial_unit=UNIT&dose=DOSE&dose_unit=UNIT&syringe=SIZE&water=AMOUNT
- Always append &t={{TRACKING_CODE}} at the end of the URL. This placeholder will be replaced with an actual tracking code after generation.
- Use peptide keys from the catalog (e.g., retatrutide, tirzepatide, wolverine, glow, klow, custom).
- Default syringe to "1" if not mentioned.
- For blends (wolverine, glow, klow), the peptide key IS the blend name, no need to list individual components.
- Only include parameters you can infer from the post. Omit unknown ones (except syringe defaults to 1)."""


def build_context(
    voice: str,
    humanizer: str,
    product: str,
    peptides_catalog: str,
    posted_examples: str,
    rejected_examples: str,
) -> str:
    """Build the large context block that gets prepended to the user prompt.

    This is separate from the system prompt because the Agent SDK passes
    system_prompt as a CLI argument (subject to OS arg size limits), while
    the prompt is sent via stdin after process creation (no size limit).
    """
    return f"""REFERENCE CONTEXT (use this to inform your reply):

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

PEPTIDE CATALOG (all supported peptides, blends, compounds, vial sizes, dose presets — source of truth for valid ?peptide= URL parameter values):
<peptides_catalog>
{peptides_catalog}
</peptides_catalog>

CORRECTION HISTORY — APPROVED REPLIES (these passed review, learn from the style, tone, and edits applied):
<posted_examples>
{posted_examples}
</posted_examples>

CORRECTION HISTORY — REJECTED REPLIES (these were rejected, the rejection_notes explain why):
<rejected_examples>
{rejected_examples}
</rejected_examples>

---
NOW REPLY TO THE FOLLOWING POST:
"""


def build_user_prompt(
    post: dict[str, str],
    *,
    third_party: bool = False,
    variant: int = 1,
    prior_replies: list[str] | None = None,
) -> str:
    if third_party:
        disclosure = (
            "DISCLOSURE MODE: Third-party account. Do NOT say "
            '"I built this", "I made this", "Disclosure: I\'m the creator", '
            "or anything similar. Just drop the link naturally without any "
            "ownership claim."
        )
    else:
        disclosure = (
            "DISCLOSURE MODE: Self (posting as the creator). "
            'Vary the disclosure phrasing: "I built this", "I made this", '
            '"Disclosure: mine", etc.'
        )

    target_section = ""
    if post.get("target_comment"):
        target_section = f"""
TARGET COMMENT (you are replying to THIS comment, not the post directly):
<target_comment>
Author: u/{post["target_comment_author"]}
{post["target_comment"]}
</target_comment>
"""
        if post.get("parent_chain"):
            target_section += f"""
PARENT COMMENT CHAIN (for context, oldest first):
<parent_chain>
{post["parent_chain"]}
</parent_chain>
"""

    variant_instruction = ""
    if variant > 1 and prior_replies:
        prior_block = "\n---\n".join(
            f"VARIANT {i + 1}:\n{r}" for i, r in enumerate(prior_replies)
        )
        variant_instruction = (
            f"\nThis is variant {variant} of 3. Here are the previous variants you wrote:\n"
            f"<prior_variants>\n{prior_block}\n</prior_variants>\n"
            "Write a meaningfully different reply. Try a different opener, "
            "angle, level of detail, or way to introduce the link. "
            "Do NOT repeat the same structure or phrasing."
        )

    return f"""REDDIT POST:
<post>
Subreddit: r/{post["subreddit"]}
Title: {post["title"]}
Author: u/{post["author"]}
Score: {post["score"]}

{post["body"]}
</post>
{target_section}
EXISTING COMMENTS (for context — do not repeat what others have already said):
<comments>
{post["comments"]}
</comments>

{disclosure}{variant_instruction}"""


async def generate_variant(
    context: str,
    user_prompt: str,
    token: str,
) -> dict[str, Any]:
    """Generate one draft variant using the Agent SDK."""
    full_prompt = context + user_prompt
    result: dict[str, Any] | None = None
    async for message in query(
        prompt=full_prompt,
        options=ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            model=MODEL,
            output_format=DRAFT_REPLY_SCHEMA,
            allowed_tools=[],
            max_turns=1,
            betas=["context-1m-2025-08-07"],
            env={"CLAUDE_CODE_OAUTH_TOKEN": token},
        ),
    ):
        if isinstance(message, ResultMessage):
            if message.structured_output:
                result = message.structured_output
        elif isinstance(message, AssistantMessage):
            # The Agent SDK delivers structured output via a ToolUseBlock
            # named 'StructuredOutput'. Extract it if ResultMessage doesn't
            # populate structured_output.
            for block in message.content:
                if (
                    hasattr(block, "name")
                    and block.name == "StructuredOutput"
                    and hasattr(block, "input")
                ):
                    result = block.input
    if result is None:
        raise RuntimeError("No structured output received from Agent SDK")
    return result


async def process_url(
    url: str,
    context: str,
    token: str,
    banned_subs: set[str],
    *,
    dry_run: bool = False,
) -> None:
    submission_id, comment_id = parse_reddit_url(url)

    if not dry_run:
        existing = await sync_to_async(
            Draft.objects.filter(
                post_url__contains=f"/comments/{submission_id}/",
                status__in=[Draft.Status.POSTED, Draft.Status.APPROVED],
            ).first
        )()
        if existing:
            print(
                f"  Skipping: already have draft #{existing.pk} "
                f"({existing.status}) for this post",
                file=sys.stderr,
            )
            return

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

    # Variant A
    print("  Generating variant A...", file=sys.stderr)
    prompt_a = build_user_prompt(post, third_party=is_third_party, variant=1)
    result_a = await generate_variant(context, prompt_a, token)

    if result_a.get("skip_reason"):
        print(f"  Skipped: {result_a['skip_reason']}", file=sys.stderr)
        if dry_run:
            print("  [dry-run] Would save as SKIPPED", file=sys.stderr)
            print(json.dumps(result_a, indent=2))
        else:
            existing_draft = await sync_to_async(
                Draft.objects.filter(post_url=post["url"]).first
            )()
            if existing_draft:
                existing_draft.status = Draft.Status.SKIPPED
                existing_draft.notes = result_a["skip_reason"]
                await sync_to_async(existing_draft.save)()
                print(f"  Skipped -> draft #{existing_draft.pk}", file=sys.stderr)
            else:
                draft = await sync_to_async(Draft.objects.create)(
                    subreddit_name=post["subreddit"],
                    post_title=post["title"],
                    post_url=post["url"],
                    post_author=post["author"],
                    post_body=post["body"],
                    status=Draft.Status.SKIPPED,
                    notes=result_a["skip_reason"],
                )
                print(f"  Skipped -> draft #{draft.pk}", file=sys.stderr)
        return

    # Variants B and C (fed prior replies for differentiation)
    print("  Generating variant B...", file=sys.stderr)
    prompt_b = build_user_prompt(
        post, third_party=is_third_party, variant=2, prior_replies=[result_a["reply"]]
    )
    result_b = await generate_variant(context, prompt_b, token)

    print("  Generating variant C...", file=sys.stderr)
    prompt_c = build_user_prompt(
        post,
        third_party=is_third_party,
        variant=3,
        prior_replies=[result_a["reply"], result_b["reply"]],
    )
    result_c = await generate_variant(context, prompt_c, token)

    replies = [result_a["reply"], result_b["reply"], result_c["reply"]]
    results = [result_a, result_b, result_c]

    # Create tracking code if any variant includes a link
    tracking_code = ""
    any_link = any(r.get("includes_link") for r in results)
    if any_link:
        if dry_run:
            tracking_code = "DRYRUN"
            print(
                "  [dry-run] Using placeholder tracking code",
                file=sys.stderr,
            )
        else:
            print("  Creating tracking link...", file=sys.stderr)
            tracking_code = create_tracking_link(post["url"], post["subreddit"])
            print(f"  Tracking code: {tracking_code}", file=sys.stderr)

    # Replace placeholder in replies that include links
    if tracking_code:
        for i in range(3):
            if results[i].get("includes_link"):
                replies[i] = replies[i].replace("{{TRACKING_CODE}}", tracking_code)

    if dry_run:
        print("  [dry-run] Skipping DB save", file=sys.stderr)
        for i, (label, reply) in enumerate(zip(["A", "B", "C"], replies)):
            link_flag = " [LINK]" if results[i].get("includes_link") else ""
            print(f"\n--- Variant {label}{link_flag} ---")
            print(reply)
        print()
    else:
        existing_draft = await sync_to_async(
            Draft.objects.filter(post_url=post["url"]).first
        )()
        if existing_draft:
            existing_draft.draft_reply = replies[0]
            existing_draft.draft_reply_b = replies[1]
            existing_draft.draft_reply_c = replies[2]
            existing_draft.tracking_code = tracking_code
            existing_draft.status = Draft.Status.PENDING
            await sync_to_async(existing_draft.save)()
            print(f"  Saved -> draft #{existing_draft.pk}", file=sys.stderr)
        else:
            draft = await sync_to_async(Draft.objects.create)(
                subreddit_name=post["subreddit"],
                post_title=post["title"],
                post_url=post["url"],
                post_author=post["author"],
                post_body=post["body"],
                draft_reply=replies[0],
                draft_reply_b=replies[1],
                draft_reply_c=replies[2],
                tracking_code=tracking_code,
                status=Draft.Status.PENDING,
            )
            print(f"  Saved -> draft #{draft.pk}", file=sys.stderr)


class Command(BaseCommand):
    help = "Generate AI draft replies for Reddit posts (v3: Agent SDK, 3 variants)"

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
            help="Generate variants and print, don't save to DB",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        url = options.get("url")
        batch = options.get("batch", False)
        dry_run = options.get("dry_run", False)

        if not url and not batch:
            self.stderr.write("Provide a Reddit URL or use --batch")
            return

        token = settings.CLAUDE_CODE_OAUTH_TOKEN
        if not token:
            self.stderr.write("Error: CLAUDE_CODE_OAUTH_TOKEN not available")
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
        product = product_file.read_text()
        humanizer = humanizer_file.read_text()
        peptides_catalog = peptides_file.read_text()
        posted_examples, rejected_examples = load_correction_history()
        banned_subs = get_banned_subreddits()

        self.stderr.write(
            f"Context loaded: voice {len(voice):,} chars, "
            f"{len(posted_examples):,} chars posted examples, "
            f"{len(rejected_examples):,} chars rejected examples"
        )
        if banned_subs:
            self.stderr.write(
                f"Banned subreddits (third-party mode): "
                f"{', '.join(sorted(banned_subs))}"
            )

        context = build_context(
            voice,
            humanizer,
            product,
            peptides_catalog,
            posted_examples,
            rejected_examples,
        )
        self.stderr.write(f"Context: {len(context):,} chars")

        if batch:
            pending = list(
                Draft.objects.filter(
                    status=Draft.Status.PENDING, draft_reply=""
                ).order_by("id")
            )
            self.stderr.write(f"Found {len(pending)} pending drafts to process")

            async def run_batch() -> None:
                for i, d in enumerate(pending):
                    self.stderr.write(f"\n[{i + 1}/{len(pending)}] #{d.pk}")
                    try:
                        await process_url(
                            d.post_url,
                            context,
                            token,
                            banned_subs,
                        )
                    except Exception as e:
                        self.stderr.write(f"  Error: {e}")

            asyncio.run(run_batch())
            self.stderr.write(f"\nDone. Processed {len(pending)} drafts.")
        else:
            assert url is not None
            asyncio.run(
                process_url(
                    url,
                    context,
                    token,
                    banned_subs,
                    dry_run=dry_run,
                )
            )
