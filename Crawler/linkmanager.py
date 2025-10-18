import asyncio
import hashlib
from datetime import datetime, timedelta, timezone  # <-- add timedelta here
import asyncpg

from Essentials.utils import remove_path_from_url
from Logging_Mechanism.logger import info, warning, error


class LinkManager:
    """
    Handles queues and DB integration for the crawler.
    Fixed: separate visited sets for sites vs pages, keep full page URLs for inner queue.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.LinksQueue = asyncio.Queue()          # Outer (site-level) items: (site_root_url, "OuterLink")
        self.InnerLinksQueue = asyncio.Queue()     # Inner (page-level) items: (full_page_url, depth)
        self.visited_sites = set()                 # normalized site roots (remove_path)
        self.visited_pages = set()                 # full page URLs (with path)

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
        """Add a new site root to LinksQueue and visited_sites (site-level)."""
        site_root = remove_path_from_url(url)
        if site_root not in self.visited_sites:
            await self.LinksQueue.put((site_root, "OuterLink"))
            self.visited_sites.add(site_root)
            info(f"🌍 Added to LinksQueue (site root): {site_root}")

    # ---------- Page-level (inner) queue ----------
    async def add_url_InnerLinksQueue(self, page_url: str, depth: int):
        """
        Add full page URL (with path) to InnerLinksQueue with depth.
        Uses visited_pages for page-level dedupe (do NOT remove path).
        """
        normalized = page_url.rstrip("/")  # keep path but normalize trailing slash
        if normalized not in self.visited_pages:
            await self.InnerLinksQueue.put((normalized, depth))
            self.visited_pages.add(normalized)
            info(f"↳ Added to InnerLinksQueue (depth={depth}): {normalized}")

    # ---------- DB insertion for new site roots ----------
    async def add_url_to_DB(self, url: str, source: str, keyword: str = ""):
        """Insert new onion site (site root) into OnionSites. Store site root."""
        site_root = remove_path_from_url(url)
        url_hash = hashlib.sha256(site_root.encode()).hexdigest()
        now = datetime.now(timezone.utc)

        try:
            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    INSERT INTO OnionSites (site_id, url, source, keyword, current_status, first_seen, last_seen)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (site_id) DO NOTHING;
                    """,
                    url_hash, site_root, source, keyword, "Alive", now, now
                )
            info(f"🗃️ Added site root to DB: {site_root}")
        except Exception as e:
            error(f"DB insert failed for {site_root}: {e}")

    async def update_status_in_DB(self, url: str, status: str):
        """Update liveness for a site root (use remove_path to get site root)."""
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

    # ---------- Queue helpers ----------
    async def has_inner_links(self) -> bool:
        return not self.InnerLinksQueue.empty()

    async def get_next_inner_link(self):
        return await self.InnerLinksQueue.get()

    async def has_links(self) -> bool:
        return not self.LinksQueue.empty()

    async def get_next_link(self):
        return await self.LinksQueue.get()
