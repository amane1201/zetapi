"""実サーバー疎通テスト。有効なトークンが要る。

    py -3 tests/test_online.py --token <アクセストークン>

既定は**読み取りのみ**。書き込み系は --write を付けた時だけ動く。
delete / purge / logout / 課金 / ブロック / 通報 は何があっても呼ばない
(下の DENY を参照)。

主な使い方::

    # まず疎通確認だけ
    py -3 tests/test_online.py --token <AT>

    # GET を総当たりして「実際に生きてる本数」を数える
    py -3 tests/test_online.py --token <AT> --sweep

    # チャットのリクエストボディの正解を探る (これが一番知りたい)
    py -3 tests/test_online.py --token <AT> --room <ROOM_ID> --probe-chat

    # ルーム作成 → 発言 まで通す
    py -3 tests/test_online.py --token <AT> --plot <PLOT_ID> --write

結果は --json で保存できる。そのまま貼ってくれれば直せる。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zetapi import ENDPOINTS, ZetaClient, ZetaHTTPError  # noqa: E402

# ---------------------------------------------------------------- 安全弁

#: 名前にこれを含むエンドポイントは sweep から必ず除外する。
#: 消える・課金される・垢に傷が付く・トークンが死ぬ、のどれか。
DENY_WORDS = (
    "delete", "purge", "remove", "withdraw", "logout",
    "block", "report", "abusing",
    "purchase", "subscribe", "refund", "cancel", "payment", "order",
    "reward", "claim", "convert", "reactivate", "migrate",
    "create", "update", "patch", "select", "pin", "follow", "like",
    "scrap", "save", "load", "clone", "generate", "request", "submit",
    "enter", "leave", "send", "verify", "issue", "regen", "crop",
)

#: 上に引っかかるが実際は安全な読み取り (名前に create などを含むだけ)
ALLOW_OVERRIDE = {
    "list_random_recently_created_plot",
}


def is_sweep_safe(name: str) -> bool:
    endpoint = ENDPOINTS[name]
    if endpoint.method != "GET":
        return False
    if endpoint.path_params:  # ID が要るものは総当たりできない
        return False
    if name in ALLOW_OVERRIDE:
        return True
    lowered = name.lower()
    return not any(word in lowered for word in DENY_WORDS)


# ---------------------------------------------------------------- 記録

class Report:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def run(self, label: str, fn, *, note: str = "") -> Any:
        started = time.monotonic()
        try:
            value = fn()
        except ZetaHTTPError as exc:
            ms = int((time.monotonic() - started) * 1000)
            # 匿名アカウントで実行している時の ANONYMOUS_NOT_ALLOWED は想定内。
            # 失敗として数えると本物の不具合が埋もれるので分けて扱う
            expected = exc.code == "ANONYMOUS_NOT_ALLOWED"
            self.rows.append({
                "label": label, "ok": expected, "expected_block": expected, "ms": ms,
                "status": exc.status, "code": exc.code,
                "message": exc.message, "body": _trim(exc.body), "note": note,
            })
            mark = "--  " if expected else "NG  "
            suffix = " (匿名では叩けない。想定どおり)" if expected else ""
            print(f"  {mark}{label}  [{exc.status}] {exc.code or ''} {exc.message or ''}{suffix}")
            return None
        except Exception as exc:  # noqa: BLE001
            ms = int((time.monotonic() - started) * 1000)
            self.rows.append({
                "label": label, "ok": False, "ms": ms,
                "error": f"{type(exc).__name__}: {exc}", "note": note,
            })
            print(f"  NG  {label}  {type(exc).__name__}: {exc}")
            return None

        ms = int((time.monotonic() - started) * 1000)
        self.rows.append({
            "label": label, "ok": True, "ms": ms,
            "sample": _trim(value), "note": note,
        })
        print(f"  ok  {label}  ({ms}ms)  {_preview(value)}")
        return value

    def summary(self) -> tuple[int, int]:
        ok = sum(1 for r in self.rows if r["ok"] and not r.get("expected_block"))
        blocked = sum(1 for r in self.rows if r.get("expected_block"))
        ng = len(self.rows) - ok - blocked
        if blocked:
            print(f"（うち {blocked} 件は匿名では叩けないもの。ログインすれば通るはず）")
        return ok, ng


def _trim(value: Any, limit: int = 600) -> Any:
    try:
        text = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        text = repr(value)
    return text if len(text) <= limit else text[:limit] + f"...(+{len(text) - limit})"


def _preview(value: Any) -> str:
    if isinstance(value, dict):
        keys = list(value)[:6]
        return "{" + ", ".join(keys) + ("..." if len(value) > 6 else "") + "}"
    if isinstance(value, list):
        return f"[{len(value)} 件]"
    return _trim(value, 80)


# ---------------------------------------------------------------- 各テスト

def test_read(zeta: ZetaClient, report: Report) -> dict[str, Any]:
    """読み取りだけ。ここが全部通れば認証とヘッダは正しい。"""
    print("\n[1] 読み取り")
    found: dict[str, Any] = {}

    me = report.run("users.me", zeta.users.me)
    if isinstance(me, dict):
        found["user_id"] = me.get("id")
        print(f"      → {me.get('username')} / {me.get('id')}")

    report.run("coin.balance", zeta.coin.balance)
    report.run("users.chat_profiles", zeta.users.chat_profiles)
    report.run("plots.ranking", lambda: zeta.plots.ranking())

    search = report.run("plots.search('猫')", lambda: zeta.plots.search("猫", limit=5))
    plot_id = _first_id(search)
    if plot_id:
        found["plot_id"] = plot_id
        print(f"      → 拾えた plotId: {plot_id}")
        report.run("plots.get", lambda: zeta.plots.get(plot_id))
        report.run("plots.similar", lambda: zeta.plots.similar(plot_id))
        report.run("plots.comments", lambda: zeta.plots.comments(plot_id))

    rooms = report.run("rooms.list_v2", lambda: zeta.rooms.list_v2(limit=5))
    room_id = _first_id(rooms)
    if room_id:
        found["room_id"] = room_id
        print(f"      → 拾えた roomId: {room_id}")
        report.run("rooms.get", lambda: zeta.rooms.get(room_id))
        report.run("rooms.messages", lambda: zeta.rooms.messages(room_id))

    report.run("raw.list_notifications",
               lambda: zeta.raw.list_notifications(params={"limit": 3}))
    return found


def test_qs(zeta: ZetaClient, report: Report) -> None:
    """クエリ直列化 (allowDots / arrayFormat=comma) をサーバーが受けるか。"""
    print("\n[2] クエリ直列化")
    report.run(
        "配列 (ids=1,2,3 形式)",
        lambda: zeta.raw.search_plot(params={"keyword": "猫", "limit": 3}),
        note="limit が効いてれば OK",
    )
    report.run(
        "日本語クエリ",
        lambda: zeta.plots.search("恋愛", limit=2),
    )


def test_refresh(zeta: ZetaClient, report: Report) -> None:
    """リフレッシュトークンが生きてるか。"""
    print("\n[3] トークン更新")
    if not zeta.refresh_token:
        print("  --  refresh_token 未指定なのでスキップ")
        return
    before = zeta.access_token
    body = report.run("auth.refresh", zeta.auth.refresh)
    if body:
        changed = zeta.access_token != before
        print(f"      → アクセストークンが変わった: {changed}")
        report.run("更新後に users.me", zeta.users.me)


CHAT_BODY_CANDIDATES: list[tuple[str, dict[str, Any]]] = [
    # zetapi の既定。ローカルに積まれるメッセージの形から起こしたもの
    ("A: {content:{type,text}}", {"content": {"type": "TEXT", "text": "こんにちは"}}),
    ("B: {content:{type,text,recommendedMessageId:null}}",
     {"content": {"type": "TEXT", "text": "こんにちは", "recommendedMessageId": None}}),
    ("C: {message:{content:{type,text}}}",
     {"message": {"content": {"type": "TEXT", "text": "こんにちは"}}}),
    ("D: {text}", {"text": "こんにちは"}),
    ("E: {content:{type,text}, timeZone}",
     {"content": {"type": "TEXT", "text": "こんにちは"}, "timeZone": "Asia/Tokyo"}),
    ("F: {type,text}", {"type": "TEXT", "text": "こんにちは"}),
]


def probe_chat(zeta: ZetaClient, report: Report, room_id: str) -> None:
    """チャットのリクエストボディの正解を総当たりで探す。

    ここが今いちばん確度の低いところ。どれが通ったかだけ分かれば直せる。
    ※ 通った時点で**実際にメッセージが送信される**ので、捨てて良いルームで。
    """
    print("\n[4] チャットのボディ探索  ※通ると実際に送信される")
    for label, body in CHAT_BODY_CANDIDATES:
        print(f"  試行 {label}")
        try:
            events = []
            for event in zeta.chat.send_raw(room_id, body):
                events.append(event)
                if len(events) >= 8:
                    break
            report.rows.append({
                "label": f"chat body {label}", "ok": True,
                "sample": _trim(events), "note": "★これが正解",
            })
            print(f"  ok  {label} が通った  最初のイベント: {_trim(events[:3], 300)}")
            print("      ↑ この形が正解。README とデフォルトをこれに直せる")
            return
        except ZetaHTTPError as exc:
            report.rows.append({
                "label": f"chat body {label}", "ok": False,
                "status": exc.status, "code": exc.code,
                "message": exc.message, "body": _trim(exc.body),
            })
            print(f"  NG  {label}  [{exc.status}] {exc.code or ''} {exc.message or ''}")
        except Exception as exc:  # noqa: BLE001
            report.rows.append({
                "label": f"chat body {label}", "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            })
            print(f"  NG  {label}  {type(exc).__name__}: {exc}")
        time.sleep(1.0)  # 連打しない
    print("  !!  全部落ちた。上の 400 のレスポンス本文を見せてくれれば直せる")


def test_write(zeta: ZetaClient, report: Report, plot_id: str) -> None:
    """ルームを作って発言する。--write の時だけ。"""
    print("\n[5] 書き込み (ルーム作成 → 発言)")
    room = report.run("rooms.create", lambda: zeta.rooms.create(plot_id))
    room_id = room.get("id") if isinstance(room, dict) else None
    if not room_id:
        print("  --  roomId が取れなかったので発言はスキップ")
        return
    print(f"      → 作成した roomId: {room_id}")
    report.run("rooms.get (作成直後)", lambda: zeta.rooms.get(room_id))
    # ボディの形は確定済み。総当たりは --probe-chat の時だけ
    report.run(
        "chat.collect(chat.send())",
        lambda: zeta.chat.collect(zeta.chat.send(room_id, "はじめまして")),
    )
    report.run(
        "chat.iter_text() の差分",
        lambda: "".join(zeta.chat.iter_text(zeta.chat.send(room_id, "そうなんだ"))),
    )
    print(f"\n  作ったルーム {room_id} は消してない。要らなければアプリ側で消して")


def sweep(zeta: ZetaClient, report: Report, delay: float, limit: int | None) -> None:
    """パスパラメータ無しの安全な GET を総当たりする。"""
    names = [n for n in sorted(ENDPOINTS) if is_sweep_safe(n)]
    if limit:
        names = names[:limit]
    skipped = len(ENDPOINTS) - len(names)
    print(f"\n[6] GET 総当たり  {len(names)} 本 (除外 {skipped} 本: 非GET / 要ID / 危険)")

    ok = ng = 0
    rate_limited = 0
    for i, name in enumerate(names, 1):
        try:
            value = getattr(zeta.raw, name)()
            ok += 1
            report.rows.append({"label": f"sweep {name}", "ok": True,
                                "sample": _trim(value, 200)})
            print(f"  ok  [{i}/{len(names)}] {name}  {_preview(value)}")
        except ZetaHTTPError as exc:
            expected = exc.code == "ANONYMOUS_NOT_ALLOWED"
            if not expected:
                ng += 1
            report.rows.append({"label": f"sweep {name}", "ok": expected,
                                "expected_block": expected,
                                "status": exc.status, "code": exc.code,
                                "message": exc.message})
            mark = "--" if expected else "NG"
            print(f"  {mark}  [{i}/{len(names)}] {name}  [{exc.status}] {exc.code or ''}")
            if exc.status == 429:
                rate_limited += 1
                if rate_limited >= 3:
                    print("  !!  429 が続くので中断する")
                    break
                time.sleep(5.0)
        except Exception as exc:  # noqa: BLE001
            ng += 1
            report.rows.append({"label": f"sweep {name}", "ok": False,
                                "error": f"{type(exc).__name__}: {exc}"})
            print(f"  NG  [{i}/{len(names)}] {name}  {type(exc).__name__}: {exc}")
        time.sleep(delay)

    print(f"\n  総当たり結果: 成功 {ok} / 失敗 {ng}")


def _first_id(payload: Any) -> str | None:
    """ページングレスポンスの形が読めないので、それっぽい所から id を1個拾う。"""
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = None
        for key in ("content", "items", "data", "results", "rooms", "plots", "list"):
            value = payload.get(key)
            if isinstance(value, list):
                items = value
                break
        if items is None:
            return payload.get("id") if isinstance(payload.get("id"), str) else None
    else:
        return None
    for item in items:
        if isinstance(item, dict):
            for key in ("id", "roomId", "plotId"):
                if isinstance(item.get(key), str):
                    return item[key]
    return None


# ---------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description="zetapi 実サーバー疎通テスト")
    parser.add_argument("--token", help="アクセストークン (省略時 ZETA_ACCESS_TOKEN)")
    parser.add_argument("--refresh", help="リフレッシュトークン (省略時 ZETA_REFRESH_TOKEN)")
    parser.add_argument("--device-id", help="端末 ID (省略時 ZETA_DEVICE_ID)")
    parser.add_argument("--language", default="ja")
    parser.add_argument("--room", help="チャット試験に使うルーム ID")
    parser.add_argument("--plot", help="--write でルームを作る対象のプロット ID")
    parser.add_argument("--probe-chat", action="store_true",
                        help="--room のルームでチャットのボディを総当たり (実際に送信される)")
    parser.add_argument("--write", action="store_true",
                        help="書き込み系を許可 (ルーム作成・発言)")
    parser.add_argument("--sweep", action="store_true",
                        help="安全な GET を総当たり")
    parser.add_argument("--sweep-delay", type=float, default=0.4)
    parser.add_argument("--sweep-limit", type=int)
    parser.add_argument("--json", help="結果の保存先")
    args = parser.parse_args()

    import os
    token = args.token or os.environ.get("ZETA_ACCESS_TOKEN")
    if token:
        zeta = ZetaClient(
            access_token=token,
            refresh_token=args.refresh or os.environ.get("ZETA_REFRESH_TOKEN"),
            device_id=args.device_id or os.environ.get("ZETA_DEVICE_ID"),
            language=args.language,
        )
    else:
        # トークンを渡されなかったら Web から匿名アカウントを1つ貰う。
        # 毎回新しく生えるので、--write しても自分のアカウントは汚れない。
        print("トークン未指定 → 匿名アカウントで実行する")
        zeta = ZetaClient.anonymous(language=args.language)

    print(f"接続先: {zeta.base_url}")
    print(f"device_id: {zeta.device_id}")
    print(f"匿名: {zeta.is_anonymous} / user_id: {zeta.user_id}")
    print(f"送るヘッダ: {json.dumps({k: v for k, v in zeta.headers().items() if k != 'Authorization'}, ensure_ascii=False)}")

    report = Report()
    try:
        found = test_read(zeta, report)
        test_qs(zeta, report)
        test_refresh(zeta, report)

        room_id = args.room or found.get("room_id")
        if args.probe_chat:
            if room_id:
                probe_chat(zeta, report, room_id)
            else:
                print("\n[4] --room も既存ルームも無いのでチャット探索はスキップ")

        if args.write:
            plot_id = args.plot or found.get("plot_id")
            if plot_id:
                test_write(zeta, report, plot_id)
            else:
                print("\n[5] plotId が無いので書き込みはスキップ")
        else:
            print("\n[5] 書き込みはスキップ (--write で有効)")

        if args.sweep:
            sweep(zeta, report, args.sweep_delay, args.sweep_limit)
        else:
            print("\n[6] 総当たりはスキップ (--sweep で有効)")

    except KeyboardInterrupt:
        print("\n中断した")
    except Exception:  # noqa: BLE001
        traceback.print_exc()

    ok, ng = report.summary()
    print("\n" + "=" * 60)
    print(f"成功 {ok} / 失敗 {ng}")
    if ng:
        print("\n落ちたやつ:")
        for row in report.rows:
            if not row["ok"]:
                detail = row.get("message") or row.get("error") or ""
                print(f"  - {row['label']}  [{row.get('status', '-')}] {detail}")

    if args.json:
        # 長い sweep の後にパス不備で結果が飛ぶのが一番もったいないので、
        # 親を作る・失敗したら手元に退避する、まではやっておく
        payload = json.dumps(report.rows, ensure_ascii=False, indent=2)
        target = Path(args.json)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(payload, encoding="utf-8")
            print(f"\n保存した: {target}")
        except OSError as exc:
            fallback = Path(__file__).with_name("online_report.json")
            fallback.write_text(payload, encoding="utf-8")
            print(f"\n{target} に書けなかった ({exc})。代わりに保存: {fallback}")

    return 1 if ng else 0


if __name__ == "__main__":
    raise SystemExit(main())
