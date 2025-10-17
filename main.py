import asyncio
import asyncpg


from Essentials.configs import *
from Crawler.linkmanager import LinkManager
from Crawler.seed import SeedCollector
from Crawler.unified_crawler import UnifiedCrawler

class Main:

    def __init__(self, keywords, seed_max_depth, pages, crawler_max_depth, polite_delay) -> None:
        self.keywords = keywords
        self.seed_max_depth = seed_max_depth
        self.crawler_max_depth = crawler_max_depth
        self.pages = pages
        self.polite_delay = polite_delay

    async def main(self):

        #1. Staring the postgres sql Server
        pool = await asyncpg.create_pool(**DB_CONFIG)

        #2. Starting the linkmanager
        link_manager = LinkManager(pool=pool)

        #3. Seed Collector
        SeedCollector(link_manager=link_manager, max_depth=self.seed_max_depth, max_pages=self.pages)

        #4. Crawler Based on keywords
        UnifiedCrawler(link_manager=link_manager, max_depth=self.crawler_max_depth, polite_delay=self.polite_delay)
        task = asyncio.create_task(crawler.start())
        await asyncio.sleep(60)
        await crawler.stop()
        await pool.close()

