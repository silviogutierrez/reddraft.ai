# Draft Generation v3

## Goals

1. Maximize reply quality. Cost reduction is a side effect, not a constraint.
2. Generate 3 draft variants per post so the reviewer can pick the best one.
3. Maintain tracking link functionality.

## Problems with v2

**Cost:**
- The triage prompt includes the entire context (voice guide, humanizer, product
  docs, peptide catalog, few-shot examples) even though triage is just
  classification. This is the most expensive call and most of those tokens are
  wasted on a LINK/ADVICE_ONLY/REJECT decision.
- Turn 2 (reply generation) resends all of turn 1's tokens as conversation
  history. The reply prompt pays for the full triage context a second time.
- Static context (voice, product, catalog, humanizer) is re-tokenized from
  scratch on every API call. In a 20-post batch, that's 20x the same tokens.
- Few-shot examples are selected by recency (last 15 posted, last 30 rejected),
  not relevance. Most are wasted context.

**Quality:**
- Only one draft is generated. If the voice is slightly off, the reviewer has to
  manually rewrite rather than pick from alternatives.
- Triage sometimes rejects posts the reviewer would have wanted to see.
- The model self-assesses confidence, which is unreliable.

**Code:**
- Uses raw `output_config` with a hand-written JSON schema dict instead of the
  SDK's Pydantic-based structured output (`client.messages.parse()` with
  `output_format`).
- No prompt caching. The same static context is sent and billed in full on every
  call.

## v3 design

### Eliminate the triage step

Don't classify posts before generating replies. Instead, generate replies for
every post and let the reviewer decide what to skip. The model can still signal
"I don't think this post is worth replying to" as one of its outputs, but it
doesn't gate whether a reply is generated.

This removes an entire API call per post (the most expensive one, since it
carried the full context).

### Single call per variant, with prompt caching

Each post gets one API call per variant (3 calls total). The prompt is structured
as:

#### System message (cached, ~386k tokens)

The system message is identical across all posts and all variants. With prompt
caching, it's tokenized once and reused for every subsequent call in the batch.
Only the short per-post user message is billed at full price after the first
call.

Contents, in order:

1. **Voice guide — full `voice.md`** (~257k tokens). Includes the distilled
   voice summary (tone, structure, signature phrases) AND all 921 raw comments.
   The raw comments are real examples of the voice across different topics and
   tones. More examples = better voice matching. The 1M context window
   accommodates this easily.

2. **Humanizer guide — full `humanizer.md`** (~6k tokens). Anti-AI writing
   patterns based on Wikipedia's "Signs of AI writing." Tells the model what
   patterns to avoid so output passes as human-written.

3. **Product documentation — full `peptide-calculator-features.md`** (~4.5k
   tokens). Calculator features, URL parameters, peptide keys. Needed so the
   model can construct valid pre-filled calculator URLs.

4. **Peptide catalog — full `peptides.json`** (~17k tokens). All supported
   peptides, blends, compounds, vial sizes, dose presets. Source of truth for
   valid `?peptide=` URL parameter values.

