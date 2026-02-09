# Backend/Reports/assembler.py

from datetime import datetime, timezone
from typing import Dict, Any
import hashlib

from Reports.crypto.hashes import canonical_json_hash
from Reports.crypto.signer import sign_hash, get_public_key_fingerprint

SCHEMA_VERSION = "1.0"

FAN_IN_THRESHOLD = 10
FAN_OUT_THRESHOLD = 10





# ============================================================
# UTILS
# ============================================================

def _iso(dt):
    if not dt:
        return None
    if isinstance(dt, str):
        return dt
    if dt.tzinfo:
        return dt.astimezone(timezone.utc).isoformat()
    return dt.replace(tzinfo=timezone.utc).isoformat()


def _record_to_dict(row):
    """
    Convert asyncpg.Record → JSON-safe dict
    (datetimes → ISO-8601 strings)
    """
    if row is None:
        return None

    out = {}
    for k, v in dict(row).items():
        if isinstance(v, datetime):
            out[k] = _iso(v)
        else:
            out[k] = v
    return out



# ============================================================
# MIXER HEURISTIC (DERIVED, NOT DB FLAG)
# ============================================================

def infer_mixer_from_fan_metrics(transactions):
    evidence = []

    for tx in transactions:
        fan_in = tx.get("fan_in") or 0
        fan_out = tx.get("fan_out") or 0

        if fan_in >= FAN_IN_THRESHOLD:
            evidence.append({
                "tx_id": tx.get("tx_id"),
                "type": "high_fan_in",
                "value": tx["fan_in"]
            })

        if fan_out >= FAN_OUT_THRESHOLD:
            evidence.append({
                "tx_id": tx["tx_id"],
                "type": "high_fan_out",
                "value": tx["fan_out"]
            })

    return evidence


# ============================================================
# SITE DOSSIER
# ============================================================

def build_site_dossier(raw: Dict[str, Any]) -> Dict[str, Any]:
    site = raw["site"]
    pages = raw["pages"]
    metadata_map = raw["metadata"]
    btc_rows = raw["bitcoin_addresses"]
    vendor_rows = raw["vendor_artifacts"]

    # ---------------- SITE TITLE ----------------
    site_title = None
    for p in pages:
        meta = metadata_map.get(p["page_id"])
        if meta and meta["title"]:
            site_title = meta["title"]
            break

    # ---------------- PAGES ----------------
    pages_out = []
    for p in pages:
        meta = metadata_map.get(p["page_id"])
        pages_out.append({
            "page_id": p["page_id"],
            "url": p["url"],
            "html_hash": p["html_hash"],
            "crawl_date": _iso(p["crawl_date"]),
            "metadata": {
                "title": meta["title"] if meta else None,
                "meta_tags": meta["meta_tags"] if meta else {},
                "language": meta["language"] if meta else None,
                "emails": meta["emails"] if meta and meta["emails"] else [],
                "pgp_keys": meta["pgp_keys"] if meta and meta["pgp_keys"] else []
            }
        })

    # ---------------- BITCOIN ARTIFACTS ----------------
    btc_out = [{
        "artifact_type": "btc",
        "artifact_value": b["address"],
        "artifact_hash": hashlib.sha256(b["address"].encode()).hexdigest(),
        "valid": bool(b["valid"]),
        "first_seen": _iso(b["detected_at"]),
        "tx_analyzed": bool(b.get("tx_analyzed", False)),
        "source_page": b["page_id"]
    } for b in btc_rows]

    # ---------------- VENDOR ARTIFACTS ----------------
    vendor_out = [{
        "artifact_type": v["artifact_type"],
        "artifact_value": v["artifact_value"],
        "artifact_hash": v["artifact_hash"],
        "confidence": v["confidence"],
        "vendor_id": v["vendor_id"],
        "risk_score": v["risk_score"],
        "first_seen": _iso(v["first_seen"]),
        "last_seen": _iso(v["last_seen"])
    } for v in vendor_rows]

    report = {
        "report_metadata": {
            "report_type": "SITE_DOSSIER",
            "schema_version": SCHEMA_VERSION,
            "generated_at": _iso(datetime.utcnow())
        },
        "executive_summary": {
            "site_id": site["site_id"],
            "url": site["url"],
            "site_title": site_title,
            "category": site["keyword"],
            "status": site["current_status"],
            "first_seen": _iso(site["first_seen"]),
            "last_seen": _iso(site["last_seen"])
        },
        "body": {
            "pages": pages_out
        },
        "artifacts": {
            "bitcoin_addresses": btc_out,
            "vendor_artifacts": vendor_out
        }
    }

    json_hash = canonical_json_hash(report)

    report["integrity"] = {
        "json_hash": json_hash,
        "signature": sign_hash(json_hash),
        "algorithm": "RSA-2048-PSS-SHA256",
        "public_key_id": get_public_key_fingerprint(),
        "signed_at": _iso(datetime.utcnow())
    }

    return report


