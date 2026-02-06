from datetime import datetime
from Logging_Mechanism.logger import info


class VendorRiskScorer:
    """
    Computes deterministic risk scores for vendors
    and stores them in Vendors.risk_score
    """

    def __init__(self, pool):
        self.pool = pool

    async def run(self):
        info("🔥 Vendor Risk Scoring started")

        async with self.pool.acquire() as conn:
            vendors = await conn.fetch(
                "SELECT vendor_id FROM Vendors;"
            )

        async with self.pool.acquire() as conn:
            for v in vendors:
                vendor_id = v["vendor_id"]
                score = await self._calculate_score(conn, vendor_id)

                await conn.execute(
                    """
                    UPDATE Vendors
                    SET risk_score = $1,
                        last_seen = $2
                    WHERE vendor_id = $3;
                    """,
                    score,
                    datetime.utcnow(),
                    vendor_id
                )

        info("✅ Vendor Risk Scoring completed")

    async def _calculate_score(self, conn, vendor_id: str) -> int:
        risk = 0

        # 1️⃣ Multiple BTC addresses
        btc_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM VendorArtifacts
            WHERE vendor_id = $1
              AND artifact_type = 'btc';
            """,
            vendor_id
        )
        if btc_count and btc_count > 1:
            risk += 30

        # 2️⃣ PGP present
        pgp_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM VendorArtifacts
            WHERE vendor_id = $1
              AND artifact_type = 'pgp';
            """,
            vendor_id
        )
        if pgp_count and pgp_count >= 1:
            risk += 20

        # 3️⃣ XMR present
        xmr_present = await conn.fetchval(
            """
            SELECT 1
            FROM VendorArtifacts
            WHERE vendor_id = $1
              AND artifact_type = 'xmr'
            LIMIT 1;
            """,
            vendor_id
        )
        if xmr_present:
            risk += 20

        # 4️⃣ Multiple sites
        site_count = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT site_id)
            FROM VendorArtifacts
            WHERE vendor_id = $1;
            """,
            vendor_id
        )
        if site_count and site_count >= 2:
            risk += 25

        # Cap the score
        return min(risk, 100)
