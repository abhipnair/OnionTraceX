from Logging_Mechanism.logger import info


class PGPMerger:

    def __init__(self, pool):
        self.pool = pool

    async def run(self):
        info("🔁 PGP Vendor Merger started")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT artifact_value AS pgp,
                       array_agg(DISTINCT vendor_id) AS vendors
                FROM VendorArtifacts
                WHERE artifact_type = 'pgp'
                GROUP BY artifact_value
                HAVING COUNT(DISTINCT vendor_id) > 1;
                """
            )

        async with self.pool.acquire() as conn:
            for row in rows:
                vendors = sorted(row["vendors"])
                canonical = vendors[0]
                to_merge = vendors[1:]

                await conn.execute(
                    """
                    UPDATE VendorArtifacts
                    SET vendor_id = $1
                    WHERE vendor_id = ANY($2);
                    """,
                    canonical,
                    to_merge
                )

                info(
                    f"🔁 Vendors merged via PGP {row['pgp']} → {canonical}"
                )
