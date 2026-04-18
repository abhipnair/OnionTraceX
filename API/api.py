# ======================================================
#  OnionTraceX Backend API
#  Version: 1.2 (Optimized for Frontend Integration)
# ======================================================

from flask import Flask, jsonify, request, make_response, Response
from flask_cors import CORS
from datetime import datetime, timedelta
import random
import csv
from io import BytesIO
import asyncio
import asyncpg
from datetime import datetime
import threading
from collections import defaultdict
from datetime import timezone


from Logging_Mechanism.logger import *
import atexit
from Crawler.linkmanager import LinkManager
from Crawler.seed import SeedCollector
from Crawler.unified_crawler import UnifiedCrawler
from Essentials.configs import *

from Reports.queries import *
from Reports.assembler import *
from Reports.pdf_renderer import *
import os
import hashlib


REPORT_EVIDENCE_DIR = "./evidence"
REPORT_LOGO_PATH = "./assets/oniontracex_logo.png"

os.makedirs(REPORT_EVIDENCE_DIR, exist_ok=True)





app = Flask(__name__)
CORS(app)

# ==================== CONFIGURATION ====================
CONFIG = {
    'MAX_PAGE_SIZE': 100,
    'DEFAULT_PAGE_SIZE': 50
}


conn = None  



# ==================== GLOBAL STATE ====================
crawler_task = None
crawler_instance = None
crawler_status = "idle"
crawler_progress = 0
crawler_message = ""

# Create a dedicated async loop in a background thread
loop = asyncio.new_event_loop()
db_pool = None

async def init_db_pool():
    global db_pool
    if not db_pool:
        db_pool = await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=10)
        info("AsyncPG pool initialized.")

def run_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=run_background_loop, args=(loop,), daemon=True).start()


@atexit.register
def close_pool():
    global db_pool
    if db_pool:
        future = asyncio.run_coroutine_threadsafe(db_pool.close(), loop)
        future.result()
        print("Closed asyncpg connection pool.")


# ==================== ASYNC CRAWLER CORE ====================
# ==================== ASYNC CRAWLER CORE ====================
async def run_crawler(
    keywords: list[str],
    manual_urls: list[str],
    crawl_depth: int,
    polite_delay: float
):
    global crawler_status, crawler_progress, crawler_message, crawler_instance

    try:
        crawler_status = "starting"
        crawler_message = "Initializing crawler components..."
        crawler_progress = 5

        if not db_pool:
            try:
                await init_db_pool()
            except Exception as e:
                crawler_status = "error"
                crawler_message = f"Failed to initialize DB pool: {e}"
                error(f"[CRAWLER INIT ERROR] {e}")
                return

        link_manager = LinkManager(pool=db_pool)  # type: ignore

        # --------------------------------------------------
        # 🔥 MANUAL URL INGESTION (CORRECT FOR YOUR LINKMANAGER)
        # --------------------------------------------------
        if manual_urls:
            crawler_message = f"Injecting {len(manual_urls)} manual URLs"
            crawler_progress = 10

            for raw_url in manual_urls:
                try:
                    url = raw_url.strip()

                    # Normalize onion URL
                    if not url.startswith(("http://", "https://")):
                        url = "http://" + url

                    if ".onion" not in url:
                        warning(f"[MANUAL URL SKIPPED] Not an onion: {url}")
                        continue

                    # Insert into DB (dedup handled internally)
                    inserted = await link_manager.add_url_to_DB(
                        url=url,
                        source="manual",
                        keyword="manual"
                    )

                    # Add to crawl queue only once
                    if inserted:
                        await link_manager.add_url_LinksQueue(url)

                except Exception as e:
                    error(f"[MANUAL URL ERROR] {raw_url}: {e}")


        # --------------------------------------------------
        # 🔍 SEED COLLECTION (UNCHANGED)
        # --------------------------------------------------
        if keywords:
            crawler_message = f"Collecting seeds for: {', '.join(keywords)}"
            seed = SeedCollector(
                link_manager=link_manager
            )
            for kw in keywords:
                await seed.collect_from_ahmia_and_duckduckgo(kw)
            crawler_progress = 30

        # --------------------------------------------------
        # 🚀 UNIFIED CRAWLER START
        # --------------------------------------------------
        crawler_status = "running"
        crawler_message = "Launching unified crawler..."
        crawler_progress = 50

        crawler_instance = UnifiedCrawler(
            link_manager=link_manager,
            max_depth=crawl_depth,
            polite_delay=polite_delay
        )

        await crawler_instance.start()

        crawler_status = "completed"
        crawler_message = "Crawler finished successfully!"
        crawler_progress = 100

    except asyncio.CancelledError:
        crawler_status = "stopped"
        crawler_message = "Crawler manually stopped."
        crawler_progress = 0

    except Exception as e:
        crawler_status = "error"
        crawler_message = f"Error: {e}"
        crawler_progress = 0
        error(f"[CRAWLER ERROR] {e}")


@app.route("/api/crawler/start", methods=["POST"])
def start_crawler():
    global crawler_task, crawler_status, crawler_progress, crawler_message

    if crawler_task and not crawler_task.done():
        return jsonify({
            "status": "error",
            "message": "Crawler already running"
        }), 400

    keywords = []
    manual_urls = []

    # --------------------------------------------------
    # HANDLE INPUT (MULTIPART / JSON)
    # --------------------------------------------------
    if request.content_type and request.content_type.startswith("multipart/form-data"):

        # ---------------- FILE INPUT ----------------
        file = request.files.get("seed_file")

        if file:
            try:
                content = file.read().decode("utf-8", errors="ignore")

                for line in content.splitlines():
                    for item in re.split(r"[,\n]", line):
                        item = item.strip()
                        if not item:
                            continue

                        # Auto classify
                        if ".onion" in item:
                            manual_urls.append(item)
                        else:
                            keywords.append(item)

            except Exception as e:
                error(f"[SEED FILE PARSE ERROR] {e}")

        # ---------------- TEXT INPUT ----------------
        raw_kw = request.form.get("keywords", "")
        raw_urls = request.form.get("manual_urls", "")

        if raw_kw:
            keywords += [k.strip() for k in raw_kw.split(",") if k.strip()]

        if raw_urls:
            manual_urls += [
                u.strip()
                for line in raw_urls.splitlines()
                for u in line.split(",")
                if u.strip()
            ]

    else:
        # ---------------- JSON INPUT ----------------
        data = request.json or {}

        kw_field = data.get("keywords", [])
        url_field = data.get("manual_urls", [])

        if isinstance(kw_field, str):
            keywords += [k.strip() for k in kw_field.split(",") if k.strip()]
        elif isinstance(kw_field, list):
            keywords += [k.strip() for k in kw_field if k.strip()]

        if isinstance(url_field, str):
            manual_urls += [u.strip() for u in url_field.split(",") if u.strip()]
        elif isinstance(url_field, list):
            manual_urls += [u.strip() for u in url_field if u.strip()]

    # --------------------------------------------------
    # NORMALIZATION & DEDUPLICATION
    # --------------------------------------------------
    keywords = list(set(k.lower() for k in keywords if k))
    manual_urls = list(set(u.strip() for u in manual_urls if u))

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------
    if not keywords and not manual_urls:
        return jsonify({
            "status": "error",
            "message": "Provide keywords OR manual .onion URLs or upload seed file"
        }), 400

    # --------------------------------------------------
    # PARAMETERS
    # --------------------------------------------------
    def get_param(key, default, cast_func):
        try:
            if request.form and key in request.form:
                return cast_func(request.form.get(key))
            if request.is_json and key in (request.json or {}):
                return cast_func(request.json.get(key))
        except:
            pass
        return default

    crawl_depth = get_param("crawl_depth", 2, int)
    polite_delay = get_param("polite_delay", 2.0, float)

    # --------------------------------------------------
    # START CRAWLER
    # --------------------------------------------------
    crawler_status = "starting"
    crawler_message = "Crawler starting..."
    crawler_progress = 1

    crawler_task = asyncio.run_coroutine_threadsafe(
        run_crawler(
            keywords,
            manual_urls,
            crawl_depth,
            polite_delay
        ),
        loop
    )

    info(
        f"[CRAWLER START] keywords={len(keywords)} | manual_urls={len(manual_urls)}"
    )

    return jsonify({
        "status": "success",
        "message": f"Crawler started ({len(keywords)} keywords, {len(manual_urls)} manual URLs)",
        "data": {
            "keywords": keywords,
            "manual_urls": manual_urls,
            "crawl_depth": crawl_depth,
            "polite_delay": polite_delay
        }
    })



