import re
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator


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
    def translate_to_english(text: str, lang: str) -> str:
        """
        Translate non-English text to English.
        Safe fallback: return original text on failure.
        """
        if not text.strip() or lang in ("en", "unknown"):
            return text

        try:
            return GoogleTranslator(
                source=lang,
                target="en"
            ).translate(text)
        except Exception:
            return text

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

        # -------- Translate if needed --------
        translated_text = MetadataExtractor.translate_to_english(
            text=text,
            lang=language
        )

        metadata_id = hashlib.sha256(
            f"{page_id}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()

        return {
            # ---- DB schema aligned ----
            "metadata_id": metadata_id,
            "page_id": page_id,
            "title": title,
            "meta_tags": meta_tags,
            "emails": emails,
            "pgp_keys": pgp_keys,
            "language": language,
            "translated_text": translated_text
        }
