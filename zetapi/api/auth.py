"""認証。

``POST /v1/auth/tokens`` が唯一のトークン発行口で、``type`` で挙動が変わる。
バンドル内で確認できたのは ``refresh`` と ``external`` の 2 つ。
"""

from __future__ import annotations

from typing import Any

from ._base import Namespace


class Auth(Namespace):
    """トークンの発行・更新と外部プラットフォーム連携。"""

    def login_external(
        self,
        issuer: str,
        token: str,
        **extra: Any,
    ) -> dict[str, Any]:
        """外部 IdP のトークンで Zeta のトークンを発行する。

        :param issuer: ``GOOGLE`` / ``APPLE`` / ``KAKAO`` / ``LINE`` /
            ``FACEBOOK`` / ``EMAIL``
        :param token: IdP から受け取った ID トークン
        :param extra: ``externalToken`` に追加で載せるフィールド

        発行に成功するとクライアントの ``access_token`` / ``refresh_token``
        を更新する。未登録ユーザーの場合はここでは通らず
        :meth:`Users.signup` が必要になる。
        """
        body = self._call(
            "issue_token",
            data={
                "deviceId": self._client.device_id,
                "type": "external",
                "externalToken": {"issuer": issuer, "token": token, **extra},
            },
            auth=False,
        )
        self._apply(body)
        return body

    def refresh(self) -> dict[str, Any]:
        """リフレッシュトークンでアクセストークンを更新する。"""
        return self._client.refresh()

    def issue_token(self, **data: Any) -> dict[str, Any]:
        """``POST /v1/auth/tokens`` を生で叩く (未知の ``type`` 用)。"""
        data.setdefault("deviceId", self._client.device_id)
        body = self._call("issue_token", data=data, auth=False)
        self._apply(body)
        return body

    def generate_sso_code(self, **data: Any) -> dict[str, Any]:
        """Web へ引き継ぐための SSO コードを発行する。"""
        return self._call("generate_sso_code", data=data or None)

    def connected_platforms(self) -> Any:
        """連携済みの外部プラットフォーム一覧。"""
        return self._call("get_connected_external_platforms")

    def logout(self) -> Any:
        """サーバー側のセッションを破棄し、手元のトークンも捨てる。"""
        result = self._call("logout", data={})
        self._client.access_token = None
        self._client.refresh_token = None
        return result

    def _apply(self, body: Any) -> None:
        if isinstance(body, dict):
            if body.get("accessToken"):
                self._client.access_token = body["accessToken"]
            if body.get("refreshToken"):
                self._client.refresh_token = body["refreshToken"]
