def refresh_token(user_id: str) -> str:
    if not user_id:
        raise ValueError("user id is required")
    return f"token:{user_id}"
