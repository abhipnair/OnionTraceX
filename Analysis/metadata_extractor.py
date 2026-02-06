import re
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from langdetect import detect, LangDetectException


class MetadataExtractor:

    EMAIL_REGEX = re.compile(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    )

    PGP_BLOCK_REGEX = re.compile(
        r"-----BEGIN PGP PUBLIC KEY BLOCK-----.*?-----END PGP PUBLIC KEY BLOCK-----",
        re.DOTALL
    )

    XMR_REGEX = re.compile(
        r"(?:^|[^A-Za-z0-9])(4|8)[0-9A-Za-z]{94,105}(?:$|[^A-Za-z0-9])"
    )

    VENDOR_HANDLE_REGEX = re.compile(
        r"(vendor|seller|dealer|admin|operator)[\s:]+([a-zA-Z0-9_-]{3,30})",
        re.IGNORECASE
    )

    @staticmethod
    def extract_pgp_fingerprint(pgp_block: str) -> str:
        return hashlib.sha1(pgp_block.encode()).hexdigest()

    @staticmethod
    def extract(page_id: str, html: bytes):
        text = html.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(text, "html.parser")

        # -------- Title --------
        title = (
            soup.title.string.strip()
            if soup.title and soup.title.string
            else None
        )

        # -------- Meta tags --------
        meta_tags = {}
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            content = meta.get("content")
            if name and content:
                meta_tags[str(name)] = str(content)

        # -------- Emails --------
        emails = list(set(MetadataExtractor.EMAIL_REGEX.findall(text)))

        # -------- PGP Keys + Fingerprints --------
        pgp_keys = list(set(MetadataExtractor.PGP_BLOCK_REGEX.findall(text)))

        pgp_fingerprints = list({
            MetadataExtractor.extract_pgp_fingerprint(block)
            for block in pgp_keys
        })

        # -------- XMR Addresses --------
        xmr_addresses = list({
            match.group(0).strip()
            for match in MetadataExtractor.XMR_REGEX.finditer(text)
        })

        # -------- Vendor Handles --------
        vendor_handles = list({
            match.group(2)
            for match in MetadataExtractor.VENDOR_HANDLE_REGEX.finditer(text)
        })

        # -------- Language detection --------
        try:
            language = detect(text[:5000])
        except LangDetectException:
            language = "unknown"

        metadata_id = hashlib.sha256(
            f"{page_id}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()

        return {
            "metadata_id": metadata_id,
            "title": title,
            "meta_tags": meta_tags,
            "emails": emails,
            "pgp_keys": pgp_keys,                       # ✅ restored
            "pgp_fingerprints": pgp_fingerprints,       # ✅ correlation
            "xmr_addresses": xmr_addresses,
            "vendor_handles": vendor_handles,
            "language": language,
        }
