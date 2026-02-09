from Logging_Mechanism.logger import info, error
from AI_Based_Classification.classifier import classify_pages


class SiteClassifier:
    def __init__(self, pool):
        self.pool = pool

        # Selection
        self.total = 0

        # Pipeline stages
        self.attempted = 0
        self.inserted = 0
        self.updated = 0

        # Skips
        self.skipped_no_pages = 0
        self.skipped_empty_html = 0
        self.skipped_unknown = 0
        self.skipped_exception = 0

        # 🔄 Keyword transitions
        self.keyword_updates = []  # (site_id, old, new)

    async def run(self):
        info("🧠 STEP — AI-Based Onion Site Classification")

        async with self.pool.acquire() as conn:
            sites = await conn.fetch("""
                SELECT o.site_id
                FROM OnionSites o
                LEFT JOIN SiteClassification s
                  ON o.site_id = s.site_id
                WHERE o.current_status = 'Alive'
                  AND s.site_id IS NULL
            """)

        self.total = len(sites)
        info(f"🔍 Sites pending classification: {self.total}")

        for row in sites:
            site_id = row["site_id"]
            try:
                await self.classify_site(site_id)
            except Exception as e:
                self.skipped_exception += 1
                error(f"⚠️ {site_id[:8]} skipped — exception: {e}")

        # 📊 FINAL SUMMARY
        info(
            "📊 Summary — "
            f"total={self.total}, "
            f"attempted={self.attempted}, "
            f"inserted={self.inserted}, "
            f"updated={self.updated}, "
            f"unknown={self.skipped_unknown}, "
            f"skipped_no_pages={self.skipped_no_pages}, "
            f"skipped_empty_html={self.skipped_empty_html}, "
            f"skipped_exception={self.skipped_exception}"
        )

        # 🔄 Keyword update summary
        if self.keyword_updates:
            info("🔁 Keyword Updates (old → new):")
            for site_id, old_kw, new_kw in self.keyword_updates:
                info(
                    f"   🔄 {site_id[:8]} : "
                    f"{old_kw or 'NULL'} → {new_kw}"
                )
        else:
            info("🔁 No keyword changes recorded")

    async def classify_site(self, site_id: str):
        async with self.pool.acquire() as conn:
            pages = await conn.fetch("""
                SELECT raw_html
                FROM Pages
                WHERE site_id = $1
                  AND raw_html IS NOT NULL
                  AND octet_length(raw_html) > 200
                ORDER BY crawl_date DESC
                LIMIT 3
            """, site_id)

        if not pages:
            self.skipped_no_pages += 1
            info(f"💤 {site_id[:8]} skipped — no usable pages")
            return

        html_pages = [p["raw_html"] for p in pages]
        self.attempted += 1

        keyword, confidence = classify_pages(html_pages)

        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO SiteClassification
                (site_id, model_name, model_version,
                 predicted_keyword, confidence,
                 analysed_at, status)
                VALUES ($1, 'DarkBERT', 'v1', $2, $3,
                        NOW(), 'classified')
            """, site_id, keyword, confidence)

        self.inserted += 1

        if keyword == "unknown":
            self.skipped_unknown += 1
            info(f"🤷 {site_id[:8]} → unknown ({confidence:.2f})")
            return

        async with self.pool.acquire() as conn:
            old_keyword = await conn.fetchval("""
                SELECT keyword
                FROM OnionSites
                WHERE site_id = $1
            """, site_id)

            await conn.execute("""
                UPDATE OnionSites
                SET keyword = $1
                WHERE site_id = $2
            """, keyword, site_id)

        self.updated += 1

        # Track only real changes
        if old_keyword != keyword:
            self.keyword_updates.append(
                (site_id, old_keyword, keyword)
            )
            info(
                f"🔄 {site_id[:8]} keyword updated: "
                f"{old_keyword or 'NULL'} → {keyword}"
            )
        else:
            info(f"🧾 {site_id[:8]} → {keyword} ({confidence:.2f})")