# ============================================================
# BTC ADDRESS REPORT
# ============================================================

def build_btc_address_report(raw: Dict[str, Any]) -> Dict[str, Any]:
    address = raw["address"]
    transactions = [_record_to_dict(t) for t in raw["transactions"]]
    sites = [_record_to_dict(s) for s in raw["sites"]]
    vendors = [_record_to_dict(v) for v in raw["vendors"]]
    graph = raw["graph"]

    mixer_evidence = infer_mixer_from_fan_metrics(transactions)

    risk_flags = []
    if mixer_evidence:
        risk_flags.append("mixer_behavior_suspected")
    if vendors:
        risk_flags.append("vendor_attribution_possible")
    if len(transactions) >= 10:
        risk_flags.append("high_transaction_volume")

    report = {
        "report_metadata": {
            "report_type": "BTC_ADDRESS_REPORT",
            "schema_version": SCHEMA_VERSION,
            "generated_at": _iso(datetime.utcnow()),
            "graph_artifacts": {
                "transaction_graph": graph
            }
        },
        "executive_summary": {
            "address_id": address["address_id"],
            "btc_address": address["address"],
            "checksum_valid": address["valid"],
            "first_seen": _iso(address["detected_at"]),
            "risk_flags": risk_flags
        },
        "analysis": {
            "mixer_analysis": {
                "method": "fan_in_fan_out_heuristic",
                "fan_in_threshold": FAN_IN_THRESHOLD,
                "fan_out_threshold": FAN_OUT_THRESHOLD,
                "evidence": mixer_evidence
            }
        },
        "evidence": {
            "linked_sites": sites,
            "transactions": transactions,
            "vendors": vendors
        }
    }

    json_hash = canonical_json_hash(report)

    report["integrity"] = {
        "json_hash": json_hash,
        "signature": sign_hash(json_hash),
        "algorithm": "RSA-2048-PSS-SHA256",
        "public_key_id": get_public_key_fingerprint(),
        "signed_at": _iso(datetime.utcnow())
    }

    return report



# ============================================================
# VENDOR PROFILE (INTEGRATED)
# ============================================================

def infer_vendor_crypto_risk(transactions):
    flags = []
    for tx in transactions:
        if tx["fan_in"] >= FAN_IN_THRESHOLD:
            flags.append("high_fan_in")
        if tx["fan_out"] >= FAN_OUT_THRESHOLD:
            flags.append("high_fan_out")
    return list(set(flags))

def build_vendor_profile_report(raw):
    vendor = raw["vendor"]
    artifacts = [_record_to_dict(a) for a in raw["artifacts"]]
    sites = [_record_to_dict(s) for s in raw["sites"]]
    btc_addresses = [_record_to_dict(b) for b in raw["btc_addresses"]]
    edges = [_record_to_dict(e) for e in raw["edges"]]


    btc_list = [b["address"] for b in btc_addresses]

    risk_flags = []
    if btc_list:
        risk_flags.append("crypto_usage_detected")
    if any(a["artifact_type"] == "pgp" for a in artifacts):
        risk_flags.append("pgp_identity_present")

    report = {
        "report_metadata": {
            "report_type": "VENDOR_PROFILE",
            "schema_version": SCHEMA_VERSION,
            "generated_at": _iso(datetime.utcnow()),
            "source_tables": [
                "Vendors",
                "VendorArtifacts",
                "OnionSites",
                "BitcoinAddresses",
                "Transactions"
            ]
        },

        "executive_summary": {
            "vendor_id": vendor["vendor_id"],
            "risk_score": vendor["risk_score"],
            "risk_flags": risk_flags,
            "first_seen": _iso(vendor["first_seen"]),
            "last_seen": _iso(vendor["last_seen"])
        },

        "artifacts": {
            "identities": artifacts,
            "bitcoin_addresses": btc_addresses
        },

        "associations": {
            "onion_sites": sites
        },

        "graph": {
            "btc_transaction_edges": edges
        }
    }

    json_hash = canonical_json_hash(report)

    report["integrity"] = {
        "json_hash": json_hash,
        "signature": sign_hash(json_hash),
        "algorithm": "RSA-2048-PSS-SHA256",
        "public_key_id": get_public_key_fingerprint(),
        "signed_at": _iso(datetime.utcnow())
    }

    return report


