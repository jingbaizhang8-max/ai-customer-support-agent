MOCK_ORDERS = {
    "ORD-1001":{
        "order_id": "ORD-1001",
        "customer_id": "CUS-001",
        "status": "shipped",
        "total_amount": 89.99,
        "currency": "USD",
        "shipping_status": "in_transit",
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "customer_id": "CUS-002",
        "status": "paid",
        "total_amount": 149.50,
        "currency": "USD",
        "shipping_status": "not_shipped",
    },
}

def get_order(order_id: str) -> dict | None:
    return MOCK_ORDERS.get(order_id)