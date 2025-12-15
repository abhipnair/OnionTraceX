import asyncio
import asyncpg

from Logging_Mechanism.logger import info, error
from .analyser import PageAnalyzer
from .transaction_worker import TransactionWorker


DB_CONFIG = {
    "user": "onion_user",
    "password": "112233",
    "database": "oniontracex_db",
    "host": "127.0.0.1",
    "min_size": 1,
    "max_size": 5
}


async def main():
    info("🚀 Initializing OnionTraceX Analysis Workers")

    try:
        pool = await asyncpg.create_pool(**DB_CONFIG)
        info("✅ Database connection pool created")
    except Exception as e:
        error(f"❌ Failed to create DB pool: {e}")
        return

    # Initialize workers
    page_analyzer = PageAnalyzer(pool)
    tx_worker = TransactionWorker(pool)

    info("🧠 Starting PageAnalyzer and TransactionWorker")

    # Run both workers concurrently
    await asyncio.gather(
        page_analyzer.run(),
        tx_worker.run()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        info("🛑 Analysis workers stopped by user")
