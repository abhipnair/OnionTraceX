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
from Crawler.linkmanager import LinkManager
from Crawler.seed import SeedCollector
from Crawler.unified_crawler import UnifiedCrawler
from Essentials.configs import *
from datetime import datetime




app = Flask(__name__)
CORS(app)

# ==================== CONFIGURATION ====================
CONFIG = {
    'MAX_PAGE_SIZE': 100,
    'DEFAULT_PAGE_SIZE': 50
}

# ==================== PLACEHOLDER DB CONNECTION ====================
conn = None  # Placeholder for actual DB connection (e.g., Mongo, Postgres)

import threading

# ==================== GLOBAL STATE ====================
crawler_task = None
crawler_instance = None
crawler_status = "idle"
crawler_progress = 0
crawler_message = ""

# Create a dedicated async loop in a background thread
loop = asyncio.new_event_loop()


def run_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


threading.Thread(target=run_background_loop, args=(loop,), daemon=True).start()


# ==================== ASYNC CRAWLER CORE ====================
async def run_crawler(keywords: list[str], seed_depth: int, pages: int, crawl_depth: int, polite_delay: float):
    global crawler_status, crawler_progress, crawler_message, crawler_instance

    try:
        crawler_status = "starting"
        crawler_message = "Initializing crawler components..."
        crawler_progress = 5

        pool = await asyncpg.create_pool(**DB_CONFIG)
        link_manager = LinkManager(pool=pool)

        # 1️⃣ Seed collection phase
        if keywords:
            crawler_message = f"Collecting seeds for: {', '.join(keywords)}"
            seed = SeedCollector(link_manager=link_manager, max_depth=seed_depth, max_pages=pages)
            for kw in keywords:
                await seed.collect_from_keywords(kw)
            crawler_progress = 30

        # 2️⃣ Crawler start
        crawler_status = "running"
        crawler_message = "Launching unified crawler..."
        crawler_progress = 50

        crawler_instance = UnifiedCrawler(link_manager=link_manager, max_depth=crawl_depth, polite_delay=polite_delay)
        await crawler_instance.start()

        crawler_status = "completed"
        crawler_message = "Crawler finished successfully!"
        crawler_progress = 100

        await pool.close()

    except asyncio.CancelledError:
        crawler_status = "stopped"
        crawler_message = "Crawler manually stopped."
        crawler_progress = 0
    except Exception as e:
        crawler_status = "error"
        crawler_message = f"Error: {e}"
        crawler_progress = 0
        print(f"[CRAWLER ERROR] {e}")


# ==================== API ROUTES ====================
@app.route("/api/crawler/start", methods=["POST"])
def start_crawler():
    global crawler_task, crawler_status, crawler_progress, crawler_message

    # Prevent multiple concurrent runs
    if crawler_task and not crawler_task.done():
        return jsonify({"status": "error", "message": "Crawler already running"}), 400

    data = request.json or {}
    keywords_field = data.get("keywords", [])
    if isinstance(keywords_field, list):
        keywords = [kw.strip() for kw in keywords_field if kw.strip()]
    else:
        keywords = [kw.strip() for kw in keywords_field.split(",") if kw.strip()]

    seed_depth = int(data.get("seed_depth", 2))
    pages = int(data.get("pages", 5))
    crawl_depth = int(data.get("crawl_depth", 2))
    polite_delay = float(data.get("polite_delay", 2.0))

    crawler_message = "Crawler starting..."
    crawler_status = "starting"
    crawler_progress = 1

    crawler_task = asyncio.run_coroutine_threadsafe(
        run_crawler(keywords, seed_depth, pages, crawl_depth, polite_delay), loop
    )

    return jsonify({"status": "success", "message": "Crawler started"})


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

