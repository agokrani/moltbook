#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "[moltbook-tools] $*" >&2
  exit 1
}

require_env() {
  local name=""
  for name in "$@"; do
    if [ -z "${!name:-}" ]; then
      fail "Missing required environment variable: $name"
    fi
  done
}

require_jq() {
  command -v jq >/dev/null 2>&1 || fail "jq is required but not available in PATH"
}

read_text_arg() {
  local value="$1"
  local file_path="$2"
  local label="$3"

  if [ -n "$value" ] && [ -n "$file_path" ]; then
    fail "Use either --${label} or --${label}-file, not both"
  fi

  if [ -n "$file_path" ]; then
    if [ "$file_path" = "-" ]; then
      cat
      return
    fi
    [ -f "$file_path" ] || fail "File not found for --${label}-file: $file_path"
    cat "$file_path"
    return
  fi

  printf '%s' "$value"
}

request_json() {
  local method="$1"
  local url="$2"
  local payload="${3:-}"
  local auth_header="${4:-}"
  local body_file
  local status
  local curl_cmd=()

  body_file="$(mktemp)"

  curl_cmd=(curl -sS -o "$body_file" -w '%{http_code}' -X "$method" "$url")
  if [ -n "$auth_header" ]; then
    curl_cmd+=(-H "$auth_header")
  fi
  if [ -n "$payload" ]; then
    curl_cmd+=(-H "Content-Type: application/json" -d "$payload")
  fi

  if ! status="$("${curl_cmd[@]}")"; then
    cat "$body_file" >&2 || true
    rm -f "$body_file"
    return 1
  fi

  case "$status" in
    2*)
      cat "$body_file"
      ;;
    *)
      echo "[moltbook-tools] Request failed: $method $url -> HTTP $status" >&2
      if jq -e . "$body_file" >/dev/null 2>&1; then
        jq . "$body_file" >&2
      else
        cat "$body_file" >&2
      fi
      rm -f "$body_file"
      return 1
      ;;
  esac

  rm -f "$body_file"
}
