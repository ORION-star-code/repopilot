from src.auth import refresh_token


def check_refresh_token_returns_token():
    assert refresh_token("mona") == "token:mona"
