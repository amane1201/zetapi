"""クリエイター機能とAIアシスタント。

``/v2/creator-assistant/*`` はプロット・キャラ・画像をサーバー側の AI に
生成させる口。生成系はクォータ (``get_creator_assistant_brief_quota``) と
コイン消費があるので、叩く前に残量を見ること。
"""

from __future__ import annotations

from typing import Any

from ._base import Namespace


class Creator(Namespace):
    """フォロー、ダッシュボード、AI アシスタント。"""

    # ------------------------------------------------------------- フォロー

    def follow(self, creator_id: str, **data: Any) -> Any:
        return self._call(
            "follow_creator", path_params={"creatorId": creator_id}, data=data or {}
        )

    def unfollow(self, creator_id: str) -> Any:
        return self._call("unfollow_creator", path_params={"creatorId": creator_id})

    def followers(self, creator_id: str, **params: Any) -> Any:
        return self._call(
            "list_follower",
            path_params={"creatorId": creator_id},
            params=params or None,
        )

    def followings(self, creator_id: str, **params: Any) -> Any:
        return self._call(
            "list_following_creator",
            path_params={"creatorId": creator_id},
            params=params or None,
        )

    def stats(self, creator_id: str) -> Any:
        return self._call("get_creator_stats", path_params={"creatorId": creator_id})

    def my_stats(self) -> Any:
        return self._call("get_my_creator_stats")

    def dashboard(self) -> Any:
        return self._call("get_creator_dashboard_summary")

    def plot_stats(self, plot_id: str, **params: Any) -> Any:
        return self._call(
            "get_plot_stats", path_params={"plotId": plot_id}, params=params or None
        )

    # ------------------------------------------------------------- AI アシスタント

    def assistant_quota(self) -> Any:
        """生成の残クォータ。生成前にこれを見る。"""
        return self._call("get_creator_assistant_brief_quota")

    def assistant_styles(self) -> Any:
        return self._call("get_creator_assistant_styles")

    def assistant_vibes(self) -> Any:
        return self._call("get_creator_assistant_brief_vibes")

    def generate_plot(self, **data: Any) -> Any:
        """プロット生成ジョブを投げる (非同期)。"""
        return self._call("request_creator_assistant_brief_plot_job", data=data)

    def generate_characters(self, **data: Any) -> Any:
        return self._call("generate_creator_assistant_brief_characters", data=data)

    def generate_backstories(self, **data: Any) -> Any:
        return self._call("generate_creator_assistant_brief_backstories", data=data)

    def generate_situations(self, **data: Any) -> Any:
        return self._call("generate_creator_assistant_brief_situations", data=data)

    def generate_character_image(self, *, by_coin: bool = False, **data: Any) -> Any:
        """キャラ画像を生成する。

        :param by_coin: 無料枠ではなくコインを使う
        """
        name = (
            "generate_creator_assistant_character_image_by_coin"
            if by_coin
            else "generate_creator_assistant_free_character_image"
        )
        return self._call(name, data=data)

    # ------------------------------------------------------------- コメント管理

    def comments(self, **params: Any) -> Any:
        return self._call("list_creator_plot_comments", params=params or None)

    def latest_comment(self) -> Any:
        return self._call("get_latest_creator_plot_comment")

    def pin_comment(self, plot_id: str, comment_id: str) -> Any:
        return self._call(
            "pin_plot_comment",
            path_params={"plotId": plot_id, "commentId": comment_id},
            data={},
        )

    def unpin_comment(self, plot_id: str, comment_id: str) -> Any:
        return self._call(
            "unpin_plot_comment",
            path_params={"plotId": plot_id, "commentId": comment_id},
        )