@app.route("/api/crawler/status", methods=["GET"])
def crawler_status_api():
    """Return live crawler status and progress"""
    return jsonify({
        "status": crawler_status,
        "progress": crawler_progress,
        "message": crawler_message
    })


@app.route("/api/crawler/stop", methods=["POST"])
def stop_crawler():
    global crawler_task, crawler_instance, crawler_status, crawler_message
    if crawler_task and not crawler_task.done():
        crawler_task.cancel()
        if crawler_instance:
            asyncio.run_coroutine_threadsafe(crawler_instance.stop(), loop)
        crawler_status = "stopped"
        crawler_message = "Crawler manually stopped."
        crawler_progress = 0
        return jsonify({"status": "success", "message": "Crawler stopped"}), 200
    return jsonify({"status": "idle", "message": "No active crawler"}), 400



# ==================== MOCK DATA INITIALIZATION ====================

SITE_NAMES = [
    'marketplace-central', 'forum-discuss', 'darknet-shop', 'vendor-hub', 'community-board',
    'trading-post', 'exchange-central', 'information-hub', 'discussion-board', 'classified-ads',
    'resource-library', 'news-network', 'documentation-wiki', 'tutorial-central', 'archive-vault'
]

VENDOR_ALIASES = [
    'ShadowMerchant', 'QuantumTrader', 'PhantomVendor', 'NeonGhost', 'CyberPhantom',
    'VortexMaster', 'NullPoint', 'EchoVendor', 'SilentTrader', 'VoidMerchant',
    'NovaVendor', 'ShadowBroker', 'GhostOperator', 'QuantumVoid', 'NexusTrader'
]

MARKETPLACES = [
    'AlphaBay', 'Dream Market', 'Wall Street Market', 'Nightmare Market',
    'Dark Market', 'Monopoly', 'Empire Market', 'White House Market'
]

mock_data = {'sites': [], 'vendors': [], 'bitcoins': [], 'reports': []}


def initialize_mock_data():
    """Generate realistic mock datasets"""
    print("Generating mock data...")
    site_categories = ['Marketplace', 'Forum', 'Scam', 'Blog', 'Illegal Content']
    sources = ['Keyword Search', 'Reference Link', 'Crawler Discovery']

    # ---------- Sites ----------
    for i in range(80):
        first_seen = datetime.now() - timedelta(days=random.randint(1, 365))
        mock_data['sites'].append({
            'id': f'site_{i:05d}',
            'url': f"http://{random.choice(SITE_NAMES)}{i}.onion",
            'category': random.choice(site_categories),
            'status': random.choices(['Alive', 'Dead', 'Timeout'], weights=[65, 25, 10])[0],
            'firstSeen': first_seen.strftime('%Y-%m-%d'),
            'lastSeen': (datetime.now() - timedelta(hours=random.randint(1, 72))).strftime('%Y-%m-%d %H:%M'),
            'source': random.choice(sources),
            'title': f"Onion Site - {SITE_NAMES[i % len(SITE_NAMES)]} #{i}",
            'metadata': {
                'language': random.choice(['English', 'Russian', 'German']),
                'ssl_cert': random.choice(['Valid', 'Expired', 'Self-Signed']),
                'response_time': round(random.uniform(0.5, 15), 2),
                'server': random.choice(['Apache', 'Nginx', 'IIS']),
                'page_size_kb': random.randint(10, 5000),
                'indexed_pages': random.randint(1, 10000),
                'external_links': random.randint(0, 500)
            }
        })

    # ---------- Vendors ----------
    for i in range(50):
        wallets = [f"bc1q{''.join(random.choices('0123456789abcdef', k=40))}" for _ in range(random.randint(1, 5))]
        mock_data['vendors'].append({
            'id': f'vendor_{i:04d}',
            'alias': f"{random.choice(VENDOR_ALIASES)}_{i:03d}",
            'marketplaces': random.sample(MARKETPLACES, k=random.randint(1, 4)),
            'wallets': wallets,
            'status': random.choice(['Active', 'Inactive', 'Banned']),
            'lastSeen': (datetime.now() - timedelta(days=random.randint(0, 60))).strftime('%Y-%m-%d'),
            'reputation': round(random.uniform(1, 5), 2),
            'totalSales': random.randint(10, 10000),
            'avgRating': round(random.uniform(3.5, 5.0), 2)
        })

    # ---------- Bitcoin Wallets ----------
    for i in range(100):
        mock_data['bitcoins'].append({
            'address': f"bc1q{''.join(random.choices('0123456789abcdef', k=40))}",
            'balance': round(random.expovariate(0.1), 4),
            'transactionCount': random.randint(1, 3000),
            'riskScore': random.randint(1, 100),
            'isMixer': random.random() < 0.15,
            'lastActivity': (datetime.now() - timedelta(hours=random.randint(0, 2160))).strftime('%Y-%m-%d %H:%M')
        })
    print("Mock data initialized.")


# ==================== HELPERS ====================

def paginate(data, page, size):
    size = min(size, CONFIG['MAX_PAGE_SIZE'])
    start = (page - 1) * size
    return data[start:start + size]


def get_int_param(param, default, min_val=1, max_val=None):
    try:
        val = int(param)
        if val < min_val:
            return min_val
        if max_val and val > max_val:
            return max_val
        return val
    except:
        return default


# ==================== API ENDPOINTS ====================

