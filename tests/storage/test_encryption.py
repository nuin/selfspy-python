"""Tests for storage.encryption."""

import pytest

from selfspy.storage.encryption import check_password, create_cipher


def test_create_cipher_returns_none_for_empty_password(tmp_path):
    assert create_cipher("", tmp_path) is None
    assert create_cipher(None, tmp_path) is None


def test_create_cipher_creates_salt_file(tmp_path):
    cipher = create_cipher("secret", tmp_path)
    assert cipher is not None
    assert (tmp_path / "encryption.salt").exists()


def test_create_cipher_reuses_existing_salt(tmp_path):
    cipher1 = create_cipher("secret", tmp_path)
    salt_first = (tmp_path / "encryption.salt").read_bytes()
    cipher2 = create_cipher("secret", tmp_path)
    salt_second = (tmp_path / "encryption.salt").read_bytes()
    assert salt_first == salt_second
    # Same password + same salt should produce same Fernet key
    token = cipher1.encrypt(b"hello")
    assert cipher2.decrypt(token) == b"hello"


@pytest.mark.asyncio
async def test_check_password_creates_digest_on_first_call(tmp_path):
    cipher = create_cipher("secret", tmp_path)
    result = await check_password(tmp_path, cipher, read_only=False)
    assert result is True
    assert (tmp_path / "password.digest").exists()


@pytest.mark.asyncio
async def test_check_password_validates_correct_password(tmp_path):
    cipher = create_cipher("secret", tmp_path)
    await check_password(tmp_path, cipher, read_only=False)
    # Second call with same cipher should validate
    cipher2 = create_cipher("secret", tmp_path)
    assert await check_password(tmp_path, cipher2, read_only=False) is True


@pytest.mark.asyncio
async def test_check_password_rejects_wrong_password(tmp_path):
    cipher = create_cipher("secret", tmp_path)
    await check_password(tmp_path, cipher, read_only=False)
    wrong_cipher = create_cipher("wrong", tmp_path)
    assert await check_password(tmp_path, wrong_cipher, read_only=False) is False