def connect_db():
    """Placeholder function for future DB connection"""
    global conn
    conn = {"status": "connected", "engine": "mock"}
    print("✅ Mock database connection established.")
    return conn

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
    print("✅ Mock data initialized.")


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
        pool = await asyncpg.create_pool(**DB_CONFIG)
        async with pool.acquire() as conn:
            # Total count
            total = await conn.fetchval('SELECT COUNT(*) FROM "onionsites";')
            # Count by status
            alive = await conn.fetchval('SELECT COUNT(*) FROM "onionsites" WHERE LOWER(current_status) = LOWER($1);', 'Alive')
            dead = await conn.fetchval('SELECT COUNT(*) FROM "onionsites" WHERE LOWER(current_status) = LOWER($1);', 'Dead')
            timeout = await conn.fetchval('SELECT COUNT(*) FROM "onionsites" WHERE LOWER(current_status) = LOWER($1);', 'Timeout')
        await pool.close()
        return total, alive, dead, timeout

    try:
        total, alive, dead, timeout = asyncio.run(fetch_stats())

        # Prevent division by zero
        if total == 0:
            alive_percent = dead_percent = timeout_percent = 0.0
        else:
            alive_percent = round((alive / total) * 100, 1)
            dead_percent = round((dead / total) * 100, 1)
            timeout_percent = round((timeout / total) * 100, 1)

        # Response JSON — structure matches your existing frontend
        return jsonify({
            "success": True,
            "data": {
                "totalSites": total,
                "alivePercent": alive_percent,
                "deadPercent": dead_percent,
                "timeoutPercent": timeout_percent,
                "activeCrawlers": 1,
                "avgCrawlTime": round(random.uniform(2, 8), 2),
                "totalVendors": 0,   # keep mock for now
                "totalWallets": 0   # keep mock for now
            }
        })

    except Exception as e:
        print("❌ /api/stats DB error:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/liveness", methods=["GET"])
def _get_liveness():
    days = int(request.args.get("days", 30))

    async def fetch_liveness():
        pool = await asyncpg.create_pool(**DB_CONFIG)
        async with pool.acquire() as conn:
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
        await pool.close()
        return rows

    try:
        rows = asyncio.run(fetch_liveness())
        data = [
            {"date": str(r["date"]), "alive": r["alive"], "dead": r["dead"], "timeout": r["timeout"]}
            for r in rows
        ]
        return jsonify({"success": True, "data": data})
    except Exception as e:
        print("❌ /api/liveness DB error:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/categories", methods=["GET"])
def _get_categories():
    async def fetch_categories():
        pool = await asyncpg.create_pool(**DB_CONFIG)
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    COALESCE(NULLIF(TRIM(keyword), ''), 'Others') AS name,
                    COUNT(*) AS value
                FROM onionsites
                GROUP BY name
                ORDER BY value DESC;
            """)
        await pool.close()
        return rows

    try:
        rows = asyncio.run(fetch_categories())
        palette = ["#06b6d4", "#8b5cf6", "#ef4444", "#f59e0b", "#10b981", "#6366f1", "#3b82f6", "#a855f7"]
        
        # Transform to frontend-ready structure
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
        print("❌ /api/categories DB error:", e)
        return jsonify({"success": False, "error": str(e)}), 500



@app.route("/api/keywords", methods=["GET"])
def _get_keywords():
    async def fetch_keywords():
        pool = await asyncpg.create_pool(**DB_CONFIG)
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    COALESCE(NULLIF(TRIM(keyword), ''), 'Others') AS keyword,
                    COUNT(*) AS discovered
                FROM onionsites
                GROUP BY keyword
                ORDER BY discovered DESC
                LIMIT 20;
            """)
        await pool.close()
        return rows

    try:
        rows = asyncio.run(fetch_keywords())
        
        # Transform query results to frontend-compatible format
        data = [
            {
                "keyword": r["keyword"],
                "discovered": r["discovered"]
            }
            for r in rows
        ]
        
        return jsonify({"success": True, "data": data})
    
    except Exception as e:
        print("❌ /api/keywords DB error:", e)
        return jsonify({"success": False, "error": str(e)}), 500




