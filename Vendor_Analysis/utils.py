import hashlib
import random
import string


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def generate_vendor_name() -> str:
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"vendor_{suffix}"
