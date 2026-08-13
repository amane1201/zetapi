"""ユーザー、プロフィール、ブロック。"""

from __future__ import annotations

from typing import Any

from ._base import Namespace


class Users(Namespace):
    """自分と他人のユーザー情報。"""

    def me(self) -> Any:
        """``GET /v1/users/me``。"""
        return self._call("get_profile")

    def get(self, user_id: str) -> Any:
        return self._call("get_user", path_params={"userId": user_id})

    def by_username(self, username: str) -> Any:
        return self._call(
            "get_user_id_by_username", path_params={"username": username}
        )

    def check_username(self, username: str) -> Any:
        """ユーザー名が使えるか調べる。"""
        return self._call("get_username", path_params={"username": username})

    def suggest_username(self) -> Any:
        """サーバーにユーザー名を提案させる。"""
        return self._call("get_awesome_username")

    def check_signup(self, **data: Any) -> Any:
        """外部トークンが既存アカウントに紐づいているか調べる。"""
        return self._call("check_signup", data=data, auth=False)

    def signup(self, **data: Any) -> Any:
        """新規登録。

        バンドル上の送信フィールドは ``deviceId`` / ``name`` / ``username`` /
        ``birthdate`` / ``gender`` / ``chatProfileDescription`` /
        ``externalToken`` / ``language`` / ``marketingOptIn`` /
        ``existingToken`` / ``timeZone``。
        """
        data.setdefault("deviceId", self._client.device_id)
        data.setdefault("language", self._client.language)
        return self._call("create_user", data=data, auth=False)

    def update(self, **data: Any) -> Any:
        return self._call("patch_user_profile", data=data)

    def set_preferred_genres(self, genre_ids: list[Any]) -> Any:
        return self._call("set_preferred_genres", data={"genreIds": genre_ids})

    # ------------------------------------------------------------- チャットプロフィール

    def chat_profiles(self, **params: Any) -> Any:
        """ペルソナ一覧。"""
        return self._call("list_user_chat_profile", params=params or None)

    def selected_chat_profile(self) -> Any:
        return self._call("get_selected_user_chat_profile")

    def create_chat_profile(self, **data: Any) -> Any:
        return self._call("create_user_chat_profile", data=data)

    def update_chat_profile(self, profile_id: str, **data: Any) -> Any:
        return self._call(
            "patch_user_chat_profile", path_params={"id": profile_id}, data=data
        )

    def select_chat_profile(self, profile_id: str) -> Any:
        return self._call(
            "select_user_chat_profile", path_params={"id": profile_id}, data={}
        )

    def delete_chat_profile(self, profile_id: str) -> Any:
        return self._call("delete_user_chat_profile", path_params={"id": profile_id})

    # ------------------------------------------------------------- ブロック

    def blocked(self, **params: Any) -> Any:
        return self._call("list_blocked_user", params=params or None)

    def block(self, user_id: str) -> Any:
        return self._call("block_user", data={"userId": user_id})

    def unblock(self, user_id: str) -> Any:
        return self._call("unblock_user", params={"userId": user_id})

    def report(self, user_id: str, **data: Any) -> Any:
        return self._call("report_user", path_params={"userId": user_id}, data=data)
