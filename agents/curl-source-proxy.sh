#!/usr/bin/env bash
set -euo pipefail

REAL_CURL="${REAL_CURL:-/usr/bin/curl}"
MANIFEST="${SOURCE_PROXY_MANIFEST:-}"
BASE_URL="${SOURCE_PROXY_BASE_URL:-}"

rewrite_url() {
  local original="$1"

  if [ -z "$MANIFEST" ] || [ -z "$BASE_URL" ] || [ ! -f "$MANIFEST" ]; then
    printf '%s\n' "$original"
    return
  fi

  while IFS=$'\t' read -r source_id source_url; do
    if [ "$original" = "$source_url" ] && [ -n "$source_id" ]; then
      printf '%s/sources/by-id/%s\n' "${BASE_URL%/}" "$source_id"
      return
    fi
  done < "$MANIFEST"

  printf '%s\n' "$original"
}

args=()
for arg in "$@"; do
  case "$arg" in
    http://*|https://*)
      args+=("$(rewrite_url "$arg")")
      ;;
    *)
      args+=("$arg")
      ;;
  esac
done

exec "$REAL_CURL" "${args[@]}"
