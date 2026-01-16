#!/bin/bash

# VolNetOffice Custom Image Builder
# This script builds all custom Docker images with your UI customizations

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}VolNetOffice Custom Image Builder${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Configuration
DEFAULT_REGISTRY="volnetoffice"
DEFAULT_TAG="latest"
DEFAULT_WEB_URL="https://your-domain.com"

# Check if registry is provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 [REGISTRY] [WEB_URL] [TAG]${NC}"
    echo ""
    echo "Examples:"
    echo "  $0 yourusername https://your-domain.com latest"
    echo "  $0 ghcr.io/yourusername https://app.example.com v1.0.0"
    echo "  $0 your-server.com:5000 https://volnet.example.org latest"
    echo ""
    echo -e "${YELLOW}Using default values:${NC}"
    REGISTRY="$DEFAULT_REGISTRY"
    WEB_URL="$DEFAULT_WEB_URL"
    TAG="$DEFAULT_TAG"
else
    REGISTRY="$1"
    WEB_URL="${2:-$DEFAULT_WEB_URL}"
    TAG="${3:-$DEFAULT_TAG}"
fi

echo -e "Registry: ${GREEN}${REGISTRY}${NC}"
echo -e "Web URL: ${GREEN}${WEB_URL}${NC}"
echo -e "Tag: ${GREEN}${TAG}${NC}"
echo ""

# Confirm before proceeding
read -p "Continue with these settings? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Aborted.${NC}"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -d "apps/web" ]; then
    echo -e "${RED}Error: Must run this script from the volnetoffice root directory${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Starting build process...${NC}"
echo ""

# Build function
build_image() {
    local name=$1
    local dockerfile=$2
    local context=${3:-.}

    echo -e "${BLUE}Building ${name}...${NC}"

    docker build \
        -f "$dockerfile" \
        -t "${REGISTRY}/volnetoffice-${name}:${TAG}" \
        --build-arg VITE_API_BASE_URL="${WEB_URL}" \
        --build-arg VITE_WEB_BASE_URL="${WEB_URL}" \
        --build-arg VITE_ADMIN_BASE_URL="${WEB_URL}" \
        --build-arg VITE_ADMIN_BASE_PATH="/god-mode" \
        --build-arg VITE_SPACE_BASE_URL="${WEB_URL}" \
        --build-arg VITE_SPACE_BASE_PATH="/spaces" \
        --build-arg VITE_LIVE_BASE_URL="${WEB_URL}" \
        --build-arg VITE_LIVE_BASE_PATH="/live" \
        "$context"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ ${name} built successfully${NC}"
        echo ""
    else
        echo -e "${RED}✗ Failed to build ${name}${NC}"
        exit 1
    fi
}

# Build all images
echo -e "${YELLOW}1/6 Building Web Frontend (includes custom theme)...${NC}"
build_image "web" "apps/web/Dockerfile.web"

echo -e "${YELLOW}2/6 Building Space Module...${NC}"
build_image "space" "apps/space/Dockerfile.space"

echo -e "${YELLOW}3/6 Building Admin Interface...${NC}"
build_image "admin" "apps/admin/Dockerfile.admin"

echo -e "${YELLOW}4/6 Building Live Collaboration...${NC}"
build_image "live" "apps/live/Dockerfile.live"

echo -e "${YELLOW}5/6 Building API Backend...${NC}"
build_image "api" "apps/api/Dockerfile.api"

echo -e "${YELLOW}6/6 Building Reverse Proxy...${NC}"
build_image "proxy" "apps/proxy/Dockerfile.ce"

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}All images built successfully!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Show image sizes
echo -e "${BLUE}Image sizes:${NC}"
docker images | grep "volnetoffice" | grep "$TAG"
echo ""

# Ask about pushing
read -p "Push images to registry? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${BLUE}Pushing images to registry...${NC}"
    echo ""

    docker push "${REGISTRY}/volnetoffice-web:${TAG}"
    docker push "${REGISTRY}/volnetoffice-space:${TAG}"
    docker push "${REGISTRY}/volnetoffice-admin:${TAG}"
    docker push "${REGISTRY}/volnetoffice-live:${TAG}"
    docker push "${REGISTRY}/volnetoffice-api:${TAG}"
    docker push "${REGISTRY}/volnetoffice-proxy:${TAG}"

    echo ""
    echo -e "${GREEN}All images pushed successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. SSH into your production server"
    echo "2. Update docker-compose.yml to use ${REGISTRY}/volnetoffice-*:${TAG}"
    echo "3. Run: docker compose pull"
    echo "4. Run: docker compose up -d"
else
    echo ""
    echo -e "${YELLOW}Images built but not pushed.${NC}"
    echo ""
    echo -e "${YELLOW}To push manually:${NC}"
    echo "docker push ${REGISTRY}/volnetoffice-web:${TAG}"
    echo "docker push ${REGISTRY}/volnetoffice-space:${TAG}"
    echo "docker push ${REGISTRY}/volnetoffice-admin:${TAG}"
    echo "docker push ${REGISTRY}/volnetoffice-live:${TAG}"
    echo "docker push ${REGISTRY}/volnetoffice-api:${TAG}"
    echo "docker push ${REGISTRY}/volnetoffice-proxy:${TAG}"
fi

echo ""
echo -e "${GREEN}Done!${NC}"
