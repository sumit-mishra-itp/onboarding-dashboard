"""Password hashing and one-time tokens. Pure functions: no DB, no HTTP."""
import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

MAX_FAILED_LOGINS = 5    # then the account locks for LOCKOUT_MINUTES
LOCKOUT_MINUTES = 15
INVITE_TTL_HOURS = 7 * 24
RESET_TTL_HOURS = 24

_hasher = PasswordHasher()  # argon2id with the library's RFC 9106 defaults
# Verified against when the email is unknown, so a miss costs the same time as a wrong password.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(stored_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(stored_hash or _DUMMY_HASH, password) and stored_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    return _hasher.check_needs_rehash(stored_hash)


def new_token() -> tuple[str, str]:
    """(raw token for the link, hash to store). The raw token is never stored."""
    raw = secrets.token_urlsafe(32)
    return raw, token_hash(raw)


def token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()  # token has 256 bits of entropy; no salt or KDF needed


if __name__ == "__main__":
    h = hash_password("correct horse battery")
    assert verify_password(h, "correct horse battery")
    assert not verify_password(h, "wrong password!!")
    assert not verify_password(None, "anything at all")
    assert not verify_password("garbage", "anything at all")
    raw, th = new_token()
    assert token_hash(raw) == th and raw != th
    print("ok")
