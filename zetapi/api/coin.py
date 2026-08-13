"""コイン (アプリ内通貨) の残高・履歴・報酬。

課金系 (``purchase_*``) はストアのレシートが要るので、実際に通すには
Play/App Store 側の購入トークンが必要。
"""

from __future__ import annotations

from typing import Any

from ._base import Namespace


class Coin(Namespace):
    """残高・取引履歴・デイリー報酬。"""

    def balance(self) -> Any:
        """``GET /v1/coin/balance``。"""
        return self._call("get_coin_balance")

    def transactions(self, **params: Any) -> Any:
        return self._call("list_coin_transactions", params=params or None)

    def expirations(self, **params: Any) -> Any:
        return self._call("list_coin_expirations", params=params or None)

    def products(self, **params: Any) -> Any:
        return self._call("list_coin_products", params=params or None)

    def daily_reward_amount(self) -> Any:
        return self._call("get_daily_reward_amount")

    def daily_reward_left(self) -> Any:
        """今日あと何回受け取れるか。"""
        return self._call("get_daily_reward_left")

    def claim_daily_reward(self, **data: Any) -> Any:
        return self._call("reward_daily", data=data or {})

    def deposit(self, transaction_id: str) -> Any:
        return self._call(
            "get_coin_deposit_detail", path_params={"transactionId": transaction_id}
        )

    def purchase(self, product_id: str, **data: Any) -> Any:
        """コイン商品を購入する (ストアのレシートが必要)。"""
        return self._call(
            "purchase_coin_product", path_params={"productId": product_id}, data=data
        )
