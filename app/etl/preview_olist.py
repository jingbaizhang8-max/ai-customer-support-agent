import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "olist"

def read_csv(filename):
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8", newline="") as file:
        yield from csv.DictReader(file)

# 1. 按订单ID汇总支付金额
payment_totals = defaultdict(lambda: Decimal("0"))

for payment in read_csv("olist_order_payments_dataset.csv"):
    order_id = payment["order_id"]
    amount = Decimal(payment["payment_value"])
    payment_totals[order_id] += amount

# 2. 从订单表中找到对应的支付金额
shown = 0

for order in read_csv("olist_orders_dataset.csv"):
    order_id = order["order_id"]

    if order_id not in payment_totals:
        continue

    result = {
        "order_id": order_id,
        "customer_id": order["customer_id"],
        "status": order["order_status"],
        "total_amount": str(payment_totals[order_id]),
        "currency": "BRL",
    }

    print(result)
    shown += 1

    if shown ==3:
        break