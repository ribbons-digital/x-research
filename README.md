# x-research

Turn X/Twitter posts into durable research notes.

`x-research` is a harness-agnostic research skill/toolkit for analyzing tweet URLs, native X articles, linked external articles, pasted text, and tweet screenshots. It can run inside Hermes Agent, or completely standalone in Codex, Claude Code, OpenCode, and plain shell workflows.

## Features

- **Tweet URL ingestion via `xurl`**
  - fetch structured tweet data from X API
  - auto-expand quoted / referenced tweet context
- **Native X article support**
  - prefer the X API `article` field when available
- **External article branch**
  - fetch the first non-X article linked from a tweet
- **Pasted text analysis**
  - analyze copied tweet/post text directly
- **Screenshot OCR**
  - extract tweet text from screenshots with `tesseract`
- **Durable storage**
  - append research notes into monthly markdown inbox files
- **Stable JSON output**
  - return machine-readable output with `--json`
- **Harness-agnostic design**
  - no Hermes-only runtime dependency for script execution

## Repo layout

```text
x-research/
├── README.md
├── SKILL.md
├── requirements.txt
├── references/
│   ├── flow.md
│   ├── harness-agnostic-design.md
│   ├── native-article-and-cleanup-notes.md
│   └── setup-macos.md
├── scripts/
│   ├── setup_macos.sh
│   ├── x_common.py
│   ├── x_fetch.py
│   ├── x_quality.py
│   ├── x_research.py
│   ├── x_research_article.py
│   ├── x_research_url.py
│   ├── x_screenshot_ocr.py
│   ├── x_store_screenshot.py
│   └── x_store_text.py
└── tests/
    └── test_x_research.py
```

## Requirements

- Python 3.9+
- `xurl` authenticated against X API for URL-based routes
- `requests`
- `tesseract` for screenshot OCR only
- `uv` recommended on macOS, but plain `python3 + pip` also works

Before using tweet URL routes, verify X auth:

```bash
xurl auth status
```

## Install

### Option A — macOS one-command setup

From the repo root:

```bash
./scripts/setup_macos.sh
```

Preview without changing the machine:

```bash
./scripts/setup_macos.sh --dry-run
```

What the script prepares:

- installs `uv` when missing
- installs `tesseract` when missing
- installs `xurl` when missing
- creates `.venv`
- installs `requirements.txt` into `.venv`

After setup:

```bash
xurl auth status
.venv/bin/python scripts/x_research.py --text 'hello world' --author '@test' --json
```

### Option B — manual install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

System dependencies are still separate:

- macOS: `brew install tesseract`
- Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
- `xurl`: install from the official repo, then finish auth with `xurl`

## Install into different harnesses

### Hermes Agent

If you want Hermes to load this repo as a local skill, place it under `~/.hermes/skills/`.

Recommended during development: symlink the repo.

```bash
mkdir -p ~/.hermes/skills
ln -s ~/Desktop/x-research ~/.hermes/skills/x-research
```

If the path already exists:

```bash
rm -rf ~/.hermes/skills/x-research
ln -s ~/Desktop/x-research ~/.hermes/skills/x-research
```

Then load it with Hermes:

```bash
hermes -s x-research
```

Or inside an existing session:

```text
/skill x-research
```

Notes:
- skill discovery is session-cached; start a new Hermes session if it does not appear immediately
- this repo already includes `SKILL.md`, so Hermes can read it directly once it sits in the skills directory

### Codex CLI

Codex can load this repo as a **skill** (appears in `/command`) or use it standalone.

#### As a Codex skill

Place the repo (or a symlink) under `~/.codex/skills/`:

```bash
mkdir -p ~/.codex/skills
ln -s ~/Desktop/x-research ~/.codex/skills/x-research
```

After restarting Codex, the skill appears in `/command` and Codex can invoke it naturally when the task matches.

#### As a standalone tool repo

```bash
git clone <repo-url>
cd x-research
./scripts/setup_macos.sh
```

Then call the scripts directly:

