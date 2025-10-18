import asyncio
from aiohttp_socks import ProxyConnector
from aiohttp import ClientSession
from Crawler.unified_crawler import UnifiedCrawler
from Crawler.linkmanager import LinkManager
from Essentials.configs import DB_CONFIG
import asyncpg
from Logging_Mechanism.logger import info

async def test_crawler():
    pool = await asyncpg.create_pool(**DB_CONFIG)
    link_manager = LinkManager(pool)

    # Add one known onion URL manually
    test_url = "http://ly75dbzixy7hlp663j32xo4dtoiikm6bxb53jvivqkpo6jwppptx3sad.onion"  # Replace with a working one
    await link_manager.add_url_to_DB(test_url, source="Manual")
    await link_manager.add_url_LinksQueue(test_url)

    # Initialize crawler
    crawler = UnifiedCrawler(link_manager, max_depth=5, polite_delay=3.0)

    # Start crawler for limited duration
    crawler_task = asyncio.create_task(crawler.start())

    try:
        await asyncio.sleep(60)  # run for 1 minute
    except asyncio.CancelledError:
        pass
    finally:
        info("🛑 Stopping test crawler...")
        await crawler.stop()
        crawler_task.cancel()

    await pool.close()
    info("✅ UnifiedCrawler test completed successfully.")

if __name__ == "__main__":
    asyncio.run(test_crawler())
