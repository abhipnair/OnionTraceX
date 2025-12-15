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

    async def _fetch_clearnet(self, url: str) -> str:
        timeout = ClientTimeout(total=20)
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "close",
        }

        try:
            async with ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.text(errors="ignore")
        except Exception as e:
            warning(f"Clearnet fetch failed for {url}: {e}")

        return ""


    async def collect_from_ahmia_and_duckduckgo(self, keyword: str):
        """
        Reliable seed collection using:
        - Ahmia (clearnet, primary)
        - DuckDuckGo (clearnet references)
        """

        discovered = set()  # (url, source)

        # ---------------- Ahmia (PRIMARY SOURCE) ----------------
        ahmia_url = f"https://ahmia.fi/search/?q={keyword}&8de34a=471bc3"
        ahmia_html = await self._fetch_clearnet(ahmia_url)

        if ahmia_html:
            for u in self._extract_onion_links(ahmia_html):
                discovered.add((u, "Ahmia"))
                info("ahmia discoverd")
        else:
            warning(f"Ahmia returned no data for keyword: {keyword}")

        # ---------------- DuckDuckGo (SECONDARY SOURCE) ----------------
        ddg_url = f"https://duckduckgo.com/html/?q={keyword}+site:.onion"
        ddg_html = await self._fetch_clearnet(ddg_url)

        if ddg_html:
            for u in self._extract_onion_links(ddg_html):
                discovered.add((u, "DuckDuckGo"))
        else:
            warning(f"DuckDuckGo returned no data for keyword: {keyword}")

        # ---------------- Deduplication + Storage ----------------
        stored = 0
        skipped = 0

        for url, source in discovered:
            h = self._hash_url(url)
            if h not in self.visited_hashes:
                self.visited_hashes.add(h)
                await self.link_manager.add_url_to_DB(url, source, keyword)
                await self.link_manager.add_url_LinksQueue(url)
                stored += 1
            else:
                skipped += 1

        info(
            f"[SeedCollector] Keyword='{keyword}' | "
            f"Stored={stored}, Skipped(Duplicates)={skipped}, "
            f"Sources=Ahmia+DuckDuckGo"
        )

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
        """Store discovered URLs into DB and queue, counting new vs duplicate."""
        inserted_count = 0
        duplicate_count = 0

        for url in urls:
            try:
                added = await self.link_manager.add_url_to_DB(url, source, keyword)
                if added:
                    await self.link_manager.add_url_LinksQueue(url)
                    inserted_count += 1
                else:
                    duplicate_count += 1
            except Exception as e:
                error(f"Error storing link {url}: {e}")

        info(
            f"✅ [{source}] Stored {inserted_count}/{len(urls)} new unique links "
            f"({duplicate_count} duplicates skipped) into DB & queue."
        )

