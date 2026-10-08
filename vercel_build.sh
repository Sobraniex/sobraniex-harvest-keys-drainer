#!/bin/bash
set -e

cd ~/harvest_keys

# Install Python dependencies for Vercel
pip install -q -r requirements.txt

# Copy env vars if present
if [ -f .env ]; then
    cp .env .env.local
else
    cp .env.example .env.local
fi

# Build output
echo "Build complete. Ready for deployment."
