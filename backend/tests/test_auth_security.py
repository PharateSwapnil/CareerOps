import pytest

from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_produces_different_hash_each_time():
    """bcrypt salts each hash, so hashing the same password twice should
    never produce identical output - a sanity check that we're not
    accidentally doing unsalted hashing."""
    h1 = hash_password("correct-horse-battery-staple")
    h2 = hash_password("correct-horse-battery-staple")
    assert h1 != h2


def test_verify_password_accepts_correct_password():
    hashed = hash_password("my-secret-password")
    assert verify_password("my-secret-password", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("my-secret-password")
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_handles_malformed_hash_gracefully():
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False


def test_access_token_round_trips():
    token = create_access_token(user_id=42)
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "42"
    assert payload["type"] == "access"


def test_refresh_token_round_trips():
    raw_token, jti, expires_at = create_refresh_token(user_id=42)
    payload = decode_token(raw_token, expected_type="refresh")
    assert payload["sub"] == "42"
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti


def test_decode_token_rejects_wrong_type():
    """An access token presented where a refresh token is expected (or
    vice versa) should be rejected - this is what stops an access token
    from being replayed as a refresh token to mint infinite new sessions."""
    access_token = create_access_token(user_id=1)
    with pytest.raises(TokenError):
        decode_token(access_token, expected_type="refresh")


def test_decode_token_rejects_garbage():
    with pytest.raises(TokenError):
        decode_token("not-a-real-jwt", expected_type="access")


def test_decode_token_rejects_tampered_signature():
    token = create_access_token(user_id=1)
    tampered = token[:-4] + "abcd"
    with pytest.raises(TokenError):
        decode_token(tampered, expected_type="access")
