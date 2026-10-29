
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


# 读取项目根目录中的 .env
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

SHOP = os.getenv("SHOPIFY_SHOP", "").strip()
CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-10")


def main():
    if not all([SHOP, CLIENT_ID, CLIENT_SECRET]):
        raise RuntimeError("Shopify 环境变量未配置完整")

    # 支持填写子域名或完整 myshopify.com 域名
    if SHOP.endswith(".myshopify.com"):
        shop_domain = SHOP
    else:
        shop_domain = f"{SHOP}.myshopify.com"

    # 防止意外填入 URL 或其他非法内容
    import re
    if not re.fullmatch(
        r"[a-z0-9][a-z0-9-]*\.myshopify\.com",
        shop_domain,
    ):
        raise ValueError("SHOPIFY_SHOP 格式不正确")

    print("=== Shopify API 连接测试 ===")
    print("店铺：", shop_domain)

    with httpx.Client(timeout=20.0) as client:

        # 1. 通过 Client Credentials 获取 Access Token
        token_response = client.post(
            f"https://{shop_domain}/admin/oauth/access_token",
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
        )

        print("Token HTTP 状态码：", token_response.status_code)
        token_response.raise_for_status()

        token_data = token_response.json()
        access_token = token_data["access_token"]

        # 只打印权限和有效期，不打印 Token
        print("授权权限：", token_data.get("scope"))
        print("Token 有效期（秒）：", token_data.get("expires_in"))

        # 2. 查询 Shopify 店铺与订单
        query = """
        query {
          shop {
            name
            myshopifyDomain
          }
          orders(first: 5) {
            nodes {
              id
              name
              displayFinancialStatus
              displayFulfillmentStatus
              totalPriceSet {
                shopMoney {
                  amount
                  currencyCode
                }
              }
            }
          }
        }
        """

        response = client.post(
            f"https://{shop_domain}/admin/api/"
            f"{API_VERSION}/graphql.json",
            headers={
                "X-Shopify-Access-Token": access_token,
                "Content-Type": "application/json",
            },
            json={"query": query},
        )

        print("GraphQL HTTP 状态码：", response.status_code)
        response.raise_for_status()

        result = response.json()

        if result.get("errors"):
            print("GraphQL 错误：", result["errors"])
            raise RuntimeError("GraphQL 查询失败")

        data = result["data"]

        print("\n=== 店铺信息 ===")
        print("名称：", data["shop"]["name"])
        print("域名：", data["shop"]["myshopifyDomain"])

        orders = data["orders"]["nodes"]

        print("\n=== 订单信息 ===")
        print("查询到的订单数：", len(orders))

        for order in orders:
            print(
                order["name"],
                "| 支付状态：", order["displayFinancialStatus"],
                "| 履约状态：", order["displayFulfillmentStatus"],
                "| 金额：",
                order["totalPriceSet"]["shopMoney"]["amount"],
                order["totalPriceSet"]["shopMoney"]["currencyCode"],
            )

        print("\nShopify API 连接测试通过！")


if __name__ == "__main__":
    main()
