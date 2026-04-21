#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_PATH="$ROOT_DIR/Enable Chrome AI.app"
RESOURCES_DIR="$APP_PATH/Contents/Resources"
LAUNCHER_DIR="$RESOURCES_DIR/launcher"
PAYLOAD_DIR="$RESOURCES_DIR/payload"
DEFAULT_REPO_URL="https://github.com/lcandy2/enable-chrome-ai.git"

if ! command -v osacompile >/dev/null 2>&1; then
  echo "Error: osacompile is required on macOS."
  exit 1
fi

REPO_URL="${ENABLE_CHROME_AI_EMBED_REPO_URL:-}"
if [[ -z "$REPO_URL" ]]; then
  REPO_URL="$(git -C "$ROOT_DIR" remote get-url upstream 2>/dev/null || true)"
fi
if [[ -z "$REPO_URL" ]]; then
  REPO_URL="$DEFAULT_REPO_URL"
fi

osacompile -o "$APP_PATH" <<'APPLESCRIPT'
on run
  set appPath to POSIX path of (path to me)
  set resourcesPath to appPath & "Contents/Resources"
  set launcherPath to resourcesPath & "/launcher/run_enable_chrome_ai.sh"
  set logsDir to (POSIX path of (path to home folder)) & "Library/Application Support/Enable Chrome AI/logs"

  set launcherReady to (do shell script "if [ -x " & quoted form of launcherPath & " ]; then echo yes; else echo no; fi")
  if launcherReady is not "yes" then
    display dialog "Setup file is missing or not executable:\n\n" & launcherPath buttons {"OK"} default button "OK" with icon stop
    return
  end if

  set introText to "Enable Chrome AI will now set everything up automatically.\n\nIt will:\n- Check for updates\n- Install required runtime and dependencies\n- Configure Chrome and reopen it\n\nChrome may close briefly while this runs."
  set introChoice to button returned of (display dialog introText buttons {"Cancel", "Continue"} default button "Continue" with icon note)
  if introChoice is "Cancel" then
    return
  end if

  set shellCmd to "ENABLE_CHROME_AI_GUI=1 " & quoted form of launcherPath

  try
    with timeout of 7200 seconds
      do shell script shellCmd
    end timeout

    set successResult to display dialog "All set. Chrome AI setup completed successfully." buttons {"Done", "Open Logs"} default button "Done" with icon note
    if button returned of successResult is "Open Logs" then
      do shell script "open " & quoted form of logsDir
    end if
  on error errMsg number errNum
    set failureResult to display dialog "Setup could not finish automatically.\n\n" & errMsg buttons {"Close", "Open Logs"} default button "Open Logs" with icon caution
    if button returned of failureResult is "Open Logs" then
      do shell script "open " & quoted form of logsDir
    end if
  end try
end run
APPLESCRIPT

mkdir -p "$LAUNCHER_DIR" "$PAYLOAD_DIR/local_patches"

cp "$ROOT_DIR/run_enable_chrome_ai.sh" "$LAUNCHER_DIR/run_enable_chrome_ai.sh"
chmod +x "$LAUNCHER_DIR/run_enable_chrome_ai.sh"

cp "$ROOT_DIR/main.py" "$PAYLOAD_DIR/main.py"
cp "$ROOT_DIR/pyproject.toml" "$PAYLOAD_DIR/pyproject.toml"
cp "$ROOT_DIR/uv.lock" "$PAYLOAD_DIR/uv.lock"
cp "$ROOT_DIR/.python-version" "$PAYLOAD_DIR/.python-version"
cp "$ROOT_DIR/local_patches/graceful_chrome_quit.patch" "$PAYLOAD_DIR/local_patches/graceful_chrome_quit.patch"
printf '%s\n' "$REPO_URL" > "$PAYLOAD_DIR/repo_url.txt"

echo "Built: $APP_PATH"
echo "Embedded update source: $REPO_URL"
