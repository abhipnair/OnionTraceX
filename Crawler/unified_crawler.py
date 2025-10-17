import asyncio
import hashlib
import re
from bs4 import BeautifulSoup, Tag
from aiohttp import ClientError, ClientSession, ClientTimeout
from aiohttp_socks import ProxyConnector
from urllib.parse import urljoin
import tldextract

from Essentials.utils import remove_path_from_url
from Logging_Mechanism.logger import info, warning, error


class UnifiedCrawler:
    """
    Graceful depth-aware Tor crawler.
    - Crawls .onion sites through Tor (SOCKS5)
    - Fully crawls within domain up to max_depth
    - Stops adding deeper links when limit reached
    - Moves to next outer link when inner queue drains
    """

    def __init__(self, link_manager, max_depth=2, polite_delay=2.0):
        self.link_manager = link_manager
        self.max_depth = max_depth
        self.polite_delay = polite_delay
        self.stop_event = asyncio.Event()

    async def start(self):
        info("🕷️ UnifiedCrawler started.")
        connector = ProxyConnector.from_url("socks5://127.0.0.1:9050")
        async with ClientSession(connector=connector) as session:
            await self._crawl_loop(session)

    async def stop(self):
        info("🛑 Stopping crawler gracefully...")
        self.stop_event.set()

    async def _crawl_loop(self, session: ClientSession):
        while not self.stop_event.is_set():
            # Prioritize same-domain inner links
            if await self.link_manager.has_inner_links():
                url, depth = await self.link_manager.get_next_inner_link()
                await self._process_url(session, url, "InnerLink", depth)
                continue

            # If no inner links left, move to new domain
            if await self.link_manager.has_links():
                url, source = await self.link_manager.get_next_link()
                await self._process_url(session, url, source, depth=0)
                continue

            info("No links in queues. Waiting for refill...")
            await asyncio.sleep(5)

    async def _process_url(self, session: ClientSession, url: str, source: str, depth: int):
        """Fetch and parse page; add discovered links."""
        clean_url = remove_path_from_url(url)
        try:
            info(f"Fetching {url} via Tor [{source}] (depth={depth})")
            timeout = ClientTimeout(total=25)
            async with session.get(url, timeout=timeout) as resp:
                html = await resp.text(errors="ignore")
                status = "Alive" if 200 <= resp.status < 400 else "Dead"
        except asyncio.TimeoutError:
            status = "Timeout"
            html = ""
        except ClientError as e:
            status = "Error"
            html = ""
            warning(f"ClientError fetching {url}: {e}")
        except Exception as e:
            status = "Error"
            html = ""
            error(f"Unexpected error for {url}: {e}")

        if source == "OuterLink":
            await self.link_manager.update_status_in_DB(url, status)

        # Skip if not alive
        if status != "Alive" or not html:
            return

        found_links = self._extract_onion_links(html, clean_url)
        current_domain = self._get_domain(clean_url)

        for new_url in found_links:
            new_domain = self._get_domain(new_url)

            if new_domain == current_domain:
                # Stay within domain but stop deeper than max_depth
                if depth < self.max_depth:
                    await self.link_manager.add_url_InnerLinksQueue(new_url, depth + 1)
                    info(f"Inner link added (depth={depth+1}): {new_url}")
            else:
                # Different domain
                await self.link_manager.add_url_to_DB(new_url, "Exploratory")
                await self.link_manager.add_url_LinksQueue(new_url)

        await asyncio.sleep(self.polite_delay)

    def _extract_onion_links(self, html: str, base_url: str = "") -> set[str]:
        """Extract all .onion URLs from HTML."""
        ONION_PATTERN = re.compile(r"https?://[a-zA-Z0-9]{16,56}\.onion")
        links = set()
        try:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                if isinstance(a, Tag):
                    full = urljoin(base_url, a.get("href", "").strip())
                    if ".onion" in full:
                        links.add(full)
        except Exception as e:
            warning(f"BeautifulSoup parse error: {e}")
        links.update(ONION_PATTERN.findall(html))
        return {url.rstrip("/") for url in links}

    def _get_domain(self, url: str) -> str:
        parsed = tldextract.extract(url)
        return parsed.registered_domain


# # Simple test harness
# if __name__ == "__main__":
#     import asyncpg
#     from Crawler.linkmanager import LinkManager

#     DB_CONFIG = {
#         "user": "onion_user",
#         "password": "112233",
#         "database": "oniontracex_db",
#         "host": "127.0.0.1",
#         "port": 5432,
#     }

#     async def test():
#         pool = await asyncpg.create_pool(**DB_CONFIG)
#         lm = LinkManager(pool)
#         await lm.add_url_to_DB("http://ly75dbzixy7hlp663j32xo4dtoiikm6bxb53jvivqkpo6jwppptx3sad.onion", "ManualTest")
#         await lm.add_url_LinksQueue("http://ly75dbzixy7hlp663j32xo4dtoiikm6bxb53jvivqkpo6jwppptx3sad.onion")
#         await lm.add_url_LinksQueue("http://blackypezbmbgvmml4vllavvdvjjh6dkuth7ngnj2qx3x56xl6eaq7qd.onion")

#         crawler = UnifiedCrawler(lm, max_depth=2)
#         task = asyncio.create_task(crawler.start())
#         await asyncio.sleep(60)
#         await crawler.stop()
#         await pool.close()

#     asyncio.run(test())
