"""Zeta (com.scatterlab.messenger) の非公式 API クライアント。

ヘッダ構成・トークン更新・クエリ直列化・SSE の仕様はすべて
アプリ 3.42.4 の Hermes バンドルから復元したもの。詳細は README.md を参照。
"""

from __future__ import annotations

import base64
import json
import uuid
from typing import Any, Iterator

import requests

from . import _qs
from .endpoints import ENDPOINTS, Endpoint
from .exceptions import (
    ZetaAuthError,
    ZetaHTTPError,
    ZetaRateLimitError,
    ZetaTokenError,
)

BASE_URL = "https://api.zeta-ai.io"
APPLICATION_VERSION = "3.42.4"

#: Web 版 (zeta-ai.io) の X-Client-Version。アプリ版より新しい
WEB_APPLICATION_VERSION = "3.44.7"

#: バンドル内 process.env より (production ビルド)
WEB_URL = "https://zeta-ai.io"
IMAGE_URL = "https://image.zeta-ai.io"
CREATOR_ASSISTANT_URL = "https://creator-assistant.zeta-ai.io"

#: /v1/auth/tokens の externalToken.issuer に入る値。
#: ``INTERNAL_ACCESS`` は Web の TokenIssuer にのみ、``EMAIL`` はアプリ側にのみあった
ISSUERS = ("GOOGLE", "APPLE", "KAKAO", "LINE", "FACEBOOK", "EMAIL", "INTERNAL_ACCESS")

#: X-User-Language が取る値。**ここを ``ja`` のような ISO コードにすると
#: サーバーが 500 を返す**ので、必ずこの形に正規化してから送る。
LANGUAGES = ("KOREAN", "JAPANESE", "ENGLISH")

_LANGUAGE_ALIASES = {
    "ja": "JAPANESE",
    "jp": "JAPANESE",
    "ja-jp": "JAPANESE",
    "japan": "JAPANESE",
    "japanese": "JAPANESE",
    "ko": "KOREAN",
    "kr": "KOREAN",
    "ko-kr": "KOREAN",
    "korea": "KOREAN",
    "korean": "KOREAN",
    "en": "ENGLISH",
    "en-us": "ENGLISH",
    "english": "ENGLISH",
}

#: 匿名トークンを配っている Web のパス (言語ごとに用意されている)
_WEB_LANGUAGE_PATH = {"JAPANESE": "/ja", "KOREAN": "/ko", "ENGLISH": "/en"}

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


def normalize_language(value: str) -> str:
    """``ja`` / ``japanese`` などを API が受け付ける ``JAPANESE`` に直す。

    知らない値はそのまま通す (将来増えた言語を塞がないため)。

    >>> normalize_language("ja")
    'JAPANESE'
    >>> normalize_language("JAPANESE")
    'JAPANESE'
    """
    if not value:
        return value
    upper = value.upper()
    if upper in LANGUAGES:
        return upper
    return _LANGUAGE_ALIASES.get(value.lower(), value)


