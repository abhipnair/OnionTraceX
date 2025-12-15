import hashlib
import aiohttp
from datetime import datetime, timezone
from typing import List, Dict

from Logging_Mechanism import logger

BLOCKSTREAM_API = "https://blockstream.info/api"

class TransactionAnalyzer:
    """
    Pulls Bitcoin transaction history for a wallet,
    extracts fan-in / fan-out metrics,
    and flags mixer-like behavior.
    """

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    # -------------------------------------------------
    async def fetch_transactions(self, address: str):
        url = f"{BLOCKSTREAM_API}/address/{address}/txs"
        try:
            async with self.session.get(url, timeout=20) as resp:
                if resp.status != 200:
                    logger.warning(f"TX fetch failed [{address}] status={resp.status}")
                    return []

                data = await resp.json()
                logger.info(f"Fetched {len(data)} txs for {address}")
                return data

        except Exception as e:
            logger.error(f"TX fetch error [{address}]: {e}")
            return []


    # -------------------------------------------------
    def analyze_transactions(
        self,
        txs: List[Dict],
        address_id: str,
        address: str
    ) -> List[Dict]:

        results = []

        for tx in txs:
            tx_id = tx["txid"]
            fan_in = len(tx.get("vin", []))
            fan_out = len(tx.get("vout", []))

            is_mixer = self.is_suspected_mixer(fan_in, fan_out)

            timestamp = (
                datetime.fromtimestamp(tx["status"]["block_time"], tz=timezone.utc)
                if tx.get("status", {}).get("block_time")
                else None
            )

            for vout in tx.get("vout", []):
                if address == vout.get("scriptpubkey_address"):
                    results.append({
                        "tx_id": tx_id,
                        "address_id": address_id,
                        "direction": "Inbound",
                        "amount": vout["value"] / 1e8,
                        "timestamp": timestamp,
                        "fan_in": fan_in,
                        "fan_out": fan_out,
                        "is_mixer": is_mixer
                    })
        logger.info(results)
        return results

    # -------------------------------------------------
    @staticmethod
    def is_suspected_mixer(fan_in: int, fan_out: int) -> bool:
        """
        Simple but effective mixer heuristic.
        """
        return fan_in >= 10 and fan_out >= 10
