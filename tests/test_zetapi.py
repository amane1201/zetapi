"""zetapi のオフライン検証。

実サーバーには一切繋がない。ヘッダ・URL 組み立て・クエリ直列化・SSE 分解・
トークン更新の分岐が、バンドルから読み取った仕様どおりかだけを見る。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zetapi import ENDPOINTS, ZetaClient  # noqa: E402
from zetapi import _qs  # noqa: E402
from zetapi.client import _parse_sse_block  # noqa: E402
from zetapi.exceptions import ZetaAuthError, ZetaHTTPError  # noqa: E402

failures: list[str] = []


def check(label: str, actual, expected) -> None:
    if actual == expected:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label}\n       期待: {expected!r}\n       実際: {actual!r}")
        failures.append(label)


def check_raises(label: str, fn, exc) -> None:
    try:
        fn()
    except exc:
        print(f"  ok   {label}")
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL {label} — 別の例外: {type(e).__name__}: {e}")
        failures.append(label)
    else:
        print(f"  FAIL {label} — 例外が出なかった")
        failures.append(label)


# ---------------------------------------------------------------- 偽セッション


class FakeResponse:
    def __init__(self, status=200, body=None, text=None):
        self.status_code = status
        self._body = body
        self.text = text if text is not None else json.dumps(body or {})
        self.content = self.text.encode()

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


class FakeSession:
    """呼び出しを記録し、用意した応答を順に返す。"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


# ---------------------------------------------------------------- テスト

print("エンドポイント表")
check("332 件ある", len(ENDPOINTS), 332)
check("chat は POST", ENDPOINTS["chat"].method, "POST")
check("chat のパス", ENDPOINTS["chat"].path, "/v1/rooms/:roomId/messages/stream")
check("path_params が拾えている", ENDPOINTS["regen"].path_params, ("roomId", "messageId"))
check("全件に path がある", all(e.path.startswith("/") for e in ENDPOINTS.values()), True)
check(
    "path_params とパスが一致",
    all(
        all(f":{p}" in e.path for p in e.path_params) for e in ENDPOINTS.values()
    ),
    True,
)

print("\nクエリ直列化 (qs: allowDots + arrayFormat=comma)")
check("素の値", _qs.stringify({"a": 1, "b": "x"}), "a=1&b=x")
check("配列はカンマ結合", _qs.stringify({"ids": [1, 2, 3]}), "ids=1,2,3")
check("ネストはドット", _qs.stringify({"a": {"b": {"c": 1}}}), "a.b.c=1")
check("bool は小文字", _qs.stringify({"f": True, "g": False}), "f=true&g=false")
check("None はキーごと落とす", _qs.stringify({"a": None, "b": 1}), "b=1")
check("空配列も落とす", _qs.stringify({"a": [], "b": 1}), "b=1")
check("空 dict は空文字", _qs.stringify({}), "")
check("None 自体も空文字", _qs.stringify(None), "")
check("日本語はパーセント符号化", _qs.stringify({"q": "猫"}), "q=%E7%8C%AB")

print("\nヘッダ")
zeta = ZetaClient(access_token="AT", device_id="DEV-1", language="ja")
h = zeta.headers()
check("X-Client-Version", h["X-Client-Version"], "3.42.4")
check("X-Client-Type", h["X-Client-Type"], "app")
check("X-Device-Type", h["X-Device-Type"], "android")
# ja のまま送るとサーバーが 500 を返す。必ず JAPANESE に正規化されること
check("X-User-Language", h["X-User-Language"], "JAPANESE")
check("language は正規化される", zeta.language, "JAPANESE")
check("ko も正規化", ZetaClient(language="ko").language, "KOREAN")
check("en も正規化", ZetaClient(language="en").language, "ENGLISH")
check("既に大文字ならそのまま", ZetaClient(language="ENGLISH").language, "ENGLISH")
check("未知の値は素通し", ZetaClient(language="FRENCH").language, "FRENCH")
check("X-Sticky は deviceId", h["X-Sticky"], "DEV-1")
check("Authorization", h["Authorization"], "Bearer AT")
check("auth=False なら付かない", "Authorization" in zeta.headers(auth=False), False)
check("device_id は自動生成される", len(ZetaClient().device_id), 36)

print("\nURL 組み立て")
check(
    "path パラメータ埋め込み",
    zeta.build_url("/v1/rooms/:roomId", {"roomId": "R1"}),
    "https://api.zeta-ai.io/v1/rooms/R1",
)
check(
    "2 個埋め込み",
    zeta.build_url(
        "/v1/rooms/:roomId/messages/:messageId", {"roomId": "R1", "messageId": "M1"}
    ),
    "https://api.zeta-ai.io/v1/rooms/R1/messages/M1",
)
check_raises(
    "不足を検出", lambda: zeta.build_url("/v1/rooms/:roomId", {}), ValueError
)
check_raises(
    "余計なキーを検出",
    lambda: zeta.build_url("/v1/rooms", {"roomId": "R1"}),
    ValueError,
)

