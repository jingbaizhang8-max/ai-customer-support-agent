
import pytest

from app.harness.tool_registry import execute_tool


PRIVATE_TOOLS = [
    "get_order",
    "get_shipping_status",
]


@pytest.mark.parametrize("tool_name", PRIVATE_TOOLS)
def test_authentication_required(tool_name):
    result = execute_tool(
        tool_name,
        {"order_id": "ORD-1001"},
    )

    assert result == {
        "success": False,
        "error": "authentication_required",
    }


@pytest.mark.parametrize("tool_name", PRIVATE_TOOLS)
def test_owner_can_access(tool_name):
    result = execute_tool(
        tool_name,
        {"order_id": "ORD-1001"},
        authenticated_customer_id="CUS-001",
    )

    assert result["success"] is True
    assert result["data"]["order_id"] == "ORD-1001"


@pytest.mark.parametrize("tool_name", PRIVATE_TOOLS)
def test_other_customer_denied(tool_name):
    result = execute_tool(
        tool_name,
        {"order_id": "ORD-1001"},
        authenticated_customer_id="CUS-002",
    )

    assert result == {
        "success": False,
        "error": "order_not_found",
    }


@pytest.mark.parametrize("tool_name", PRIVATE_TOOLS)
def test_llm_cannot_override_customer_id(tool_name):
    result = execute_tool(
        tool_name,
        {
            "order_id": "ORD-1001",
            "authenticated_customer_id": "CUS-001",
        },
        authenticated_customer_id="CUS-002",
    )

    assert result == {
        "success": False,
        "error": "invalid_arguments",
    }