5. **Reply rules** (~1k tokens). Hardcoded rules currently scattered across
   `build_triage_prompt()` and `build_reply_prompt_link()`:
   - Peptide dosing facts (retatrutide 2mg, tirzepatide 2.5mg, semaglutide
     0.25mg, cagrilintide varies)
   - Voice rules (no em dashes, no greetings, no emoji, informal shorthand like
     "subq", "bac water", "tirz", "reta", "sema")
   - Water param rules (include `&water=X` ONLY if poster has ALREADY
     reconstituted; omit if they're asking how much to add)
   - Calculator URL format and `{{TRACKING_CODE}}` placeholder explanation
   - Reply length (2-4 sentences before link, answer ONLY what was asked)
   - Disclosure variation ("I built this", "Disclosure: mine", etc.)
   - Casual imperfection (drop an article, run-on sentence, lowercase)

6. **ALL correction history** (~100k tokens). Every posted draft (original +
   edited + edit notes) and every rejected draft (draft + rejection notes),
   formatted as XML. Posted corrections come first (they show what good looks
   like). If this ever exceeds the token budget, truncate rejected before
   posted, oldest first. Currently: 52 posted, 191 rejected, ~400k chars.

Total system message: ~386k tokens (39% of the 1M context window).

#### User message (per-post, not cached, ~2k tokens)

1. Reddit post: subreddit name, title, author, score, body
2. Existing comments (up to 15, excluding our own account)
3. Target comment + parent chain (if replying to a specific comment, not the
   post directly)
4. Third-party flag: whether the subreddit is banned (changes disclosure
   rules — no "I built this", no ownership claims)
5. Pre-filled calculator URL with `{{TRACKING_CODE}}` placeholder
6. Variant instruction: "This is variant N of 3. Vary your approach, angle,
   and phrasing from other variants."

### Prompt caching implementation

Use explicit cache breakpoints on the system message. The system prompt is a list
of text blocks; the last block gets `cache_control`:

```python
response = client.messages.parse(
    model="claude-opus-4-6",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        },
    ],
    messages=[{"role": "user", "content": per_post_prompt}],
    output_format=DraftReply,
    temperature=0.8,
)
```

The first call in a batch pays the cache write cost (1.25x base input price).
All subsequent calls in the batch pay the cache read cost (0.1x base input
price, a 90% discount). The cache TTL is 5 minutes by default, which is more
than enough for a batch run.

Monitor cache performance via `response.usage`:
- `cache_creation_input_tokens`: tokens written to cache (first call)
- `cache_read_input_tokens`: tokens read from cache (subsequent calls)
- `input_tokens`: non-cached tokens (the per-post user message)

### Tracking link creation

Don't create tracking codes upfront. Instead, use a placeholder URL in the
prompt:

```
Calculator URL (use this if you include a link):
https://www.joyapp.com/peptides/?peptide=retatrutide&vial=10&dose=2&t={{TRACKING_CODE}}
```

After all variants are generated for a post, check which ones have
`includes_link: true`. If any do, create one tracking code and string-replace
`{{TRACKING_CODE}}` in those replies. If no variant includes a link, skip
tracking code creation entirely.

This avoids orphaned tracking codes, which would pollute conversion analytics.
A tracking code with 0 clicks should mean "the reply was posted but nobody
clicked" — not "the code was created but never used in a reply."

### Structured output with Pydantic

Replace the hand-written `TRIAGE_SCHEMA` dict with Pydantic models and use
`client.messages.parse()` with `output_format`. The SDK handles JSON schema
generation, constraint transformation, and response validation automatically.

```python
from pydantic import BaseModel


class ExtractedParams(BaseModel):
    peptide: str | None = None
    vial: str | None = None
    vial_unit: str | None = None
    dose: str | None = None
    dose_unit: str | None = None
    syringe: str | None = None
    water: str | None = None


class DraftReply(BaseModel):
    reply: str
    includes_link: bool
    skip_reason: str | None = None
    extracted_params: ExtractedParams
```

Usage:

```python
response = client.messages.parse(
    model="claude-opus-4-6",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        },
    ],
    messages=[{"role": "user", "content": per_post_prompt}],
    output_format=DraftReply,
    temperature=0.8,
)

# Typed access, no json.loads() needed
draft = response.parsed_output
if draft.skip_reason:
    print(f"Skipped: {draft.skip_reason}")
else:
    print(draft.reply)
    if draft.includes_link:
        print(f"Params: {draft.extracted_params}")
```

`skip_reason` is non-null when the post is clearly irrelevant (carpentry
question, meme, off-topic). When `skip_reason` is set, `reply` is empty — the
model doesn't waste tokens writing a reply for garbage. The draft is saved with
`status=SKIPPED` (a new status, distinct from REJECTED). The reviewer can see
skipped drafts in their own tab and override back to PENDING if the model was
wrong.

### Correction history

Send ALL posted drafts (with original draft, edited version, and edit notes) and
ALL rejected drafts (with rejection notes). Don't limit to recent ones. Don't
filter by subreddit. The model benefits from seeing the full history of what was
changed and why.

If the correction history exceeds the context window, truncate oldest
corrections first. Posted corrections are more valuable than rejected ones (they
show what good looks like), so truncate rejected examples before posted ones.

### 3 variants

For each post, start with variant 1. If the model returns a `skip_reason`, stop
there — save the draft as auto-skipped, don't generate variants 2 and 3. No
point generating 3 variants of "this post is about carpentry."

If variant 1 produces a reply, generate variants 2 and 3 with the same prompt
but `temperature=0.8` and "This is variant N of 3. Vary your approach, angle,
and phrasing." to encourage different angles, openers, levels of detail, and ways
to introduce the link.

All 3 variants share the same tracking code (same post, same tracking). The
reviewer sees all 3 and picks one (or edits one, or rejects all).

### Cost breakdown (v2 vs v3)

Model: Claude Opus (`claude-opus-4-6`). Opus pricing: $15/M input, $75/M
output. Cache write: 1.25x ($18.75/M). Cache read: 0.1x ($1.50/M).

Assume a batch of 20 posts, system context of ~386k tokens (full voice.md +
all corrections + everything else), per-post user message of ~2k tokens.

**v2 (current, Sonnet @ $3/$15 per M):**
- Triage: 20 calls x ~102k input = ~2.04M input tokens at $3/M = ~$6.12
- Reply: 20 calls x ~103k input (resent) = ~2.06M at $3/M = ~$6.18
- Output: 40 calls x ~500 tokens at $15/M = ~$0.30
- **Total: ~$12.60** (40 calls, 1 variant, Sonnet quality)

**v3 (Opus with prompt caching):**
- Call 1 (cache write): 386k tokens at $18.75/M = ~$7.24
- Calls 2-60 (cache read): 59 x 386k at $1.50/M = ~$34.19
- User messages: 60 x 2k at $15/M = ~$1.80
- Output: 60 x ~500 tokens at $75/M = ~$2.25
- **Total: ~$45.48** (60 calls, 3 variants, Opus quality, full context)

v3 costs ~3.6x more per batch, but delivers Opus-quality output with 3
variants per post, full voice context (not truncated), and ALL correction
history. The cost increase is entirely from upgrading Sonnet → Opus, not from
the architecture — the caching actually makes the per-call marginal cost very
low ($0.61/call after the first).

### What we lose

- Automatic rejection. Every post gets replies generated. The reviewer sees more
  posts. In practice most "rejected" posts were borderline anyway, so this is
  arguably better — the reviewer makes the call instead of the model. Clearly
  irrelevant posts still get auto-skipped via `skip_reason`.
- Confidence score. Not useful since it was self-assessed. Could be
  reintroduced later using historical approval rates if needed.
- Separate triage reasoning field. Replaced by `skip_reason` which serves the
  same purpose (model can flag posts it thinks are bad) without gating reply
  generation.

### What we gain

- 3 variants per post. Reviewer picks the best voice/angle.
- Lower cost despite more output.
- Full correction history. Model improves with every review cycle.
- Simpler code. One API call type instead of two. No triage-then-reply
  orchestration.
- No false negative rejections. Reviewer sees everything.
- Type-safe structured output via Pydantic instead of hand-rolled JSON schemas.
- Prompt caching across the entire batch run.

## Data model changes

Add `SKIPPED` to `Draft.Status`. This keeps it separate from `REJECTED` (which
means a human reviewed the reply and rejected it — those drafts have edit notes
about what was wrong with the reply itself). SKIPPED means the model decided the
post wasn't worth replying to. Different meaning, different tab in the UI.

The `Draft` model currently stores a single `draft_reply`. To support 3
variants, either:

**Option A: 3 fields.** Add `draft_reply_b` and `draft_reply_c` to the Draft
model. Simple, no migrations headache, the reviewer picks one and it becomes
`edited_reply`. The other two are just stored for reference.

**Option B: Separate model.** Create a `DraftVariant` model with a FK to Draft.
More normalized, supports N variants, but adds complexity to the UI and queries.

Option A is simpler and sufficient. We're not going to want more than 3 variants.

## Implementation order

1. Add `SKIPPED` to `Draft.Status`, add `draft_reply_b` and `draft_reply_c`
   fields to Draft model + migration.
2. Rewrite `generate_draft` command:
   - Drop triage step entirely.
   - Define `DraftReply` and `ExtractedParams` Pydantic models.
   - Use `client.messages.parse()` with `output_format=DraftReply`.
   - Build system prompt with `cache_control` for prompt caching.
   - Generate 3 variants per post (stop at 1 if `skip_reason`).
   - Create tracking code AFTER generation, only if any variant has
     `includes_link: true`. Replace `{{TRACKING_CODE}}` in those replies.
3. Update DraftPage template to show all 3 variants with a pick button.
4. Update QueuePage to show variant count or best-variant preview.
5. Remove triage-related fields from the model (or leave them; they're harmless).
