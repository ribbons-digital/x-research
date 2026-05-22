# macOS setup helper

Use `scripts/setup_macos.sh` when moving this skill to another Mac and you want one command to prepare the Python + CLI dependencies.

## What it does

- verifies macOS
- requires Homebrew
- installs `uv` if missing
- installs `tesseract` if missing
- installs `xurl` via the official install script if missing
- creates `.venv` under the skill root
- installs `requirements.txt` into that `.venv` via `uv pip`

## Run

From the skill root:

```bash
./scripts/setup_macos.sh
```

Dry-run first if you want to inspect actions without changing the machine:

```bash
./scripts/setup_macos.sh --dry-run
```

## After setup

1. ensure `~/.local/bin` is on PATH if `xurl` was newly installed
2. run `xurl auth status`
3. if not authenticated, complete `xurl` auth before using URL routes
4. smoke test:

```bash
.venv/bin/python scripts/x_research.py --text 'hello world' --author '@test' --json
```

## Notes

- `uv` only manages Python dependencies; `xurl` and `tesseract` are still system tools
- screenshot OCR needs `tesseract`; URL/text routes do not
- the helper intentionally does not automate `xurl` auth because that depends on your X app/account setup
