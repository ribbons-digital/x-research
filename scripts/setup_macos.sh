#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${BASE_DIR}/.venv"
REQ_FILE="${BASE_DIR}/requirements.txt"
XURL_INSTALL_URL="https://raw.githubusercontent.com/xdevplatform/xurl/main/install.sh"

log() {
  printf '[x-research setup] %s\n' "$*"
}

fail() {
  printf '[x-research setup] ERROR: %s\n' "$*" >&2
  exit 1
}

run_cmd() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run]'
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
    return 0
  fi
  "$@"
}

ensure_macos() {
  [[ "$(uname -s)" == "Darwin" ]] || fail 'This setup script is for macOS only.'
}

ensure_brew() {
  if ! command -v brew >/dev/null 2>&1; then
    fail 'Homebrew is required. Install it first from https://brew.sh/'
  fi
}

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    log "uv already installed: $(command -v uv)"
    return
  fi
  log 'Installing uv via Homebrew'
  run_cmd brew install uv
}

ensure_tesseract() {
  if command -v tesseract >/dev/null 2>&1; then
    log "tesseract already installed: $(command -v tesseract)"
    return
  fi
  log 'Installing tesseract via Homebrew'
  run_cmd brew install tesseract
}

ensure_xurl() {
  export PATH="${HOME}/.local/bin:${PATH}"
  if command -v xurl >/dev/null 2>&1; then
    log "xurl already installed: $(command -v xurl)"
    return
  fi
  log 'Installing xurl via official install script'
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run] curl -fsSL %q | bash\n' "$XURL_INSTALL_URL"
    return
  fi
  curl -fsSL "$XURL_INSTALL_URL" | bash
}

ensure_venv() {
  log "Creating uv virtualenv at ${VENV_DIR}"
  run_cmd uv venv "$VENV_DIR"
}

install_python_deps() {
  [[ -f "$REQ_FILE" ]] || fail "requirements.txt not found at ${REQ_FILE}"
  log 'Installing Python dependencies into .venv via uv pip'
  run_cmd uv pip install --python "${VENV_DIR}/bin/python" -r "$REQ_FILE"
}

print_next_steps() {
  cat <<'EOF'

[x-research setup] Done.

Next steps:
1. Ensure ~/.local/bin is in PATH for future shells if xurl was newly installed:
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
2. Authenticate xurl:
   xurl auth status
3. Run a smoke test:
   .venv/bin/python scripts/x_research.py --text 'hello world' --author '@test' --json
EOF
}

main() {
  ensure_macos
  ensure_brew
  ensure_uv
  ensure_tesseract
  ensure_xurl
  ensure_venv
  install_python_deps
  print_next_steps
}

main "$@"
