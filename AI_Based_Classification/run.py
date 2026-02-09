import asyncio
import asyncpg

from Logging_Mechanism.logger import info, error
from AI_Based_Classification.site_classifier import SiteClassifier


DB_CONFIG = {
    "user": "onion_user",
    "password": "112233",
    "database": "oniontracex_db",
    "host": "127.0.0.1",
    "min_size": 1,
    "max_size": 5
}


async def main():
    info("🚀 Starting OnionTraceX — AI-Based Classification Phase")

    try:
        pool = await asyncpg.create_pool(**DB_CONFIG)
        info("✅ DB pool ready")
    except Exception as e:
        error(f"❌ DB pool failed: {e}")
        return

    try:
        await SiteClassifier(pool).run()
        info("✅ AI-Based Classification completed successfully")

    except Exception as e:
        error(f"❌ Classification phase error: {e}")

    finally:
        await pool.close()
        info("🔌 DB pool closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        info("🛑 Classification stopped by user")
