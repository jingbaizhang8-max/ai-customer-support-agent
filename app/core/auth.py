import os
from pathlib import Path

import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, status


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "customer-support-dev"
JWT_AUDIENCE = "customer-support-api"

def verify_access_token(token: str) -> str:
    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={
                "require": [
                    "sub",
                    "exp",
                    "iat",
                    "iss",
                    "aud",
                ],
            },
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    customer_id = payload.get("sub")

    if not isinstance(customer_id, str) or not customer_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid customer identity",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return customer_id