#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

pause_and_exit() {
  local code="${1:-0}"
  echo
  read -r -p "Press Enter to close this window..." _
  exit "$code"
}

if [[ ! -x "$SCRIPT_DIR/run_enable_chrome_ai.sh" ]]; then
  echo "Error: run_enable_chrome_ai.sh is missing or not executable."
  pause_and_exit 1
fi

echo "Running Enable Chrome AI..."
echo

set +e
"$SCRIPT_DIR/run_enable_chrome_ai.sh"
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  echo
  echo "Completed successfully."
else
  echo
  echo "Completed with errors (exit code: $status)."
fi

pause_and_exit "$status"
