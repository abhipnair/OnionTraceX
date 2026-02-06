import json
from datetime import datetime, timezone
from Logging_Mechanism.logger import info
from .utils import sha256_hex


CONFIDENCE = {
    "pgp": 80,
    "xmr": 70,
    "email": 50,
    "handle": 40
}


class PageMetadataAttacher:

    def __init__(self, pool):
        self.pool = pool

    async def run(self):
        info("🔗 Page Metadata Attacher started")

        async with self.pool.acquire() as conn:
            btc_rows = await conn.fetch(
                """
                SELECT vendor_id, page_id, site_id
                FROM VendorArtifacts
                WHERE artifact_type = 'btc';
                """
            )

        now = datetime.now(timezone.utc)

        async with self.pool.acquire() as conn:
            for btc in btc_rows:
                meta = await conn.fetchrow(
                    """
                    SELECT pgp_fingerprints, xmr_addresses, emails, vendor_handles
                    FROM Metadata
                    WHERE page_id = $1;
                    """,
                    btc["page_id"]
                )

                if not meta:
                    continue

                artifacts = {
                    "pgp": meta["pgp_fingerprints"],
                    "xmr": meta["xmr_addresses"],
                    "email": meta["emails"],
                    "handle": meta["vendor_handles"]
                }

                for atype, values in artifacts.items():
                    if not values:
                        continue

                    for value in json.loads(values):
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
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $9)
                            ON CONFLICT DO NOTHING;
                            """,
                            sha256_hex(f"{atype}:{value}:{btc['page_id']}"),   # artifact_id
                            btc["vendor_id"],
                            atype,
                            value,
                            sha256_hex(f"{atype}:{value}"),                    # ✅ artifact_hash
                            CONFIDENCE[atype],
                            btc["site_id"],
                            btc["page_id"],
                            now
                        )

                        

        info("🔗 Metadata attached to BTC-seeded vendors")
