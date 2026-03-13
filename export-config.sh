#!/usr/bin/env bash
# export-config.sh — Read CoolerControl daemon state via REST API and
# generate a Nix attrset documenting the current configuration.
#
# Usage:
#   ./export-config.sh                              # default localhost
#   ./export-config.sh --url https://host:11987     # custom URL
#   ./export-config.sh --token <access-token>       # access token auth (Bearer)
#   ./export-config.sh --password <password>        # basic auth login (CCAdmin)
#   COOLERCONTROL_TOKEN=xxx ./export-config.sh      # env var token auth
#   COOLERCONTROL_PASSWORD=xxx ./export-config.sh   # env var password auth
#
# Dependencies: curl, jq

set -euo pipefail

URL="https://localhost:11987"
TOKEN="${COOLERCONTROL_TOKEN:-}"
PASSWORD="${COOLERCONTROL_PASSWORD:-}"
COOKIE_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
  --url)
    URL="$2"
    shift 2
    ;;
  --token)
    TOKEN="$2"
    shift 2
    ;;
  --password)
    PASSWORD="$2"
    shift 2
    ;;
  -h | --help)
    echo "Usage: $0 [--url URL] [--token TOKEN] [--password PASSWORD]"
    echo ""
    echo "Read CoolerControl daemon state and output a Nix attrset."
    echo ""
    echo "Options:"
    echo "  --url URL          Daemon URL (default: https://localhost:11987)"
    echo "  --token TOKEN      Access token for Bearer auth"
    echo "                     (or set COOLERCONTROL_TOKEN env var)"
    echo "  --password PASS    Password for CCAdmin basic auth login"
    echo "                     (or set COOLERCONTROL_PASSWORD env var)"
    exit 0
    ;;
  *)
    echo "Unknown option: $1" >&2
    exit 1
    ;;
  esac
done

# Strip trailing slash
URL="${URL%/}"

# Cleanup temp files on exit
cleanup() {
  [[ -n $COOKIE_FILE && -f $COOKIE_FILE ]] && rm -f "$COOKIE_FILE"
}
trap cleanup EXIT

# Perform basic auth login if password provided (and no token)
if [[ -z $TOKEN && -n $PASSWORD ]]; then
  COOKIE_FILE=$(mktemp)
  BASIC_CREDS=$(printf 'CCAdmin:%s' "$PASSWORD" | base64 -w0)
  login_status=$(curl -sk -o /dev/null -w '%{http_code}' \
    -X POST \
    -H "Authorization: Basic $BASIC_CREDS" \
    -c "$COOKIE_FILE" \
    "${URL}/login" 2>/dev/null) || {
    echo "# ERROR: Failed to connect to ${URL}" >&2
    exit 1
  }
  if [[ $login_status -ge 400 ]]; then
    echo "# ERROR: Login failed with HTTP ${login_status}. Check password." >&2
    exit 1
  fi
  # Verify cookie file has content
  if [[ ! -s $COOKIE_FILE ]]; then
    echo "# WARNING: Login succeeded (HTTP ${login_status}) but no cookies received." >&2
  fi
fi

# Try a request; handle auth gracefully
api_get() {
  local path="$1"
  local response status body
  local auth_args=()

  if [[ -n $TOKEN ]]; then
    auth_args+=(-H "Authorization: Bearer $TOKEN")
  elif [[ -n $COOKIE_FILE && -f $COOKIE_FILE ]]; then
    auth_args+=(-b "$COOKIE_FILE")
  fi

  response=$(curl -sk -w '\n%{http_code}' "${auth_args[@]}" "${URL}${path}" 2>/dev/null) || {
    echo "# ERROR: Failed to connect to ${URL}" >&2
    return 1
  }
  status=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')

  if [[ $status == "401" ]]; then
    if [[ -z $TOKEN && -z $PASSWORD ]]; then
      echo "# WARNING: API returned 401 Unauthorized. Use --token, --password, or set COOLERCONTROL_TOKEN/COOLERCONTROL_PASSWORD." >&2
    else
      echo "# ERROR: Authentication rejected (401)." >&2
    fi
    return 1
  fi

  if [[ $status -ge 400 ]]; then
    echo "# WARNING: GET ${path} returned HTTP ${status}" >&2
    echo "null"
    return 0
  fi

  echo "$body"
}

# Helper: convert JSON to Nix-ish repr via jq
to_nix() {
  jq -r '
    def to_nix:
      if type == "null" then "null"
      elif type == "boolean" then (if . then "true" else "false" end)
      elif type == "number" then tostring
      elif type == "string" then "\"\(gsub("\\\\"; "\\\\") | gsub("\""; "\\\""))\""
      elif type == "array" then "[\n" + ([.[] | "    " + to_nix] | join("\n")) + "\n  ]"
      elif type == "object" then "{\n" + ([to_entries[] | "    \(.key) = \(.value | to_nix);"] | join("\n")) + "\n  }"
      else tostring
      end;
    to_nix
  '
}

echo "# CoolerControl configuration export"
echo "# Generated: $(date -Iseconds)"
echo "# Source: ${URL}"
echo "#"
echo "# This is a documentation snapshot of the daemon's current state."
echo "# Paste relevant sections into your Home Manager coolercontrol config."
echo ""
echo "{"

# ── Devices ──
echo "  # ── Devices ──"
devices=$(api_get "/devices" 2>/dev/null) || devices="[]"
echo "  devices = $(echo "$devices" | to_nix);"
echo ""

# ── Profiles ──
echo "  # ── Profiles (fan curves) ──"
profiles=$(api_get "/profiles" 2>/dev/null) || profiles="[]"
echo "  profiles = $(echo "$profiles" | to_nix);"
echo ""

# ── Functions ──
echo "  # ── Functions ──"
functions=$(api_get "/functions" 2>/dev/null) || functions="[]"
echo "  functions = $(echo "$functions" | to_nix);"
echo ""

# ── Modes ──
echo "  # ── Modes ──"
modes=$(api_get "/modes" 2>/dev/null) || modes="[]"
echo "  modes = $(echo "$modes" | to_nix);"
echo ""

# ── Active mode ──
echo "  # ── Active mode ──"
active_mode=$(api_get "/modes-active" 2>/dev/null) || active_mode="null"
echo "  activeMode = $(echo "$active_mode" | to_nix);"
echo ""

# ── Custom sensors ──
echo "  # ── Custom sensors (may not exist) ──"
custom_sensors=$(api_get "/custom-sensors" 2>/dev/null) || custom_sensors="[]"
echo "  customSensors = $(echo "$custom_sensors" | to_nix);"
echo ""

# ── Alerts ──
echo "  # ── Alerts ──"
alerts=$(api_get "/alerts" 2>/dev/null) || alerts="[]"
echo "  alerts = $(echo "$alerts" | to_nix);"
echo ""

# ── Global settings ──
echo "  # ── Global settings ──"
settings=$(api_get "/settings" 2>/dev/null) || settings="{}"
echo "  settings = $(echo "$settings" | to_nix);"
echo ""

echo "}"
