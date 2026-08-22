#!/bin/bash
# BookForge Go Environment Variables
# Load environment variables from .env file
# Usage: source load-env.sh

if [ ! -f .env ]; then
    echo "Error: .env file not found"
    echo "Please copy .env.example to .env and configure it"
    return 1 2>/dev/null || exit 1
fi

# Load environment variables
set -a
source .env
set +a

echo "Environment variables loaded successfully"
echo ""
echo "To run the agent:"
echo "  go run agent.go"
echo ""
echo "To run web interface:"
echo "  go run agent.go web api webui"
