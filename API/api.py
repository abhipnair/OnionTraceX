# ======================================================
#  OnionTraceX Backend API
#  Version: 1.2 (Optimized for Frontend Integration)
# ======================================================

from flask import Flask, jsonify, request, make_response
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
        return jsonify({"status": "error", "message": "Crawler already running"}), 400

    keywords = []
    manual_urls = []

    # --------------------------------------------------
    # HANDLE INPUT (JSON or FORM)
    # --------------------------------------------------
    if request.content_type and request.content_type.startswith("multipart/form-data"):
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

    # Deduplicate
    keywords = list(set(keywords))
    manual_urls = list(set(manual_urls))

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------
    if not keywords and not manual_urls:
        return jsonify({
            "status": "error",
            "message": "Provide keywords OR manual .onion URLs"
        }), 400

    # --------------------------------------------------
    # PARAMETERS
    # --------------------------------------------------
    def get_param(key, default, cast_func):
        return cast_func(
            request.form.get(key)
            or (request.json.get(key) if request.is_json else None)
            or default
        )

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
        f"Starting crawler | keywords={len(keywords)} | manual_urls={len(manual_urls)}"
    )

    return jsonify({
        "status": "success",
        "message": f"Crawler started ({len(keywords)} keywords, {len(manual_urls)} manual URLs)"
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

        # ---------------- CURSOR PARSING (CRITICAL FIX) ----------------

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



@app.route("/api/system/health")
def system_health():
    return jsonify({
        "success": True,
        "data": {
            "database": "connected",
            "cpuUsage": round(random.uniform(10, 70), 1),
            "memoryUsage": round(random.uniform(30, 90), 1),
            "uptime": f"{random.randint(10, 120)} days"
        }
    })


@app.route("/api/system/info")
def system_info():
    """Provides backend metadata for frontend dashboard"""
    return jsonify({
        "success": True,
        "data": {
            "backend": "OnionTraceX Flask API",
            "version": "1.2",
            "mockMode": True,
            "database": conn,
            "apiEndpoints": [
                "/api/stats", "/api/sites", "/api/vendors",
                "/api/bitcoin/wallets", "/api/system/health"
            ]
        }
    })



@app.route('/api/reports', methods=['GET'])
def get_reports():
    """Return recent report summaries"""
    reports = []
    for i in range(10):
        days_ago = i * 7
        reports.append({
            'id': f'report_{i:05d}',
            'generatedAt': (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S'),
            'dateRange': f'Week of {(datetime.now() - timedelta(days=days_ago + 7)).strftime("%Y-%m-%d")}',
            'sitesCount': random.randint(500, 8000),
            'fileSize': f'{random.randint(5, 150)} MB',
            'status': random.choice(['completed', 'processing', 'failed']),
            'vendorCount': random.randint(50, 500),
            'bitcoinAnalyzed': random.randint(100, 1000)
        })

    return jsonify({
        'success': True,
        'data': reports,
        'pagination': {
            'page': 1,
            'page_size': len(reports),
            'total': len(reports),
            'pages': 1
        }
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

