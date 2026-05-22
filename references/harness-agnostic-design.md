# Harness-Agnostic Skill Design

Design decisions made during the 2026-05 refactor so the x-research skill can run outside Hermes (e.g., Codex, direct shell clone).

## Principles

### 1. No hardcoded Hermes paths
Bad: `WORKSPACE = Path('~/.hermes/workspace').expanduser()`  
Good: `SCRIPT_DIR = Path(__file__).parent.resolve()`

Scripts resolve sibling helpers via `__file__`, not environment assumptions.

### 2. Delegated CLI over embedded credentials
Bad: Read `X_API_BEARER_TOKEN` from `~/.hermes/.env`, call `requests.get()` directly.  
Good: Shell out to `xurl` CLI which manages its own auth store (`xurl auth status`).

This removes the skill's dependency on Hermes env files and lets xurl handle token refresh, app switching, and OAuth2 flows.

### 3. Configurable output directory
Default: `~/.hermes/workspace/research/x-research/inbox/` (for backward compat).  
Override hierarchy:
1. `--output-dir` CLI flag
2. `X_RESEARCH_DIR` environment variable
3. Default path

### 4. Self-contained script suite
Every script is runnable standalone. Inter-script calls use explicit `python3 str(SCRIPT_DIR / 'helper.py')` so they work regardless of PYTHONPATH or cwd.

### 5. Minimal Python dependencies
Only `requests` is required. System deps (`tesseract`, `xurl`) are declared in SKILL.md, not auto-installed.

## Why this matters

Hermes skills that hardcode `~/.hermes/...` paths or depend on Hermes-specific env files cannot be cloned into a Codex workspace or a CI runner and used immediately. Making the skill harness-agnostic means the same scripts work in:
- Hermes agent sessions
- Codex CLI projects
- Standalone cron jobs
- Docker containers (with xurl + tesseract installed)
