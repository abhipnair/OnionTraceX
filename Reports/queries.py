# Backend/Reports/queries.py

from typing import Dict, List, Tuple, Optional
import asyncpg


# ============================================================
# SITE DOSSIER QUERIES
# ============================================================

async def fetch_site_core(
    conn: asyncpg.Connection,
    site_id: str
) -> Optional[asyncpg.Record]:
    """
    Fetch core site information.
    """
    return await conn.fetchrow("""
        SELECT
            site_id,
            url,
            source,
            keyword,
            current_status,
            first_seen,
            last_seen
        FROM OnionSites
        WHERE site_id = $1;
    """, site_id)


async def fetch_site_liveness(
    conn: asyncpg.Connection,
    site_id: str
) -> List[asyncpg.Record]:
    """
    Fetch full liveness history for the site.
    """
    return await conn.fetch("""
        SELECT
            status,
            response_time,
            check_time
        FROM SiteLiveness
        WHERE site_id = $1
        ORDER BY check_time ASC;
    """, site_id)


async def fetch_site_pages(
    conn: asyncpg.Connection,
    site_id: str
) -> List[asyncpg.Record]:
    """
    Fetch crawled pages for the site.
    """
    return await conn.fetch("""
        SELECT
            page_id,
            url,
            html_hash,
            crawl_date
        FROM Pages
        WHERE site_id = $1
        ORDER BY crawl_date DESC;
    """, site_id)


async def fetch_page_metadata(
    conn: asyncpg.Connection,
    page_ids: List[str]
) -> Dict[str, asyncpg.Record]:
    """
    Fetch metadata for pages and return a page_id → metadata map.
    """
    if not page_ids:
        return {}

    rows = await conn.fetch("""
        SELECT
            page_id,
            title,
            meta_tags,
            emails,
            pgp_keys,
            language
        FROM Metadata
        WHERE page_id = ANY($1);
    """, page_ids)

    return {row["page_id"]: row for row in rows}


async def fetch_site_bitcoin_addresses(
    conn: asyncpg.Connection,
    site_id: str
) -> List[asyncpg.Record]:
    """
    Fetch Bitcoin addresses detected on this site.
    """
    return await conn.fetch("""
        SELECT
            address_id,
            address,
            page_id,
            valid,
            detected_at,
            tx_analyzed
        FROM BitcoinAddresses
        WHERE site_id = $1
        ORDER BY detected_at ASC;
    """, site_id)


async def fetch_site_vendor_artifacts(
    conn: asyncpg.Connection,
    site_id: str
) -> List[asyncpg.Record]:
    """
    Fetch vendor artifacts linked to this site.
    """
    return await conn.fetch("""
        SELECT
            va.artifact_id,
            va.artifact_type,
            va.artifact_value,
            va.artifact_hash,
            va.confidence,
            va.first_seen,
            va.last_seen,
            v.vendor_id,
            v.risk_score
        FROM VendorArtifacts va
        LEFT JOIN Vendors v
            ON va.vendor_id = v.vendor_id
        WHERE va.site_id = $1
        ORDER BY va.first_seen ASC;
    """, site_id)


async def fetch_site_classification(
    conn: asyncpg.Connection,
    page_ids: List[str]
) -> List[asyncpg.Record]:
    """
    Fetch AI/NLP classification results for pages.
    """
    if not page_ids:
        return []

    return await conn.fetch("""
        SELECT
            page_id,
            category,
            confidence
        FROM Classification
        WHERE page_id = ANY($1);
    """, page_ids)


# ============================================================
# AGGREGATED FETCH (ENTRY POINT FOR SITE DOSSIER)
# ============================================================

async def fetch_site_dossier(
    pool: asyncpg.Pool,
    site_id: str
) -> Dict[str, object]:
    """
    High-level fetcher for full SITE_DOSSIER data.
    """
    async with pool.acquire() as conn:

        site = await fetch_site_core(conn, site_id)
        if not site:
            return {}

        liveness = await fetch_site_liveness(conn, site_id)
        pages = await fetch_site_pages(conn, site_id)

        page_ids = [p["page_id"] for p in pages]

        metadata = await fetch_page_metadata(conn, page_ids)
        btc_addresses = await fetch_site_bitcoin_addresses(conn, site_id)
        vendor_artifacts = await fetch_site_vendor_artifacts(conn, site_id)
        classifications = await fetch_site_classification(conn, page_ids)

        return {
            "site": site,
            "liveness": liveness,
            "pages": pages,
            "metadata": metadata,
            "bitcoin_addresses": btc_addresses,
            "vendor_artifacts": vendor_artifacts,
            "classifications": classifications
        }



