"""認証。

``POST /v1/auth/tokens`` が唯一のトークン発行口で、``type`` で挙動が変わる。
受け付けるのは ``refresh`` と ``external`` の 2 つだけ
(``anonymous`` / ``guest`` などは 400 で弾かれるのを実サーバーで確認済み)。

トークンの入手経路は 2 つある:

1. **匿名** — Web (``zeta-ai.io``) にただ GET するとアカウントが 1 つ生えて
   Cookie でトークンが降ってくる。:meth:`Auth.login_anonymous` /
   :meth:`~zetapi.ZetaClient.anonymous`。閲覧とチャットまでは出来る。
2. **外部 IdP** — Google / Apple / LINE / KAKAO の OAuth を通して得た
   code か ID トークンを :meth:`Auth.login_external` に渡す。
   認可 URL は :func:`authorize_url` が組み立てる。
"""

from __future__ import annotations

import urllib.parse
from typing import Any

from ._base import Namespace

#: Web (zeta-ai.io) のログイン画面が使っている各 IdP のクライアント識別子。
#: 3rd-party のバンドルに平文で置かれている公開値で、秘密鍵ではない。
OAUTH_CLIENTS = {
    "GOOGLE": "525134294958-mljfskqips16vo9so99v3eroniqi85gf.apps.googleusercontent.com",
    "LINE": "2002675299",
    "KAKAO": "a910522abf6591852f96f59c651723f5",
    "APPLE": "io.zeta-ai",
}

#: 各 IdP の認可エンドポイント
_AUTHORIZE_ENDPOINTS = {
    "GOOGLE": "https://accounts.google.com/o/oauth2/v2/auth",
    "LINE": "https://access.line.me/oauth2/v2.1/authorize",
    "KAKAO": "https://kauth.kakao.com/oauth/authorize",
    "APPLE": "https://appleid.apple.com/auth/authorize",
}

_SCOPES = {
    "GOOGLE": "openid email profile",
    "LINE": "profile openid email",
    "KAKAO": "phone_number account_email",
    "APPLE": "email",
}


def authorize_url(
    issuer: str,
    *,
    redirect_uri: str = "https://zeta-ai.io/auth/{provider}",
    state: str = "zetapi",
    scope: str | None = None,
) -> str:
    """IdP の認可 URL を組み立てる。ブラウザで開いて code を取るための入口。

    Web 版と同じクライアント ID・同じ redirect_uri を使う。既定の
    ``redirect_uri`` は Zeta 自身のコールバックなので、ログインを完了すると
    ブラウザのアドレスバーに ``?code=...`` が乗った状態で戻ってくる。
    その ``code`` を :meth:`Auth.login_external` に渡す。

    >>> authorize_url("LINE")[:60]
    'https://access.line.me/oauth2/v2.1/authorize?response_type='
    """
    issuer = issuer.upper()
    if issuer not in _AUTHORIZE_ENDPOINTS:
        raise ValueError(f"認可 URL を知らない issuer: {issuer} (対応: {sorted(_AUTHORIZE_ENDPOINTS)})")

    redirect = redirect_uri.format(provider=issuer.lower())
    params = {
        "response_type": "code",
        "client_id": OAUTH_CLIENTS[issuer],
        "redirect_uri": redirect,
        "scope": scope or _SCOPES[issuer],
        "state": state,
    }
    if issuer == "APPLE":
        params["response_mode"] = "form_post"
    return f"{_AUTHORIZE_ENDPOINTS[issuer]}?{urllib.parse.urlencode(params)}"


class Auth(Namespace):
    """トークンの発行・更新と外部プラットフォーム連携。"""

    def login_anonymous(self) -> dict[str, Any]:
        """Web から匿名トークンを貰ってきて、このクライアントに載せる。

        ``ZetaClient.anonymous()`` が新しいクライアントを作るのに対して、
        こちらは既存のクライアントのトークンを差し替える。

        >>> zeta = ZetaClient()
        >>> zeta.auth.login_anonymous()          # doctest: +SKIP
        {'accessToken': '...', 'refreshToken': '...', 'deviceId': '...'}
        """
        from ..client import _BROWSER_UA, _WEB_LANGUAGE_PATH, WEB_URL, ZetaTokenError

        path = _WEB_LANGUAGE_PATH.get(self._client.language, "/en")
        response = self._client.session.get(
            WEB_URL + path,
            headers={"User-Agent": _BROWSER_UA},
            timeout=self._client.timeout,
        )
        response.raise_for_status()

        access = response.cookies.get("TOKEN")
        if not access:
            raise ZetaTokenError(
                f"匿名トークンが取れなかった (status={response.status_code})"
            )
        body = {
            "accessToken": access,
            "refreshToken": response.cookies.get("REFRESH_TOKEN"),
            "deviceId": response.cookies.get("DEVICE_ID"),
        }
        self._apply(body)
        if body["deviceId"]:
            self._client.device_id = body["deviceId"]
        return body

    def authorize_url(self, issuer: str, **kwargs: Any) -> str:
        """:func:`authorize_url` と同じ。名前空間から呼びたい時用。"""
        return authorize_url(issuer, **kwargs)

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
