from datetime import datetime, timezone
from Logging_Mechanism.logger import info
from .utils import sha256_hex, generate_vendor_name


class BTCVendorCreator:

    def __init__(self, pool):
        self.pool = pool

    async def run(self):
        info("₿ BTC Vendor Creator started")

        async with self.pool.acquire() as conn:
            btc_rows = await conn.fetch(
                """
                SELECT DISTINCT address, site_id, page_id
                FROM BitcoinAddresses;
                """
            )

        now = datetime.now(timezone.utc)

        async with self.pool.acquire() as conn:
            for row in btc_rows:
                vendor_id = sha256_hex(row["address"])
                vendor_name = generate_vendor_name()

                # Create vendor
                await conn.execute(
                    """
                    INSERT INTO Vendors (vendor_id, vendor_name, first_seen, last_seen)
                    VALUES ($1, $2, $3, $3)
                    ON CONFLICT (vendor_id) DO NOTHING;
                    """,
                    vendor_id,
                    vendor_name,
                    now
                )

                # Insert BTC artifact
                await conn.execute(
                    """
                    INSERT INTO VendorArtifacts
                    (
                        artifact_id,
                        vendor_id,
                        artifact_type,
                        artifact_value,
                        artifact_hash,
                        confidence,
                        site_id,
                        page_id,
                        first_seen,
                        last_seen
                    )
                    VALUES ($1, $2, 'btc', $3, $4, 90, $5, $6, $7, $7)
                    ON CONFLICT DO NOTHING;
                    """,
                    sha256_hex(f"btc:{row['address']}:{row['page_id']}"),   # artifact_id
                    vendor_id,
                    row["address"],
                    sha256_hex(f"btc:{row['address']}"),                   # ✅ artifact_hash
                    row["site_id"],
                    row["page_id"],
                    now
                )


        info(f"₿ BTC vendors processed: {len(btc_rows)}")
