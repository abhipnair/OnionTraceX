import asyncio
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
    Depth-aware Tor crawler.
    - Crawls .onion sites through Tor (SOCKS5)
    - Fully crawls within domain up to max_depth
    - Prioritizes inner links before moving to new domains
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

        """Main crawl loop — inner links always take priority."""
        while not self.stop_event.is_set():
            # Always exhaust inner links first
            while not self.stop_event.is_set() and await self.link_manager.has_inner_links():
                info("!!!Inside Loop INNER !!!")
                url, depth = await self.link_manager.get_next_inner_link()
                await self._process_url(session, url, "InnerLink", depth)
                await asyncio.sleep(self.polite_delay)

            # Move to a new outer domain only if no inner links are left
            if await self.link_manager.has_links():
                url, source = await self.link_manager.get_next_link()
                await self._process_url(session, url, source, depth=0)
                await asyncio.sleep(self.polite_delay)
                continue

            info("🕸️ No links left in queues — waiting for refill...")
            await asyncio.sleep(5)

    async def _process_url(self, session: ClientSession, url: str, source: str, depth: int):
        """Fetch and parse a page; add discovered links."""
        clean_url = remove_path_from_url(url)
        html = ""
        status = "Unknown"

        try:
            info(f"🌐 Fetching {url} via Tor [{source}] (depth={depth})")
            timeout = ClientTimeout(total=25)
            async with session.get(url, timeout=timeout) as resp:
                html = await resp.text(errors="ignore")
                status = "Alive" if 200 <= resp.status < 400 else "Dead"
        except asyncio.TimeoutError:
            status = "Timeout"
        except ClientError as e:
            status = "Error"
            warning(f"ClientError fetching {url}: {e}")
        except Exception as e:
            status = "Error"
            error(f"Unexpected error for {url}: {e}")

        if source == "OuterLink":
            await self.link_manager.update_status_in_DB(url, status)

        if status != "Alive" or not html:
            return

        found_links = self._extract_onion_links(html, clean_url)
        current_domain = self._get_domain(clean_url)

        for new_url in found_links:
            new_domain = self._get_domain(new_url)

            if new_domain == current_domain:
                # Crawl deeper within the same domain
                if depth < self.max_depth:
                    await self.link_manager.add_url_InnerLinksQueue(new_url, depth + 1)
                    info(f"↳ Queued inner link (depth={depth+1}): {new_url}")
            else:
                # Queue for later cross-domain exploration
                await self.link_manager.add_url_to_DB(new_url, "Exploratory")
                await self.link_manager.add_url_LinksQueue(new_url)

    def _extract_onion_links(self, html: str, base_url: str = "") -> set[str]:
        """Extract all .onion URLs from HTML content."""
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
