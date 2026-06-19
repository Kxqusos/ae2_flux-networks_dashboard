from app.auth import SessionStore, create_session_token, verify_client_token


def test_verify_client_token_accepts_matching_bearer():
    assert verify_client_token("Bearer secret", "secret") is True


def test_verify_client_token_rejects_mismatch():
    assert verify_client_token("Bearer wrong", "secret") is False


def test_verify_client_token_rejects_missing_header():
    assert verify_client_token(None, "secret") is False


def test_verify_client_token_rejects_malformed_header():
    assert verify_client_token("secret", "secret") is False


def test_create_session_token_returns_token_on_match():
    token = create_session_token("pw", "pw")
    assert isinstance(token, str)
    assert len(token) > 10


def test_create_session_token_returns_none_on_mismatch():
    assert create_session_token("wrong", "pw") is None


def test_session_store_add_and_contains():
    store = SessionStore()
    assert store.contains("abc") is False
    store.add("abc")
    assert store.contains("abc") is True


def test_session_store_clear():
    store = SessionStore()
    store.add("abc")
    store.clear()
    assert store.contains("abc") is False
