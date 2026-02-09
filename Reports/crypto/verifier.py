# Reports/crypto/verifier.py

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
from pathlib import Path
import base64


PUBLIC_KEY_FILE = Path(__file__).parent / "keys" / "public.pem"


def verify_signature(hex_hash: str, signature_b64: str) -> bool:
    """
    Verify a signature against a SHA-256 hex hash.
    """
    public_key = serialization.load_pem_public_key(
        PUBLIC_KEY_FILE.read_bytes()
    )

    try:
        public_key.verify(
            base64.b64decode(signature_b64),
            bytes.fromhex(hex_hash),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except InvalidSignature:
        return False
