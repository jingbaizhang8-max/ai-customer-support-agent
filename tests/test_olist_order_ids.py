
import pytest
from pydantic import ValidationError

from app.harness.tool_registry import (
    GetOrderInput,
    GetShippingStatusInput,
)


OLIST_ID = "e481f51cbdc54678b7cc49136f2d6af7"


@pytest.mark.parametrize(
    "schema",
    [GetOrderInput, GetShippingStatusInput],
)
def test_accept_olist_order_id(schema):
    result = schema(order_id=OLIST_ID)
    assert result.order_id == OLIST_ID


@pytest.mark.parametrize(
    "schema",
    [GetOrderInput, GetShippingStatusInput],
)
def test_accept_legacy_order_id(schema):
    result = schema(order_id="ORD-1001")
    assert result.order_id == "ORD-1001"


@pytest.mark.parametrize(
    "schema",
    [GetOrderInput, GetShippingStatusInput],
)
def test_reject_invalid_order_id(schema):
    with pytest.raises(ValidationError):
        schema(order_id="hello123")
