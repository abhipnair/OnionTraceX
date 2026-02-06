import asyncio
import asyncpg

from Logging_Mechanism.logger import info, error

from Vendor_Analysis.btc_vendor_creator import BTCVendorCreator
from Vendor_Analysis.page_metadata_attacher import PageMetadataAttacher
from Vendor_Analysis.pgp_vendor_merger import PGPMerger
from Vendor_Analysis.vendor_risk_scorer import VendorRiskScorer


DB_CONFIG = {
    "user": "onion_user",
    "password": "112233",
    "database": "oniontracex_db",
    "host": "127.0.0.1",
    "min_size": 1,
    "max_size": 5
}


async def main():
    info("🚀 Starting OnionTraceX Phase-3 Vendor Intelligence")

    try:
        pool = await asyncpg.create_pool(**DB_CONFIG)
        info("✅ DB pool ready")
    except Exception as e:
        error(f"❌ DB pool failed: {e}")
        return

    try:
        info("🟢 STEP 1 — BTC Vendor Creation")
        await BTCVendorCreator(pool).run()

        info("🟢 STEP 2 — Metadata Attachment")
        await PageMetadataAttacher(pool).run()

        info("🟠 STEP 3 — PGP Vendor Merge")
        await PGPMerger(pool).run()

        info("✅ Phase-3 completed successfully")

        info("🔥 STEP 4 — Vendor Risk Scoring")
        await VendorRiskScorer(pool).run()


    except Exception as e:
        error(f"❌ Phase-3 error: {e}")

    finally:
        await pool.close()
        info("🔌 DB pool closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        info("🛑 Phase-3 stopped by user")
