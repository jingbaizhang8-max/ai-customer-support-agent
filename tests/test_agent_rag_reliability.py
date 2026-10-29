
import httpx
import pytest

from app.tools.policy_tools import search_refund_policy


@pytest.fixture(autouse=True)
def configure_rag(monkeypatch):
    # 测试使用虚拟文档 ID，不使用真实 .env 凭证
    monkeypatch.setenv(
        "RAG_API_BASE_URL",
        "http://127.0.0.1:8000",
    )
    monkeypatch.setenv(
        "REFUND_POLICY_DOCUMENT_ID",
        "test-policy-id",
    )


def mock_rag_response(monkeypatch, response_data):
    """模拟 RAG API 的 HTTP 200 响应。"""

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return response_data

    def fake_post(url, json, timeout):
        assert url == "http://127.0.0.1:8000/ask"
        assert json["document_id"] == "test-policy-id"
        assert json["limit"] == 3
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)


def test_rag_returns_grounded_answer(monkeypatch):
    """有证据，正确返回政策。"""

    mock_rag_response(
        monkeypatch,
        {
            "answer": (
                "Shipped orders may request a refund, "
                "subject to human review."
            ),
            "sources": [
                {
                    "source": "demo_refund_policy.md",
                    "page": None,
                }
            ],
        },
    )

    result = search_refund_policy(
        "Can shipped orders request a refund?"
    )

    assert result["status"] == "retrieved"
    assert "human review" in result["answer"]
    assert len(result["sources"]) == 1
    assert (
        result["sources"][0]["source"]
        == "demo_refund_policy.md"
    )


def test_rag_refuses_without_evidence(monkeypatch):
    """没有来源，不得当作有效政策。"""

    mock_rag_response(
        monkeypatch,
        {
            "answer": (
                "I don't know based on "
                "the provided context."
            ),
            "sources": [],
        },
    )

    result = search_refund_policy(
        "Does the policy guarantee every refund?"
    )

    assert result["status"] == "insufficient_evidence"
    assert result["answer"] is None
    assert result["sources"] == []


def test_rag_service_unavailable(monkeypatch):
    """RAG 连接失败，返回明确错误。"""

    def fake_post(*args, **kwargs):
        raise httpx.ConnectError("RAG is offline")

    monkeypatch.setattr(httpx, "post", fake_post)

    result = search_refund_policy(
        "What is the refund policy?"
    )

    assert result["status"] == "service_error"
    assert result["answer"] is None
    assert result["sources"] == []


def test_rag_invalid_response(monkeypatch):
    """RAG 返回错误格式时不能假装成功。"""

    mock_rag_response(
        monkeypatch,
        {
            "answer": ["invalid answer type"],
            "sources": "invalid sources type",
        },
    )

    result = search_refund_policy(
        "What is the refund policy?"
    )

    assert result["status"] == "invalid_response"
    assert result["answer"] is None
    assert result["sources"] == []



def test_rag_refusal_with_sources(monkeypatch):
    """
    即使有来源，如果模型明确拒答，
    也不能标记为 retrieved。
    """
    mock_rag_response(
        monkeypatch,
        {
            "answer": (
                "I don't know based on "
                "the provided context."
            ),
            "sources": [
                {
                    "source": "demo_refund_policy.md",
                    "page": None,
                }
            ],
        },
    )

    result = search_refund_policy(
        "Does every order get an automatic refund?"
    )

    assert result["status"] == "insufficient_evidence"
    assert result["answer"] is None
    assert result["sources"] == []
