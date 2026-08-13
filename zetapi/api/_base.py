"""名前空間の共通土台。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..client import ZetaClient


class Namespace:
    """``client.rooms`` のような名前空間の基底。"""

    def __init__(self, client: ZetaClient) -> None:
        self._client = client

    def _call(self, name: str, **kwargs: Any) -> Any:
        return self._client.call(name, **kwargs)