class ZetaClient:
    """Zeta API クライアント。

    高レベルの名前空間 (:attr:`auth`, :attr:`rooms`, :attr:`plots` ...) と、
    全 332 エンドポイントを機械的に叩ける :attr:`raw` の両方を持つ。

    >>> zeta = ZetaClient(access_token="...", refresh_token="...")
    >>> zeta.users.me()
    {'id': ..., 'username': ...}
    >>> zeta.raw.list_rooms(params={"limit": 20})
    {...}
    """

    def __init__(
        self,
        access_token: str | None = None,
        refresh_token: str | None = None,
        device_id: str | None = None,
        *,
        language: str = "ja",
        device_type: str = "android",
        client_type: str = "app",
        native_version: str = APPLICATION_VERSION,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
        auto_refresh: bool = True,
        session: requests.Session | None = None,
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        #: X-Sticky と各種 API の deviceId に使う。使い回さないと別端末扱いになる
        self.device_id = device_id or str(uuid.uuid4())
        self.language = language
        self.device_type = device_type
        self.client_type = client_type
        self.native_version = native_version
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auto_refresh = auto_refresh
        self.session = session or requests.Session()

        from .api import (
            Auth,
            Chat,
            Coin,
            Creator,
            Lorebooks,
            Plots,
            Rooms,
            Users,
            ZetaPass,
        )

        self.auth = Auth(self)
        self.users = Users(self)
        self.rooms = Rooms(self)
        self.chat = Chat(self)
        self.plots = Plots(self)
        self.lorebooks = Lorebooks(self)
        self.coin = Coin(self)
        self.creator = Creator(self)
        self.zeta_pass = ZetaPass(self)
        self.raw = RawAPI(self)

    # ------------------------------------------------------------------ 言語

    @property
    def language(self) -> str:
        """X-User-Language に載せる値。代入時に自動で正規化される。"""
        return self._language

    @language.setter
    def language(self, value: str) -> None:
        self._language = normalize_language(value)

    # ------------------------------------------------------------------ 匿名ログイン

    @classmethod
    def anonymous(
        cls,
        *,
        language: str = "ja",
        web_url: str = WEB_URL,
        session: requests.Session | None = None,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> ZetaClient:
        """ログイン無しで使えるクライアントを作る。

        Web (``zeta-ai.io``) は未ログインの訪問者にも匿名アカウントを 1 つ
        発行しており、``TOKEN`` / ``REFRESH_TOKEN`` / ``DEVICE_ID`` の 3 つが
        Set-Cookie で降ってくる。それをそのまま使う。

        匿名で通るのは閲覧系とルーム作成・チャットまで。コインや
        スクラップなど所有物が絡む API は ``ANONYMOUS_NOT_ALLOWED`` (401) で
        弾かれるので、そこまでやりたいなら :meth:`Auth.login_external` が要る。

        >>> zeta = ZetaClient.anonymous(language="ja")
        >>> zeta.is_anonymous
        True
        >>> zeta.plots.ranking(type="DAILY")     # doctest: +SKIP
        """
        lang = normalize_language(language)
        session = session or requests.Session()
        response = session.get(
            web_url.rstrip("/") + _WEB_LANGUAGE_PATH.get(lang, "/en"),
            headers={"User-Agent": _BROWSER_UA},
            timeout=timeout,
        )
        response.raise_for_status()

        access = response.cookies.get("TOKEN")
        refresh = response.cookies.get("REFRESH_TOKEN")
        device = response.cookies.get("DEVICE_ID")
        if not access:
            raise ZetaTokenError(
                f"{web_url} が匿名トークンを返さなかった "
                f"(status={response.status_code}, cookies={list(response.cookies.keys())})"
            )

        kwargs.setdefault("client_type", "web")
        kwargs.setdefault("device_type", "pc_web")
        kwargs.setdefault("native_version", WEB_APPLICATION_VERSION)
        return cls(
            access_token=access,
            refresh_token=refresh,
            device_id=device,
            language=lang,
            session=session,
            timeout=timeout,
            **kwargs,
        )

    @property
    def token_claims(self) -> dict[str, Any]:
        """アクセストークン (JWT) の中身を読む。API を叩かずに分かる情報。

        ``uid`` (ユーザー ID) / ``did`` (デバイス ID) / ``ano`` (匿名か) /
        ``cty`` (言語) / ``tz`` (タイムゾーン) / ``exp`` (失効時刻) が入っている。
        """
        if not self.access_token:
            return {}
        try:
            payload = self.access_token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            return json.loads(base64.urlsafe_b64decode(payload))
        except (IndexError, ValueError):
            return {}

    @property
    def is_anonymous(self) -> bool:
        """匿名アカウントのトークンか。"""
        return bool(self.token_claims.get("ano"))

    @property
    def user_id(self) -> str | None:
        """トークンに埋まっているユーザー ID。"""
        return self.token_claims.get("uid")

    # ------------------------------------------------------------------ 低レベル

    def headers(self, *, auth: bool = True) -> dict[str, str]:
        """アプリが必ず送る共通ヘッダを組み立てる。"""
        h = {
            "X-Client-Version": APPLICATION_VERSION,
            "X-Client-Native-Version": self.native_version,
            "X-Client-Type": self.client_type,
            "X-Device-Type": self.device_type,
            "X-User-Language": self.language,
            "X-Sticky": self.device_id,
            "Accept": "application/json",
        }
        if auth and self.access_token:
            h["Authorization"] = f"Bearer {self.access_token}"
        return h

    def build_url(self, path: str, path_params: dict[str, Any] | None = None) -> str:
        """``/v1/rooms/:roomId`` の ``:roomId`` を埋めて絶対 URL にする。"""
        filled = path
        for key, value in (path_params or {}).items():
            token = f":{key}"
            if token not in filled:
                raise ValueError(f"{path} に :{key} は無い")
            filled = filled.replace(token, str(value))
        if ":" in filled.split("://")[-1]:
            missing = [s for s in filled.split("/") if s.startswith(":")]
            raise ValueError(f"path パラメータが足りない: {missing}")
        return f"{self.base_url}{filled}"

    def request(
        self,
        method: str,
        path: str,
        *,
        path_params: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        data: Any = None,
        auth: bool = True,
        raw_response: bool = False,
        _retried: bool = False,
        **kwargs: Any,
    ) -> Any:
        """1 回の API 呼び出し。401 なら 1 度だけトークン更新して再試行する。"""
        url = self.build_url(path, path_params)
        query = _qs.stringify(params)
        if query:
            url = f"{url}?{query}"

        headers = self.headers(auth=auth)
        if data is not None:
            headers["Content-Type"] = "application/json"

        response = self.session.request(
            method,
            url,
            data=json.dumps(data, ensure_ascii=False).encode() if data is not None else None,
            headers=headers,
            timeout=self.timeout,
            **kwargs,
        )

        if response.status_code == 401 and auth and self.auto_refresh and not _retried:
            if self.refresh_token:
                self.refresh()
                return self.request(
                    method,
                    path,
                    path_params=path_params,
                    params=params,
                    data=data,
                    auth=auth,
                    raw_response=raw_response,
                    _retried=True,
                    **kwargs,
                )

        if raw_response:
            return response
        return self._unwrap(response, method, url)

    @staticmethod
    def _unwrap(response: requests.Response, method: str, url: str) -> Any:
        try:
            body = response.json() if response.content else None
        except ValueError:
            body = response.text

        if response.ok:
            return body

        cls = ZetaHTTPError
        if response.status_code in (401, 403):
            cls = ZetaAuthError
        elif response.status_code == 429:
            cls = ZetaRateLimitError
        raise cls(response.status_code, body, method, url)

    def call(self, name: str, **kwargs: Any) -> Any:
        """エンドポイント名 (:data:`~zetapi.endpoints.ENDPOINTS` のキー) で呼ぶ。"""
        try:
            endpoint = ENDPOINTS[name]
        except KeyError:
            raise KeyError(f"未知のエンドポイント: {name}") from None
        return self.call_endpoint(endpoint, **kwargs)

    def call_endpoint(self, endpoint: Endpoint, **kwargs: Any) -> Any:
        return self.request(endpoint.method, endpoint.path, **kwargs)

    # ------------------------------------------------------------------ 認証

    def refresh(self) -> dict[str, Any]:
        """リフレッシュトークンでアクセストークンを更新する。

        アプリと同じく ``POST /v1/auth/tokens`` に ``type: "refresh"`` を送る。
        """
        if not self.refresh_token:
            raise ZetaTokenError("refresh_token が無い")
        try:
            body = self.request(
                "POST",
                "/v1/auth/tokens",
                data={
                    "deviceId": self.device_id,
                    "type": "refresh",
                    "refreshToken": self.refresh_token,
                },
                auth=False,
            )
        except ZetaHTTPError as exc:
            raise ZetaTokenError(f"トークン更新に失敗: {exc}") from exc

        self.access_token = body.get("accessToken") or self.access_token
        # refreshToken は返らないこともある。その場合は既存を使い続ける
        self.refresh_token = body.get("refreshToken") or self.refresh_token
        return body

    # ------------------------------------------------------------------ SSE

    def stream(
        self,
        method: str,
        path: str,
        *,
        path_params: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        data: Any = None,
        timeout: float | None = None,
    ) -> Iterator[dict[str, Any]]:
        """SSE エンドポイントを読み、``data:`` 行の JSON を順に yield する。

        アプリはレスポンス全文を ``\\n\\n`` で切って ``data:`` 始まりだけを
        JSON.parse している。ここでも同じ切り方をする。
        """
        url = self.build_url(path, path_params)
        query = _qs.stringify(params)
        if query:
            url = f"{url}?{query}"

        headers = self.headers()
        headers["Accept"] = "text/event-stream"
        if data is not None:
            headers["Content-Type"] = "application/json"

        with self.session.request(
            method,
            url,
            data=json.dumps(data, ensure_ascii=False).encode() if data is not None else None,
            headers=headers,
            timeout=timeout or self.timeout,
            stream=True,
        ) as response:
            if not response.ok:
                self._unwrap(response, method, url)

            buffer = ""
            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                if not chunk:
                    continue
                buffer += chunk
                while "\n\n" in buffer:
                    block, buffer = buffer.split("\n\n", 1)
                    event = _parse_sse_block(block)
                    if event is not None:
                        yield event
            event = _parse_sse_block(buffer)
            if event is not None:
                yield event


def _parse_sse_block(block: str) -> dict[str, Any] | None:
    block = block.strip()
    if not block.startswith("data:") or len(block) <= 5:
        return None
    try:
        return json.loads(block[5:])
    except ValueError:
        return None


class RawAPI:
    """全 332 エンドポイントへの機械的アクセス。

    属性名は :data:`~zetapi.endpoints.ENDPOINTS` のキー。パスパラメータは
    キーワード引数でも ``path_params=`` でも渡せる。

    >>> zeta.raw.get_room(roomId="abc")
    >>> zeta.raw.search_plots(params={"query": "猫", "limit": 10})
    """

    def __init__(self, client: ZetaClient) -> None:
        self._client = client

    def __getattr__(self, name: str):
        try:
            endpoint = ENDPOINTS[name]
        except KeyError:
            raise AttributeError(f"未知のエンドポイント: {name}") from None

        def call(
            *,
            params: dict[str, Any] | None = None,
            data: Any = None,
            path_params: dict[str, Any] | None = None,
            **kwargs: Any,
        ):
            merged = dict(path_params or {})
            # パスパラメータ名に一致するキーワード引数は path_params に寄せる
            for key in list(kwargs):
                if key in endpoint.path_params:
                    merged[key] = kwargs.pop(key)
            return self._client.call_endpoint(
                endpoint, path_params=merged, params=params, data=data, **kwargs
            )

        call.__name__ = name
        call.__doc__ = (
            f"{endpoint.method} {endpoint.path}\n\n"
            f"JS 側の名前: {endpoint.js_name}\n"
            f"レスポンス型: {endpoint.response or '(未定義)'}"
        )
        return call

    def __dir__(self):
        return sorted(ENDPOINTS)