# ============================================================
# CATEGORY INTEL (INTEGRATED)
# ============================================================

def category_risk_summary(vendors, btc_addresses):
    flags = []

    if len(vendors) >= 3:
        flags.append("multiple_vendors_detected")

    if len(btc_addresses) >= 5:
        flags.append("shared_crypto_infrastructure")

    high_risk = [v for v in vendors if (v["risk_score"] or 0) >= 70]
    if high_risk:
        flags.append("high_risk_vendors_present")

    return flags

def build_category_intel_report(raw):
    
    sites = [_record_to_dict(s) for s in raw["sites"]]
    vendors = [_record_to_dict(v) for v in raw["vendors"]]
    btc_addresses = [_record_to_dict(b) for b in raw["btc_addresses"]]
    edges = [_record_to_dict(e) for e in raw["edges"]]
    category = raw["category"]



    risk_flags = category_risk_summary(vendors, btc_addresses)

    report = {
        "report_metadata": {
            "report_type": "CATEGORY_INTEL",
            "schema_version": SCHEMA_VERSION,
            "generated_at": _iso(datetime.utcnow()),
            "source_tables": [
                "OnionSites",
                "Classification",
                "VendorArtifacts",
                "Vendors",
                "BitcoinAddresses",
                "Transactions"
            ],
            "graph_artifacts": {
                "btc_transaction_graph": raw["graph"]
            }
        },

        "executive_summary": {
            "category": category,
            "site_count": len(sites),
            "vendor_count": len(vendors),
            "btc_address_count": len(btc_addresses),
            "risk_flags": risk_flags
        },

        "sites": sites,
        "vendors": vendors,
        "bitcoin_addresses": btc_addresses,
        "graph_evidence": edges
    }

    json_hash = canonical_json_hash(report)

    report["integrity"] = {
        "json_hash": json_hash,
        "signature": sign_hash(json_hash),
        "algorithm": "RSA-2048-PSS-SHA256",
        "public_key_id": get_public_key_fingerprint(),
        "signed_at": _iso(datetime.utcnow())
    }

    return report



# ============================================================
# ALL SITES (INTEGRATED)
# ============================================================
def build_all_sites_report(raw):
    sites = [_record_to_dict(s) for s in raw["sites"]]
    vendors = [_record_to_dict(v) for v in raw["vendors"]]
    btc_addresses = [_record_to_dict(b) for b in raw["btc_addresses"]]
    categories = [_record_to_dict(c) for c in raw["categories"]]
    edges = [_record_to_dict(e) for e in raw["edges"]]

    risk_flags = global_risk_flags(vendors, btc_addresses)

    report = {
        "report_metadata": {
            "report_type": "ALL_SITES",
            "schema_version": SCHEMA_VERSION,
            "generated_at": _iso(datetime.utcnow()),
            "graph_artifacts": {
                "btc_transaction_graph": raw.get("graph")
            }
        },

        "executive_summary": {
            "total_sites": len(sites),
            "total_vendors": len(vendors),
            "total_btc_addresses": len(btc_addresses),
            "risk_flags": risk_flags
        },

        "category_intel": categories,

        "entities": {
            "sites": sites,
            "vendors": vendors,
            "bitcoin_addresses": btc_addresses
        }
    }

    json_hash = canonical_json_hash(report)
    report["integrity"] = {
        "json_hash": json_hash,
        "signature": sign_hash(json_hash),
        "algorithm": "RSA-2048-PSS-SHA256",
        "public_key_id": get_public_key_fingerprint(),
        "signed_at": _iso(datetime.utcnow())
    }

    return report



def global_risk_flags(vendors, btc_addresses):
    flags = []

    if len(vendors) >= 10:
        flags.append("large_vendor_ecosystem")

    high_risk = [v for v in vendors if (v["risk_score"] or 0) >= 70]
    if high_risk:
        flags.append("high_risk_vendors_present")

    if len(btc_addresses) >= 20:
        flags.append("extensive_crypto_infrastructure")

    return flags