print("\nリクエスト送信")
session = FakeSession([FakeResponse(200, {"id": "R1"})])
zeta = ZetaClient(access_token="AT", device_id="DEV-1", session=session)
result = zeta.raw.get_room(roomId="R1")
call = session.calls[0]
check("戻り値は JSON", result, {"id": "R1"})
check("メソッド", call["method"], "GET")
check("URL", call["url"], "https://api.zeta-ai.io/v1/rooms/R1")
check("GET にボディなし", call["data"], None)

session = FakeSession([FakeResponse(200, {})])
zeta = ZetaClient(access_token="AT", session=session)
zeta.raw.search_plot(params={"query": "猫", "limit": 10})
check(
    "クエリが URL に載る",
    session.calls[0]["url"],
    "https://api.zeta-ai.io/v1/plots/search?query=%E7%8C%AB&limit=10",
)

session = FakeSession([FakeResponse(200, {})])
zeta = ZetaClient(access_token="AT", session=session)
zeta.rooms.create("PLOT-1", extra=1)
call = session.calls[0]
check("POST ボディ", json.loads(call["data"]), {"plotId": "PLOT-1", "extra": 1})
check("Content-Type", call["headers"]["Content-Type"], "application/json")

print("\nキーワード引数と path_params の振り分け")
session = FakeSession([FakeResponse(200, {})])
zeta = ZetaClient(access_token="AT", session=session)
zeta.raw.regen(roomId="R1", messageId="M1", data={"x": 1})
check(
    "両方ともパスに入る",
    session.calls[0]["url"],
    "https://api.zeta-ai.io/v1/rooms/R1/messages/M1/candidates/stream",
)

print("\nエラー")
session = FakeSession([FakeResponse(400, {"code": "BAD", "message": "だめ"})])
zeta = ZetaClient(access_token="AT", session=session)
try:
    zeta.users.me()
except ZetaHTTPError as e:
    check("status", e.status, 400)
    check("code", e.code, "BAD")
    check("message", e.message, "だめ")
else:
    failures.append("400 で例外が出なかった")
    print("  FAIL 400 で例外が出なかった")

print("\n401 → 自動リフレッシュ → 再試行")
session = FakeSession(
    [
        FakeResponse(401, {"message": "expired"}),
        FakeResponse(200, {"accessToken": "AT2", "refreshToken": "RT2"}),
        FakeResponse(200, {"id": "ME"}),
    ]
)
zeta = ZetaClient(access_token="AT1", refresh_token="RT1", device_id="D", session=session)
check("最終的に成功する", zeta.users.me(), {"id": "ME"})
check("3 回叩いている", len(session.calls), 3)
check(
    "2 回目はトークン更新",
    session.calls[1]["url"],
    "https://api.zeta-ai.io/v1/auth/tokens",
)
check(
    "更新ボディ",
    json.loads(session.calls[1]["data"]),
    {"deviceId": "D", "type": "refresh", "refreshToken": "RT1"},
)
check("更新時は Authorization なし", "Authorization" in session.calls[1]["headers"], False)
check("新トークンを保持", zeta.access_token, "AT2")
check("新リフレッシュを保持", zeta.refresh_token, "RT2")
check("再試行は新トークンで", session.calls[2]["headers"]["Authorization"], "Bearer AT2")

print("\n401 でリフレッシュトークンが無い場合")
session = FakeSession([FakeResponse(401, {"message": "expired"})])
zeta = ZetaClient(access_token="AT", session=session)
check_raises("ZetaAuthError になる", zeta.users.me, ZetaAuthError)
check("再試行しない", len(session.calls), 1)

print("\n無限リトライしない")
session = FakeSession(
    [
        FakeResponse(401, {}),
        FakeResponse(200, {"accessToken": "AT2"}),
        FakeResponse(401, {}),
    ]
)
zeta = ZetaClient(access_token="AT", refresh_token="RT", session=session)
check_raises("2 度目の 401 で諦める", zeta.users.me, ZetaAuthError)
check("3 回で打ち止め", len(session.calls), 3)

print("\nSSE の分解")
check(
    "data: 行を JSON 化",
    _parse_sse_block('data: {"event":"TOKEN","text":"あ"}'),
    {"event": "TOKEN", "text": "あ"},
)
check("data: 以外は無視", _parse_sse_block("event: ping"), None)
check("空は無視", _parse_sse_block(""), None)
check("data: だけの行も無視", _parse_sse_block("data:"), None)
check("壊れた JSON は無視", _parse_sse_block("data: {broken"), None)

print("\nSSE ストリーム (チャンク境界がイベント境界とずれる場合)")


class FakeStreamResponse(FakeResponse):
    def __init__(self, chunks, status=200):
        super().__init__(status, {})
        self.chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, chunk_size=None, decode_unicode=False):
        return iter(self.chunks)


