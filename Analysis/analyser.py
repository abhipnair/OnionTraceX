import asyncio
import json
from Logging_Mechanism.logger import info, error
from .metadata_extractor import MetadataExtractor
from .bitcoin_extractor import BitcoinExtractor


class PageAnalyzer:
    """
    Background analysis worker for OnionTraceX.
    """

    def __init__(self, pool, batch_size: int = 50, sleep_interval: int = 10):
        self.pool = pool
        self.batch_size = batch_size
        self.sleep_interval = sleep_interval
        self.btc_extractor = BitcoinExtractor()

    async def run(self):
        info("🧠 PageAnalyzer started")
        while True:
            try:
                processed = await self.analyze_unprocessed_pages()
                if processed == 0:
                    await asyncio.sleep(self.sleep_interval)
            except Exception as e:
                error(f"PageAnalyzer fatal error: {e}")
                await asyncio.sleep(self.sleep_interval)

    async def analyze_unprocessed_pages(self) -> int:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT p.page_id, p.site_id, p.raw_html
                FROM Pages p
                LEFT JOIN Metadata m ON p.page_id = m.page_id
                WHERE m.page_id IS NULL
                LIMIT $1;
                """,
                self.batch_size
            )

        if not rows:
            info("🧠 No new pages to analyze")
            return 0

        for row in rows:
            try:
                await self._analyze_single_page(row)
            except Exception as e:
                error(f"Page analysis failed for {row['page_id']}: {e}")

        info(f"🧠 Analyzed {len(rows)} pages")
        return len(rows)

    async def _analyze_single_page(self, row):
        page_id = row["page_id"]
        site_id = row["site_id"]
        raw_html = row["raw_html"]

        # -------- Metadata Extraction --------
        meta = MetadataExtractor.extract(page_id, raw_html)

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO Metadata
                (metadata_id, page_id, title, meta_tags, emails, pgp_keys, language)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (metadata_id) DO NOTHING;
                """,
                meta["metadata_id"],
                page_id,
                meta["title"],
                json.dumps(meta["meta_tags"]),   # ✅ FIX
                json.dumps(meta["emails"]),      # ✅ FIX
                json.dumps(meta["pgp_keys"]),    # ✅ FIX
                meta["language"]
            )

        # -------- Bitcoin Extraction --------
        btc_results = self.btc_extractor.extract_from_html(
            raw_html.decode("utf-8", errors="ignore"),
            site_id,
            page_id
        )

        if btc_results:
            async with self.pool.acquire() as conn:
                for btc in btc_results:
                    await conn.execute(
                        """
                        INSERT INTO BitcoinAddresses
                        (address_id, address, site_id, page_id, valid, detected_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (address_id) DO NOTHING;
                        """,
                        btc["address_id"],
                        btc["address"],
                        btc["site_id"],
                        btc["page_id"],
                        btc["valid"],
                        btc["detected_at"]
                    )

        info(f"📄 Page enriched: {page_id}")
