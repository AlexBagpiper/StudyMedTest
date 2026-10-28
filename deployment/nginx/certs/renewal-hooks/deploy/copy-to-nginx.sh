#!/bin/sh
# Copy renewed certs to nginx flat paths and reload (nginx reads fullchain.pem, not live/).
set -eu
DEPLOY_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
cp "$RENEWED_LINEAGE/fullchain.pem" "$DEPLOY_DIR/nginx/certs/fullchain.pem"
cp "$RENEWED_LINEAGE/privkey.pem" "$DEPLOY_DIR/nginx/certs/privkey.pem"
chmod 644 "$DEPLOY_DIR/nginx/certs/fullchain.pem"
chmod 600 "$DEPLOY_DIR/nginx/certs/privkey.pem"
cd "$DEPLOY_DIR"
docker compose restart nginx
