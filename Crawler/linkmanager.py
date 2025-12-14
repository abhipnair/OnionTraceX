import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
import asyncpg

from Essentials.utils import remove_path_from_url
from Logging_Mechanism.logger import info, warning, error


class LinkManager:
    """
    Handles queues and DB integration for the crawler.
    - Separates visited sets for sites vs pages.
    - Limits number of inner links per site.
    - Enforces maximum crawl depth.
    """

    def __init__(self, pool: asyncpg.Pool, max_depth: int = 2, max_inner_links_per_site: int = 50):
        self.pool = pool
        self.LinksQueue = asyncio.Queue()          # Outer (site-level): (root_url, "OuterLink")
        self.InnerLinksQueue = asyncio.Queue()     # Inner (page-level): (full_url, depth)
        self.visited_sites = set()
        self.visited_pages = set()

        # Control limits
        self.max_depth = max_depth
        self.max_inner_links_per_site = max_inner_links_per_site

        # Track how many inner pages we've queued per domain
        self.domain_inner_counts = {}

    async def init_LinksQueue(self, hours_threshold: int = 6):
        """Initialize queue from DB (site roots)."""
        threshold_time = datetime.now(timezone.utc) - timedelta(hours=hours_threshold)

        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch(
                    "SELECT url FROM OnionSites WHERE last_seen IS NULL OR last_seen < $1;",
                    threshold_time,
                )

                for row in rows:
                    site_root = remove_path_from_url(row["url"])
                    if site_root not in self.visited_sites:
                        await self.LinksQueue.put((site_root, "OuterLink"))
                        self.visited_sites.add(site_root)

            info(f"✅ Initialized LinksQueue with {len(rows)} URLs.")
        except Exception as e:
            error(f"init_LinksQueue failed: {e}")

    # ---------- Site-level (outer) queue ----------
    async def add_url_LinksQueue(self, url: str):
        """Add a new site root to LinksQueue."""
        site_root = remove_path_from_url(url)
        if site_root not in self.visited_sites:
            await self.LinksQueue.put((site_root, "OuterLink"))
            self.visited_sites.add(site_root)
            info(f"🌍 Added to LinksQueue (site root): {site_root}")

    # ---------- Page-level (inner) queue ----------
    async def add_url_InnerLinksQueue(self, page_url: str, depth: int):
        """
        Add full page URL to InnerLinksQueue if:
        - Not visited.
        - Depth <= max_depth.
        - Site's inner link count < max_inner_links_per_site.
        """
        normalized = page_url.rstrip("/")
        if depth > self.max_depth:
            warning(f"⛔ Depth limit reached (depth={depth}) for {normalized}")
            return

        # Track domain count
        domain = remove_path_from_url(normalized)
        count = self.domain_inner_counts.get(domain, 0)
        if count >= self.max_inner_links_per_site:
            warning(f"🚫 Skipping inner link — limit {self.max_inner_links_per_site} reached for {domain}")
            return

        if normalized not in self.visited_pages:
            await self.InnerLinksQueue.put((normalized, depth))
            self.visited_pages.add(normalized)
            self.domain_inner_counts[domain] = count + 1
            info(f"↳ Added to InnerLinksQueue (depth={depth}) [{count+1}/{self.max_inner_links_per_site}]: {normalized}")

    # ---------- DB management ----------
    async def add_url_to_DB(self, url: str, source: str, keyword: str = "") -> bool:
        """
        Insert a new onion site (site root) into the DB.
        Returns:
            bool: True if inserted, False if it already existed (duplicate)
        """
        site_root = remove_path_from_url(url)
        url_hash = hashlib.sha256(site_root.encode()).hexdigest()
        now = datetime.now(timezone.utc)

        try:
            async with self.pool.acquire() as connection:
                result = await connection.execute(
                    """
                    INSERT INTO OnionSites (site_id, url, source, keyword, current_status, first_seen, last_seen)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (site_id) DO NOTHING;
                    """,
                    url_hash, site_root, source, keyword, "Alive", now, now
                )

            if result and "INSERT 0 1" in result:
                info(f"🗃️ Added site root to DB: {site_root}")
                return True  # new record
            else:
                # already existed
                return False

        except Exception as e:
            error(f"DB insert failed for {site_root}: {e}")
            return False


    async def update_status_in_DB(self, url: str, status: str):
        """Update liveness for a site root."""
        site_root = remove_path_from_url(url)
        url_hash = hashlib.sha256(site_root.encode()).hexdigest()
        now = datetime.now(timezone.utc)
        try:
            async with self.pool.acquire() as connection:
                result = await connection.execute(
                    """
                    UPDATE OnionSites
                    SET current_status = $1, last_seen = $2
                    WHERE site_id = $3;
                    """,
                    status, now, url_hash
                )
            if "UPDATE 1" in result:
                info(f"✅ Status updated ({status}): {site_root}")
            else:
                warning(f"⚠️ No DB record found to update: {site_root}")
        except Exception as e:
            error(f"DB update failed for {site_root}: {e}")

    async def add_html_page(self, page_url: str, html: str):
        """
        Inserts a crawled HTML page into the Pages table (BYTEA compatible).
        Args:
            page_url: Full page URL
            html: Raw HTML content as string
        """
        try:
            # Normalize & compute identifiers
            site_root = remove_path_from_url(page_url)
            site_id = hashlib.sha256(site_root.encode()).hexdigest()
            page_id = hashlib.sha256(page_url.encode()).hexdigest()

            html_bytes = html.encode("utf-8", errors="ignore")  # store as BYTEA
            html_hash = hashlib.sha256(html_bytes).hexdigest()
            crawl_date = datetime.now(timezone.utc)

            # Insert into Pages table
            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    INSERT INTO Pages (page_id, site_id, url, html_hash, raw_html, crawl_date)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (page_id) DO UPDATE
                    SET html_hash = EXCLUDED.html_hash,
                        raw_html = EXCLUDED.raw_html,
                        crawl_date = EXCLUDED.crawl_date;
                    """,
                    page_id, site_id, page_url, html_hash, html_bytes, crawl_date
                )

            info(f"📝 Page stored successfully: {page_url}")

        except Exception as e:
            error(f"❌ Page insert failed for {page_url}: {e}")


    # ---------- Queue helpers ----------
    async def has_inner_links(self) -> bool:
        return not self.InnerLinksQueue.empty()

    async def get_next_inner_link(self):
        return await self.InnerLinksQueue.get()

    async def has_links(self) -> bool:
        return not self.LinksQueue.empty()

    async def get_next_link(self):
        return await self.LinksQueue.get()
