# Reports/crypto/signer.py

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from pathlib import Path
import base64


KEY_DIR = Path(__file__).parent / "keys"
PRIVATE_KEY_FILE = KEY_DIR / "private.pem"
PUBLIC_KEY_FILE = KEY_DIR / "public.pem"


def generate_keys():
    """One-time keypair generation"""
    KEY_DIR.mkdir(parents=True, exist_ok=True)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    PRIVATE_KEY_FILE.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
    )

    PUBLIC_KEY_FILE.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )


def sign_hash(hex_hash: str) -> str:
    """
    Sign a SHA-256 hex hash.
    Returns base64 signature.
    """
    private_key = serialization.load_pem_private_key(
        PRIVATE_KEY_FILE.read_bytes(),
        password=None,
        backend=default_backend()
    )

    signature = private_key.sign(
        bytes.fromhex(hex_hash),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    return base64.b64encode(signature).decode("utf-8")


def get_public_key_fingerprint() -> str:
    """Short identifier for key trust"""
    data = PUBLIC_KEY_FILE.read_bytes()
    digest = hashes.Hash(hashes.SHA256())
    digest.update(data)
    return digest.finalize().hex()[:16]
