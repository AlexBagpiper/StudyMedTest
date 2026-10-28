#!/bin/bash
# Patch live mox config: refuse reserved-domain deliveries (null MX DSNs).
# Run on the production host. sconf requires tabs.
set -euo pipefail

if docker exec medtest-mail grep -q 'example_null_mx:' /data/config/mox.conf; then
  echo "mox.conf already has example_null_mx"
else
  docker exec -i -u root medtest-mail sh -c 'cat >> /data/config/mox.conf' <<'EOF'

# Refuse RFC 2606 example.* so smoke/locust cannot queue DSNs (null MX).
Transports:
	example_null_mx:
		Fail:
			SMTPCode: 550
			SMTPMessage: reserved example domain, null MX
EOF
  echo "appended Transports to mox.conf"
fi

if docker exec medtest-mail grep -q 'example_null_mx' /data/config/domains.conf; then
  echo "domains.conf already routes example_null_mx"
else
  docker exec -i -u root medtest-mail sh -c 'cat >> /data/config/domains.conf' <<'EOF'

Routes:
	-
		ToDomain:
			- example.com
			- example.net
			- example.org
			- example.edu
		Transport: example_null_mx
EOF
  echo "appended Routes to domains.conf"
fi

if docker exec medtest-mail /bin/mox config test; then
  docker exec medtest-mail /bin/mox reload 2>/dev/null || docker restart medtest-mail
else
  echo "mox config test failed"
  exit 1
fi
echo "mox delivery patch applied"