# ============================================================
# BTC ADDRESS REPORT QUERIES (INTEGRATED)
# ============================================================

async def fetch_btc_address_core(conn, address_id):
    return await conn.fetchrow("""
        SELECT
            address_id,
            address,
            valid,
            detected_at,
            site_id,
            page_id
        FROM BitcoinAddresses
        WHERE address_id = $1;
    """, address_id)


async def fetch_btc_transactions(conn, address_id):
    return await conn.fetch("""
        SELECT
            tx_id,
            direction,
            amount,
            timestamp,
            fan_in,
            fan_out
        FROM Transactions
        WHERE address_id = $1
        ORDER BY timestamp ASC;
    """, address_id)


async def fetch_btc_linked_sites(conn, address_id):
    return await conn.fetch("""
        SELECT DISTINCT
            s.site_id,
            s.url,
            s.keyword,
            s.first_seen,
            s.last_seen
        FROM BitcoinAddresses b
        JOIN OnionSites s ON b.site_id = s.site_id
        WHERE b.address_id = $1;
    """, address_id)


async def fetch_btc_vendor_artifacts(conn, btc_address):
    return await conn.fetch("""
        SELECT
            va.vendor_id,
            v.risk_score,
            va.artifact_hash,
            va.first_seen,
            va.last_seen
        FROM VendorArtifacts va
        JOIN Vendors v ON va.vendor_id = v.vendor_id
        WHERE va.artifact_type = 'btc'
          AND va.artifact_value = $1;
    """, btc_address)


async def fetch_btc_transaction_edges(conn, btc_address):
    return await conn.fetch("""
        SELECT
            e.from_address,
            e.to_address,
            e.amount,
            COALESCE(t.fan_in, 0) AS fan_in,
            COALESCE(t.fan_out, 0) AS fan_out
        FROM BitcoinTransactionEdges e
        LEFT JOIN BitcoinAddresses b ON b.address = e.from_address
        LEFT JOIN Transactions t ON t.address_id = b.address_id
        WHERE e.from_address = $1 OR e.to_address = $1;
    """, btc_address)



# ============================================================
# VENDOR PROFILE (INTEGRATED)
# ============================================================


async def fetch_vendor_core(conn, vendor_id):
    return await conn.fetchrow("""
        SELECT
            vendor_id,
            risk_score,
            first_seen,
            last_seen
        FROM Vendors
        WHERE vendor_id = $1;
    """, vendor_id)


async def fetch_vendor_artifacts(conn, vendor_id):
    return await conn.fetch("""
        SELECT
            artifact_type,
            artifact_value,
            artifact_hash,
            confidence,
            page_id,
            site_id,
            first_seen,
            last_seen
        FROM VendorArtifacts
        WHERE vendor_id = $1
        ORDER BY first_seen ASC;
    """, vendor_id)

async def fetch_vendor_sites(conn, vendor_id):
    return await conn.fetch("""
        SELECT DISTINCT
            s.site_id,
            s.url,
            s.keyword,
            s.first_seen,
            s.last_seen
        FROM VendorArtifacts va
        JOIN OnionSites s ON va.site_id = s.site_id
        WHERE va.vendor_id = $1;
    """, vendor_id)

async def fetch_vendor_btc_addresses(conn, vendor_id):
    return await conn.fetch("""
        SELECT
            b.address_id,
            b.address,
            b.valid,
            b.detected_at
        FROM VendorArtifacts va
        JOIN BitcoinAddresses b
            ON va.artifact_value = b.address
        WHERE va.vendor_id = $1
          AND va.artifact_type = 'btc';
    """, vendor_id)

async def fetch_vendor_btc_edges(conn, btc_addresses):
    if not btc_addresses:
        return []

    return await conn.fetch("""
        SELECT
            e.from_address,
            e.to_address,
            e.amount,
            t.fan_in,
            t.fan_out
        FROM BitcoinTransactionEdges e
        LEFT JOIN BitcoinAddresses b
            ON b.address = e.from_address
        LEFT JOIN Transactions t
            ON t.address_id = b.address_id
        WHERE e.from_address = ANY($1)
           OR e.to_address = ANY($1);
    """, btc_addresses)



