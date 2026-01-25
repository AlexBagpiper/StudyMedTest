#!/bin/bash

# Script to initialize SSL certificates using Let's Encrypt
# Usage: ./init_ssl.sh your-domain.com your-email@example.com

set -e

DOMAIN=$1
EMAIL=$2

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "Usage: $0 <domain> <email>"
    echo "Example: $0 medtest.example.com admin@example.com"
    exit 1
fi

echo "🔒 Initializing SSL for domain: $DOMAIN"

# 1. Create directories
mkdir -p ../nginx/certs
mkdir -p ../certbot/www

# 2. Create temporary nginx config without SSL
cat > ../nginx/nginx.conf.temp << 'EOF'
events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        server_name _;

        # Let's Encrypt challenge
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 200 "SSL setup in progress...";
            add_header Content-Type text/plain;
        }
    }
}
EOF

# 3. Backup original nginx config
cp ../nginx/nginx.conf ../nginx/nginx.conf.backup

# 4. Use temporary config
cp ../nginx/nginx.conf.temp ../nginx/nginx.conf

# 5. Update docker-compose to add certbot volume
echo "📝 Updating docker-compose.yml..."

# 6. Start nginx temporarily
cd ..
docker compose up -d nginx

echo "⏳ Waiting for nginx to start..."
sleep 5

# 7. Run certbot to get certificates
echo "📜 Requesting SSL certificate from Let's Encrypt..."
docker run -it --rm \
    -v "$(pwd)/nginx/certs:/etc/letsencrypt" \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    --network deployment_medtest-network \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN

# 8. Copy certificates to nginx certs directory
echo "📋 Setting up certificates..."
cp nginx/certs/live/$DOMAIN/fullchain.pem nginx/certs/fullchain.pem
cp nginx/certs/live/$DOMAIN/privkey.pem nginx/certs/privkey.pem

# 9. Restore original nginx config
cp nginx/nginx.conf.backup nginx/nginx.conf
rm nginx/nginx.conf.temp nginx/nginx.conf.backup

# 10. Update server_name in nginx.conf
sed -i "s/server_name _;/server_name $DOMAIN;/g" nginx/nginx.conf

# 11. Restart nginx with SSL
echo "🔄 Restarting nginx with SSL..."
docker compose up -d nginx

echo "✅ SSL setup complete!"
echo "Your site should now be available at: https://$DOMAIN"
echo ""
echo "To renew certificates (every 90 days), run:"
echo "docker run --rm -v $(pwd)/nginx/certs:/etc/letsencrypt certbot/certbot renew"
