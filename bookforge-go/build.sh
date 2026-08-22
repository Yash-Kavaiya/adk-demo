#!/bin/bash
# BookForge Go - Cross-platform Build Script
# Builds binaries for multiple platforms

set -e

echo "Building BookForge Go for multiple platforms..."

# Create output directory
mkdir -p dist

# Version info
VERSION=${VERSION:-"0.1.0"}
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "dev")
BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

LDFLAGS="-s -w -X main.Version=${VERSION} -X main.Commit=${COMMIT} -X main.BuildTime=${BUILD_TIME}"

# Build for different platforms
echo ""
echo "Building Linux AMD64..."
GOOS=linux GOARCH=amd64 go build -ldflags="${LDFLAGS}" -o dist/bookforge-linux-amd64 agent.go

echo "Building Linux ARM64..."
GOOS=linux GOARCH=arm64 go build -ldflags="${LDFLAGS}" -o dist/bookforge-linux-arm64 agent.go

echo "Building macOS AMD64 (Intel)..."
GOOS=darwin GOARCH=amd64 go build -ldflags="${LDFLAGS}" -o dist/bookforge-darwin-amd64 agent.go

echo "Building macOS ARM64 (Apple Silicon)..."
GOOS=darwin GOARCH=arm64 go build -ldflags="${LDFLAGS}" -o dist/bookforge-darwin-arm64 agent.go

echo "Building Windows AMD64..."
GOOS=windows GOARCH=amd64 go build -ldflags="${LDFLAGS}" -o dist/bookforge-windows-amd64.exe agent.go

echo ""
echo "Build complete! Binaries in dist/ directory:"
ls -lh dist/

echo ""
echo "To run a binary:"
echo "  ./dist/bookforge-linux-amd64"
echo "  ./dist/bookforge-darwin-arm64"
echo "  ./dist/bookforge-windows-amd64.exe"
