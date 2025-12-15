import asyncio
import aiohttp
from Logging_Mechanism.logger import info, warning, error
from .transaction_analyzer import TransactionAnalyzer


class TransactionWorker:
    """
    Independent background worker for Bitcoin transaction analysis.

    - Scans BitcoinAddresses table
    - Fetches blockchain tx history
    - Stores Transactions
    - Flags mixers
    """

    def __init__(self, pool, batch_size: int = 10, sleep_interval: int = 30):
        self.pool = pool
        self.batch_size = batch_size
        self.sleep_interval = sleep_interval

    async def run(self):
        info("🔗 TransactionWorker started")

        while True:
            try:
                processed = await self.process_wallets()
                if processed == 0:
                    await asyncio.sleep(self.sleep_interval)
            except Exception as e:
                error(f"TransactionWorker fatal error: {e}")
                await asyncio.sleep(self.sleep_interval)

    # -------------------------------------------------
    async def process_wallets(self) -> int:
        """
        Fetch wallets that have not yet been transaction-analyzed.
        """

        async with self.pool.acquire() as conn:
            wallets = await conn.fetch(
                """
                SELECT address_id, address
                FROM BitcoinAddresses
                WHERE valid = TRUE
                  AND tx_analyzed = FALSE
                LIMIT $1;
                """,
                self.batch_size
            )

        if not wallets:
            info("🔗 No pending wallets for transaction analysis")
            return 0

        async with aiohttp.ClientSession() as session:
            analyzer = TransactionAnalyzer(session)

            for w in wallets:
                try:
                    await self._analyze_wallet(analyzer, w)
                except Exception as e:
                    error(f"Wallet analysis failed [{w['address']}]: {e}")

        info(f"🔗 Processed {len(wallets)} wallets")
        return len(wallets)

    # -------------------------------------------------
    async def _analyze_wallet(self, analyzer, wallet):
        address_id = wallet["address_id"]
        address = wallet["address"]

        info(f"🔍 Analyzing wallet: {address}")

        raw_txs = await analyzer.fetch_transactions(address)

        if not raw_txs:
            warning(f"No transactions found for {address}")
            await self._mark_analyzed(address_id)
            return

        tx_rows = analyzer.analyze_transactions(
            raw_txs,
            address_id,
            address
        )

        if not tx_rows:
            warning(f"No relevant tx rows extracted for {address}")
            await self._mark_analyzed(address_id)
            return

        async with self.pool.acquire() as conn:
            for tx in tx_rows:
                await conn.execute(
                    """
                    INSERT INTO Transactions
                    (tx_id, address_id, direction, amount, timestamp, fan_in, fan_out, is_mixer)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (tx_id) DO NOTHING;
                    """,
                    tx["tx_id"],
                    tx["address_id"],
                    tx["direction"],
                    tx["amount"],
                    tx["timestamp"],
                    tx["fan_in"],
                    tx["fan_out"],
                    tx["is_mixer"]
                )

        await self._mark_analyzed(address_id)
        info(f"✅ Wallet fully analyzed: {address}")

    # -------------------------------------------------
    async def _mark_analyzed(self, address_id: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE BitcoinAddresses
                SET tx_analyzed = TRUE
                WHERE address_id = $1;
                """,
                address_id
            )
