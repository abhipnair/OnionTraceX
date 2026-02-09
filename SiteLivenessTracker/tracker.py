import asyncio
import time
import hashlib
import random
from datetime import datetime, timezone

import aiohttp
from aiohttp_socks import ProxyConnector
import asyncpg

# =====================================================
# LOGGING (MUST BE FIRST)
# =====================================================

from Logging_Mechanism.logger import (
    setup_logger,
    info,
    warning,
    error,
    exception,
)

logger = setup_logger(
    name="SiteLivenessTracker",
    log_level=20,  # logging.INFO
    log_dir="logs"
)

# =====================================================
# CONFIG (Crawler-friendly)
# =====================================================

TOR_PROXY = "socks5://127.0.0.1:9050"

DB_DSN = "postgresql://onion_user:112233@localhost/oniontracex_db"

MAX_CONCURRENCY = 10
BATCH_SIZE = 50
JITTER_RANGE = (0.3, 1.2)

REQUEST_TIMEOUT = 45
CONNECT_TIMEOUT = 25

# =====================================================
# HELPERS
# =====================================================

def generate_liveness_id(site_id: str, ts: datetime) -> str:
    raw = f"{site_id}{ts.isoformat()}".encode()
    return hashlib.sha256(raw).hexdigest()

# =====================================================
# NETWORK CHECK
# =====================================================

async def check_site(session: aiohttp.ClientSession, site: dict):
    start = time.monotonic()

    try:
        async with session.get(
            site["url"],
            allow_redirects=True
        ) as resp:
            await resp.read()
            latency = time.monotonic() - start
            return "Alive", latency

    except asyncio.TimeoutError:
        warning("Timeout while checking %s", site["url"])
        return "Timeout", None

    except Exception as e:
        error("Connection error for %s | %s", site["url"], str(e))
        return "Dead", None

# =====================================================
# DB WRITE (Minimal & Atomic)
# =====================================================

async def write_result(pool, site, status, latency):
    now = datetime.now(timezone.utc)
    liveness_id = generate_liveness_id(site["site_id"], now)

    async with pool.acquire() as conn:
        async with conn.transaction():

            await conn.execute("""
                INSERT INTO SiteLiveness (
                    liveness_id,
                    site_id,
                    status,
                    response_time,
                    check_time
                )
                VALUES ($1, $2, $3, $4, $5)
            """, liveness_id, site["site_id"], status, latency, now)

            await conn.execute("""
                UPDATE OnionSites
                SET current_status = $1,
                    last_seen = $2
                WHERE site_id = $3
            """, status, now, site["site_id"])

# =====================================================
# WORKER (Rate-limited + Safe)
# =====================================================

async def process_site(sem, session, pool, site):
    async with sem:
        try:
            status, latency = await check_site(session, site)
            await write_result(pool, site, status, latency)

            info(
                "Checked %s | status=%s | latency=%s",
                site["site_id"][:12],
                status,
                f"{latency:.2f}s" if latency else "N/A"
            )

        except Exception:
            exception(
                "Unhandled error while processing site %s",
                site.get("site_id")
            )

        await asyncio.sleep(random.uniform(*JITTER_RANGE))

# =====================================================
# BATCH EXECUTION
# =====================================================

async def run_batch(sites, session, pool, sem):
    tasks = [
        process_site(sem, session, pool, site)
        for site in sites
    ]
    await asyncio.gather(*tasks)

# =====================================================
# MAIN TRACKER
# =====================================================

async def run_tracker():
    info("Site liveness tracker started")

    try:
        pool = await asyncpg.create_pool(
            dsn=DB_DSN,
            min_size=3,
            max_size=10
        )
        info("PostgreSQL connection pool initialized")

        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT site_id, url
                FROM OnionSites
            """)
            sites = [dict(r) for r in rows]

        info("Fetched %d onion sites for liveness check", len(sites))

        if not sites:
            warning("No sites found, exiting tracker")
            await pool.close()
            return

        connector = ProxyConnector.from_url(TOR_PROXY)
        timeout = aiohttp.ClientTimeout(
            total=REQUEST_TIMEOUT,
            connect=CONNECT_TIMEOUT
        )

        sem = asyncio.Semaphore(MAX_CONCURRENCY)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        ) as session:

            for i in range(0, len(sites), BATCH_SIZE):
                batch = sites[i:i + BATCH_SIZE]
                info(
                    "Processing batch %d-%d",
                    i + 1,
                    min(i + BATCH_SIZE, len(sites))
                )

                await run_batch(batch, session, pool, sem)
                await asyncio.sleep(2)

        await pool.close()
        info("Site liveness tracker finished successfully")

    except Exception:
        exception("Fatal error in site liveness tracker")

