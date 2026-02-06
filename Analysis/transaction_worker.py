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
    - Stores REAL transaction edges
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

        # ---------------- SUMMARY TRANSACTIONS ----------------
        tx_rows = analyzer.analyze_transactions(
            raw_txs,
            address_id,
            address
        )

        # ---------------- REAL FLOW EDGES ----------------
        all_edges = []
        for tx in raw_txs:
            edges = analyzer.extract_edges(tx)
            all_edges.extend(edges)

        if not tx_rows and not all_edges:
            warning(f"No usable tx data extracted for {address}")
            await self._mark_analyzed(address_id)
            return

        async with self.pool.acquire() as conn:

            # ----------- TRANSACTIONS (SUMMARY) -----------
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

            # ----------- REAL TRANSACTION EDGES -----------
            for e in all_edges:
                await conn.execute(
                    """
                    INSERT INTO BitcoinTransactionEdges
                    (tx_id, from_address, to_address, amount, timestamp)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT DO NOTHING;
                    """,
                    e["tx_id"],
                    e["from_address"],
                    e["to_address"],
                    e["amount"],
                    e["timestamp"]
                )

        info(f"🔗 Stored {len(all_edges)} real edges for {address}")

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
