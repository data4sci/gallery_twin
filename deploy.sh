#!/bin/bash

set -e

echo "🚀 Starting Gallery Twin deployment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Install Docker: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose is not available"
    echo "Install Docker Compose plugin: sudo apt install docker-compose-plugin"
    exit 1
fi

# Create db directory if it doesn't exist
if [ ! -d "db" ]; then
    echo "📁 Creating db directory..."
    mkdir -p db
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Creating .env from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "⚠️  IMPORTANT: Edit .env file and set SECRET_KEY and ADMIN_PASSWORD!"
    else
        echo "❌ Error: .env.example not found"
        exit 1
    fi
fi

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker compose down

# Pull latest changes (if in git repo)
if [ -d ".git" ]; then
    echo "📥 Pulling latest changes..."
    git pull || echo "⚠️  Warning: Could not pull latest changes"
fi

# Build and start containers
echo "🔨 Building and starting containers..."
docker compose up -d --build

# Wait for application to be ready
echo "⏳ Waiting for application to start..."
sleep 5

# Check if application is running
if docker compose ps | grep -q "Up"; then
    echo "✅ Deployment successful!"
    echo ""
    echo "Application is running at http://localhost:8000"
    echo "Admin panel: http://localhost:8000/admin"
    echo ""
    echo "Useful commands:"
    echo "  docker compose logs -f    # View logs"
    echo "  docker compose restart    # Restart application"
    echo "  docker compose down       # Stop application"
else
    echo "❌ Error: Containers failed to start"
    echo "Check logs with: docker compose logs"
    exit 1
fi
