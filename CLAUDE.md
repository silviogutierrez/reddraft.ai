# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Start dev server (Vite + Django + tsc --watch)
python dev.py

# Start dev server in build mode (no Vite HMR, full rebuilds)
python dev.py --build

# Install dependencies
source helpers.sh && setup   # runs npm install && uv sync

# Linting & type checking (all files)
bash scripts/test.sh

# Lint only server or client
bash scripts/test.sh --server    # ruff check, ruff format --check, mypy, migration check
bash scripts/test.sh --client    # eslint, prettier, tsc

# Auto-fix lint issues (changed files vs origin/main)
bash scripts/fix.sh
bash scripts/fix.sh --all        # all tracked files
bash scripts/fix.sh --files server/drafts/models.py  # specific files

# Django management
python manage.py makemigrations
python manage.py migrate
python manage.py generate_draft <reddit-url>         # generate AI draft for a post
python manage.py generate_draft <reddit-url> --dry-run
python manage.py generate_draft --batch              # process all pending drafts
python manage.py process_f5bot                       # ingest F5Bot alert emails
```

## Architecture

This is a Django 6 + React app using the **reactivated** framework, which provides server-side rendering of React templates with full type safety between Python and TypeScript.

### How reactivated works

- Django views return `Template` subclasses (not `HttpResponse` directly) that get rendered as React components
- `Pick` subclasses define typed data shapes passed from Python views to TypeScript templates
- `Router` handles RPC endpoints — Python functions decorated with `@rpc()` become callable from the client as typed functions via `schema.function_name()`
- `client/schema.tsx` is auto-generated (gitignored) — contains TypeScript types for all templates, enums, and RPC functions
- Path alias `@client/*` maps to `client/*`, `@reactivated` maps to `node_modules/_reactivated`

### Project structure

- `server/` — Django project (`server.settings`, `server.urls`)
  - `server/core/` — Base `Model` (uuid, created_at, updated_at) and custom `User` model
  - `server/drafts/` — Main app: `Draft` and `Subreddit` models, views, RPC endpoints, management commands
  - `server/rpc/` — The reactivated RPC/template framework (imported from `upstream/`)
- `client/` — React frontend
  - `client/templates/` — One `.tsx` per Django `Template` subclass (e.g., `QueuePage.tsx` renders `views.QueuePage`)
  - `client/components/` — Shared components (`Shell.tsx` is the HTML wrapper)
- `data/` — Prompt context files: `voice.md`, `humanizer.md`, `peptide-calculator-features.md`, `peptides.json`
- `upstream/` — Shared framework code (eslint config, admin, user model, setup scripts)

### Data flow

1. F5Bot email alerts → `process_f5bot` command → creates `Draft` records with `status=PENDING`
2. `generate_draft` command → uses Anthropic API (Claude) to triage posts and generate reply drafts
3. Web UI (QueuePage → DraftPage) → human reviews/edits drafts → approves/rejects via RPC

### Key conventions

- Enums use Python `enum.Enum` with `EnumField` (from reactivated) — they serialize to string values in TypeScript
- Formatting: Python uses ruff (E501 ignored), TypeScript uses eslint + prettier (tabWidth: 4, printWidth: 88, no bracket spacing)
- mypy runs in strict mode with django-stubs and reactivated plugins
- The Nix shell (`shell.nix`) provides all tooling: Python 3.12, Node 22, uv, postgresql, ruff, etc.
- SQLite database for local development
- This is a local-only project. The dev server is generally always running with `python dev.py --build`
