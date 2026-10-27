#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# ChessCode Setup — run once on a fresh Ubuntu/Debian server
# Usage: bash setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "\n${GREEN}♟  ChessCode Automated Channel Setup${NC}\n"

# ── System dependencies ───────────────────────────────────────────────────────
echo "Installing system packages..."
sudo apt-get update -q
sudo apt-get install -y \
    stockfish \
    ffmpeg \
    libcairo2 libcairo2-dev \
    python3-pip python3-venv \
    wget curl git

# ── Python environment ────────────────────────────────────────────────────────
echo "Setting up Python virtualenv..."
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip -q
pip install -r requirements.txt -q

echo -e "  ${GREEN}✓ Python packages installed${NC}"

# ── Assets: Hindi font ────────────────────────────────────────────────────────
echo "Downloading Hindi font (Noto Sans Devanagari)..."
mkdir -p assets/fonts
FONT_BASE="https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari"
wget -q "$FONT_BASE/NotoSansDevanagari-Regular.ttf" -O assets/fonts/NotoSansDevanagari-Regular.ttf
wget -q "$FONT_BASE/NotoSansDevanagari-Bold.ttf"    -O assets/fonts/NotoSansDevanagari-Bold.ttf
echo -e "  ${GREEN}✓ Hindi fonts downloaded${NC}"

# ── Environment file ──────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "  ${YELLOW}⚠  Created .env — open it and fill in your API keys${NC}"
    echo -e "  ${YELLOW}   Required: ANTHROPIC_API_KEY, LICHESS_TOKEN${NC}"
    echo -e "  ${YELLOW}   Optional: LEONARDO_API_KEY, ELEVENLABS_API_KEY${NC}"
else
    echo -e "  ${GREEN}✓ .env already exists${NC}"
fi

# ── Output directories ────────────────────────────────────────────────────────
mkdir -p output/pgn_cache output/openings output/traps

# ── YouTube OAuth (first-time only) ──────────────────────────────────────────
echo ""
echo -e "${YELLOW}YouTube upload setup:${NC}"
echo "  1. Go to https://console.cloud.google.com"
echo "  2. Create a project → Enable 'YouTube Data API v3'"
echo "  3. Create OAuth2 credentials (Desktop App) → Download as client_secret.json"
echo "  4. Place client_secret.json in this directory"
echo "  5. Run: python youtube_uploader.py  (opens browser once for auth)"

# ── System test ───────────────────────────────────────────────────────────────
echo ""
echo "Running system test..."
python main.py --test

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ChessCode ready! Quick start:${NC}"
echo -e "${GREEN}${NC}"
echo -e "${GREEN}  # Test with a game${NC}"
echo -e "${GREEN}  python main.py --test${NC}"
echo -e "${GREEN}  python main.py game.pgn --hindi${NC}"
echo -e "${GREEN}${NC}"
echo -e "${GREEN}  # Opening theory video${NC}"
echo -e "${GREEN}  python main.py --opening 'London System' --hindi${NC}"
echo -e "${GREEN}${NC}"
echo -e "${GREEN}  # Start autonomous 24/7 runner${NC}"
echo -e "${GREEN}  python autonomous_runner.py --dry-run  # test first${NC}"
echo -e "${GREEN}  python autonomous_runner.py            # go live${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
