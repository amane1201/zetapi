"""ロアブック (プロットに差し込む設定資料)。"""

from __future__ import annotations

from typing import Any

from ._base import Namespace


class Lorebooks(Namespace):
    """ロアブックの CRUD と探索。"""

    def get(self, lorebook_id: str) -> Any:
        return self._call("get_lorebook", path_params={"id": lorebook_id})

    def mine(self, **params: Any) -> Any:
        return self._call("list_my_visible_lorebooks", params=params or None)

    def search(self, query: str, **params: Any) -> Any:
        return self._call("search_lorebooks", params={"query": query, **params})

    def popular(self, **params: Any) -> Any:
        return self._call("discover_popular_lorebooks", params=params or None)

    def recommended(self, **params: Any) -> Any:
        return self._call("discover_recommended_lorebooks", params=params or None)

    def create(self, **data: Any) -> Any:
        return self._call("create_lorebook", data=data)

    def update(self, lorebook_id: str, **data: Any) -> Any:
        return self._call(
            "update_lorebook", path_params={"id": lorebook_id}, data=data
        )

    def delete(self, lorebook_id: str) -> Any:
        return self._call("delete_lorebook", path_params={"id": lorebook_id})

    def check_title(self, title: str) -> Any:
        return self._call("check_lorebook_title", params={"title": title})

    def plots(self, lorebook_id: str, **params: Any) -> Any:
        """このロアブックを使っているプロット。"""
        return self._call(
            "list_plots_by_lorebook_id",
            path_params={"lorebookId": lorebook_id},
            params=params or None,
        )

    def attach(self, plot_id: str, lorebook_id: str, **data: Any) -> Any:
        return self._call(
            "attach_lorebook",
            path_params={"plotId": plot_id, "lorebookId": lorebook_id},
            data=data or {},
        )

    def detach(self, plot_id: str, lorebook_id: str) -> Any:
        return self._call(
            "detach_lorebook",
            path_params={"plotId": plot_id, "lorebookId": lorebook_id},
        )
