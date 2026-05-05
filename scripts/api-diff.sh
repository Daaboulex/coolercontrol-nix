#!/usr/bin/env bash
set -euo pipefail

# API contract diff — compares old and new OpenAPI specs
# Called by update.sh after version bump to detect breaking changes
# Exit 0: no breaking changes (or no spec found)
# Outputs: human-readable summary of changes

OLD_SPEC="${1:-api-schema.json}"
NEW_SPEC="${2:-}"

if [ ! -f "$OLD_SPEC" ]; then
  echo "No baseline spec found — skipping API diff"
  exit 0
fi

if [ -z "$NEW_SPEC" ]; then
  echo "Usage: api-diff.sh <old-spec> <new-spec>"
  exit 0
fi

if [ ! -f "$NEW_SPEC" ]; then
  echo "New spec not found: $NEW_SPEC"
  exit 0
fi

# Use Python for structured diff (available in Nix builds)
python3 - "$OLD_SPEC" "$NEW_SPEC" <<'PYTHON'
import json
import sys

def load_spec(path):
    with open(path) as f:
        return json.load(f)

old = load_spec(sys.argv[1])
new = load_spec(sys.argv[2])

changes = []
breaking = []

# --- Path changes ---
old_paths = set(old.get("paths", {}).keys())
new_paths = set(new.get("paths", {}).keys())

added_paths = new_paths - old_paths
removed_paths = old_paths - new_paths

if added_paths:
    changes.append(f"Added endpoints ({len(added_paths)}):")
    for p in sorted(added_paths):
        methods = ", ".join(new["paths"][p].keys()).upper()
        changes.append(f"  + {methods} {p}")

if removed_paths:
    breaking.append(f"Removed endpoints ({len(removed_paths)}):")
    for p in sorted(removed_paths):
        methods = ", ".join(old["paths"][p].keys()).upper()
        breaking.append(f"  - {methods} {p}")

# --- Method changes on existing paths ---
for path in sorted(old_paths & new_paths):
    old_methods = set(old["paths"][path].keys())
    new_methods = set(new["paths"][path].keys())
    removed_methods = old_methods - new_methods
    added_methods = new_methods - old_methods
    if removed_methods:
        breaking.append(f"Removed methods on {path}: {', '.join(m.upper() for m in sorted(removed_methods))}")
    if added_methods:
        changes.append(f"Added methods on {path}: {', '.join(m.upper() for m in sorted(added_methods))}")

# --- Schema changes ---
old_schemas = set(old.get("components", {}).get("schemas", {}).keys())
new_schemas = set(new.get("components", {}).get("schemas", {}).keys())

added_schemas = new_schemas - old_schemas
removed_schemas = old_schemas - new_schemas

if added_schemas:
    changes.append(f"Added schemas ({len(added_schemas)}): {', '.join(sorted(added_schemas))}")
if removed_schemas:
    breaking.append(f"Removed schemas ({len(removed_schemas)}): {', '.join(sorted(removed_schemas))}")

# --- Required field changes on existing schemas ---
old_schema_defs = old.get("components", {}).get("schemas", {})
new_schema_defs = new.get("components", {}).get("schemas", {})

for name in sorted(old_schemas & new_schemas):
    old_s = old_schema_defs[name]
    new_s = new_schema_defs[name]

    old_required = set(old_s.get("required", []))
    new_required = set(new_s.get("required", []))
    added_required = new_required - old_required
    removed_required = old_required - new_required

    if added_required:
        breaking.append(f"New required fields on {name}: {', '.join(sorted(added_required))}")
    if removed_required:
        changes.append(f"Fields no longer required on {name}: {', '.join(sorted(removed_required))}")

    # Check for removed properties
    old_props = set(old_s.get("properties", {}).keys())
    new_props = set(new_s.get("properties", {}).keys())
    removed_props = old_props - new_props
    added_props = new_props - old_props

    if removed_props:
        breaking.append(f"Removed properties on {name}: {', '.join(sorted(removed_props))}")
    if added_props:
        changes.append(f"Added properties on {name}: {', '.join(sorted(added_props))}")

# --- Output ---
if not changes and not breaking:
    print("No API changes detected.")
    sys.exit(0)

if breaking:
    print("BREAKING API CHANGES:")
    print()
    for line in breaking:
        print(f"  {line}")
    print()

if changes:
    print("Non-breaking changes:")
    print()
    for line in changes:
        print(f"  {line}")
    print()

# Summary
print(f"Summary: {len(breaking)} breaking, {len(changes)} non-breaking changes")

if breaking:
    print()
    print("ACTION REQUIRED: Update hm-module.nix and coolerctl/ for breaking changes.")
    sys.exit(1)

sys.exit(0)
PYTHON
