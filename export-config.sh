#!/usr/bin/env bash
# export-config.sh — Read CoolerControl daemon state via REST API and
# generate a Nix attrset documenting the current configuration.
#
# Usage:
#   ./export-config.sh                              # default localhost
#   ./export-config.sh --url http://host:11987      # custom URL
#   ./export-config.sh --token <bearer-token>       # explicit auth
#   COOLERCONTROL_TOKEN=xxx ./export-config.sh      # env var auth
#
# Dependencies: curl, jq

set -euo pipefail

URL="http://localhost:11987"
TOKEN="${COOLERCONTROL_TOKEN:-}"

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
  -h | --help)
    echo "Usage: $0 [--url URL] [--token TOKEN]"
    echo ""
    echo "Read CoolerControl daemon state and output a Nix attrset."
    echo ""
    echo "Options:"
    echo "  --url URL      Daemon URL (default: http://localhost:11987)"
    echo "  --token TOKEN  Bearer token for authentication"
    echo "                 (or set COOLERCONTROL_TOKEN env var)"
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

# Build curl auth header
AUTH_HEADER=()
if [[ -n $TOKEN ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer $TOKEN")
fi

# Try a request; handle auth gracefully
api_get() {
  local path="$1"
  local response status body
  response=$(curl -s -w '\n%{http_code}' "${AUTH_HEADER[@]}" "${URL}/api${path}" 2>/dev/null) || {
    echo "# ERROR: Failed to connect to ${URL}" >&2
    return 1
  }
  status=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')

  if [[ $status == "401" ]]; then
    if [[ -z $TOKEN ]]; then
      echo "# WARNING: API returned 401 Unauthorized. Use --token or COOLERCONTROL_TOKEN." >&2
    else
      echo "# ERROR: Token rejected (401)." >&2
    fi
    return 1
  fi

  if [[ $status -ge 400 ]]; then
    echo "# WARNING: GET /api${path} returned HTTP ${status}" >&2
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
echo "  # ── Custom sensors ──"
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
