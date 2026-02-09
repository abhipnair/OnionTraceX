# Reports/crypto/hashes.py

import json
import hashlib
from typing import Any


def canonical_json_hash(data: Any) -> str:
    """
    Generate SHA-256 hash of canonical JSON.
    - Sorted keys
    - UTF-8 encoding
    - No whitespace ambiguity
    """
    canonical = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()
