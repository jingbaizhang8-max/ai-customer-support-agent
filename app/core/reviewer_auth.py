import os

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import (
HTTPBearer,
HTTPAuthorizationCredentials,
)

from app.core.auth import JWT_ISSUER


REVIEWER_JWT_ALGORITHM = "HS256"
REVIEWER_JWT_AUDIENCE = "customer-support-review-api"

reviewer_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="ReviewerBearer",
)

def unauthorized():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid reviewer credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

def verify_reviewer_token(token: str) -> str:
    secret_key = os.getenv("REVIEWER_JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError(
            "REVIEWER_JWT_SECRET_KEY is not configured"
        )

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[REVIEWER_JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=REVIEWER_JWT_AUDIENCE,
            options={
                "require": [
                    "sub",
                    "role",
                    "exp",
                    "iat",
                    "iss",
                    "aud",
                ],
            },
        )

    except jwt.PyJWTError:
        raise unauthorized()

    reviewer_id = payload.get("sub")
    role = payload.get("role")

    if (
        not isinstance(reviewer_id, str)
        or not reviewer_id.strip()
        or len(reviewer_id) > 64
        or role != "reviewer"
    ):
        raise unauthorized()
    return reviewer_id

def get_authenticated_reviewer_id(
        credentials: HTTPAuthorizationCredentials | None = Depends(reviewer_bearer),
) -> str:
    if credentials is None:
        raise unauthorized()
    return verify_reviewer_token(
        credentials.credentials
    )