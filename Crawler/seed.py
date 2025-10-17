import asyncio
import hashlib
import re
from collections import deque
from bs4 import BeautifulSoup
from aiohttp import ClientSession, ClientTimeout
from aiohttp_socks import ProxyConnector

from Logging_Mechanism.logger import info, warning, error
from Essentials.utils import remove_path_from_url


class SeedCollector:
    """
    Unified Seed Collector for OnionTraceX.
    Supports:
        - Keyword Mode: Fetches Ahmia search results via Tor
        - File Mode: Loads onion URLs from a local file
        - Exploratory Mode: Traverses onion directories (BFS)
    """

    def __init__(self, link_manager, tor_proxy: str = "socks5://127.0.0.1:9050", max_depth: int = 2, max_pages: int = 8):
        self.link_manager = link_manager
        self.tor_proxy = tor_proxy
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.timeout = ClientTimeout(total=30)
        self.visited_hashes = set()
        self.sem = asyncio.Semaphore(5)

    # --------------------------------------------------
    # UTILITIES
    # --------------------------------------------------
    def _hash_url(self, url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()

    def _extract_onion_links(self, html: str) -> list[str]:
        pattern = re.compile(r"http[s]?://[a-zA-Z0-9\-\.]{16,56}\.onion\b")
        return list(set(pattern.findall(html)))

    def _deduplicate(self, urls: list[str], source: str) -> list[str]:
        unique = []
        for url in urls:
            h = self._hash_url(url)
            if h not in self.visited_hashes:
                self.visited_hashes.add(h)
                unique.append(url)
        info(f"[{source}] Added {len(unique)} unique links")
        return unique

    # --------------------------------------------------
    # NETWORK HELPERS
    # --------------------------------------------------
    async def _fetch(self, session: ClientSession, url: str) -> str:
        """Fetch URL through Tor with retries."""
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

    # --------------------------------------------------
    # MODE 1: KEYWORD (Ahmia)
    # --------------------------------------------------
    async def collect_from_keywords(self, keyword: str):
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

        deduped = self._deduplicate(list(all_links), f"Ahmia:{keyword}")
        await self._store_links(deduped, source="Keyword", keyword=keyword)

    # --------------------------------------------------
    # MODE 2: FILE
    # --------------------------------------------------
    async def collect_from_file(self, file_path: str):
        try:
            with open(file_path, "r") as f:
                lines = [l.strip() for l in f.readlines() if ".onion" in l]
            deduped = self._deduplicate(lines, "File")
            await self._store_links(deduped, source="File", keyword="")
        except Exception as e:
            error(f"File read error: {e}")

    # --------------------------------------------------
    # MODE 3: EXPLORATORY (BFS)
    # --------------------------------------------------
    async def collect_from_directory(self, start_url: str):
        connector = ProxyConnector.from_url(self.tor_proxy)
        discovered = set()
        queue = deque([(start_url, 0)])

        async with ClientSession(connector=connector, timeout=self.timeout) as session:
            while queue:
                url, depth = queue.popleft()
                if depth > self.max_depth:
                    continue

                html = await self._fetch(session, url)
                if not html:
                    continue

                links = self._extract_onion_links(html)
                for link in links:
                    h = self._hash_url(link)
                    if h not in self.visited_hashes:
                        self.visited_hashes.add(h)
                        discovered.add(link)
                        queue.append((link, depth + 1))

        deduped = self._deduplicate(list(discovered), "Exploratory")
        await self._store_links(deduped, source="Exploratory", keyword="")

    # --------------------------------------------------
    # STORE LINKS INTO DB + QUEUES
    # --------------------------------------------------
    async def _store_links(self, urls: list[str], source: str, keyword:str):
        """Push links to DB and Queues."""
        for url in urls:
            try:
                await self.link_manager.add_url_to_DB(url, source, keyword)
                await self.link_manager.add_url_LinksQueue(url)
                info(f"Added {url} to DB")
            except Exception as e:
                warning(f"Failed to store {url}: {e}")

        info(f"✅ Stored {len(urls)} links from [{source}] into DB & queue.")
