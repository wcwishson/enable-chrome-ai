#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="Enable Chrome AI"
WORK_ROOT="${ENABLE_CHROME_AI_WORK_ROOT:-$HOME/Library/Application Support/$APP_NAME}"
LOG_DIR="$WORK_ROOT/logs"
RUNTIME_DIR="$WORK_ROOT/runtime"
REPO_DIR="$WORK_ROOT/repo"
mkdir -p "$LOG_DIR" "$RUNTIME_DIR"
LOG_FILE="$LOG_DIR/enable_chrome_ai_$(date '+%Y%m%d_%H%M%S').log"

GUI_MODE="${ENABLE_CHROME_AI_GUI:-0}"
UV_BIN=""
DEFAULT_REPO_URL="https://github.com/lcandy2/enable-chrome-ai.git"
REPO_URL="${ENABLE_CHROME_AI_REPO_URL:-}"
ACTIVE_SOURCE_DIR=""
PAYLOAD_DIR=""
PATCH_MARKER="def gracefully_quit_chrome_on_mac"
GIT_CHECKED=0
GIT_OK=0

CHROME_APP_NAMES=(
  "Google Chrome"
  "Google Chrome Canary"
  "Google Chrome Dev"
  "Google Chrome Beta"
)

CHROME_USER_DATA_PATHS=(
  "$HOME/Library/Application Support/Google/Chrome"
  "$HOME/Library/Application Support/Google/Chrome Canary"
  "$HOME/Library/Application Support/Google/Chrome Dev"
  "$HOME/Library/Application Support/Google/Chrome Beta"
)

log() {
  local message="$1"
  local line="[$(date '+%H:%M:%S')] $message"
  echo "$line" >>"$LOG_FILE"
  if [[ "$GUI_MODE" != "1" ]]; then
    echo "$line"
  fi
}

fail() {
  local message="$1"
  echo "ERROR: $message" >>"$LOG_FILE"
  echo "Log file: $LOG_FILE" >>"$LOG_FILE"
  echo "$message" >&2
  echo "Details were saved to: $LOG_FILE" >&2
  exit 1
}

find_payload_dir() {
  # Repo mode: script sits next to main.py.
  if [[ -f "$SCRIPT_DIR/main.py" && -f "$SCRIPT_DIR/pyproject.toml" ]]; then
    PAYLOAD_DIR="$SCRIPT_DIR"
    return 0
  fi

  # App-bundle mode: script is under .../Contents/Resources/launcher, payload is sibling folder.
  if [[ -f "$SCRIPT_DIR/../payload/main.py" && -f "$SCRIPT_DIR/../payload/pyproject.toml" ]]; then
    PAYLOAD_DIR="$(cd "$SCRIPT_DIR/../payload" && pwd)"
    return 0
  fi

  fail "Could not find bundled setup files. Please reinstall the app package."
}

resolve_repo_url() {
  if [[ -n "$REPO_URL" ]]; then
    return 0
  fi

  if git_is_usable && git -C "$PAYLOAD_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    REPO_URL="$(git -C "$PAYLOAD_DIR" remote get-url upstream 2>/dev/null || true)"
    if [[ -n "$REPO_URL" ]]; then
      return 0
    fi
  fi

  if [[ -z "$REPO_URL" && -f "$PAYLOAD_DIR/repo_url.txt" ]]; then
    REPO_URL="$(head -n 1 "$PAYLOAD_DIR/repo_url.txt" | tr -d '\r')"
    return 0
  fi

  if [[ -z "$REPO_URL" ]]; then
    REPO_URL="$DEFAULT_REPO_URL"
  fi
}

git_is_usable() {
  if [[ "$GIT_CHECKED" -eq 1 ]]; then
    [[ "$GIT_OK" -eq 1 ]]
    return
  fi

  GIT_CHECKED=1
  if command -v git >/dev/null 2>&1 && git --version >>"$LOG_FILE" 2>&1; then
    GIT_OK=1
  else
    GIT_OK=0
  fi

  [[ "$GIT_OK" -eq 1 ]]
}

is_graceful_main() {
  local target_file="$1"
  grep -q "$PATCH_MARKER" "$target_file"
}

