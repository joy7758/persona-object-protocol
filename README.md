<!-- language-switch:start -->
[English](./README.md) | [中文](./README.zh-CN.md)
<!-- language-switch:end -->

# POP Persona Cockpit

`POP Persona Cockpit` is a local-first CLI for building and using a personal digital persona workspace.
It now also includes a simple local web shell built with FastAPI and Jinja2.

This MVP is intentionally narrow:

- one user
- local files + SQLite
- readable JSON and Markdown outputs
- simple CLI workflows
- no cloud dependency by default

## Scope of v1

The first version focuses on four core jobs:

1. Import chat logs and notes into a local workspace
2. Extract structured daily persona signals
3. Maintain a stable `persona_core.json`
4. Inject persona context before answering a new question

Every persona-assisted session should also leave an audit trail.

## Project Layout

```text
pop-persona-cockpit/
  data/
    raw_logs/
    daily_notes/
    persona_core/
    sessions/
  src/pop_cockpit/
  tests/
```

## Setup

```bash
cd /Users/zhangbin/GitHub/pop-persona-cockpit
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

This repository was scaffolded and verified locally with `python3`, which resolves to Python `3.14.3` on this machine.

## CLI

The scaffold exposes a `pop` command.

```bash
pop --help
pop status
pop import file ./example.txt
pop import folder ./sample-data
pop import chatgpt-export ~/Downloads/chatgpt-export.zip
python3 -m pop_cockpit.cli import file ./example.txt
pop extract daily --from 2026-03-20 --to 2026-03-22
pop extract backfill --from 2024-01-01 --to 2026-03-22 --source-type chatgpt_export
pop persona rebuild
pop persona show
pop persona export
pop persona rebuild --scope source_type:chatgpt_export
pop ask "What should I focus on today?"
pop web
```

The import commands are implemented in v1. The later persona commands remain placeholders and will be completed step by step.

Import normalization is intentionally simple and deterministic:

- text and markdown files normalize line endings and trim outer whitespace
- JSON files are parsed and re-serialized with stable key ordering when possible

Daily extraction currently uses a local heuristic fallback provider, so snapshot fields are deterministic and reviewable even without an external API.

Daily extraction is source-time aware. The effective event timestamp resolution is:

1. use `metadata.created_at` when it exists and parses as an ISO timestamp
2. otherwise fallback to `imported_at`

This prevents historical ChatGPT messages from collapsing into the day they were imported.

## Storage

The CLI bootstraps local storage automatically on first run:

- SQLite database: `data/pop_persona.db`
- raw imports: `data/raw_logs/`
- daily notes: `data/daily_notes/`
- persona core exports: `data/persona_core/`
- session artifacts: `data/sessions/`
- web/workflow logs: `data/logs/`
- local settings: `data/settings.json`

## Local Web UI

Start the local web shell with:

```bash
pop web
```

Then open:

```text
http://127.0.0.1:8765
```

The web UI wraps the existing backend logic for:

- dashboard and workflow status
- file and ChatGPT export import
- persona rebuild/export
- persona-assisted ask
- audit browsing
- scheduler settings

## Chrome Capture Extension

Phase 2 adds a local Chrome extension under `extension/`.

It captures ChatGPT web conversation turns from:

- `https://chatgpt.com/*`
- `https://chat.openai.com/*`

and sends them to the local backend:

- `POST /api/capture/chat-message`
- `GET /api/capture/status`

Load it from Chrome via:

```text
chrome://extensions
```

then enable Developer Mode and choose `Load unpacked` for the `extension/` directory.

## Development

Run tests with:

```bash
pytest
```
