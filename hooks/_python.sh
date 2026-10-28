#!/usr/bin/env bash
# Prints the command that runs Python 3.11+ (python, then py -3) and exits 0.
# When none qualifies, prints a message on stderr and exits 1.
# The Windows Store "python" alias is rejected.
found=""
try() {
  local label="$1"; shift
  local first="$1"
  local path
  path="$(command -v "$first" 2>/dev/null)" || { found="$found $label=missing"; return 1; }
  case "$path" in
    *WindowsApps*|*windowsapps*) found="$found $label=store-alias"; return 1 ;;
  esac
  local out
  out="$("$@" --version 2>&1)" || { found="$found $label=fails"; return 1; }
  if [[ "$out" =~ Python\ ([0-9]+)\.([0-9]+) ]]; then
    found="$found $label=${BASH_REMATCH[1]}.${BASH_REMATCH[2]}"
    if (( BASH_REMATCH[1] > 3 || (BASH_REMATCH[1] == 3 && BASH_REMATCH[2] >= 11) )); then
      return 0
    fi
    return 1
  fi
  found="$found $label=unknown"
  return 1
}
if try python python; then echo "python"; exit 0; fi
if try "py -3" py -3; then echo "py -3"; exit 0; fi
echo "game-studio hook: Python 3.11+ not found (${found# }). Install Python 3.11+ from python.org." >&2
exit 1