copy_runtime_payload() {
  local source_dir="$1"
  local source_main="$source_dir/main.py"
  local source_pyproject="$source_dir/pyproject.toml"
  local source_lock="$source_dir/uv.lock"
  local payload_main="$PAYLOAD_DIR/main.py"
  local payload_pyproject="$PAYLOAD_DIR/pyproject.toml"
  local payload_lock="$PAYLOAD_DIR/uv.lock"
  local source_patch="$source_dir/local_patches/graceful_chrome_quit.patch"
  local payload_patch="$PAYLOAD_DIR/local_patches/graceful_chrome_quit.patch"

  mkdir -p "$RUNTIME_DIR/local_patches"

  if [[ -f "$source_pyproject" ]]; then
    cp "$source_pyproject" "$RUNTIME_DIR/pyproject.toml"
  else
    cp "$payload_pyproject" "$RUNTIME_DIR/pyproject.toml"
  fi

  if [[ -f "$source_lock" ]]; then
    cp "$source_lock" "$RUNTIME_DIR/uv.lock"
  elif [[ -f "$payload_lock" ]]; then
    cp "$payload_lock" "$RUNTIME_DIR/uv.lock"
  fi

  if [[ -f "$source_main" ]]; then
    cp "$source_main" "$RUNTIME_DIR/main.py"
  else
    cp "$payload_main" "$RUNTIME_DIR/main.py"
  fi

  if [[ -f "$source_patch" ]]; then
    cp "$source_patch" "$RUNTIME_DIR/local_patches/graceful_chrome_quit.patch"
  elif [[ -f "$payload_patch" ]]; then
    cp "$payload_patch" "$RUNTIME_DIR/local_patches/graceful_chrome_quit.patch"
  fi
}

ensure_runtime_graceful_patch() {
  local runtime_main="$RUNTIME_DIR/main.py"
  local runtime_patch="$RUNTIME_DIR/local_patches/graceful_chrome_quit.patch"
  local payload_main="$PAYLOAD_DIR/main.py"

  if [[ ! -f "$runtime_main" ]]; then
    fail "Runtime setup is incomplete (main.py missing)."
  fi

  if is_graceful_main "$runtime_main"; then
    return 0
  fi

  if [[ ! -f "$runtime_patch" ]]; then
    fail "Runtime setup is incomplete (graceful patch file missing)."
  fi

  if command -v patch >/dev/null 2>&1; then
    if (cd "$RUNTIME_DIR" && patch -p1 -N -r - < "$runtime_patch") >>"$LOG_FILE" 2>&1; then
      if is_graceful_main "$runtime_main"; then
        log "Applied local graceful-quit safety patch to latest script."
        return 0
      fi
    fi
  fi

  log "Could not patch latest upstream script cleanly. Falling back to bundled compatible script."
  cp "$payload_main" "$runtime_main"

  if ! is_graceful_main "$runtime_main"; then
    fail "Graceful-quit safety patch is not present in runtime script."
  fi
}

refresh_source_tree() {
  ACTIVE_SOURCE_DIR="$PAYLOAD_DIR"
  log "Checking for script updates..."

  if ! git_is_usable; then
    log "Git is not available. Using bundled scripts."
    return 0
  fi

  resolve_repo_url

  if [[ -d "$REPO_DIR/.git" ]]; then
    git -C "$REPO_DIR" remote set-url origin "$REPO_URL" >>"$LOG_FILE" 2>&1 || true
    if git -C "$REPO_DIR" pull --rebase --autostash >>"$LOG_FILE" 2>&1; then
      log "Scripts updated from $REPO_URL."
      ACTIVE_SOURCE_DIR="$REPO_DIR"
    else
      log "Could not update repo copy. Re-downloading scripts..."
      rm -rf "$REPO_DIR" >>"$LOG_FILE" 2>&1 || true
      if git clone --depth 1 "$REPO_URL" "$REPO_DIR" >>"$LOG_FILE" 2>&1; then
        log "Downloaded latest scripts from $REPO_URL."
        ACTIVE_SOURCE_DIR="$REPO_DIR"
      else
        log "Could not download latest scripts. Using bundled scripts."
      fi
    fi
    return 0
  fi

  local clone_tmp_dir="$WORK_ROOT/repo_clone_$$"
  if git clone --depth 1 "$REPO_URL" "$clone_tmp_dir" >>"$LOG_FILE" 2>&1; then
    rm -rf "$REPO_DIR" >>"$LOG_FILE" 2>&1 || true
    mv "$clone_tmp_dir" "$REPO_DIR"
    log "Downloaded latest scripts from $REPO_URL."
    ACTIVE_SOURCE_DIR="$REPO_DIR"
  else
    rm -rf "$clone_tmp_dir" >>"$LOG_FILE" 2>&1 || true
    log "Could not download latest scripts. Using bundled scripts."
  fi
}

