"""チャット (SSE ストリーミング)。

アプリはメッセージ送信・再生成・選択肢生成をすべて SSE で受け取る。
イベントは ``data: {...}`` の 1 行 1 JSON で、``\\n\\n`` 区切り。
バンドル内で観測できたイベント種別は ``TOKEN`` / ``START`` / ``END`` /
``COMPLETE`` / ``CYOA`` / ``ERROR``。

.. warning::
   リクエストボディの完全な形はバイトコードから確定できていない。
   送信フックが呼び出し側から body を丸ごと受け取る作りのため、
   ローカルに積まれるメッセージの形 (``{"content": {...}}``) を既定にしつつ、
   任意のフィールドを ``**extra`` で足せるようにしてある。
"""

from __future__ import annotations

from typing import Any, Iterator

from ._base import Namespace

#: content.type に入る値 (文字列テーブルより)
CONTENT_TYPES = ("TEXT", "IMAGE", "CYOA", "OPTION", "SITUATION", "INTRO")


class Chat(Namespace):
    """メッセージ送信と再生成。いずれもイベントを逐次 yield する。"""

    def send(
        self,
        room_id: str,
        text: str,
        *,
        content_type: str = "TEXT",
        recommended_message_id: str | None = None,
        **extra: Any,
    ) -> Iterator[dict[str, Any]]:
        """メッセージを送り、応答トークンを順に受け取る。

        >>> for event in zeta.chat.send(room_id, "こんにちは"):
        ...     print(event)
        """
        content: dict[str, Any] = {"type": content_type, "text": text}
        if recommended_message_id is not None:
            content["recommendedMessageId"] = recommended_message_id
        return self.send_raw(room_id, {"content": content, **extra})

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
        """``TOKEN`` イベントを繋いで最終テキストにする簡易ヘルパー。

        イベント形式が想定と違う場合に備えて、``text`` / ``content`` /
        ``delta`` のいずれかを拾う。
        """
        parts: list[str] = []
        for event in events:
            if event.get("event") == "ERROR" or event.get("type") == "CHAT_ERROR":
                raise RuntimeError(f"ストリームがエラーを返した: {event}")
            for key in ("text", "delta", "content"):
                value = event.get(key)
                if isinstance(value, str):
                    parts.append(value)
                    break
        return "".join(parts)

    def _stream(
        self, name: str, path_params: dict[str, Any], data: Any
    ) -> Iterator[dict[str, Any]]:
        from ..endpoints import ENDPOINTS

        endpoint = ENDPOINTS[name]
        return self._client.stream(
            endpoint.method, endpoint.path, path_params=path_params, data=data
        )
