"""Zeta Pass (サブスクリプション)。

購入・解約系はストアやトス決済 (BrandPay) を経由するため、ここから
呼べるのは状態参照と、レシートを自前で用意した場合の申込みのみ。
"""

from __future__ import annotations

from typing import Any

from ._base import Namespace


class ZetaPass(Namespace):
    """サブスクの状態確認と解約。"""

    def subscription(self) -> Any:
        """``GET /v1/zeta-pass/subscription``。"""
        return self._call("get_zeta_pass_subscription")

    def payment_method(self) -> Any:
        return self._call("get_zeta_pass_payment_method")

    def cancel(self, **data: Any) -> Any:
        return self._call("cancel_zeta_pass", data=data or {})

    def reactivate(self, **data: Any) -> Any:
        return self._call("reactivate_zeta_pass", data=data or {})

    def refund_eligibility(self) -> Any:
        return self._call("get_zeta_pass_refund_eligibility")

    def request_refund(self, **data: Any) -> Any:
        return self._call("request_zeta_pass_refund", data=data or {})

    def promotion_eligibility(self) -> Any:
        return self._call("get_zeta_pass_promotion_eligibility")

    def pro_conversion_status(self) -> Any:
        return self._call("get_zeta_pass_pro_conversion_status")

    def pro_conversion_preview(self, **params: Any) -> Any:
        return self._call(
            "get_zeta_pass_pro_conversion_preview", params=params or None
        )
