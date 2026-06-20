# Rule 30 — HF Space Deployment

> **Law. Spaces must be verified live before claims of deployment.**

## Deployment Rules

1. Every HF Space deployment must produce a live URL.
2. The URL must return HTTP 200 within 60 seconds of deployment.
3. Space status must be "Running" not "Building" or "Error".
4. Deployment logs are artifacts and must be saved.

## Verification Protocol

1. `curl -s -o /dev/null -w "%{http_code}" <space_url>` returns 200.
2. `huggingface_hub` API confirms space status.
3. Screenshot of the live Space is captured as artifact.
4. All three checks must pass. Any failure = deployment not verified.

## Secrets

1. HF tokens are read from environment variables only. Never hardcoded.
2. Tokens are never logged, never included in receipts.
3. Token validation: check if `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN` is set before deployment.

## Enforcement

- `/verify-space` command runs the full verification protocol.
- Result is logged with artifact paths.
- No "deployed successfully" claim without all 3 checks passing.
