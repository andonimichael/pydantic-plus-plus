#!/usr/bin/env bash
set -euo pipefail

SCOPE="${1:?Usage: release.sh <patch|minor|major>}"

if [[ "$SCOPE" != "patch" && "$SCOPE" != "minor" && "$SCOPE" != "major" ]]; then
  echo "Error: scope must be patch, minor, or major" >&2
  exit 1
fi

PYPROJECT="pyproject.toml"
CURRENT=$(grep -E '^version = "' "$PYPROJECT" | head -1 | sed 's/version = "\(.*\)"/\1/')

if [[ -z "$CURRENT" ]]; then
  echo "Error: could not read version from $PYPROJECT" >&2
  exit 1
fi

IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

case "$SCOPE" in
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  patch) PATCH=$((PATCH + 1)) ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"

sed -i'' -e "s/^version = \"${CURRENT}\"/version = \"${NEW_VERSION}\"/" "$PYPROJECT"
uv lock

echo "Bumped version: ${CURRENT} -> ${NEW_VERSION}"

# Set outputs for GitHub Actions
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "old_version=${CURRENT}" >> "$GITHUB_OUTPUT"
  echo "new_version=${NEW_VERSION}" >> "$GITHUB_OUTPUT"
fi
