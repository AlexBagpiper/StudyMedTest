#!/bin/bash

# StudyMedTest Deployment Script for Linux Server
# This script automates the deployment process using Docker Compose.

# Exit on error
set -e

echo "🚀 Starting automated deployment of StudyMedTest..."

# 1. Check for .env file
if [ ! -f .env ]; then
    if [ -f env.example ]; then
        echo "⚠️  .env file not found. Creating from env.example..."
        cp env.example .env
        echo "‼️  Please edit the .env file with your DOMAIN_NAME and secrets, then run this script again."
        exit 1
    else
        echo "❌ Error: .env or env.example not found!"
        exit 1
    fi
fi

# 2. Pull latest changes if it's a git repo
if [ -d "../.git" ]; then
    echo "📥 Pulling latest changes from repository..."
    git -C .. pull
fi

# 3. Build and start containers
echo "🏗️  Building and starting containers in automated mode..."
# Note: Migrations, admin creation and SSL are now handled automatically by containers
docker compose up -d --build

echo "✅ Deployment initiated successfully!"
echo "------------------------------------------------"
echo "The system is now performing automatic setup:"
echo "1. Requesting SSL certificates via Certbot"
echo "2. Waiting for Database readiness"
echo "3. Running migrations and creating admin user"
echo "------------------------------------------------"
echo "Monitoring progress: docker compose logs -f backend"
echo "Check SSL status: docker compose logs -f nginx"
echo "------------------------------------------------"
