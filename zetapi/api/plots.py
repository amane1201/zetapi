"""プロット (キャラクター/シナリオ) の検索・閲覧・作成。

エンドポイント数が最も多い領域 (90 本)。ここに無いものは
``client.raw.<name>()`` から叩ける。
"""

from __future__ import annotations

from typing import Any

from ._base import Namespace


class Plots(Namespace):
    """プロットの検索・取得・作成とコメント。"""

    def search(self, query: str, **params: Any) -> Any:
        """``GET /v1/plots/search``。"""
        return self._call("search_plot", params={"query": query, **params})

    def autocomplete(self, query: str, **params: Any) -> Any:
        return self._call("get_search_autocomplete", params={"query": query, **params})

    def list(self, **params: Any) -> Any:
        return self._call("list_plot", params=params or None)

    def get(self, plot_id: str, **params: Any) -> Any:
        return self._call(
            "get_plot", path_params={"plotId": plot_id}, params=params or None
        )

    def ranking(self, **params: Any) -> Any:
        return self._call("list_plot_ranking", params=params or None)

    def similar(self, plot_id: str, **params: Any) -> Any:
        return self._call(
            "list_similar_plots",
            path_params={"plotId": plot_id},
            params=params or None,
        )

    def recommended_keywords(self, **params: Any) -> Any:
        return self._call("get_recommended_keywords", params=params or None)

    # ------------------------------------------------------------- 作成/編集

    def create(self, **data: Any) -> Any:
        """プロットの下書きを作る。"""
        return self._call("create_plot", data=data)

    def check_name(self, name: str) -> Any:
        return self._call("check_plot_name", params={"name": name})

    def update_draft(self, plot_id: str, **data: Any) -> Any:
        return self._call(
            "update_plot_draft_by_creator", path_params={"plotId": plot_id}, data=data
        )

    def patch_draft(self, plot_id: str, **data: Any) -> Any:
        return self._call(
            "patch_plot_draft_by_creator", path_params={"plotId": plot_id}, data=data
        )

    def update_status(self, plot_id: str, **data: Any) -> Any:
        """公開/非公開などのステータスを変える。"""
        return self._call(
            "update_plot_status_by_creator",
            path_params={"plotId": plot_id},
            data=data,
        )

    def set_private(self, plot_id: str, is_private: bool) -> Any:
        return self._call(
            "update_plot_is_private",
            path_params={"plotId": plot_id},
            data={"isPrivate": is_private},
        )

    def mine(self, **params: Any) -> Any:
        """自分が作ったプロット。"""
        return self._call("list_plot_for_creator", params=params or None)

    # ------------------------------------------------------------- 反応

    def like(self, plot_id: str) -> Any:
        return self._call("like_plot_v2", path_params={"plotId": plot_id}, data={})

    def unlike(self, plot_id: str) -> Any:
        return self._call("unlike_plot_v2", path_params={"plotId": plot_id})

    def scrap(self, plot_id: str) -> Any:
        """お気に入り登録。"""
        return self._call("scrap_plot", path_params={"plotId": plot_id}, data={})

    def unscrap(self, plot_id: str) -> Any:
        return self._call("unscrap_plot", path_params={"plotId": plot_id})

    def scrapped(self, **params: Any) -> Any:
        return self._call("page_plot_scrapped", params=params or None)

    def liked(self, **params: Any) -> Any:
        return self._call("list_liked_plots_v2", params=params or None)

    # ------------------------------------------------------------- コメント

    def comments(self, plot_id: str, **params: Any) -> Any:
        return self._call(
            "list_plot_comments",
            path_params={"plotId": plot_id},
            params=params or None,
        )

    def comment(self, plot_id: str, **data: Any) -> Any:
        return self._call(
            "create_plot_comment", path_params={"plotId": plot_id}, data=data
        )

    def reply(self, plot_id: str, comment_id: str, **data: Any) -> Any:
        return self._call(
            "create_plot_comment_reply",
            path_params={"plotId": plot_id, "commentId": comment_id},
            data=data,
        )

    def like_comment(self, plot_id: str, comment_id: str) -> Any:
        return self._call(
            "like_plot_comment",
            path_params={"plotId": plot_id, "commentId": comment_id},
            data={},
        )

    # ------------------------------------------------------------- ブロック

    def block(self, plot_id: str) -> Any:
        return self._call("block_plot", data={"plotId": plot_id})

    def unblock(self, plot_id: str) -> Any:
        return self._call("unblock_plot", params={"plotId": plot_id})

    def report(self, plot_id: str, **data: Any) -> Any:
        return self._call(
            "create_plot_report", path_params={"plotId": plot_id}, data=data
        )