@app.route("/api/sites")
def sites():
    async def fetch_sites(search, status, keyword, start_date, end_date, page, size):
        pool = await asyncpg.create_pool(**DB_CONFIG)
        async with pool.acquire() as conn:
            query = """
                SELECT site_id AS id, url, keyword, current_status AS status,
                       first_seen, last_seen, source
                FROM onionsites
                WHERE ($1 = '' OR LOWER(url) LIKE LOWER('%' || $1 || '%'))
                  AND ($2 = 'all' OR LOWER(current_status) = LOWER($2))
                  AND ($3 = '' OR LOWER(keyword) = LOWER($3))
                  AND ($4::timestamp IS NULL OR first_seen >= $4::timestamp)
                  AND ($5::timestamp IS NULL OR last_seen <= $5::timestamp)
                ORDER BY last_seen DESC
                LIMIT $6 OFFSET $7;
            """
            offset = (page - 1) * size

            # Convert dates safely
            start_dt = None
            end_dt = None
            try:
                if start_date:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                if end_date:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                start_dt = end_dt = None

            rows = await conn.fetch(query, search, status, keyword, start_dt, end_dt, size, offset)
            total = await conn.fetchval("SELECT COUNT(*) FROM onionsites;")
        await pool.close()
        return rows, total

    try:
        search = request.args.get("search", "").strip()
        status = request.args.get("status", "all").strip()
        keyword = request.args.get("keyword", "").strip()
        start_date = request.args.get("start_date", "").strip()
        end_date = request.args.get("end_date", "").strip()
        page = int(request.args.get("page", 1))
        size = int(request.args.get("page_size", 25))

        rows, total = asyncio.run(fetch_sites(search, status, keyword, start_date, end_date, page, size))

        data = [
            {
                "id": r["id"],
                "url": r["url"],
                "category": r["keyword"] or "Other",
                "status": r["status"],
                "firstSeen": r["first_seen"].strftime("%Y-%m-%d %H:%M") if r["first_seen"] else None,
                "lastSeen": r["last_seen"].strftime("%Y-%m-%d %H:%M") if r["last_seen"] else None,
                "source": r["source"],
            }
            for r in rows
        ]

        return jsonify({
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "page_size": size,
                "total": total
            }
        })

    except Exception as e:
        print("❌ /api/sites DB error:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/site/<site_id>", methods=["GET"])
def get_site_details(site_id):
    async def fetch_site(site_id):
        pool = await asyncpg.create_pool(**DB_CONFIG)
        async with pool.acquire() as conn:
            query = """
                SELECT 
                    site_id,
                    url,
                    source,
                    keyword,
                    current_status AS status,
                    first_seen,
                    last_seen
                FROM onionsites
                WHERE site_id = $1;
            """
            result = await conn.fetchrow(query, site_id)
        await pool.close()
        return result

    try:
        row = asyncio.run(fetch_site(site_id))
        if not row:
            return jsonify({"success": False, "error": "Site not found"}), 404

        data = {
            "id": row["site_id"],
            "url": row["url"],
            "source": row["source"],
            "category": row["keyword"] or "Other",
            "status": row["status"],
            "firstSeen": row["first_seen"].strftime("%Y-%m-%d %H:%M") if row["first_seen"] else None,
            "lastSeen": row["last_seen"].strftime("%Y-%m-%d %H:%M") if row["last_seen"] else None,
            # Future-proof placeholder for metadata or page analysis
            "title": None,
            "metadata": {
                "ssl_cert": "N/A",
                "language": "N/A",
                "indexed_pages": 0,
                "server": "N/A"
            }
        }

        return jsonify({"success": True, "data": data})

    except Exception as e:
        print(f"❌ /api/site/{site_id} error:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/vendors")
def vendors():
    page = get_int_param(request.args.get("page"), 1)
    size = get_int_param(request.args.get("page_size"), CONFIG['DEFAULT_PAGE_SIZE'])
    return jsonify({
        "success": True,
        "data": paginate(mock_data['vendors'], page, size),
        "pagination": {"page": page, "total": len(mock_data['vendors'])}
    })


