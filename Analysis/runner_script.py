import asyncio
import asyncpg

from .analyser import PageAnalyzer



async def main():
    pool = await asyncpg.create_pool(
        user="onion_user",
        password="112233",
        database="oniontracex_db",
        host="127.0.0.1",
        min_size=1,
        max_size=5
    )

    analyzer = PageAnalyzer(pool)
    await analyzer.run()


if __name__ == "__main__":
    asyncio.run(main())
