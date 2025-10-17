import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
import asyncpg

from Essentials.utils import remove_path_from_url
from Logging_Mechanism.logger import info, warning, error


class LinkManager:
    """
    Manages queues and database integration for OnionTraceX crawler.
    - Tracks visited URLs to prevent duplicates
    - Keeps separate queues for outer and inner links
    - Updates PostgreSQL status table
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool
        self.LinksQueue = asyncio.Queue()          # Outer links (new domains)
        self.InnerLinksQueue = asyncio.Queue()     # (url, depth) for same-domain links
        self.visited = set()

    async def init_LinksQueue(self, hours_threshold: int = 6):
        """Initialize crawl queue with old or unseen links from DB."""
        threshold_time = datetime.now(timezone.utc) - timedelta(hours=hours_threshold)

        async with self.pool.acquire() as connection:
            rows = await connection.fetch(
                "SELECT url FROM OnionSites WHERE last_seen IS NULL OR last_seen < $1;",
                threshold_time,
            )

            for row in rows:
                url = row["url"]
                await self.LinksQueue.put(url)
                self.visited.add(url)

        info(f"✅ Initialized LinksQueue with {len(rows)} URLs.")

    async def add_url_LinksQueue(self, url: str):
        """Add a new outer link (domain-level)."""
        url = remove_path_from_url(url)
        if url not in self.visited:
            await self.LinksQueue.put((url, "OuterLink"))
            self.visited.add(url)
            info(f"🌍 Added to LinksQueue: {url}")

    async def add_url_InnerLinksQueue(self, url: str, depth: int):
        """Add a new same-domain link for deeper crawling."""
        url = remove_path_from_url(url)
        if url not in self.visited:
            await self.InnerLinksQueue.put((url, depth))
            self.visited.add(url)
            info(f"↳ Added to InnerLinksQueue (depth={depth}): {url}")

    async def add_url_to_DB(self, url: str, source: str, keyword: str = ""):
        """Insert new onion site into DB (ignore duplicates)."""
        url = remove_path_from_url(url)
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        now = datetime.now(timezone.utc)

        try:
            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    INSERT INTO OnionSites (site_id, url, source, keyword, current_status, first_seen, last_seen)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (site_id) DO NOTHING;
                    """,
                    url_hash, url, source, keyword, "Alive", now, now
                )
            info(f"🗃️ Added to DB: {url}")
        except Exception as e:
            error(f"DB insert failed for {url}: {e}")

    async def update_status_in_DB(self, url: str, status: str):
        """Update the liveness status for a site."""
        url = remove_path_from_url(url)
        url_hash = hashlib.sha256(url.encode()).hexdigest()
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
                info(f"✅ Status updated ({status}): {url}")
            else:
                warning(f"⚠️ No DB record found to update: {url}")
        except Exception as e:
            error(f"DB update failed for {url}: {e}")

    # Helpers
    async def has_inner_links(self):
        return not self.InnerLinksQueue.empty()

    async def get_next_inner_link(self):
        return await self.InnerLinksQueue.get()

    async def has_links(self):
        return not self.LinksQueue.empty()

    async def get_next_link(self):
        return await self.LinksQueue.get()
