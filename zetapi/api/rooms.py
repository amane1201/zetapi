"""ルーム (プロットとの会話スレッド)。"""

from __future__ import annotations

from typing import Any

from ._base import Namespace


class Rooms(Namespace):
    """ルームの一覧・作成・削除とメッセージ履歴。"""

    def list(self, **params: Any) -> Any:
        """``GET /v1/rooms``。"""
        return self._call("list_rooms", params=params or None)

    def list_v2(self, **params: Any) -> Any:
        """``GET /v2/rooms``。アプリの現行版はこちらを使う。"""
        return self._call("list_rooms_v2", params=params or None)

    def get(self, room_id: str) -> Any:
        return self._call("get_room", path_params={"roomId": room_id})

    def create(self, plot_id: str, **data: Any) -> Any:
        """プロットとの新しいルームを開く。"""
        return self._call("create_room", data={"plotId": plot_id, **data})

    def update(self, room_id: str, **data: Any) -> Any:
        return self._call("update_room", path_params={"roomId": room_id}, data=data)

    def delete(self, room_id: str) -> Any:
        return self._call("delete_room", path_params={"roomId": room_id})

    def purge(self) -> Any:
        """全ルームを削除する。取り消せないので注意。"""
        return self._call("purge_rooms", data={})

    def active_room_id(self) -> Any:
        return self._call("get_active_room_id")

    # ------------------------------------------------------------- メッセージ

    def messages(self, room_id: str, **params: Any) -> Any:
        """``GET /v1/rooms/:roomId/messages``。ページングは ``params`` で。"""
        return self._call(
            "list_messages", path_params={"roomId": room_id}, params=params or None
        )

    def candidates(self, room_id: str, message_id: str, **params: Any) -> Any:
        """1 メッセージに対する生成候補の一覧。"""
        return self._call(
            "list_candidate",
            path_params={"roomId": room_id, "messageId": message_id},
            params=params or None,
        )

    def update_message(self, room_id: str, message_id: str, **data: Any) -> Any:
        return self._call(
            "update_message",
            path_params={"roomId": room_id, "messageId": message_id},
            data=data,
        )

    def delete_messages(self, room_id: str, **params: Any) -> Any:
        return self._call(
            "delete_room_messages",
            path_params={"roomId": room_id},
            params=params or None,
        )

    # ------------------------------------------------------------- その他

    def pin(self, room_id: str) -> Any:
        return self._call("pin_room", path_params={"roomId": room_id}, data={})

    def unpin(self, room_id: str) -> Any:
        return self._call("unpin_room", path_params={"roomId": room_id})

    def clone(self, room_id: str, **data: Any) -> Any:
        return self._call(
            "clone_room", path_params={"roomId": room_id}, data=data or {}
        )

    def save(self, room_id: str, **data: Any) -> Any:
        """会話をセーブする (ゲームのセーブデータ相当)。"""
        return self._call(
            "create_saved_room", path_params={"roomId": room_id}, data=data or {}
        )

    def load(self, room_id: str, **data: Any) -> Any:
        return self._call(
            "load_saved_room", path_params={"roomId": room_id}, data=data or {}
        )

    def bookmarks(self, room_id: str, **params: Any) -> Any:
        return self._call(
            "list_message_bookmark",
            path_params={"roomId": room_id},
            params=params or None,
        )

    def recommended_messages(self, room_id: str, **params: Any) -> Any:
        """いわゆる「おすすめの返信」。"""
        return self._call(
            "get_recommended_messages",
            path_params={"roomId": room_id},
            params=params or None,
        )
