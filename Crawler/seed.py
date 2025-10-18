import asyncio
import hashlib
import re
from collections import deque
from aiohttp import ClientSession, ClientTimeout
from aiohttp_socks import ProxyConnector

from Logging_Mechanism.logger import info, warning, error


class SeedCollector:
    """Collects initial onion seeds via Ahmia or file."""

    def __init__(self, link_manager, tor_proxy="socks5://127.0.0.1:9050", max_depth=2, max_pages=8):
        self.link_manager = link_manager
        self.tor_proxy = tor_proxy
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.timeout = ClientTimeout(total=30)
        self.visited_hashes = set()
        self.sem = asyncio.Semaphore(5)

    def _hash_url(self, url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()

    def _extract_onion_links(self, html: str) -> list[str]:
        pattern = re.compile(r"http[s]?://[a-zA-Z0-9\-\.]{16,56}\.onion\b")
        return list(set(pattern.findall(html)))

    async def _fetch(self, session: ClientSession, url: str) -> str:
        for _ in range(3):
            try:
                async with self.sem:
                    async with session.get(url, timeout=self.timeout) as resp:
                        if resp.status == 200:
                            return await resp.text(errors="ignore")
            except Exception as e:
                warning(f"Fetch failed for {url}: {e}")
                await asyncio.sleep(2)
        return ""

    async def collect_from_keywords(self, keyword: str):
        """Collect seeds from Ahmia search results."""
        connector = ProxyConnector.from_url(self.tor_proxy)
        all_links = set()

        async with ClientSession(connector=connector, timeout=self.timeout) as session:
            tasks = []
            for start in range(0, self.max_pages * 10, 10):
                url = f"https://ahmia.fi/search/?q={keyword}&start={start}"
                tasks.append(self._fetch(session, url))
            pages = await asyncio.gather(*tasks)

            for html in pages:
                if html:
                    all_links.update(self._extract_onion_links(html))

        deduped = [u for u in all_links if self._hash_url(u) not in self.visited_hashes]
        for u in deduped:
            self.visited_hashes.add(self._hash_url(u))

        info(f"[Ahmia:{keyword}] Found {len(deduped)} new onion links.")
        await self._store_links(deduped, "Keyword", keyword)

    async def collect_from_file(self, file_path: str):
        """Load seeds from a file."""
        try:
            with open(file_path, "r") as f:
                lines = [l.strip() for l in f.readlines() if ".onion" in l]
            deduped = [u for u in lines if self._hash_url(u) not in self.visited_hashes]
            for u in deduped:
                self.visited_hashes.add(self._hash_url(u))
            info(f"[File] Loaded {len(deduped)} new onion links.")
            await self._store_links(deduped, "File", "")
        except Exception as e:
            error(f"File read error: {e}")

    async def _store_links(self, urls: list[str], source: str, keyword: str):
        for url in urls:
            await self.link_manager.add_url_to_DB(url, source, keyword)
            await self.link_manager.add_url_LinksQueue(url)
        info(f"✅ Stored {len(urls)} links from [{source}] into DB & queue.")
