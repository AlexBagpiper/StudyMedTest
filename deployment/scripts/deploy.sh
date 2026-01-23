#!/bin/bash

# StudyMedTest Deployment Script for Linux Server

# Exit on error
set -e

echo "🚀 Starting deployment of StudyMedTest..."

# 1. Check for .env file
if [ ! -f .env ]; then
    if [ -f env.example ]; then
        echo "⚠️  .env file not found. Creating from env.example..."
        cp env.example .env
        echo "‼️  Please edit the .env file with your secrets and run this script again."
        exit 1
    else
        echo "❌ Error: .env or env.example not found!"
        exit 1
    fi
fi

# 2. Pull latest changes if it's a git repo
if [ -d "../.git" ]; then
    echo "📥 Pulling latest changes..."
    git -C .. pull
fi

# 3. Cleanup unwanted files (like IDE configs)
echo "🧹 Cleaning up deployment environment..."
rm -rf ../.cursor
rm -rf ../.vscode
rm -rf ../.idea

# 4. Build and start containers
echo "🏗️  Building and starting containers..."
docker compose pull
docker compose up -d --build

# 4. Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 5

# 5. Run migrations and create admin (handled by docker-compose command, but we double check)
# docker compose exec backend alembic upgrade head
# docker compose exec backend python create_admin.py

echo "✅ Deployment successful!"
echo "------------------------------------------------"
echo "API: http://$(hostname -I | awk '{print $1}')/api/docs"
echo "Frontend: http://$(hostname -I | awk '{print $1}')/"
echo "------------------------------------------------"
echo "Logs: docker compose logs -f"
