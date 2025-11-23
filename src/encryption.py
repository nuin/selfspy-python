"""
Encryption utilities for Selfspy
"""

import base64
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC_STRING = b"selfspy-v2-verification-token"

# Rate limiting for password verification
_password_attempts = defaultdict(list)
MAX_ATTEMPTS = 5
LOCKOUT_DURATION = 300  # 5 minutes in seconds


def _get_or_create_salt(data_dir: Path) -> bytes:
    """Get existing salt or create a new random one"""
    salt_path = data_dir / "encryption.salt"

    if salt_path.exists():
        return salt_path.read_bytes()
    else:
        # Generate cryptographically secure random salt
        salt = os.urandom(32)
        # Ensure data directory exists
        data_dir.mkdir(parents=True, exist_ok=True)
        # Store salt with restrictive permissions
        salt_path.write_bytes(salt)
        salt_path.chmod(0o600)  # Read/write for owner only
        return salt


def create_cipher(password: Optional[str], data_dir: Path) -> Optional[Fernet]:
    """Create a Fernet cipher from password using installation-specific salt"""
    if not password:
        return None

    # Get or create installation-specific salt
    salt = _get_or_create_salt(data_dir)

    # Use PBKDF2 to derive a key from the password
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    derived_key = kdf.derive(password.encode())
    key = base64.urlsafe_b64encode(derived_key)
    return Fernet(key)


def _check_rate_limit(data_dir: Path) -> bool:
    """Check if password verification is rate limited"""
    current_time = time.time()
    key = str(data_dir)

    # Clean up old attempts
    _password_attempts[key] = [
        attempt_time for attempt_time in _password_attempts[key]
        if current_time - attempt_time < LOCKOUT_DURATION
    ]

    # Check if locked out
    if len(_password_attempts[key]) >= MAX_ATTEMPTS:
        oldest_attempt = min(_password_attempts[key])
        time_remaining = LOCKOUT_DURATION - (current_time - oldest_attempt)
        if time_remaining > 0:
            raise PermissionError(
                f"Too many password attempts. Please wait {int(time_remaining)} seconds."
            )

    return True


def _record_password_attempt(data_dir: Path) -> None:
    """Record a password verification attempt"""
    _password_attempts[str(data_dir)].append(time.time())


async def check_password(
    data_dir: Path, cipher: Optional[Fernet], read_only: bool = False
) -> bool:
    """Check if the password is correct with rate limiting"""
    digest_path = data_dir / "password.digest"

    if digest_path.exists():
        if cipher is None:
            _record_password_attempt(data_dir)
            return False

        # Check rate limit before attempting verification
        _check_rate_limit(data_dir)

        stored = digest_path.read_bytes()
        try:
            decrypted = cipher.decrypt(stored)
            is_valid = decrypted == MAGIC_STRING
            if not is_valid:
                _record_password_attempt(data_dir)
            return is_valid
        except Exception:
            _record_password_attempt(data_dir)
            return False
    else:
        if cipher is not None and not read_only:
            encrypted = cipher.encrypt(MAGIC_STRING)
            digest_path.write_bytes(encrypted)
            digest_path.chmod(0o600)  # Secure permissions
        return True
