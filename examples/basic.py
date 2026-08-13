"""zetapi の使い方。

トークンは環境変数から読む。実行には有効な access/refresh トークンが要る::

    set ZETA_ACCESS_TOKEN=...
    set ZETA_REFRESH_TOKEN=...
    set ZETA_DEVICE_ID=...      # 省略可。省くと毎回別端末扱いになる
    py -3 examples/basic.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zetapi import ZetaClient, ZetaHTTPError  # noqa: E402


def main() -> int:
    access = os.environ.get("ZETA_ACCESS_TOKEN")
    if not access:
        print("ZETA_ACCESS_TOKEN が未設定", file=sys.stderr)
        return 1

    zeta = ZetaClient(
        access_token=access,
        refresh_token=os.environ.get("ZETA_REFRESH_TOKEN"),
        device_id=os.environ.get("ZETA_DEVICE_ID"),
        language="ja",
    )

    try:
        me = zeta.users.me()
        print(f"ログイン中: {me.get('username')} ({me.get('id')})")

        print(f"コイン残高: {zeta.coin.balance()}")

        found = zeta.plots.search("猫", limit=5)
        plots = found.get("content") or found.get("items") or []
        for plot in plots[:5]:
            print(f"  - {plot.get('name')} / {plot.get('id')}")

        rooms = zeta.rooms.list_v2(limit=5)
        print(f"ルーム: {rooms}")

        # チャットを流す場合 (ルーム ID が要る)
        room_id = os.environ.get("ZETA_ROOM_ID")
        if room_id:
            print("応答:", end=" ", flush=True)
            for event in zeta.chat.send(room_id, "こんにちは"):
                text = event.get("text")
                if text:
                    print(text, end="", flush=True)
            print()

        # 定義していないエンドポイントは raw から全部叩ける
        print(f"通知: {zeta.raw.list_notifications(params={'limit': 3})}")

    except ZetaHTTPError as exc:
        print(f"API エラー: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