@app.route("/api/stats")
def stats():
    async def fetch_stats():
        global db_pool
        if not db_pool:
            await init_db_pool()

        async with db_pool.acquire() as conn: # type: ignore
            total = await conn.fetchval('SELECT COUNT(*) FROM "onionsites";')
            alive = await conn.fetchval(
                'SELECT COUNT(*) FROM "onionsites" WHERE LOWER(current_status) = LOWER($1);', 'Alive'
            )
            dead = await conn.fetchval(
                'SELECT COUNT(*) FROM "onionsites" WHERE LOWER(current_status) = LOWER($1);', 'Dead'
            )
            timeout = await conn.fetchval(
                'SELECT COUNT(*) FROM "onionsites" WHERE LOWER(current_status) = LOWER($1);', 'Timeout'
            )
        return total, alive, dead, timeout

    try:
        # Run the coroutine safely in the existing background loop
        future = asyncio.run_coroutine_threadsafe(fetch_stats(), loop)
        total, alive, dead, timeout = future.result()

        # Avoid division by zero
        if total == 0:
            alive_percent = dead_percent = timeout_percent = 0.0
        else:
            alive_percent = round((alive / total) * 100, 1)
            dead_percent = round((dead / total) * 100, 1)
            timeout_percent = round((timeout / total) * 100, 1)

        # Structure matches frontend expectations
        return jsonify({
            "success": True,
            "data": {
                "totalSites": total,
                "alivePercent": alive_percent,
                "deadPercent": dead_percent,
                "timeoutPercent": timeout_percent,
                "activeCrawlers": 1,
                "avgCrawlTime": round(random.uniform(2, 8), 2),
                "totalVendors": 0,
                "totalWallets": 0
            }
        })

    except Exception as e:
        error("❌ /api/stats DB error:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/liveness", methods=["GET"])
def _get_liveness():
    days = int(request.args.get("days", 30))

    async def fetch_liveness():
        global db_pool
        if not db_pool:
            await init_db_pool()
        async with db_pool.acquire() as conn: # type: ignore
            rows = await conn.fetch("""
                SELECT 
                    DATE(last_seen) AS date,
                    SUM(CASE WHEN LOWER(current_status) = 'alive' THEN 1 ELSE 0 END) AS alive,
                    SUM(CASE WHEN LOWER(current_status) = 'dead' THEN 1 ELSE 0 END) AS dead,
                    SUM(CASE WHEN LOWER(current_status) = 'timeout' THEN 1 ELSE 0 END) AS timeout
                FROM onionsites
                WHERE last_seen >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(last_seen)
                ORDER BY DATE(last_seen);
            """ % days)
        return rows

    try:
        future = asyncio.run_coroutine_threadsafe(fetch_liveness(), loop)
        rows = future.result()

        data = [
            {
                "date": str(r["date"]),
                "alive": r["alive"],
                "dead": r["dead"],
                "timeout": r["timeout"]
            }
            for r in rows
        ]
        return jsonify({"success": True, "data": data})

    except Exception as e:
        error("❌ /api/liveness DB error:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/categories", methods=["GET"])
def _get_categories():
    async def fetch_categories():
        global db_pool
        if not db_pool:
            await init_db_pool()
        async with db_pool.acquire() as conn: # type: ignore
            rows = await conn.fetch("""
                SELECT 
                    COALESCE(NULLIF(TRIM(keyword), ''), 'Others') AS name,
                    COUNT(*) AS value
                FROM onionsites
                GROUP BY name
                ORDER BY value DESC;
            """)
        return rows

    try:
        future = asyncio.run_coroutine_threadsafe(fetch_categories(), loop)
        rows = future.result()

        palette = ["#06b6d4", "#8b5cf6", "#ef4444", "#f59e0b", "#10b981", "#6366f1", "#3b82f6", "#a855f7"]
        data = [
            {
                "name": r["name"],
                "value": r["value"],
                "color": palette[i % len(palette)]
            }
            for i, r in enumerate(rows)
        ]
        return jsonify({"success": True, "data": data})

    except Exception as e:
        error("/api/categories DB error:", e)
        return jsonify({"success": False, "error": str(e)}), 500




@app.route("/api/keywords", methods=["GET"])
def _get_keywords():
    async def fetch_keywords():
        global db_pool
        if not db_pool:
            await init_db_pool()
        async with db_pool.acquire() as conn: # type: ignore
            rows = await conn.fetch("""
                SELECT 
                    COALESCE(NULLIF(TRIM(keyword), ''), 'Others') AS keyword,
                    COUNT(*) AS discovered
                FROM onionsites
                GROUP BY keyword
                ORDER BY discovered DESC
                LIMIT 20;
            """)
        return rows

    try:
        future = asyncio.run_coroutine_threadsafe(fetch_keywords(), loop)
        rows = future.result()

        data = [
            {
                "keyword": r["keyword"],
                "discovered": r["discovered"]
            }
            for r in rows
        ]
        return jsonify({"success": True, "data": data})

    except Exception as e:
        error("/api/keywords DB error:", e)
        return jsonify({"success": False, "error": str(e)}), 500

from datetime import datetime, timedelta
import asyncio
from flask import request, jsonify

from datetime import datetime
from flask import request, jsonify
import asyncio

