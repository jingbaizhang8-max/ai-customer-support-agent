import argparse
import csv
from collections import defaultdict
from decimal import Decimal
from  pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from app.core.database import engine
from app.models.order import Order

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "olist"

def read_csv(filename):
    path = DATA_DIR / filename

    with path.open("r", encoding="utf-8", newline="") as file:
        yield from csv.DictReader(file)

def import_orders(limit=None):
    payment_totals = defaultdict(lambda : Decimal("0.00"))

    # 汇总每笔订单的支付金额
    for payment in read_csv("olist_order_payments_dataset.csv"):
        order_id = payment["order_id"]
        payment_totals[order_id] += Decimal(payment["payment_value"])

    processed = 0
    inserted = 0
    batch = []

    # 一个事务：全部成功则提交，发生异常则回滚
    with engine.begin() as connection:
        for order in read_csv("olist_orders_dataset.csv"):
            order_id = order["order_id"]

            if order_id not in payment_totals:
                continue

            batch.append({
                "order_id": order_id,
                "customer_id": order["customer_id"],
                "status": order["order_status"],
                "total_amount": payment_totals[order_id],
                "currency": "BRL",
            })

            processed += 1

            if len(batch) >= 500:
                stmt = insert(Order).values(batch)
                stmt = stmt.on_conflict_do_nothing(index_elements=[Order.order_id]).returning(Order.order_id)
                result = connection.execute(stmt)
                inserted += len(result.scalars().all())
                batch.clear()

            if limit is not None and processed >= limit:
                break

        # 处理最后不足 500 条的数据
        if batch:
            stmt = insert(Order).values(batch)
            stmt = stmt.on_conflict_do_nothing(index_elements=[Order.order_id]).returning(Order.order_id)
            result = connection.execute(stmt)
            inserted += len(result.scalars().all())

    print(f"Processed orders: {processed}")
    print(f"Inserted orders: {inserted}")
    print(f"Existing orders skipped: {processed - inserted}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be a positive integer")

    import_orders(limit=args.limit)