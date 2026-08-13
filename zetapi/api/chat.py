"""チャット (SSE ストリーミング)。

メッセージ送信・再生成・選択肢生成はすべて SSE で返ってくる。
イベントは ``data: {...}`` の 1 行 1 JSON で ``\\n\\n`` 区切り。

実サーバーで確認した挙動 (2026-08-13):

* リクエストボディは入れ子なしの ``{"type": "TEXT", "text": "..."}``。
  ``{"content": {...}}`` で包むと 400 ``Failed to read HTTP message`` になる。
* イベント種別は ``IN_PROGRESS`` (生成中) と ``CHAT_COMPLETE`` (完了) の 2 つ。
* ``IN_PROGRESS`` の ``chunkMessage.contents[].text`` は **差分ではなく累積**。
  素朴に連結すると同じ文が何度も繋がるので :meth:`Chat.collect` か
  :meth:`Chat.iter_text` を使うこと。
* 最終的な返信は ``CHAT_COMPLETE`` の ``replyMessage.contents[]`` に入る。
  キャラごとに ``speakerName`` / ``position`` 付きで分かれている。
"""

from __future__ import annotations

from typing import Any, Iterator

from ._base import Namespace

#: content.type に入る値 (文字列テーブルより)
CONTENT_TYPES = ("TEXT", "IMAGE", "CYOA", "OPTION", "SITUATION", "INTRO")

#: 実サーバーで観測した SSE の event 値
EVENT_IN_PROGRESS = "IN_PROGRESS"
EVENT_COMPLETE = "CHAT_COMPLETE"


def _contents_text(contents: Any) -> str:
    """``contents[]`` から text を取り出して繋ぐ。"""
    if not isinstance(contents, list):
        return ""
    return "".join(
        c["text"] for c in contents if isinstance(c, dict) and isinstance(c.get("text"), str)
    )


def _common_prefix(a: str, b: str) -> str:
    limit = min(len(a), len(b))
    i = 0
    while i < limit and a[i] == b[i]:
        i += 1
    return a[:i]


def event_text(event: dict[str, Any]) -> str:
    """1 イベントが持っている「その時点の全文」を返す。

    ``IN_PROGRESS`` なら ``chunkMessage``、``CHAT_COMPLETE`` なら
    ``replyMessage`` を見る。どちらでもなければ空文字。
    """
    for key in ("replyMessage", "chunkMessage"):
        message = event.get(key)
        if isinstance(message, dict):
            return _contents_text(message.get("contents"))
    return ""


class Chat(Namespace):
    """メッセージ送信と再生成。いずれもイベントを逐次 yield する。"""

    def send(
        self,
        room_id: str,
        text: str,
        *,
        content_type: str = "TEXT",
        **extra: Any,
    ) -> Iterator[dict[str, Any]]:
        """メッセージを送り、生成イベントを順に受け取る。

        >>> for event in zeta.chat.send(room_id, "こんにちは"):
        ...     print(event["event"])          # doctest: +SKIP
        IN_PROGRESS
        ...
        CHAT_COMPLETE

        流れてくる文字だけ欲しいなら :meth:`iter_text`、
        最終結果だけで良いなら :meth:`collect` を使う。
        """
        return self.send_raw(room_id, {"type": content_type, "text": text, **extra})

    def send_raw(self, room_id: str, data: dict[str, Any]) -> Iterator[dict[str, Any]]:
        """``POST /v1/rooms/:roomId/messages/stream`` にボディを丸投げする。"""
        return self._stream("chat", {"roomId": room_id}, data)

    def regenerate(
        self, room_id: str, message_id: str, **data: Any
    ) -> Iterator[dict[str, Any]]:
        """既存メッセージの候補を作り直す。"""
        return self._stream(
            "regen", {"roomId": room_id, "messageId": message_id}, data or {}
        )

    def options(self, room_id: str, **data: Any) -> Iterator[dict[str, Any]]:
        """選択肢 (CYOA) を生成する。"""
        return self._stream("option", {"roomId": room_id}, data or {})

    def more_options(self, room_id: str, **data: Any) -> Iterator[dict[str, Any]]:
        return self._stream("option_regen", {"roomId": room_id}, data or {})

    def example_chat(self, plot_id: str, **data: Any) -> Iterator[dict[str, Any]]:
        """プロットの会話例を生成する (ルーム不要)。"""
        return self._stream("example_chat", {"plotId": plot_id}, data or {})

    def choose_option(self, room_id: str, option_id: str, **data: Any) -> Any:
        """生成済みの選択肢を 1 つ選ぶ (これは通常の POST)。"""
        return self._call(
            "choose_option",
            path_params={"roomId": room_id, "id": option_id},
            data=data or {},
        )

    def collect(self, events: Iterator[dict[str, Any]]) -> str:
        """ストリームを最後まで読んで、返信の全文を返す。

        ``IN_PROGRESS`` は累積なので連結してはいけない。最後に届いた
        ``CHAT_COMPLETE`` を優先し、無ければ最後の ``IN_PROGRESS`` を使う。

        >>> zeta.chat.collect(zeta.chat.send(room_id, "元気？"))   # doctest: +SKIP
        '*その声は、廃墟の奥から響いた...'
        """
        latest = ""
        for event in events:
            if event.get("event") == "ERROR" or event.get("type") == "CHAT_ERROR":
                raise RuntimeError(f"ストリームがエラーを返した: {event}")
            text = event_text(event)
            if text:
                latest = text
        return latest

    def iter_text(self, events: Iterator[dict[str, Any]]) -> Iterator[str]:
        """増えた分だけを順に yield する。そのまま print すれば流れて見える。

        サーバーは毎回「その時点の全文」を送ってくるので、
        前回との差分を取って渡す。

        >>> for delta in zeta.chat.iter_text(zeta.chat.send(room_id, "やあ")):
        ...     print(delta, end="", flush=True)      # doctest: +SKIP
        """
        seen = ""
        for event in events:
            if event.get("event") == "ERROR" or event.get("type") == "CHAT_ERROR":
                raise RuntimeError(f"ストリームがエラーを返した: {event}")
            text = event_text(event)
            if not text:
                continue
            # 完全な前方一致とは限らない。CHAT_COMPLETE の最終形は途中経過と
            # 改行の入り方が違うことがあるので、共通接頭辞から先だけを出す
            delta = text[len(_common_prefix(seen, text)) :]
            seen = text
            if delta:
                yield delta

    def _stream(
        self, name: str, path_params: dict[str, Any], data: Any
    ) -> Iterator[dict[str, Any]]:
        from ..endpoints import ENDPOINTS

        endpoint = ENDPOINTS[name]
        return self._client.stream(
            endpoint.method, endpoint.path, path_params=path_params, data=data
        )
