"""axios の paramsSerializer 互換のクエリ文字列生成。

バンドル内の設定はこうなっている::

    paramsSerializer: (p) => qs.stringify(p, {allowDots: true, arrayFormat: 'comma'})

- ``allowDots``  : ネストは ``a.b=1`` (``a[b]=1`` ではない)
- ``arrayFormat``: 配列は ``a=1,2,3`` (カンマ結合、キーの繰り返しではない)
- ``None`` の値はキーごと落とす (qs の既定挙動)
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _flatten(prefix: str, value: Any, out: list[tuple[str, str]]) -> None:
    if value is None:
        return
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten(f"{prefix}.{k}" if prefix else str(k), v, out)
    elif isinstance(value, (list, tuple, set)):
        items = [_scalar(v) for v in value if v is not None]
        if items:  # 空配列はキーごと送らない
            out.append((prefix, ",".join(items)))
    else:
        out.append((prefix, _scalar(value)))


def stringify(params: dict[str, Any] | None) -> str:
    """dict をアプリと同じ規則でクエリ文字列にする。"""
    if not params:
        return ""
    out: list[tuple[str, str]] = []
    _flatten("", params, out)
    return "&".join(f"{quote(k, safe='.')}={quote(v, safe=',')}" for k, v in out)