# ============================================================
# CATEGORY INTEL(INTEGRATED)
# ============================================================

async def fetch_category_sites(conn, category):
    return await conn.fetch("""
        SELECT DISTINCT
            s.site_id,
            s.url,
            s.keyword,
            s.current_status,
            s.first_seen,
            s.last_seen
        FROM OnionSites s
        LEFT JOIN Pages p ON s.site_id = p.site_id
        LEFT JOIN Classification c ON p.page_id = c.page_id
        WHERE LOWER(s.keyword) = LOWER($1)
           OR LOWER(c.category) = LOWER($1);
    """, category)

async def fetch_category_vendors(conn, site_ids):
    if not site_ids:
        return []

    return await conn.fetch("""
        SELECT DISTINCT
            v.vendor_id,
            v.risk_score,
            v.first_seen,
            v.last_seen
        FROM VendorArtifacts va
        JOIN Vendors v ON va.vendor_id = v.vendor_id
        WHERE va.site_id = ANY($1);
    """, site_ids)

async def fetch_category_btc_addresses(conn, site_ids):
    if not site_ids:
        return []

    return await conn.fetch("""
        SELECT
            address_id,
            address,
            site_id,
            detected_at,
            valid
        FROM BitcoinAddresses
        WHERE site_id = ANY($1);
    """, site_ids)

async def fetch_category_btc_edges(conn, addresses):
    if not addresses:
        return []

    return await conn.fetch("""
        SELECT
            e.from_address,
            e.to_address,
            SUM(e.amount) AS amount,
            MAX(t.fan_in) AS fan_in,
            MAX(t.fan_out) AS fan_out
        FROM BitcoinTransactionEdges e
        LEFT JOIN BitcoinAddresses b ON b.address = e.from_address
        LEFT JOIN Transactions t ON t.address_id = b.address_id
        WHERE e.from_address = ANY($1)
           OR e.to_address = ANY($1)
        GROUP BY e.from_address, e.to_address
        HAVING SUM(e.amount) > 0;
    """, addresses)





# ============================================================
# ALL SITES (INTEGRATED)
# ============================================================

async def fetch_all_sites(conn):
    return await conn.fetch("""
        SELECT
            s.site_id,
            s.url,
            s.keyword,
            s.current_status,
            s.first_seen,
            s.last_seen,
            COUNT(DISTINCT va.vendor_id) AS vendor_count,
            COUNT(DISTINCT b.address_id) AS btc_count
        FROM OnionSites s
        LEFT JOIN VendorArtifacts va ON va.site_id = s.site_id
        LEFT JOIN BitcoinAddresses b ON b.site_id = s.site_id
        GROUP BY s.site_id
        ORDER BY s.last_seen DESC;
    """)

async def fetch_site_category_distribution(conn):
    return await conn.fetch("""
        SELECT
            COALESCE(NULLIF(TRIM(keyword), ''), 'Other') AS category,
            COUNT(*) AS count
        FROM OnionSites
        GROUP BY category
        ORDER BY count DESC;
    """)

async def fetch_all_vendors(conn):
    return await conn.fetch("""
        SELECT
        v.vendor_id,
        v.risk_score,
        COUNT(DISTINCT va.site_id) AS site_count,
        COUNT(DISTINCT b.address_id) AS btc_count,
        v.first_seen,
        v.last_seen
    FROM Vendors v
    LEFT JOIN VendorArtifacts va ON va.vendor_id = v.vendor_id
    LEFT JOIN BitcoinAddresses b ON va.artifact_value = b.address
    GROUP BY v.vendor_id
    ORDER BY v.risk_score DESC;

    """)

async def fetch_all_btc_addresses(conn):
    return await conn.fetch("""
        SELECT
            address_id,
            address,
            site_id,
            detected_at,
            valid
        FROM BitcoinAddresses;
    """)

async def fetch_global_btc_edges(conn):
    return await conn.fetch("""
        SELECT
            e.from_address,
            e.to_address,
            SUM(e.amount) AS amount,
            MAX(t.fan_in) AS fan_in,
            MAX(t.fan_out) AS fan_out
        FROM BitcoinTransactionEdges e
        LEFT JOIN BitcoinAddresses b ON b.address = e.from_address
        LEFT JOIN Transactions t ON t.address_id = b.address_id
        GROUP BY e.from_address, e.to_address
        HAVING SUM(e.amount) > 0
        LIMIT 1000;
    """)


