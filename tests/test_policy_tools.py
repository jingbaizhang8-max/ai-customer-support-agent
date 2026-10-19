import httpx

from app.tools import policy_tools
from app.harness.tool_registry import execute_tool


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def test_policy_retrieved(monkeypatch):
    monkeypatch.setenv(
        "REFUND_POLICY_DOCUMENT_ID",
        "test-policy-id"
    )

    def fake_post(url, json, timeout):
        assert url.endswith("/ask")
        assert json["document_id"] == "test-policy-id"
        assert json["query"] == "What is the return window?"

        return FakeResponse({
            "answer": "14 calendar days",
            "sources": [
                {"source": "demo_refund_policy.md", "page": None}
            ],
        })

    monkeypatch.setattr(policy_tools.httpx, "post", fake_post)

    result = policy_tools.search_refund_policy(
        "What is the return window?"
    )

    assert result["status"] == "retrieved"
    assert result["answer"] == "14 calendar days"
    assert len(result["sources"]) == 1


def test_policy_insufficient_evidence(monkeypatch):
    monkeypatch.setenv(
        "REFUND_POLICY_DOCUMENT_ID",
        "test-policy-id"
    )

    monkeypatch.setattr(
        policy_tools.httpx,
        "post",
        lambda *args, **kwargs: FakeResponse({
            "answer": "I don't know.",
            "sources": [],
        }),
    )

    result = policy_tools.search_refund_policy(
        "What is the return shipping fee?"
    )

    assert result["status"] == "insufficient_evidence"
    assert result["answer"] is None


def test_policy_service_error(monkeypatch):
    monkeypatch.setenv(
        "REFUND_POLICY_DOCUMENT_ID",
        "test-policy-id"
    )

    def fake_post(*args, **kwargs):
        raise httpx.ConnectError("RAG unavailable")

    monkeypatch.setattr(policy_tools.httpx, "post", fake_post)

    result = policy_tools.search_refund_policy(
        "What is the return window?"
    )

    assert result["status"] == "service_error"


def test_policy_rejects_document_override():
    result = execute_tool(
        "search_refund_policy",
        {
            "question": "What is the return window?",
            "document_id": "another-document",
        },
    )

    assert result["success"] is False
    assert result["error"] == "invalid_arguments"
