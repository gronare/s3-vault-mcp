#!/usr/bin/env bash
set -euo pipefail

IMAGE="${S3_VAULT_IMAGE:-ghcr.io/OWNER/s3-vault-mcp:latest}"

# ——————————————————————————————
# Prereq checks
# ——————————————————————————————

if ! command -v docker &>/dev/null; then
  echo "Error: docker is not installed."
  echo "Install it from https://docs.docker.com/get-docker/ and try again."
  exit 1
fi

if ! command -v claude &>/dev/null; then
  echo "Error: claude CLI is not installed."
  echo "Install it from https://claude.ai/download and try again."
  exit 1
fi

# ——————————————————————————————
# Collect credentials
# ——————————————————————————————

echo ""
echo "S3 Vault MCP — Setup"
echo "────────────────────"
echo "Connects Claude to your S3-compatible markdown vault."
echo ""

read -rp "S3 endpoint URL (e.g. https://minio.example.com): " S3_ENDPOINT
read -rp "S3 access key: " S3_ACCESS_KEY
read -rsp "S3 secret key: " S3_SECRET_KEY
echo ""
read -rp "S3 bucket name [obsidian]: " S3_BUCKET
S3_BUCKET="${S3_BUCKET:-obsidian}"
read -rp "Frontmatter fields to search (comma-separated) [title,tags,path]: " S3_SEARCH_FIELDS
S3_SEARCH_FIELDS="${S3_SEARCH_FIELDS:-title,tags,path}"

# ——————————————————————————————
# Pull image
# ——————————————————————————————

echo ""
echo "Pulling image: $IMAGE"
docker pull "$IMAGE"

# ——————————————————————————————
# Register MCP
# ——————————————————————————————

echo ""
echo "Registering vault MCP with Claude..."

claude mcp add \
  -s user \
  -e S3_ENDPOINT="$S3_ENDPOINT" \
  -e S3_ACCESS_KEY="$S3_ACCESS_KEY" \
  -e S3_SECRET_KEY="$S3_SECRET_KEY" \
  -e S3_BUCKET="$S3_BUCKET" \
  -e S3_SEARCH_FIELDS="$S3_SEARCH_FIELDS" \
  vault -- docker run -i --rm \
    -e S3_ENDPOINT \
    -e S3_ACCESS_KEY \
    -e S3_SECRET_KEY \
    -e S3_BUCKET \
    -e S3_SEARCH_FIELDS \
    "$IMAGE"

# ——————————————————————————————
# Confirm
# ——————————————————————————————

echo ""
echo "Done. Verify with:"
echo ""
claude mcp get vault
echo ""
echo "Restart Claude Code and check /mcp to confirm the vault server is connected."
