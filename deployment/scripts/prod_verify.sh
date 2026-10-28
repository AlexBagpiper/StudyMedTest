#!/bin/bash
# Post-deploy verification on production (run on VPS as medtest).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV="$ROOT/deployment/.env"
DOM=$(grep -m1 '^DOMAIN_NAME=' "$ENV" | cut -d= -f2-)
ADM=$(grep -m1 '^FIRST_ADMIN_EMAIL=' "$ENV" | cut -d= -f2-)
APW=$(grep -m1 '^FIRST_ADMIN_PASSWORD=' "$ENV" | cut -d= -f2-)
RES=$(curl -skS --resolve "${DOM}:443:127.0.0.1" -X POST "https://${DOM}/api/v1/auth/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "username=$ADM" --data-urlencode "password=$APW")
TOK=$(printf '%s' "$RES" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')
if [[ -z "$TOK" ]]; then
  echo "admin login failed"
  exit 1
fi
echo "admin login ok"
NEW="smoke_admin_$(date +%s)@med-testing.ru"
CODE=$(curl -skS --resolve "${DOM}:443:127.0.0.1" -o /tmp/create_user.json -w '%{http_code}' \
  -X POST "https://${DOM}/api/v1/admin/users" \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$NEW\",\"password\":\"Smoke123!\",\"last_name\":\"Smoke\",\"first_name\":\"Test\",\"role\":\"teacher\",\"is_active\":true,\"is_verified\":true}")
echo "create_user http=$CODE"
[[ "$CODE" == "201" ]] || exit 1
USER_ID=$(python3 -c 'import json; print(json.load(open("/tmp/create_user.json"))["id"])')
DEL=$(curl -skS --resolve "${DOM}:443:127.0.0.1" -o /dev/null -w '%{http_code}' \
  -X DELETE "https://${DOM}/api/v1/admin/users/$USER_ID" -H "Authorization: Bearer $TOK")
echo "delete_user http=$DEL"
cd "$ROOT/deployment"
docker compose exec -T backend python -c \
  'from app.services.email import templates; from app.services.email.smtp_backend import send_blocking; print(send_blocking("x@example.com", templates.render_verification_email("123456")))'
docker exec medtest-mail /bin/mox config test
echo "prod_verify ok"
