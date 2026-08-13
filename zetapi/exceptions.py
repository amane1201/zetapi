"""zetapi の例外。"""

from __future__ import annotations

from typing import Any


class ZetaError(Exception):
    """zetapi が投げる全例外の基底。"""


class ZetaHTTPError(ZetaError):
    """API が 4xx/5xx を返した。

    Zeta のエラーボディは ``{"code": ..., "message": ...}`` 形式のことが多い。
    """

    def __init__(self, status: int, body: Any, method: str = "", url: str = "") -> None:
        self.status = status
        self.body = body
        self.method = method
        self.url = url

        code = message = None
        if isinstance(body, dict):
            code = body.get("code") or body.get("errorCode")
            message = body.get("message") or body.get("error")
        self.code = code
        self.message = message

        where = f" ({method} {url})" if url else ""
        detail = f"{code}: {message}" if code or message else repr(body)[:300]
        super().__init__(f"HTTP {status}{where} — {detail}")


class ZetaAuthError(ZetaHTTPError):
    """401/403。アクセストークン切れ、またはリフレッシュ失敗。"""


class ZetaRateLimitError(ZetaHTTPError):
    """429。"""


class ZetaTokenError(ZetaError):
    """トークンの発行・更新そのものに失敗した。"""