@app.route("/api/sites")
def sites():

    async def fetch_sites(
        search,
        status,
        keyword,
        source,
        start_date,
        end_date,
        page_size,
        cursor_last_seen,
        cursor_site_id
    ):
        global db_pool
        if not db_pool:
            await init_db_pool()

        # ---------------- NORMALIZE FILTERS ----------------
        search = search or None
        keyword = keyword or None
        source = source or None
        status = None if status == "all" else status

        # ---------------- DATE FILTERS ----------------
        start_dt = None
        end_dt = None

        try:
            if start_date:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            if end_date:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            get_logger().warning("Invalid date filter")


        # ---------------- CURSOR PARSING (FINAL FIX) ----------------
        cursor_dt = None
        if cursor_last_seen:
            try:
                cursor_dt = datetime.fromisoformat(
                    cursor_last_seen.replace("Z", "+00:00")
                )

                # 🔥 CRITICAL FIX: make it NAIVE UTC
                if cursor_dt.tzinfo is not None:
                    cursor_dt = cursor_dt.astimezone(timezone.utc).replace(tzinfo=None)

            except ValueError:
                get_logger().warning(
                    "Invalid cursor_last_seen",
                    extra={"value": cursor_last_seen}
                )
                cursor_dt = None


        async with db_pool.acquire() as conn:
            query = """
                SELECT
                    site_id AS id,
                    url,
                    keyword,
                    current_status AS status,
                    first_seen,
                    last_seen,
                    source
                FROM OnionSites
                WHERE
                    ($1::text IS NULL OR LOWER(url) LIKE '%' || LOWER($1) || '%' OR site_id = $1)
                AND ($2::text IS NULL OR LOWER(current_status) = LOWER($2))
                AND ($3::text IS NULL OR LOWER(keyword) = LOWER($3))
                AND ($4::text IS NULL OR LOWER(source) = LOWER($4))
                AND ($5::timestamp IS NULL OR first_seen >= $5)
                AND ($6::timestamp IS NULL OR last_seen < $6)
                AND (
                    $7::timestamp IS NULL OR
                    (last_seen, site_id) < ($7, $8)
                )
                ORDER BY last_seen DESC, site_id DESC
                LIMIT $9;
            """

            rows = await conn.fetch(
                query,
                search,
                status,
                keyword,
                source,
                start_dt,
                end_dt,
                cursor_dt,
                cursor_site_id,
                page_size,
            )

        # ---------------- NEXT CURSOR ----------------
        next_cursor = None
        if rows:
            last = rows[-1]
            next_cursor = {
                "last_seen": last["last_seen"].isoformat(),
                "site_id": last["id"]
            }

        return rows, next_cursor

    # ========================= ROUTE HANDLER =========================
    try:
        args = request.args

        future = asyncio.run_coroutine_threadsafe(
            fetch_sites(
                search=args.get("search", "").strip(),
                status=args.get("status", "all").strip(),
                keyword=args.get("keyword", "").strip(),
                source=args.get("source", "").strip(),
                start_date=args.get("start_date", "").strip(),
                end_date=args.get("end_date", "").strip(),
                page_size=min(int(args.get("page_size", 25)), 100),
                cursor_last_seen=args.get("cursor_last_seen"),
                cursor_site_id=args.get("cursor_site_id"),
            ),
            loop,
        )

        rows, next_cursor = future.result()

        data = [{
            "id": r["id"],
            "url": r["url"],
            "category": r["keyword"] or "Other",
            "status": r["status"],
            "firstSeen": r["first_seen"].strftime("%Y-%m-%d %H:%M") if r["first_seen"] else None,
            "lastSeen": r["last_seen"].strftime("%Y-%m-%d %H:%M") if r["last_seen"] else None,
            "source": r["source"],
        } for r in rows]

        return jsonify({
            "success": True,
            "data": data,
            "next_cursor": next_cursor
        })

    except Exception:
        get_logger().exception("/api/sites failed")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500


