from .auth import refresh_token


def login(user_id: str) -> str:
    return refresh_token(user_id)
