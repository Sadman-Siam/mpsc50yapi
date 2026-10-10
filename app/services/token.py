from datetime import timedelta
from typing import Any

import jwt

from app.helper import now
from app.settings import settings

ACCESS_TOKEN_TTL_SECONDS: int = 60 * 60 * 24


def encode_access_token(
    data: dict[str, Any], expiry_seconds: int = ACCESS_TOKEN_TTL_SECONDS
) -> str:
    issued_at = now()
    expires_at = issued_at + timedelta(seconds=expiry_seconds)

    payload: dict[str, Any] = {
        **data,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    return jwt.encode(
        payload=payload,
        key=settings.jwt_private_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str, verify_exp: bool = True) -> dict[str, Any]:
    return jwt.decode(
        jwt=token,
        key=settings.jwt_public_key,
        algorithms=[settings.jwt_algorithm],
        leeway=30,
        options={"verify_exp": verify_exp},
    )