# 1 イベントが 2 チャンクに割れ、1 チャンクに 2 イベントが入る意地悪な分かれ方
stream_response = FakeStreamResponse(
    [
        'data: {"event":"STA',
        'RT"}\n\ndata: {"event":"TOKEN","text":"こん"}\n\n',
        'data: {"event":"TOKEN","text":"にちは"}\n\n',
        ": keepalive\n\n",
        'data: {"event":"END"}',
    ]
)
session = FakeSession([stream_response])
zeta = ZetaClient(access_token="AT", session=session)
events = list(zeta.chat.send("R1", "やあ"))
check(
    "チャンク境界をまたいで復元",
    events,
    [
        {"event": "START"},
        {"event": "TOKEN", "text": "こん"},
        {"event": "TOKEN", "text": "にちは"},
        {"event": "END"},
    ],
)
check("Accept は event-stream", session.calls[0]["headers"]["Accept"], "text/event-stream")
check("stream=True", session.calls[0]["stream"], True)
# 入れ子にすると 400 Failed to read HTTP message。フラットが正解
check(
    "送信ボディ",
    json.loads(session.calls[0]["data"]),
    {"type": "TEXT", "text": "やあ"},
)
check(
    "URL",
    session.calls[0]["url"],
    "https://api.zeta-ai.io/v1/rooms/R1/messages/stream",
)

# 実サーバーの形。IN_PROGRESS の text は差分ではなく累積で、
# 最終形は CHAT_COMPLETE の replyMessage に入る
_CHUNK = 'data:{{"event":"IN_PROGRESS","chunkMessage":{{"contents":[{{"type":"TEXT","text":"{0}"}}]}},"index":null}}'
_DONE = (
    'data:{"event":"CHAT_COMPLETE","replyMessage":{"contents":'
    '[{"type":"TEXT","speakerName":"ナレーター","text":"あいうえお"},'
    '{"type":"TEXT","speakerName":"蓮","text":"……は？"}]}}'
)
_STREAM = "\n\n".join([_CHUNK.format("あ"), _CHUNK.format("あい"), _CHUNK.format("あいう"), _DONE]) + "\n\n"

session = FakeSession([FakeStreamResponse([_STREAM])])
zeta = ZetaClient(access_token="AT", session=session)
check(
    "collect は累積を連結しない",
    zeta.chat.collect(zeta.chat.send("R1", "x")),
    "あいうえお……は？",
)

session = FakeSession([FakeStreamResponse([_STREAM])])
zeta = ZetaClient(access_token="AT", session=session)
check(
    "iter_text は差分だけ返す",
    list(zeta.chat.iter_text(zeta.chat.send("R1", "x"))),
    ["あ", "い", "う", "えお……は？"],
)

session = FakeSession([FakeStreamResponse([_CHUNK.format("あい") + "\n\n"])])
zeta = ZetaClient(access_token="AT", session=session)
check(
    "CHAT_COMPLETE が無ければ最後の IN_PROGRESS",
    zeta.chat.collect(zeta.chat.send("R1", "x")),
    "あい",
)

# 最終形が途中経過と食い違っても、全文を出し直さず違う所だけ出す
_DIVERGE = "\n\n".join(
    [
        _CHUNK.format("あいう"),
        'data:{"event":"CHAT_COMPLETE","replyMessage":{"contents":[{"type":"TEXT","text":"あい\\nえお"}]}}',
    ]
) + "\n\n"
session = FakeSession([FakeStreamResponse([_DIVERGE])])
zeta = ZetaClient(access_token="AT", session=session)
check(
    "食い違っても重複させない",
    list(zeta.chat.iter_text(zeta.chat.send("R1", "x"))),
    ["あいう", "\nえお"],
)

session = FakeSession([FakeStreamResponse(['data: {"event":"ERROR","message":"だめ"}\n\n'])])
zeta = ZetaClient(access_token="AT", session=session)
check_raises(
    "collect は ERROR で止まる",
    lambda: zeta.chat.collect(zeta.chat.send("R1", "x")),
    RuntimeError,
)

print("\n名前空間")
zeta = ZetaClient()
for ns in ("auth", "users", "rooms", "chat", "plots", "lorebooks", "coin", "creator", "zeta_pass", "raw"):
    check(f"{ns} がある", hasattr(zeta, ns), True)
check("raw の dir は全件", len(dir(zeta.raw)), 332)
check_raises(
    "未知の名前は AttributeError",
    lambda: zeta.raw.no_such_endpoint,
    AttributeError,
)
check_raises("call も KeyError", lambda: zeta.call("no_such"), KeyError)

print("\n名前空間が参照する名前が実在するか")
import inspect  # noqa: E402

import zetapi.api as api_pkg  # noqa: E402

referenced: set[str] = set()
for _, cls in inspect.getmembers(api_pkg, inspect.isclass):
    source = inspect.getsource(cls)
    for line in source.splitlines():
        if '_call("' in line:
            referenced.add(line.split('_call("')[1].split('"')[0])
unknown = sorted(referenced - set(ENDPOINTS))
check(f"{len(referenced)} 個の参照すべてが実在", unknown, [])

print("\n" + "=" * 60)
if failures:
    print(f"失敗 {len(failures)} 件: {failures}")
    sys.exit(1)
print("全て通過")
