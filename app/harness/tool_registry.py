from pydantic import BaseModel, ConfigDict, Field,ValidationError

from app.tools.order_tools import get_order
from app.tools.shipping_tools import get_shipping_status

class GetOrderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(
        pattern=r"^ORD-\d{4}$"
    )

class GetShippingStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(
        pattern=r"^ORD-\d{4}$"
    )


TOOL_REGISTRY = {
    "get_order": {
        "handler": get_order,
        "schema": GetOrderInput,
    },

    "get_shipping_status": {
        "handler": get_shipping_status,
        "schema": GetShippingStatusInput,
    },
}

def execute_tool(tool_name: str, arguments: dict) -> dict:
    tool = TOOL_REGISTRY.get(tool_name)

    if tool is None:
        return {
            "success": False,
            "error": "tool_not_allowed",
        }

    try:
        validated_args = tool["schema"].model_validate(arguments)

    except ValidationError:
        return {
            "success": False,
            "error": "invalid_arguments",
        }

    result = tool["handler"](**validated_args.model_dump())

    if result is None:
        return {
            "success": False,
            "error": "order_not_found",
        }

    return {
        "success": True,
        "data": result,
    }