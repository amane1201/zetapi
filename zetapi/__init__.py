"""zetapi — Zeta (com.scatterlab.messenger) の非公式 Python API ラッパー。

Android アプリ 3.42.4 の Hermes バンドルから復元した 332 エンドポイントを
そのまま扱える。公式のものではなく、上流の変更で壊れる前提で使うこと。

>>> from zetapi import ZetaClient
>>> zeta = ZetaClient(access_token="...", refresh_token="...")
>>> zeta.users.me()
>>> for event in zeta.chat.send(room_id, "こんにちは"):
...     print(event)
"""

from .api.auth import OAUTH_CLIENTS, authorize_url
from .client import (
    APPLICATION_VERSION,
    BASE_URL,
    CREATOR_ASSISTANT_URL,
    IMAGE_URL,
    ISSUERS,
    LANGUAGES,
    WEB_APPLICATION_VERSION,
    WEB_URL,
    RawAPI,
    ZetaClient,
    normalize_language,
)
from .endpoints import ENDPOINTS, Endpoint
from .exceptions import (
    ZetaAuthError,
    ZetaError,
    ZetaHTTPError,
    ZetaRateLimitError,
    ZetaTokenError,
)

__version__ = "0.2.0"

__all__ = [
    "APPLICATION_VERSION",
    "BASE_URL",
    "CREATOR_ASSISTANT_URL",
    "ENDPOINTS",
    "IMAGE_URL",
    "ISSUERS",
    "LANGUAGES",
    "OAUTH_CLIENTS",
    "WEB_APPLICATION_VERSION",
    "WEB_URL",
    "Endpoint",
    "RawAPI",
    "ZetaAuthError",
    "ZetaClient",
    "ZetaError",
    "ZetaHTTPError",
    "ZetaRateLimitError",
    "ZetaTokenError",
    "__version__",
    "authorize_url",
    "normalize_language",
]
