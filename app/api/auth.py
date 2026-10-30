import os
from datetime import datetime,timedelta,timezone

import jwt

from app.core.passwords import verify_password
from app.core.auth import (
JWT_ISSUER,
JWT_AUDIENCE,
JWT_ALGORITHM,
)
from app.schemas.account import LoginRequest,LoginResponse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.account import (
RegisterRequest,
AccountResponse
)
from app.core.passwords import hash_password
from app.repositories.customer_account_repository import (
get_customer_by_email,
create_customer_account,
)

from app.core.database import get_db

router = APIRouter()

@router.post(
    "/register",
    response_model=AccountResponse,
    status_code=201,
)
def register(
        request: RegisterRequest,
        db: Session = Depends(get_db),
):
    email = str(request.email).strip().lower()

    existing = get_customer_by_email(
        db=db,
        email=email
    )

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="email_already_registered",
        )

    hashed_password = hash_password(request.password)

    try:
        account = create_customer_account(
            db=db,
            email=email,
            password_hash=hashed_password,
        )

    except ValueError as exc:
        if str(exc) == "email_already_registered":
            raise HTTPException(
                status_code=409,
                detail="email_already_registered",
            ) from exc
        raise

    return account

@router.post("/login", response_model=LoginResponse)
def login(
        request: LoginRequest,
        db: Session = Depends(get_db),
):
    account = get_customer_by_email(
        db,
        str(request.email)
    )

    if (
        account is None
        or not verify_password(
            request.password,
            account.password_hash,
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="invalid_credentials",
        )

    if not account.is_active:
        raise HTTPException(
            status_code=403,
            detail="account_disabled",
        )

    secret= os.getenv("JWT_SECRET_KEY")

    if not secret:
        raise RuntimeError("JWT_SECRET_KEY not available")

    now = datetime.now(timezone.utc)
    expires_in = 30 * 60

    token = jwt.encode(
        {"sub": account.customer_id,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
         },
        secret,
        algorithm=JWT_ALGORITHM,
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        customer_id=account.customer_id,
    )