@app.route("/api/bitcoin/wallets")
def btc_wallets():
    page = get_int_param(request.args.get("page"), 1)
    size = get_int_param(request.args.get("page_size"), CONFIG['DEFAULT_PAGE_SIZE'])
    data = paginate(mock_data['bitcoins'], page, size)
    return jsonify({
        "success": True,
        "data": {
            "stats": {
                "totalWallets": len(mock_data['bitcoins']),
                "totalTransactions": sum(w['transactionCount'] for w in mock_data['bitcoins']),
                "suspectedMixers": sum(1 for w in mock_data['bitcoins'] if w['isMixer']),
                "totalVolume": round(sum(w['balance'] for w in mock_data['bitcoins']), 2),
                "averageBalance": round(sum(w['balance'] for w in mock_data['bitcoins']) / len(mock_data['bitcoins']), 4)
            },
            "wallets": data
        }
    })


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


@app.route('/api/liveness', methods=['GET'])
def get_liveness():
    days = get_int_param(request.args.get('days'), 30, 1, 365)
    data = []

    base_alive = 800
    base_dead = 200
    base_timeout = 50

    for i in range(days):
        date = (datetime.now() - timedelta(days=days - i)).strftime('%Y-%m-%d')
        trend = i * 2
        data.append({
            'date': date,
            'alive': max(600, base_alive + trend + random.randint(-50, 50)),
            'dead': max(100, base_dead - trend + random.randint(-30, 30)),
            'timeout': base_timeout + random.randint(-20, 20)
        })

    return jsonify({'success': True, 'data': data})


@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = [
        {'name': 'Marketplace', 'value': 42, 'color': '#06b6d4'},
        {'name': 'Forum', 'value': 28, 'color': '#8b5cf6'},
        {'name': 'Illegal Content', 'value': 18, 'color': '#ef4444'},
        {'name': 'Information Hub', 'value': 8, 'color': '#f59e0b'},
        {'name': 'Other', 'value': 4, 'color': '#6b7280'}
    ]
    return jsonify({'success': True, 'data': categories})

@app.route('/api/keywords', methods=['GET'])
def get_keywords():
    keywords = [
        {'keyword': 'marketplace', 'discovered': 3452},
        {'keyword': 'vendor', 'discovered': 2876},
        {'keyword': 'forum', 'discovered': 2134},
        {'keyword': 'trading', 'discovered': 1987},
        {'keyword': 'shop', 'discovered': 1654},
        {'keyword': 'exchange', 'discovered': 1432},
        {'keyword': 'community', 'discovered': 987},
        {'keyword': 'crypto', 'discovered': 876}
    ]
    return jsonify({'success': True, 'data': keywords})

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


@app.route('/api/vendors/network', methods=['GET'])
def get_vendor_network():
    """Return vendor relationship network graph"""

    # Limit to 30 vendors for clarity
    vendors = mock_data.get('vendors', [])[:30]

    # Build node list
    nodes = [
        {
            'id': v['id'],
            'name': v.get('alias', v['id']),
            'status': v.get('status', 'unknown'),
            'reputation': v.get('reputation', 0),
            'size': max(3, (v.get('totalSales', 1) / 100)),  # Ensure visible node size
            'color': '#06b6d4' if v.get('status') == 'active' else '#9ca3af'
        }
        for v in vendors
    ]

    # Generate relationship links (edges)
    links = []
    for i, v1 in enumerate(vendors):
        for v2 in vendors[i + 1:]:
            shared = set(v1.get('marketplaces', [])) & set(v2.get('marketplaces', []))
            if shared or random.random() < 0.12:  # 12% random links
                links.append({
                    'source': v1['id'],
                    'target': v2['id'],
                    'weight': len(shared) if shared else 1,
                    'type': 'shared_marketplace' if shared else 'connection',
                    'color': '#8b5cf6' if shared else '#10b981'
                })

    # Final JSON response
    return jsonify({
        'success': True,
        'data': {
            'nodes': nodes,
            'links': links,
            'nodeCount': len(nodes),
            'linkCount': len(links)
        }
    })


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"success": False, "error": "Server error"}), 500




# ==================== ENTRYPOINT ====================

if __name__ == "__main__":
    print("=" * 60)
    print("🌐  OnionTraceX Flask Backend API")
    print("=" * 60)
    connect_db()
    initialize_mock_data()
    print(f"Sites: {len(mock_data['sites'])} | Vendors: {len(mock_data['vendors'])} | Wallets: {len(mock_data['bitcoins'])}")
    print("Running at: http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