```bash
.venv/bin/python scripts/x_research.py '<tweet-url>' --json
```

To make it available inside another Codex workspace, use one of these:

- clone it next to the target project
- add it as a git submodule
- symlink the folder into the workspace

### Claude Code

Claude Code can load this as a **skill** (auto-invoked via natural language) or use it standalone.

#### As a Claude Code skill

Place the repo (or a symlink) under `~/.claude/skills/`:

```bash
mkdir -p ~/.claude/skills
ln -s ~/Desktop/x-research ~/.claude/skills/x-research
```

Claude Code reads markdown guides in `.claude/skills/` and auto-invokes them when the task matches. The repo's `SKILL.md` serves as the skill guide.

For project-local use instead of global:

```bash
mkdir -p .claude/skills
ln -s ~/Desktop/x-research .claude/skills/x-research
```

#### As a standalone tool repo

```bash
git clone <repo-url>
cd x-research
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Then run the scripts directly.

Why this works: internal script-to-script calls resolve paths via `__file__`, not Hermes-specific filesystem assumptions.

## Usage

### Unified entrypoint

```bash
python3 scripts/x_research.py '<tweet-url>'
python3 scripts/x_research.py '<tweet-url>' --store
python3 scripts/x_research.py '<tweet-url>' --json
python3 scripts/x_research.py '<tweet-url>' --route external
python3 scripts/x_research.py --text '<tweet text>' --author '@handle'
python3 scripts/x_research.py /path/to/screenshot.jpg --route image --lang eng
```

### Fetch structured tweet JSON

```bash
python3 scripts/x_fetch.py '<tweet-url>'
python3 scripts/x_fetch.py '<tweet-url>' --pretty
```

### Pasted text route

```bash
python3 scripts/x_store_text.py --author '@handle' --text '<tweet text>'
```

### Screenshot OCR only

```bash
python3 scripts/x_screenshot_ocr.py /path/to/image.jpg --lang eng
python3 scripts/x_screenshot_ocr.py /path/to/image.jpg --lang chi_sim
python3 scripts/x_screenshot_ocr.py /path/to/image.jpg --lang chi_tra
```

### Screenshot OCR + analyze + store

```bash
python3 scripts/x_store_screenshot.py /path/to/image.jpg --lang eng
```

## Route behavior

- **normal tweet URL** → fetch through `xurl`
- **native X article** → prefer X API `article` field
- **tweet with external link** → fetch tweet first, then fetch the first non-X article URL
- **pasted text** → direct analysis path
- **screenshot** → OCR path

If URL ingestion fails, use pasted text or screenshot OCR instead of inferring meaning from the URL.

## Storage

When `--store` is used, notes append to:

```text
~/.hermes/workspace/research/x-research/inbox/YYYY-MM.md
```

Override the destination with either:

```bash
python3 scripts/x_research.py '<tweet-url>' --store --output-dir /tmp/x-research
```

or:

```bash
export X_RESEARCH_DIR=/tmp/x-research
```

## JSON output

Use `--json` when another tool, agent, or harness needs stable machine-readable output.

Current top-level fields:

- `route`
- `author`
- `tweet_time`
- `source_url`
- `stored_to`
- `analysis`
- `raw_text`
- `note_body`
- `metadata`

## Smoke test

This route does not require X auth, so it is the fastest install check:

```bash
python3 scripts/x_research.py --text 'hello world' --author '@test' --json
```

To verify URL ingestion too:

```bash
xurl auth status
python3 scripts/x_fetch.py '<tweet-url>' --pretty
```

## Development

Run tests:

```bash
python3 -m pytest tests/test_x_research.py -q
```

## Notes

- `xurl` auth is intentionally not automated by the setup script
- OCR quality depends on image quality
- `tesseract` is only required for screenshot routes
- this repo is designed to run outside Hermes; Hermes installation is optional

## References

- `SKILL.md`
- `references/setup-macos.md`
- `references/harness-agnostic-design.md`
- `references/native-article-and-cleanup-notes.md`
- `references/flow.md`

## License

MIT
