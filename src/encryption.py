"""
Encryption utilities for Selfspy
"""

import base64
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC_STRING = b"selfspy-v2-verification-token"


def create_cipher(password: Optional[str]) -> Optional[Fernet]:
    """Create a Fernet cipher from password"""
    if not password:
        return None

    # Use PBKDF2 to derive a key from the password
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"selfspy-salt",
        iterations=100000,
    )
    derived_key = kdf.derive(password.encode())
    key = base64.urlsafe_b64encode(derived_key)
    return Fernet(key)


async def check_password(
    data_dir: Path, cipher: Optional[Fernet], read_only: bool = False
) -> bool:
    """Check if the password is correct"""
    digest_path = data_dir / "password.digest"

    if digest_path.exists():
        if cipher is None:
            return False

        stored = digest_path.read_bytes()
        try:
            decrypted = cipher.decrypt(stored)
            return decrypted == MAGIC_STRING
        except Exception:
            return False
    else:
        if cipher is not None and not read_only:
            encrypted = cipher.encrypt(MAGIC_STRING)
            digest_path.write_bytes(encrypted)
        return True
