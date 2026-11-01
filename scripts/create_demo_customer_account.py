
from getpass import getpass

from dotenv import load_dotenv
from sqlalchemy import func, select, text

load_dotenv(".env", override=True)

from app.core.database import get_db
from app.core.passwords import hash_password
from app.models.customer_account import CustomerAccount


CUSTOMER_ID = "CUS-002"
ORDER_ID = "ORD-1002"
EMAIL = "cus002-demo@example.com"


def main():
    db_generator = get_db()
    db = next(db_generator)

    try:
        # 1. 确认订单确实属于 CUS-002
        owner = db.execute(
            text(
                "SELECT customer_id FROM orders "
                "WHERE order_id = :order_id"
            ),
            {"order_id": ORDER_ID},
        ).scalar_one_or_none()

        if owner != CUSTOMER_ID:
            raise RuntimeError("订单客户归属不匹配，停止创建账户")

        # 2. 不覆盖已有账户
        existing = db.get(CustomerAccount, CUSTOMER_ID)

        if existing is not None:
            print("CUS-002 已有账户:", existing.email)
            print("未修改已有账户")
            return

        # 3. 检查邮箱是否被其他账户使用
        email_owner = db.scalar(
            select(CustomerAccount.customer_id).where(
                func.lower(CustomerAccount.email) == EMAIL.lower()
            )
        )

        if email_owner is not None:
            raise RuntimeError("测试邮箱已被其他账户使用")

        # 4. 在终端安全输入测试密码
        password = getpass("设置 CUS-002 测试密码: ")
        confirm = getpass("再次输入密码: ")

        if len(password) < 12:
            raise ValueError("测试密码至少需要 12 个字符")

        if password != confirm:
            raise ValueError("两次输入的密码不一致")

        # 5. 使用现有项目的密码哈希函数
        account = CustomerAccount(
            customer_id=CUSTOMER_ID,
            email=EMAIL,
            password_hash=hash_password(password),
            is_active=True,
        )

        db.add(account)
        db.commit()

        print("测试账户创建成功")
        print("客户 ID:", CUSTOMER_ID)
        print("登录邮箱:", EMAIL)
        print("订单编号:", ORDER_ID)

    except Exception:
        db.rollback()
        raise
    finally:
        db_generator.close()


if __name__ == "__main__":
    main()
