import re
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from langdetect import detect, LangDetectException
import json


class MetadataExtractor:

    EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    PGP_REGEX = re.compile(
        r"-----BEGIN PGP PUBLIC KEY BLOCK-----.*?-----END PGP PUBLIC KEY BLOCK-----",
        re.DOTALL
    )

    @staticmethod
    def extract(page_id: str, html: bytes):
        text = html.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(text, "html.parser")

        # -------- Title --------
        title = soup.title.string.strip() if soup.title and soup.title.string else None

        # -------- Meta tags --------
        meta_tags = {}
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")  # type: ignore
            content = meta.get("content") # type: ignore
            if name and content:
                meta_tags[str(name)] = str(content)

        # -------- Emails --------
        emails = list(set(MetadataExtractor.EMAIL_REGEX.findall(text)))

        # -------- PGP keys --------
        pgp_keys = [str(k) for k in MetadataExtractor.PGP_REGEX.findall(text)]

        # -------- Language detection --------
        try:
            language = detect(text[:5000])
        except LangDetectException:
            language = "unknown"

        metadata_id = hashlib.sha256(
            f"{page_id}{datetime.now(timezone.utc)}".encode()
        ).hexdigest()

        return {
            "metadata_id": metadata_id,
            "title": title,
            "meta_tags": meta_tags,   # dict (will be json.dumps before DB insert)
            "emails": emails,         # list
            "pgp_keys": pgp_keys,     # list
            "language": language,
        }
