#!/bin/bash

# Creates self-signed certificate for initial setup
# Run this before first docker-compose up if you don't have real certificates yet

set -e

CERTS_DIR="../nginx/certs"

echo "🔐 Creating dummy SSL certificates..."

# Create certs directory
mkdir -p "$CERTS_DIR"

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$CERTS_DIR/privkey.pem" \
    -out "$CERTS_DIR/fullchain.pem" \
    -subj "/C=RU/ST=Moscow/L=Moscow/O=MedTest/CN=localhost" \
    2>/dev/null

chmod 644 "$CERTS_DIR/fullchain.pem"
chmod 600 "$CERTS_DIR/privkey.pem"

echo "✅ Dummy certificates created in $CERTS_DIR"
echo ""
echo "⚠️  WARNING: These are self-signed certificates for testing only!"
echo "   Browsers will show security warnings."
echo ""
echo "For production, run: ./init_ssl.sh your-domain.com your-email@example.com"
