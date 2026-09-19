import uuid

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    get_token_subject,
    verify_password,
)


def test_password_hash_and_verify():
    hashed = get_password_hash("staff123")
    assert hashed != "staff123"
    assert verify_password("staff123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_jwt_roundtrip():
    subject = uuid.uuid4()
    token = create_access_token(
        subject=subject, roles=["staff"], permissions=["constituents.read"]
    )
    payload = decode_access_token(token)
    assert payload["sub"] == str(subject)
    assert payload["roles"] == ["staff"]
    assert payload["permissions"] == ["constituents.read"]
    assert get_token_subject(token) == subject


def test_invalid_token_returns_empty():
    assert decode_access_token("not-a-token") == {}
    assert get_token_subject("not-a-token") is None
    assert get_token_subject("") is None
