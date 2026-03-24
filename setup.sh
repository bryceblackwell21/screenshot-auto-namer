#!/bin/bash
# Screenshot Auto-Namer — One-command setup
# Usage: bash setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "📸 Screenshot Auto-Namer — Setup"
echo "================================"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install it from https://python.org or via:"
    echo "   brew install python3"
    exit 1
fi

echo "✓ Found Python: $(python3 --version)"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "→ Creating virtual environment..."
    python3 -m venv .venv
else
    echo "✓ Virtual environment already exists"
fi

# Activate and install
echo "→ Installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "✓ Dependencies installed"

# Set up .env if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        echo ""
        echo "⚠️  No ANTHROPIC_API_KEY found."
        read -p "Paste your Anthropic API key (or press Enter to skip): " api_key
        if [ -n "$api_key" ]; then
            echo "ANTHROPIC_API_KEY=$api_key" > .env
            echo "✓ API key saved to .env"
        else
            cp .env.example .env
            echo "→ Skipped. Edit .env later with your key."
        fi
    else
        echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" > .env
        echo "✓ API key captured from environment"
    fi
else
    echo "✓ .env file exists"
fi

# Create output directory
mkdir -p "$HOME/Screenshots"
echo "✓ Output directory ready: ~/Screenshots/"

echo ""
echo "================================"
echo "✅ Setup complete! Usage:"
echo ""
echo "   source .venv/bin/activate"
echo "   python main.py --dry-run        # preview changes"
echo "   python main.py                  # process Desktop screenshots"
echo "   python main.py --file <path>    # process one file"
echo ""
