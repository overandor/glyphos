#!/bin/bash
# Deploy HDAR anchor to Cloudflare Pages
#
# Prerequisites:
#   1. Rotate the compromised token in Cloudflare dashboard
#   2. Create a new token with "Pages Write" permission only
#   3. Export credentials:
#      export CLOUDFLARE_API_TOKEN="your_new_token"
#      export CLOUDFLARE_ACCOUNT_ID="your_account_id"
#
# Usage:
#   ./deploy_pages.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo "ERROR: CLOUDFLARE_API_TOKEN not set"
  echo "  export CLOUDFLARE_API_TOKEN=\"your_token\""
  exit 1
fi

if [ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]; then
  echo "ERROR: CLOUDFLARE_ACCOUNT_ID not set"
  echo "  export CLOUDFLARE_ACCOUNT_ID=\"your_account_id\""
  exit 1
fi

PROJECT_NAME="hdar-anchor"

echo "Deploying HDAR anchor to Cloudflare Pages..."
echo "  Project: $PROJECT_NAME"
echo "  Directory: $SCRIPT_DIR"
echo ""

# Deploy using wrangler if available, otherwise use direct API
if command -v npx &>/dev/null; then
  echo "Using wrangler..."
  CLOUDFLARE_API_TOKEN="$CLOUDFLARE_API_TOKEN" \
  CLOUDFLARE_ACCOUNT_ID="$CLOUDFLARE_ACCOUNT_ID" \
  npx wrangler pages deploy . --project-name "$PROJECT_NAME"
else
  echo "wrangler not found, using direct API..."

  # Create project if it doesn't exist
  curl -s -X POST \
    "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/pages/projects" \
    -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$PROJECT_NAME\",\"production_branch\":\"main\"}" || true

  # Deploy via direct upload (requires creating a deployment first)
  # This is a simplified path — wrangler is recommended
  echo "Please install wrangler for reliable deployment: npm install -g wrangler"
  exit 1
fi

echo ""
echo "Deploy complete."
echo "Your anchor is live at: https://$PROJECT_NAME.pages.dev"
echo ""
echo "Next steps:"
echo "  1. Add a custom domain in Cloudflare Pages dashboard (optional)"
echo "  2. Update index.html canonical URL to match your Pages domain"
echo "  3. Set up named tunnel: cloudflared tunnel create hdar"
echo "  4. Start named tunnel: python3 ../tunnel_rotator.py start --provider cloudflare-named --tunnel-name hdar --hostname your.domain.com"
