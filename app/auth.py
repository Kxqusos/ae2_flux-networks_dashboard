import secrets


def verify_client_token(authorization: str | None, expected_token: str) -> bool:
    if authorization is None:
        return False
    if not authorization.startswith("Bearer "):
        return False
    token = authorization[len("Bearer "):]
    return secrets.compare_digest(token, expected_token)


def create_session_token(password: str, expected_password: str) -> str | None:
    if not secrets.compare_digest(password, expected_password):
        return None
    return secrets.token_urlsafe(32)


class SessionStore:
    def __init__(self) -> None:
        self._tokens: set[str] = set()

    def add(self, token: str) -> None:
        self._tokens.add(token)

    def contains(self, token: str) -> bool:
        return token in self._tokens

    def clear(self) -> None:
        self._tokens.clear()