@app.route("/api/site/<site_id>", methods=["GET"])
def get_site_full_analysis(site_id):
    async def fetch_site_data(site_id):
        global db_pool
        if not db_pool:
            await init_db_pool()

        async with db_pool.acquire() as conn:

            # ---------------- SITE ----------------
            site = await conn.fetchrow("""
                SELECT site_id, url, source, keyword, current_status,
                       first_seen, last_seen
                FROM OnionSites
                WHERE site_id = $1;
            """, site_id)

            if not site:
                return None

            # ---------------- PAGES ----------------
            pages = await conn.fetch("""
                SELECT page_id, url, crawl_date
                FROM Pages
                WHERE site_id = $1
                ORDER BY crawl_date DESC;
            """, site_id)

            page_ids = [p["page_id"] for p in pages]

            # ---------------- METADATA ----------------
            metadata_rows = []
            if page_ids:
                metadata_rows = await conn.fetch("""
                    SELECT page_id, title, meta_tags, emails,
                           pgp_keys, language
                    FROM Metadata
                    WHERE page_id = ANY($1);
                """, page_ids)

            metadata_map = {m["page_id"]: m for m in metadata_rows}

            # ---------------- BITCOIN ADDRESSES ----------------
            btc_rows = await conn.fetch("""
                SELECT address,
                    page_id,
                    valid,
                    detected_at,
                    tx_analyzed
                FROM BitcoinAddresses
                WHERE site_id = $1;
            """, site_id)


        return site, pages, metadata_map, btc_rows

    try:
        future = asyncio.run_coroutine_threadsafe(
            fetch_site_data(site_id), loop
        )
        result = future.result()

        if not result:
            return jsonify({"success": False, "error": "Site not found"}), 404

        site, pages, metadata_map, btc_rows = result

        # ---------------- FORMAT RESPONSE ----------------
        response = {
            "site": {
                "site_id": site["site_id"],
                "url": site["url"],
                "category": site["keyword"] or "Unknown",
                "status": site["current_status"],
                "source": site["source"],
                "first_seen": site["first_seen"].strftime("%Y-%m-%d %H:%M") if site["first_seen"] else None,
                "last_seen": site["last_seen"].strftime("%Y-%m-%d %H:%M") if site["last_seen"] else None
            },
            "pages": [],
            "bitcoin_addresses": []
        }

        # ---------------- PAGES + METADATA ----------------
        for p in pages:
            meta = metadata_map.get(p["page_id"])

            response["pages"].append({
                "page_id": p["page_id"],
                "url": p["url"],
                "crawled_at": p["crawl_date"].strftime("%Y-%m-%d %H:%M"),
                "metadata": {
                    "title": meta["title"] if meta else None,
                    "language": meta["language"] if meta else None,
                    "emails": meta["emails"] if meta and meta["emails"] else [],
                    "pgp_keys": meta["pgp_keys"] if meta and meta["pgp_keys"] else [],
                    "meta_tags": meta["meta_tags"] if meta and meta["meta_tags"] else {}
                }
            })

        # ---------------- BITCOIN ----------------
        for b in btc_rows:
            response["bitcoin_addresses"].append({
                "address": b["address"],
                "page_id": b["page_id"],
                "valid": b["valid"],
                "detected_at": b["detected_at"].strftime("%Y-%m-%d %H:%M") if b["detected_at"] else None,
                "tx_analyzed": b["tx_analyzed"],
            })


        return jsonify({"success": True, "data": response})

    except Exception as e:
        error(f"/api/site/{site_id} error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500





@app.route("/api/bitcoin/wallets", methods=["GET"])
def api_bitcoin_wallets():
    page = get_int_param(request.args.get("page"), 1)
    size = get_int_param(request.args.get("page_size"), CONFIG["DEFAULT_PAGE_SIZE"])
    offset = (page - 1) * size

    async def fetch_real_data():
        global db_pool
        if not db_pool:
            await init_db_pool()

        async with db_pool.acquire() as conn:  # type: ignore
            wallets = await conn.fetch("""
                SELECT 
                    b.address,
                    COUNT(t.tx_id) AS tx_count,
                    COALESCE(SUM(t.amount), 0) AS total_volume,
                    MIN(t.timestamp) AS first_seen,
                    MAX(t.timestamp) AS last_activity,
                    BOOL_OR(t.is_mixer) AS is_mixer,
                    ARRAY_AGG(DISTINCT s.url) FILTER (WHERE s.url IS NOT NULL) AS linked_sites
                FROM BitcoinAddresses b
                LEFT JOIN Transactions t ON b.address_id = t.address_id
                LEFT JOIN OnionSites s ON b.site_id = s.site_id
                GROUP BY b.address
                ORDER BY last_activity DESC NULLS LAST
                LIMIT $1 OFFSET $2;
            """, size, offset)

            stats = await conn.fetchrow("""
                SELECT
                    COUNT(DISTINCT address_id) AS total_wallets,
                    COUNT(tx_id) AS total_transactions,
                    SUM(amount) AS total_volume,
                    COUNT(DISTINCT address_id) FILTER (WHERE is_mixer = TRUE) AS suspected_mixers
                FROM Transactions;
            """)

        return wallets, stats

    try:
        future = asyncio.run_coroutine_threadsafe(fetch_real_data(), loop)
        wallets, stats = future.result()

        # ---------- FALLBACK TO MOCK ----------
        if not wallets:
            data = paginate(mock_data["bitcoins"], page, size)
            return jsonify({
                "success": True,
                "data": {
                    "stats": {
                        "totalWallets": len(mock_data["bitcoins"]),
                        "totalTransactions": sum(w["transactionCount"] for w in mock_data["bitcoins"]),
                        "suspectedMixers": sum(1 for w in mock_data["bitcoins"] if w["isMixer"]),
                        "totalVolume": round(sum(w["balance"] for w in mock_data["bitcoins"]), 2)
                    },
                    "wallets": data,
                    "network": None
                }
            })

        # ---------- REAL DATA ----------
        wallet_rows = []
        for w in wallets:
            risk = min(
                95,
                20 +
                (w["tx_count"] or 1) * 3 +
                (30 if w["is_mixer"] else 0)
            )

            wallet_rows.append({
                "address": w["address"],
                "balance": round(w["total_volume"], 4),
                "transactionCount": w["tx_count"] or 0,
                "firstSeen": w["first_seen"].strftime("%Y-%m-%d") if w["first_seen"] else "N/A",
                "lastActivity": w["last_activity"].strftime("%Y-%m-%d %H:%M") if w["last_activity"] else "N/A",
                "linkedSites": w["linked_sites"] or [],
                "riskScore": risk
            })

        return jsonify({
            "success": True,
            "data": {
                "stats": {
                    "totalWallets": stats["total_wallets"] or 0,
                    "totalTransactions": stats["total_transactions"] or 0,
                    "suspectedMixers": stats["suspected_mixers"] or 0,
                    "totalVolume": round(stats["total_volume"] or 0, 2)
                },
                "wallets": wallet_rows,
                "network": None
            }
        })

    except Exception as e:
        error("❌ /api/bitcoin/wallets error:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/bitcoin/network", methods=["GET"])
def bitcoin_transaction_network():
    async def fetch_network():
        global db_pool
        if not db_pool:
            await init_db_pool()

        async with db_pool.acquire() as conn:

            edges = await conn.fetch("""
                SELECT
                    e.from_address,
                    e.to_address,
                    SUM(e.amount) AS amount,
                    BOOL_OR(t.is_mixer) AS is_mixer,
                    MAX(t.fan_in) AS fan_in,
                    MAX(t.fan_out) AS fan_out
                FROM BitcoinTransactionEdges e
                LEFT JOIN BitcoinAddresses b
                    ON b.address = e.from_address
                LEFT JOIN Transactions t
                    ON t.address_id = b.address_id
                GROUP BY e.from_address, e.to_address
                HAVING SUM(e.amount) > 0
                LIMIT 500;
            """)

        return edges

    try:
        future = asyncio.run_coroutine_threadsafe(fetch_network(), loop)
        rows = future.result()

        node_map = {}
        links = []

        for r in rows:
            src = r["from_address"]
            dst = r["to_address"]

            for addr in (src, dst):
                if addr not in node_map:
                    risk = min(
                        95,
                        20 +
                        ((r["fan_in"] or 0) + (r["fan_out"] or 0)) * 2 +
                        (30 if r["is_mixer"] else 0)
                    )

                    node_map[addr] = {
                        "id": addr,
                        "fanIn": r["fan_in"] or 0,
                        "fanOut": r["fan_out"] or 0,
                        "isMixer": r["is_mixer"] or False,
                        "riskScore": risk
                    }

            links.append({
                "source": src,
                "target": dst,
                "amount": round(float(r["amount"]), 4)
            })

        info(f"🔗 BTC Network | Nodes={len(node_map)} Links={len(links)}")

        return jsonify({
            "success": True,
            "data": {
                "nodes": list(node_map.values()),
                "links": links
            }
        })

    except Exception as e:
        error(f"❌ /api/bitcoin/network error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@app.route("/api/system/health", methods=["GET"])
def api_system_health():
    global db_pool, crawler_status

    # ---- Database health ----
    db_status = "down"
    db_connections = 0

    try:
        if db_pool:
            db_connections = db_pool._queue.qsize() + db_pool._holders  # asyncpg internals
            db_status = "healthy"
    except Exception:
        db_status = "degraded"

    # ---- Crawler health ----
    crawler_map = {
        "running": "active",
        "starting": "active",
        "completed": "idle",
        "stopped": "idle",
        "idle": "idle",
        "error": "down"
    }

    crawler_state = crawler_map.get(crawler_status, "idle")

    # ---- Tor health (best-effort) ----
    # If you later add Tor controller, plug it here
    tor_status = "connected"
    tor_circuits = random.randint(3, 8)

    return jsonify({
        "success": True,
        "data": {
            "database": db_status,
            "dbConnections": db_connections,
            "crawler": crawler_state,
            "activeCrawlers": 1 if crawler_state == "active" else 0,
            "tor": tor_status,
            "torCircuits": tor_circuits
        }
    })


@app.route("/api/system/info", methods=["GET"])
def api_system_info():
    async def fetch_info():
        global db_pool
        if not db_pool:
            await init_db_pool()

        async with db_pool.acquire() as conn:
            # --- Database size ---
            db_size_bytes = await conn.fetchval(
                "SELECT pg_database_size(current_database());"
            )

            # --- PostgreSQL uptime ---
            db_uptime = await conn.fetchval(
                "SELECT now() - pg_postmaster_start_time();"
            )

            # --- Last meaningful update (domain specific) ---
            last_update = await conn.fetchval(
                "SELECT MAX(last_seen) FROM OnionSites;"
            )

        return db_size_bytes, db_uptime, last_update

    try:
        db_size_bytes, db_uptime, last_update = (
            asyncio.run_coroutine_threadsafe(fetch_info(), loop).result()
        )

        return jsonify({
            "success": True,
            "data": {
                "version": "1.2",
                "uptime": str(db_uptime).split(".")[0],  # clean HH:MM:SS / days
                "totalDataGB": round(db_size_bytes / (1024 ** 3), 2),
                "lastUpdate": (
                    last_update.isoformat()
                    if last_update
                    else "No data yet"
                )
            }
        })

    except Exception as e:
        error(f"/api/system/info error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


import psutil

@app.route("/api/system/resources", methods=["GET"])
def api_system_resources():
    try:
        cpu = int(psutil.cpu_percent(interval=0.4))

        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return jsonify({
            "success": True,
            "data": {
                "cpu": cpu,
                "ram": {
                    "used": round((ram.used / (1024 ** 3)), 2),
                    "total": round((ram.total / (1024 ** 3)), 2)
                },
                "disk": {
                    "used": round((disk.used / (1024 ** 3)), 2),
                    "total": round((disk.total / (1024 ** 3)), 2)
                }
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500




@app.route("/api/reports", methods=["GET"])
def list_reports():
    async def runner():
        global db_pool
        if not db_pool:
            await init_db_pool()

        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    report_id,
                    report_type,
                    site_id,
                    generated_at
                FROM Reports
                ORDER BY generated_at DESC
                LIMIT 50;
            """)
        return rows

    rows = asyncio.run_coroutine_threadsafe(runner(), loop).result()

    return jsonify({
        "success": True,
        "data": [
            {
                "report_id": r["report_id"],
                "report_type": r["report_type"],   # ✅ authoritative
                "scope": (
                    r["site_id"]
                    if r["site_id"] else "GLOBAL"
                ),
                "generated_at": r["generated_at"].isoformat(),
                "evidence_count": 1  # you can improve this later
            }
            for r in rows
        ]
    })


@app.route("/api/reports/verify/pdf", methods=["POST"])
def verify_report_pdf():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "PDF file required"}), 400

    pdf = request.files["file"]
    pdf_bytes = pdf.read()

    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

    async def runner():
        global db_pool
        if not db_pool:
            await init_db_pool()

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT report_hash, generated_at
                FROM Reports
                WHERE report_hash = $1;
            """, pdf_hash)

        return row

    row = asyncio.run_coroutine_threadsafe(runner(), loop).result()

    if not row:
        return jsonify({
            "success": True,
            "status": "UNKNOWN",
            "message": "Report not found in evidence database"
        })

    return jsonify({
        "success": True,
        "status": "VALID",
        "report_hash": pdf_hash,
        "generated_at": row["generated_at"].isoformat()
    })

@app.route("/api/reports/<report_id>/download", methods=["GET"])
def download_report(report_id):
    async def runner():
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT report_file
                FROM Reports
                WHERE report_id = $1
            """, report_id)
            return row

    row = asyncio.run_coroutine_threadsafe(runner(), loop).result()

    if not row:
        return jsonify({"success": False, "error": "Report not found"}), 404

    return Response(
        row["report_file"],
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={report_id}.pdf"
        }
    )


@app.route("/api/reports/<report_id>/view", methods=["GET"])
def view_report(report_id):
    async def runner():
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT report_file
                FROM Reports
                WHERE report_id = $1
            """, report_id)
            return row

    row = asyncio.run_coroutine_threadsafe(runner(), loop).result()

    if not row:
        return jsonify({"success": False, "error": "Report not found"}), 404

    return Response(
        row["report_file"],
        mimetype="application/pdf",
        headers={
            "Content-Disposition": "inline; filename=report.pdf"
        }
    )


@app.route("/api/reports/verify", methods=["POST"])
def verify_report():
    data = request.json

    if not data or "json_hash" not in data or "signature" not in data:
        return jsonify({"success": False, "error": "Invalid payload"}), 400

    from Reports.crypto.verifier import verify_signature

    valid = verify_signature(
        data["json_hash"],
        data["signature"]
    )

    return jsonify({
        "success": True,
        "status": "VALID" if valid else "TAMPERED"
    })

# -----------------------------
# RESOLVER FUNCTIONS
# -----------------------------
async def resolve_site_id(conn, site_id=None, url=None):
    if site_id:
        return site_id

    if url:
        row = await conn.fetchrow("""
            SELECT site_id
            FROM onionsites
            WHERE url = $1
        """, url)

        if row:
            return row["site_id"]

    return None


async def resolve_btc_address_id(conn, address_id=None, address=None):
    if address_id:
        return address_id

    if address:
        row = await conn.fetchrow("""
            SELECT address_id
            FROM BitcoinAddresses
            WHERE address = $1
        """, address)

        if row:
            return row["address_id"]

    return None


async def resolve_vendor_id(conn, vendor_id=None, vendor_name=None):
    if vendor_id:
        return vendor_id

    if vendor_name:
        row = await conn.fetchrow("""
            SELECT vendor_id
            FROM Vendors
            WHERE vendor_name ILIKE $1
        """, vendor_name)

        if row:
            return row["vendor_id"]

    return None


# ============================================================
# SITE DOSSIER REPORT
# ============================================================

@app.route("/api/reports/site", methods=["POST"])
def generate_site_dossier_report():

    data = request.json or {}

    site_id = data.get("site_id")
    url = data.get("url")

    async def runner():
        global db_pool

        if not db_pool:
            await init_db_pool()

        async with db_pool.acquire() as conn:

            # 🔎 Resolve site_id
            resolved_site_id = await resolve_site_id(conn, site_id, url)

            if not resolved_site_id:
                return None

            raw = await fetch_site_dossier(db_pool, resolved_site_id)

            if not raw:
                return None

        report_json = build_site_dossier(raw)

        pdf_path = os.path.join(
            REPORT_EVIDENCE_DIR,
            f"SITE_DOSSIER_{resolved_site_id}.pdf"
        )

        render_site_dossier_pdf(
            report=report_json,
            output_path=pdf_path,
            logo_path=REPORT_LOGO_PATH
        )

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        report_hash = hashlib.sha256(pdf_bytes).hexdigest()
        report_id = report_hash

        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO Reports (
                    report_id,
                    site_id,
                    report_hash,
                    report_file,
                    generated_at,
                    report_type
                )
                VALUES ($1, $2, $3, $4, $5, 'SITE DOSSIER')
                ON CONFLICT (report_id) DO NOTHING;
            """,
            report_id,
            resolved_site_id,
            report_hash,
            pdf_bytes,
            datetime.now(timezone.utc)
            )

        return {
            "report_id": report_id,
            "report_hash": report_hash,
            "integrity": report_json["integrity"],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    try:

        result = asyncio.run_coroutine_threadsafe(runner(), loop).result()

        if not result:
            return jsonify({
                "success": False,
                "error": "Site not found"
            }), 404

        info(f"📄 SITE_DOSSIER generated")

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:

        error(f"SITE_DOSSIER generation failed: {e}")

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# BITCOIN ADDRESS REPORT
# ============================================================

@app.route("/api/reports/bitcoin", methods=["POST"])
def generate_btc_address_report():

    data = request.json or {}

    address_id = data.get("address_id")
    btc_address = data.get("address")

    async def runner():

        global db_pool

        if not db_pool:
            await init_db_pool()

        async with db_pool.acquire() as conn:

            resolved_address_id = await resolve_btc_address_id(
                conn,
                address_id,
                btc_address
            )

            if not resolved_address_id:
                return None

            address = await fetch_btc_address_core(conn, resolved_address_id)

            if not address:
                return None

            transactions = await fetch_btc_transactions(conn, resolved_address_id)

            sites = await fetch_btc_linked_sites(conn, resolved_address_id)

            vendors = await fetch_btc_vendor_artifacts(conn, address["address"])

            edges = await fetch_btc_transaction_edges(conn, address["address"])

        graph_path = os.path.join(
            REPORT_EVIDENCE_DIR,
            f"BTC_GRAPH_{resolved_address_id}.png"
        )

        graph_hash = draw_btc_transaction_graph(
            edges=edges,
            subject=address["address"],
            output_path=graph_path
        )

        graph_artifact = {
            "file": graph_path,
            "sha256": graph_hash,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        report_json = build_btc_address_report({
            "address": address,
            "transactions": [
                {
                    "tx_id": t["tx_id"],
                    "direction": t["direction"],
                    "amount": float(t["amount"]),
                    "timestamp": t["timestamp"].isoformat(),
                    "fan_in": t["fan_in"],
                    "fan_out": t["fan_out"]
                }
                for t in transactions
            ],
            "sites": [
                {
                    "site_id": s["site_id"],
                    "url": s["url"],
                    "first_seen": s["first_seen"].isoformat() if s["first_seen"] else None,
                    "last_seen": s["last_seen"].isoformat() if s["last_seen"] else None
                }
                for s in sites
            ],
            "vendors": [
                {
                    "vendor_id": v["vendor_id"],
                    "vendor_name": v["vendor_name"],
                    "risk_score": v["risk_score"],
                    "artifact_hash": v["artifact_hash"],
                    "first_seen": v["first_seen"].isoformat() if v["first_seen"] else None,
                    "last_seen": v["last_seen"].isoformat() if v["last_seen"] else None
                }
                for v in vendors
            ],
            "graph": graph_artifact
        })

        pdf_path = os.path.join(
            REPORT_EVIDENCE_DIR,
            f"BTC_ADDRESS_{resolved_address_id}.pdf"
        )

        render_btc_address_pdf(
            report=report_json,
            output_path=pdf_path,
            logo_path=REPORT_LOGO_PATH
        )

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        report_hash = hashlib.sha256(pdf_bytes).hexdigest()

        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO Reports (
                    report_id,
                    site_id,
                    report_hash,
                    report_file,
                    generated_at,
                    report_type
                )
                VALUES ($1, NULL, $2, $3, $4, 'BTC ADDRESS REPORT')
                ON CONFLICT (report_id) DO NOTHING;
            """,
            report_hash,
            report_hash,
            pdf_bytes,
            datetime.now(timezone.utc)
            )

        return {
            "report_id": report_hash,
            "report_hash": report_hash,
            "integrity": report_json["integrity"],
            "graph_hash": graph_hash,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    try:

        result = asyncio.run_coroutine_threadsafe(runner(), loop).result()

        if not result:
            return jsonify({
                "success": False,
                "error": "Bitcoin address not found"
            }), 404

        info("📄 BTC_ADDRESS_REPORT generated")

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:

        error(f"BTC_ADDRESS_REPORT generation failed: {e}")

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

    
@app.route("/api/reports/category", methods=["POST"])
def generate_category_intel_report():
    data = request.json or {}
    category = data.get("category")

    if not category:
        return jsonify({"success": False, "error": "category required"}), 400

    async def runner():
        global db_pool
        if not db_pool:
            await init_db_pool()

        async with db_pool.acquire() as conn:
            sites = await fetch_category_sites(conn, category)
            site_ids = [s["site_id"] for s in sites]

            vendors = await fetch_category_vendors(conn, site_ids)
            btc_addresses = await fetch_category_btc_addresses(conn, site_ids)

            btc_list = [b["address"] for b in btc_addresses]
            edges = await fetch_category_btc_edges(conn, btc_list)

        graph_path = os.path.join(
            REPORT_EVIDENCE_DIR,
            f"CATEGORY_BTC_{category}.png"
        )

        graph_hash = draw_btc_transaction_graph(
            edges=edges,
            subject=f"CATEGORY:{category}",
            output_path=graph_path
        )

        report_json = build_category_intel_report({
            "category": category,
            "sites": sites,
            "vendors": vendors,
            "btc_addresses": btc_addresses,
            "edges": edges,
            "graph": {
                "file": graph_path,
                "sha256": graph_hash
            }
        })

        pdf_path = os.path.join(
            REPORT_EVIDENCE_DIR,
            f"CATEGORY_INTEL_{category}.pdf"
        )

        render_category_intel_pdf(
            report=report_json,
            output_path=pdf_path,
            logo_path=REPORT_LOGO_PATH
        )

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        report_hash = hashlib.sha256(pdf_bytes).hexdigest()

        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO Reports (
                    report_id, site_id, report_hash, report_file, generated_at, report_type
                ) VALUES ($1, NULL, $2, $3, $4, 'CATEGORY INTEL')
                ON CONFLICT DO NOTHING;
            """,
            report_hash,
            report_hash,
            pdf_bytes,
            datetime.now(timezone.utc))

        return {
            "report_id": report_hash,
            "report_hash": report_hash,
            "integrity": report_json["integrity"]
        }

    result = asyncio.run_coroutine_threadsafe(runner(), loop).result()
    if not result:
        return jsonify({"success": False, "error": "No data for category"}), 404

    return jsonify({"success": True, "data": result})


@app.route("/api/reports/all", methods=["POST"])
def generate_all_sites_report():

    async def runner():
        global db_pool
        if not db_pool:
            await init_db_pool()

        async with db_pool.acquire() as conn:
            sites = await fetch_all_sites(conn)
            categories = await fetch_site_category_distribution(conn)
            vendors = await fetch_all_vendors(conn)
            btc_addresses = await fetch_all_btc_addresses(conn)
            edges = await fetch_global_btc_edges(conn)

        graph_path = os.path.join(
            REPORT_EVIDENCE_DIR,
            "ALL_SITES_BTC_GRAPH.png"
        )

        graph_hash = draw_btc_transaction_graph(
            edges=edges,
            subject="ALL_SITES",
            output_path=graph_path
        )

        report_json = build_all_sites_report({
            "sites": sites,
            "categories": categories,
            "vendors": vendors,
            "btc_addresses": btc_addresses,
            "edges": edges,
            "graph": {
                "file": graph_path,
                "sha256": graph_hash
            }
        })

        pdf_path = os.path.join(
            REPORT_EVIDENCE_DIR,
            "ALL_SITES_INTELLIGENCE.pdf"
        )

        render_all_sites_pdf(
            report=report_json,
            output_path=pdf_path,
            logo_path=REPORT_LOGO_PATH
        )

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        report_hash = hashlib.sha256(pdf_bytes).hexdigest()

        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO Reports (
                    report_id, site_id, report_hash, report_file, generated_at, report_type
                ) VALUES ($1, NULL, $2, $3, $4, 'ALL SITES')
                ON CONFLICT DO NOTHING;
            """,
            report_hash,
            report_hash,
            pdf_bytes,
            datetime.now(timezone.utc))

        return {
            "report_id": report_hash,
            "report_hash": report_hash,
            "integrity": report_json["integrity"]
        }

    result = asyncio.run_coroutine_threadsafe(runner(), loop).result()

    return jsonify({"success": True, "data": result})


@app.route("/api/reports/vendor", methods=["POST"])
def generate_vendor_profile_report():

    data = request.json or {}

    vendor_id = data.get("vendor_id")
    vendor_name = data.get("vendor_name")

    if not vendor_id and not vendor_name:
        return jsonify({
            "success": False,
            "error": "vendor_id or vendor_name required"
        }), 400


    async def resolve_vendor_id(conn, vendor_id=None, vendor_name=None):

        # If vendor_id provided → use directly
        if vendor_id:
            return vendor_id

        # If vendor_name provided → lookup
        if vendor_name:
            row = await conn.fetchrow("""
                SELECT vendor_id
                FROM Vendors
                WHERE vendor_name ILIKE $1
                LIMIT 1
            """, vendor_name)

            if row:
                return row["vendor_id"]

        return None


    async def runner():

        global db_pool

        if not db_pool:
            await init_db_pool()

        async with db_pool.acquire() as conn:

            # 🔎 Resolve vendor_id from name if needed
            resolved_vendor_id = await resolve_vendor_id(
                conn,
                vendor_id,
                vendor_name
            )

            if not resolved_vendor_id:
                return None

            vendor = await fetch_vendor_core(conn, resolved_vendor_id)

            if not vendor:
                return None

            artifacts = await fetch_vendor_artifacts(conn, resolved_vendor_id)

            sites = await fetch_vendor_sites(conn, resolved_vendor_id)

            btc_addresses = await fetch_vendor_btc_addresses(conn, resolved_vendor_id)

            btc_list = [b["address"] for b in btc_addresses]

            edges = await fetch_vendor_btc_edges(conn, btc_list)

        # -----------------------------
        # Build JSON report
        # -----------------------------

        report_json = build_vendor_profile_report({
            "vendor": vendor,
            "artifacts": artifacts,
            "sites": sites,
            "btc_addresses": btc_addresses,
            "edges": edges
        })


        # -----------------------------
        # Render PDF
        # -----------------------------

        pdf_path = os.path.join(
            REPORT_EVIDENCE_DIR,
            f"VENDOR_PROFILE_{resolved_vendor_id}.pdf"
        )

        render_vendor_profile_pdf(
            report=report_json,
            output_path=pdf_path,
            logo_path=REPORT_LOGO_PATH
        )

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        report_hash = hashlib.sha256(pdf_bytes).hexdigest()


        # -----------------------------
        # Store report
        # -----------------------------

        async with db_pool.acquire() as conn:

            await conn.execute("""
                INSERT INTO Reports (
                    report_id,
                    site_id,
                    report_hash,
                    report_file,
                    generated_at,
                    report_type
                )
                VALUES ($1, NULL, $2, $3, $4, 'VENDOR PROFILE')
                ON CONFLICT DO NOTHING;
            """,
            report_hash,
            report_hash,
            pdf_bytes,
            datetime.now(timezone.utc)
            )


        return {
            "report_id": report_hash,
            "report_hash": report_hash,
            "integrity": report_json["integrity"]
        }


    result = asyncio.run_coroutine_threadsafe(runner(), loop).result()

    if not result:
        return jsonify({
            "success": False,
            "error": "Vendor not found"
        }), 404


    return jsonify({
        "success": True,
        "data": result
    })





@app.route("/api/vendors/overview", methods=["GET"])
def vendors_overview():
    async def fetch():
        global db_pool
        if not db_pool:
            await init_db_pool()

        async with db_pool.acquire() as conn:

            # ---------------- Vendors (list view) ----------------
            vendor_rows = await conn.fetch("""
                SELECT
                    vendor_id,
                    vendor_name,
                    risk_score,
                    first_seen,
                    last_seen
                FROM Vendors
                ORDER BY risk_score DESC, last_seen DESC;
            """)

            # ---------------- Graph nodes ----------------
            node_rows = await conn.fetch("""
                SELECT
                    v.vendor_id,
                    v.vendor_name,
                    v.risk_score,
                    COUNT(DISTINCT va.artifact_value) AS artifact_count
                FROM Vendors v
                LEFT JOIN VendorArtifacts va
                    ON v.vendor_id = va.vendor_id
                GROUP BY v.vendor_id, v.vendor_name, v.risk_score;
            """)

            # ---------------- Graph edges ----------------
            edge_rows = await conn.fetch("""
                SELECT
                    a.vendor_id AS source,
                    b.vendor_id AS target,
                    a.artifact_type,
                    COUNT(*) AS weight
                FROM VendorArtifacts a
                JOIN VendorArtifacts b
                  ON a.artifact_type = b.artifact_type
                 AND a.artifact_value = b.artifact_value
                 AND a.vendor_id < b.vendor_id
                WHERE a.artifact_type IN ('pgp', 'email', 'xmr')
                GROUP BY source, target, a.artifact_type;
            """)

        return vendor_rows, node_rows, edge_rows

    try:
        vendor_rows, node_rows, edge_rows = (
            asyncio.run_coroutine_threadsafe(fetch(), loop).result()
        )

        # -------- Vendors list --------
        vendors = [
            {
                "id": r["vendor_id"],
                "name": r["vendor_name"],
                "riskScore": r["risk_score"],
                "firstSeen": r["first_seen"].isoformat() if r["first_seen"] else None,
                "lastSeen": r["last_seen"].isoformat() if r["last_seen"] else None
            }
            for r in vendor_rows
        ]

        # -------- Graph nodes --------
        nodes = []
        for r in node_rows:
            risk = r["risk_score"] or 0
            nodes.append({
                "id": r["vendor_id"],
                "name": r["vendor_name"],  # ✅ single source of truth
                "risk": risk,
                "size": min(30, 8 + (r["artifact_count"] or 0) * 2),
                "color": (
                    "#ef4444" if risk >= 80 else
                    "#f59e0b" if risk >= 50 else
                    "#10b981"
                )
            })

        # -------- Graph links --------
        links = [
            {
                "source": e["source"],
                "target": e["target"],
                "weight": e["weight"],
                "type": e["artifact_type"]
            }
            for e in edge_rows
        ]

        return jsonify({
            "success": True,
            "data": {
                "vendors": vendors,
                "network": {
                    "nodes": nodes,
                    "links": links
                }
            }
        })

    except Exception as e:
        error(f"/api/vendors/overview error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500





# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"success": False, "error": "Server error"}), 500




# ==================== ENTRYPOINT ====================

if __name__ == "__main__":
    info("=" * 60)
    info("🌐  OnionTraceX Flask Backend API")
    info("=" * 60)
    asyncio.run_coroutine_threadsafe(init_db_pool(), loop)
    initialize_mock_data()
    info(f"Sites: {len(mock_data['sites'])} | Vendors: {len(mock_data['vendors'])} | Wallets: {len(mock_data['bitcoins'])}")
    info("Running at: http://localhost:5000")
    info("=" * 60)



    # ✅ NEW — disables auto-reload but keeps logs
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