update_repository() {
  refresh_source_tree
  copy_runtime_payload "$ACTIVE_SOURCE_DIR"
  ensure_runtime_graceful_patch

  if [[ ! -f "$RUNTIME_DIR/main.py" ]]; then
    fail "Runtime setup is incomplete (main.py missing)."
  fi
  if [[ ! -f "$RUNTIME_DIR/pyproject.toml" ]]; then
    fail "Runtime setup is incomplete (pyproject.toml missing)."
  fi
}

has_chrome_user_data() {
  local path
  for path in "${CHROME_USER_DATA_PATHS[@]}"; do
    if [[ -d "$path" ]]; then
      return 0
    fi
  done
  return 1
}

first_installed_chrome_app() {
  local name
  for name in "${CHROME_APP_NAMES[@]}"; do
    if [[ -d "/Applications/$name.app" || -d "$HOME/Applications/$name.app" ]]; then
      echo "$name"
      return 0
    fi
  done
  return 1
}

ensure_chrome_ready() {
  if has_chrome_user_data; then
    return 0
  fi

  local chrome_app
  chrome_app="$(first_installed_chrome_app || true)"
  if [[ -z "$chrome_app" ]]; then
    if command -v open >/dev/null 2>&1; then
      open "https://www.google.com/chrome/" >>"$LOG_FILE" 2>&1 || true
    fi
    fail "Google Chrome is required. A download page was opened. Install Chrome, open it once, then run this app again."
  fi

  log "Preparing Chrome profile for first run..."
  if ! open -a "$chrome_app" >>"$LOG_FILE" 2>&1; then
    fail "Could not open $chrome_app. Please open Chrome once manually and try again."
  fi

  local _i
  for _i in {1..30}; do
    if has_chrome_user_data; then
      break
    fi
    sleep 1
  done

  osascript -e "tell application \"$chrome_app\" to quit" >>"$LOG_FILE" 2>&1 || true

  if ! has_chrome_user_data; then
    fail "Chrome profile setup did not complete. Open Chrome once manually, close it, then run this app again."
  fi
}

detect_uv() {
  if command -v uv >/dev/null 2>&1; then
    UV_BIN="$(command -v uv)"
    return 0
  fi

  local candidate
  for candidate in "$HOME/.local/bin/uv" "/opt/homebrew/bin/uv" "/usr/local/bin/uv"; do
    if [[ -x "$candidate" ]]; then
      UV_BIN="$candidate"
      return 0
    fi
  done

  return 1
}

ensure_uv() {
  if detect_uv; then
    return 0
  fi

  if ! command -v curl >/dev/null 2>&1; then
    fail "An internet installer dependency (curl) is missing, so setup cannot continue automatically."
  fi

  log "Installing required runtime helper (uv)..."
  if ! curl -LsSf https://astral.sh/uv/install.sh | sh >>"$LOG_FILE" 2>&1; then
    fail "Automatic runtime setup failed while installing uv."
  fi

  if ! detect_uv; then
    fail "uv was installed but could not be located."
  fi
}

prepare_python_and_dependencies() {
  log "Preparing Python runtime and dependencies (first run may take a few minutes)..."
  "$UV_BIN" python install 3.13 >>"$LOG_FILE" 2>&1 || true
  if ! "$UV_BIN" sync --project "$RUNTIME_DIR" --frozen >>"$LOG_FILE" 2>&1; then
    fail "Dependency setup failed. Please check the internet connection and try again."
  fi
}

run_main_script() {
  log "Applying Chrome AI setup..."
  if ! "$UV_BIN" run --project "$RUNTIME_DIR" main.py <<< "" >>"$LOG_FILE" 2>&1; then
    fail "Chrome AI setup did not finish successfully."
  fi
}

main() {
  log "Starting Enable Chrome AI setup."
  find_payload_dir
  update_repository
  ensure_chrome_ready
  ensure_uv
  prepare_python_and_dependencies
  run_main_script
  log "Finished successfully."

  echo "$LOG_FILE"
}

main "$@"
