import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

def search_refund_policy(question: str) -> dict:
    question = question.strip()

    if not question:
        return {
            "status": "invalid_question",
            "answer": None,
            "source": [],
        }

    base_url = os.getenv(
        "RAG_API_BASE_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")

    document_id = os.getenv("REFUND_POLICY_DOCUMENT_ID")

    if not document_id:
        return {
            "status": "not_configured",
            "answer": None,
            "sources": [],
        }

    payload = {
        "query": question,
        "limit": 3,
        "document_id":document_id,
    }

    try:
        response = httpx.post(
            f"{base_url}/ask",
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()

    except (httpx.HTTPError, ValueError):
        return {
            "status": "service_error",
            "answer": None,
            "sources": [],
        }

    if not isinstance(data,dict):
        return {
            "status": "invalid_response",
            "answer": None,
            "sources": [],
        }

    answer = data.get("answer")
    sources = data.get("sources")

    if not isinstance(answer, str) or not isinstance(sources, list):
        return {
            "status": "invalid_response",
            "answer": None,
            "sources": [],
        }

    if not answer.strip() or not sources:
        return {
            "status": "insufficient_evidence",
            "answer": None,
            "sources": [],
            "policy_scope": "fictional_demo_only",
        }

    return {
        "status": "retrieved",
        "answer": answer,
        "sources": sources,
        "policy_scope": "fictional_demo_only",
    }