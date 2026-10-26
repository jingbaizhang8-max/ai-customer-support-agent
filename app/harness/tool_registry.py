from pydantic import BaseModel, ConfigDict, Field,ValidationError

from app.tools.order_tools import get_order_for_authenticated_customer
from app.tools.shipping_tools import get_shipping_status_for_authenticated_customer
from app.tools.policy_tools import search_refund_policy
from app.tools.ticket_tools import get_ticket_for_authenticated_customer

class GetOrderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(
        pattern=r"^(?:ORD-\d{4}|[0-9a-f]{32})$"
    )

class GetShippingStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(
        pattern=r"^(?:ORD-\d{4}|[0-9a-f]{32})$"
    )

class SearchRefundPolicyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str =  Field(
        min_length=1,
        max_length=1000
    )

class GetTicketInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(
        pattern=(
            r"^[0-9a-fA-F]{8}-"
            r"(?:[0-9a-fA-F]{4}-){3}"
            r"[0-9a-fA-F]{12}$"
        )
    )

TOOL_REGISTRY = {
    "get_order": {
        "handler": get_order_for_authenticated_customer,
        "schema": GetOrderInput,
        "requires_auth": True,
    },

    "get_shipping_status": {
        "handler": get_shipping_status_for_authenticated_customer,
        "schema": GetShippingStatusInput,
        "requires_auth": True,
    },

    "search_refund_policy": {
        "handler": search_refund_policy,
        "schema": SearchRefundPolicyInput,
        "requires_auth": False,
    },


    "get_ticket": {
        "handler": get_ticket_for_authenticated_customer,
        "schema": GetTicketInput,
        "requires_auth": True,
    },

}

def execute_tool(
    tool_name: str,
    arguments: dict,
    *,
    authenticated_customer_id: str | None = None,
) -> dict:
    tool = TOOL_REGISTRY.get(tool_name)

    if tool is None:
        return {
            "success": False,
            "error": "tool_not_allowed",
        }
    if tool["requires_auth"] and not authenticated_customer_id:
        return {
            "success": False,
            "error": "authentication_required",
        }

    try:
        validated_args = tool["schema"].model_validate(arguments)

    except ValidationError:
        return {
            "success": False,
            "error": "invalid_arguments",
        }


    call_args = validated_args.model_dump()

    if tool["requires_auth"]:
        call_args["authenticated_customer_id"] = (
            authenticated_customer_id
        )
    result = tool["handler"](**call_args)

    if result is None:
        error_code = (
            "ticket_not_found"
            if tool_name == "get_ticket"
            else "order_not_found"
        )
        return {
            "success": False,
            "error": error_code,
        }

    return {
        "success": True,
        "data": result,
    }