
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import (
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
)


def main():
    # Enable LangGraph for this local test process only.
    os.environ["USE_LANGGRAPH_AGENT"] = "true"

    secret = os.getenv("JWT_SECRET_KEY")

    if not secret:
        raise RuntimeError("JWT secret is not configured")

    if not os.getenv("DEEPSEEK_API_KEY"):
        raise RuntimeError("DeepSeek API key is not configured")

    # Create a local development token.
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": "CUS-001",
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        secret,
        algorithm=JWT_ALGORITHM,
    )

    # Exercise the actual FastAPI endpoint.
    with TestClient(app) as client:
        response = client.post(
            "/agent/chat",
            json={
                "message": (
                    "Please use get_order to check "
                    "the status and total amount "
                    "of order ORD-1001."
                )
            },
            headers={
                "Authorization": f"Bearer {token}"
            },
        )

    print("HTTP status:", response.status_code)

    if response.status_code != 200:
        print("Error:", response.text[:500])
        return

    result = response.json()

    print("Result type:", result.get("type"))

    tool_results = result.get("tool_results", [])

    print(
        "Tools called:",
        [item.get("tool_name") for item in tool_results],
    )

    print(
        "Answer:",
        (result.get("content") or "")[:500],
    )


if __name__ == "__main__":
    main()