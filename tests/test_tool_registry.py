from app.harness.tool_registry import execute_tool


def test_get_order_success():
    result = execute_tool(
        "get_order",
        {"order_id": "ORD-1001"}
    )

    assert result["success"] is True
    assert result["data"]["order_id"] == "ORD-1001"


def test_order_not_found():
    result = execute_tool(
        "get_order",
        {"order_id": "ORD-9999"}
    )

    assert result["success"] is False
    assert result["error"] == "order_not_found"


def test_invalid_arguments():
    result = execute_tool(
        "get_order",
        {
            "order_id": "ORD-1001",
            "admin": True
        }
    )

    assert result["success"] is False
    assert result["error"] == "invalid_arguments"


def test_unauthorized_tool():
    result = execute_tool(
        "delete_all_orders",
        {}
    )

    assert result["success"] is False
    assert result["error"] == "tool_not_allowed"