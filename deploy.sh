#!/bin/bash

set -e

echo "🚀 Starting Gallery Twin deployment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Install Docker: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Configuration
CONTAINER_NAME="gallery-twin-app"
IMAGE_NAME="gallery-twin"

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

# Pull latest changes (if in git repo)
if [ -d ".git" ]; then
    echo "📥 Pulling latest changes..."
    git pull || echo "⚠️  Warning: Could not pull latest changes"
fi

# Stop and remove existing container
echo "🛑 Stopping existing container..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t "$IMAGE_NAME" .

# Start container
echo "🚀 Starting container..."
docker run -d \
    -p 8000:8000 \
    -v "$(pwd)/db:/app/db" \
    --env-file .env \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    "$IMAGE_NAME"

# Wait for application to start
echo "⏳ Waiting for application to start..."
sleep 5

# Check if container is running
if docker ps | grep -q "$CONTAINER_NAME"; then
    echo "✅ Deployment successful!"
    echo ""
    echo "Application is running at http://localhost:8000"
    echo "Admin panel: http://localhost:8000/admin"
    echo ""
    echo "Useful commands:"
    echo "  docker logs -f $CONTAINER_NAME       # View logs"
    echo "  docker restart $CONTAINER_NAME       # Restart application"
    echo "  docker stop $CONTAINER_NAME          # Stop application"
    echo "  docker start $CONTAINER_NAME         # Start application"
else
    echo "❌ Error: Container failed to start"
    echo "Check logs with: docker logs $CONTAINER_NAME"
    exit 1
fi
