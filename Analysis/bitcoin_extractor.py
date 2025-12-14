import re
import hashlib
from datetime import datetime, timezone
from typing import List, Dict

import base58


class BitcoinExtractor:
    """
    Extracts and validates Bitcoin wallet addresses from HTML content.
    Validation follows Bitcoin protocol Base58Check specification.
    """

    # Regex patterns (candidate extraction only)
    BASE58_PATTERN = re.compile(r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b')
    BECH32_PATTERN = re.compile(r'\bbc1[ac-hj-np-z02-9]{11,71}\b')

    def __init__(self, enable_bech32: bool = True):
        self.enable_bech32 = enable_bech32

    # -----------------------------
    # Public API
    # -----------------------------
    def extract_from_html(
        self,
        html: str,
        site_id: str,
        page_id: str
    ) -> List[Dict]:
        """
        Extract and validate Bitcoin addresses from raw HTML.

        Returns:
            List of dictionaries ready for DB insertion.
        """

        results = []
        now = datetime.now(timezone.utc)

        # Step 1: Regex extraction
        candidates = set(self.BASE58_PATTERN.findall(html))

        if self.enable_bech32:
            candidates.update(self.BECH32_PATTERN.findall(html))

        # Step 2: Validation
        for address in candidates:
            is_valid = self._validate_address(address)

            results.append({
                "address_id": self._hash(address),
                "address": address,
                "site_id": site_id,
                "page_id": page_id,
                "valid": is_valid,
                "detected_at": now,
            })

        return results

    # -----------------------------
    # Validation Logic
    # -----------------------------
    def _validate_address(self, address: str) -> bool:
        """
        Validate Bitcoin address using appropriate method.
        """
        if address.startswith(("1", "3")):
            return self._validate_base58(address)

        if address.startswith("bc1") and self.enable_bech32:
            return self._validate_bech32(address)

        return False

    def _validate_base58(self, address: str) -> bool:
        """
        Base58Check validation:
        - Base58 decode
        - Double SHA256
        - Compare checksum
        """
        try:
            decoded = base58.b58decode(address)
            payload, checksum = decoded[:-4], decoded[-4:]
            hashed = hashlib.sha256(
                hashlib.sha256(payload).digest()
            ).digest()
            return checksum == hashed[:4]
        except Exception:
            return False

    def _validate_bech32(self, address: str) -> bool:
        """
        Minimal Bech32 sanity check.
        Full Bech32 checksum can be added later if required.
        """
        return address.lower().startswith("bc1")

    # -----------------------------
    # Utilities
    # -----------------------------
    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()
