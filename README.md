# zetapi

Zeta（ゼータ / ScatterLab）の非公式 Python API ラッパーだよ。
**高レベル 129 メソッド / raw 332 エンドポイント** — アプリで出来ることは、だいたい出来ると思う。

## インストール

```sh
pip install zetapi
```

依存は `requests` だけ。軽いでしょ。Python は 3.10 以上。

###### インストール名と import 名は `zetapi`
```py
from zetapi import ZetaClient
```

ローカルで弄りたい人はこっち：

```sh
pip install -e .
```

## 始める前に確認すること

### これは非公式です
ScatterLab とは縁もゆかりもありません。中の人でもないです。
非公式 API を叩くのは規約的にたぶんアウトなので、**自分のアカウントで、自己責任で**遊んでね。
垢が凍っても「あーあ」って一緒に言うことしか出来ないよ。

### トークンは保存して使い回して
毎回ログインし直すとセッションが積み上がってよくない気がする。
**access / refresh / device_id の3点セットを保存して使い回して**。それだけで寿命が伸びる。

### device_id は固定して
省略すると毎回ランダム UUID が生えて、サーバーから見ると**毎回新しい端末**。
`X-Sticky` ヘッダと各種 API の `deviceId` に入る値なので、一度決めたらメモっとくのが吉。

### 実サーバーでは試してません
正直に言うけど、**有効なトークンが手元に無いので実際の疎通は未確認**。
テストは全部オフライン（ヘッダ組み立て・URL・クエリ直列化・401リトライ・SSE分解）。
仕様自体はバイトコードから読んだやつなので合ってるはずだけど、動かなかったら Issue 投げて。

## Let's Go!

#### example.py

```py
from zetapi import ZetaClient

# ① トークン持ってるならこれだけ
zeta = ZetaClient(
    access_token="...",
    refresh_token="...",
    device_id="...",      # 固定してね（省くと毎回別端末扱い）
    language="ja",        # ko / en も通る
)

# ② 外部 IdP のトークンからログインすることも出来る
zeta = ZetaClient(device_id="...")
zeta.auth.login_external("GOOGLE", "IdPのIDトークン")
# issuer は GOOGLE / APPLE / KAKAO / LINE / FACEBOOK / EMAIL
print(zeta.access_token, zeta.refresh_token)   # 成功すると勝手に入ってる

# ─────────────────────────────────────────
# プロフィールとコイン
me = zeta.users.me()
print(me["username"], me["id"])

print(zeta.coin.balance())              # 残高
print(zeta.coin.daily_reward_left())    # デイリー報酬あと何回いける？
zeta.coin.claim_daily_reward()          # もらう

# ─────────────────────────────────────────
# プロット（キャラ / シナリオ）を探す
zeta.plots.search("猫", limit=10)
zeta.plots.ranking()
zeta.plots.get("PLOT_ID")
zeta.plots.similar("PLOT_ID")

zeta.plots.like("PLOT_ID")              # いいね
zeta.plots.scrap("PLOT_ID")             # お気に入り
zeta.plots.scrapped()                   # お気に入り一覧

# ─────────────────────────────────────────
# ルーム（＝会話スレッド）
room = zeta.rooms.create("PLOT_ID")     # そのキャラと話し始める
room_id = room["id"]

zeta.rooms.list_v2(limit=20)            # ルーム一覧（アプリの現行版はこっち）
zeta.rooms.messages(room_id)            # 履歴
zeta.rooms.pin(room_id)                 # ピン留め
zeta.rooms.save(room_id)                # セーブ（ゲームのセーブデータ的なやつ）
zeta.rooms.load(room_id)                # ロード

# ─────────────────────────────────────────
# 本題：チャット。SSE なのでイベントが順に降ってくる
for event in zeta.chat.send(room_id, "こんにちは"):
    print(event.get("text"), end="", flush=True)

# 全部溜めて文字列で欲しいだけなら
text = zeta.chat.collect(zeta.chat.send(room_id, "元気？"))

zeta.chat.regenerate(room_id, "MESSAGE_ID")   # 気に入らなかったら生成し直し
zeta.chat.options(room_id)                    # 選択肢（CYOA）を出す
zeta.chat.example_chat("PLOT_ID")             # ルーム無しで会話例だけ見る

# ─────────────────────────────────────────
# 作る側
zeta.creator.assistant_quota()          # 生成の残り回数。叩く前にこれ見て
zeta.creator.generate_characters(...)   # AI にキャラ考えさせる
zeta.creator.generate_plot(...)         # AI にプロット考えさせる
zeta.creator.dashboard()                # 自作プロットの成績表

zeta.plots.create(...)                  # 下書き作る
zeta.plots.update_status("PLOT_ID", ...)  # 公開する

zeta.lorebooks.create(...)              # 設定資料（ロアブック）
zeta.lorebooks.attach("PLOT_ID", "LOREBOOK_ID")   # プロットに差す
```

長いけど使い方はコメントに全部書いたから、これ読めばだいたい分かるはず。

## 全部叩く → `zeta.raw`

高レベルに無いエンドポイントは `zeta.raw.<メソッド名>` で **332 本ぜんぶ**呼べる。
名前はアプリ内の `getRoomApi` みたいなやつを snake_case にしただけなので、素直。

```py
zeta.raw.get_room(roomId="...")                       # パスパラメータはキーワードで
zeta.raw.list_notifications(params={"limit": 3})      # クエリは params=
zeta.raw.update_room(roomId="...", data={...})        # ボディは data=

zeta.raw.list_coin_transactions(params={"limit": 50})
zeta.raw.request_daily_quiz()
zeta.raw.list_contest_plots()
```

全メソッド一覧が欲しかったら：

```py
python -c "from zetapi import ENDPOINTS; print('\n'.join(sorted(ENDPOINTS)))"
```

`help(zeta.raw.get_room)` すれば元のエンドポイントとレスポンス型が docstring に書いてある。迷ったら叩いて。

```
GET /v1/rooms/:roomId

JS 側の名前: getRoomApi
レスポンス型: RoomApiDto
```

## もう少し詳しく

### 返り値は素の dict

正直に言うと、pypaypay みたいな `.属性` アクセスの砂糖は**まだ無い**。
`me["username"]` って書いてね。レスポンスの型名（`RoomApiDto` とか）は分かってるけど
中身のフィールドまではバイトコードに残ってなかったので、変に型を偽装するよりは素で渡す方針にした。

### 401 は勝手に直る

`refresh_token` を渡しておくと **401 が来たら黙って更新して1回だけ叩き直す**。
無限ループはしないので、リフレッシュも死んでたら諦めて `ZetaAuthError` を投げる。

```py
zeta.auth.refresh()          # 手動で更新したい時はこれ
print(zeta.access_token)     # 更新後のが入ってる
```

### クエリの直列化がちょっと変

アプリは axios の `paramsSerializer` に `qs.stringify(p, {allowDots: true, arrayFormat: 'comma'})`
を刺してる。つまり：

```py
{"ids": [1, 2, 3]}      # → ids=1,2,3     （キー繰り返しじゃない）
{"a": {"b": {"c": 1}}}  # → a.b.c=1       （a[b][c] じゃない）
{"f": True}             # → f=true
{"a": None}             # → キーごと消える
```

ここを普通の `urlencode` でやると静かに違う結果になるので、`zetapi/_qs.py` で再現してある。

### チャットが SSE

`Accept: text/event-stream` を投げて、レスポンスを `\n\n` で切って `data:` 行だけ
JSON パースする、という素朴な作り（アプリもそうしてる）。
チャンク境界がイベント境界とズレても大丈夫なようにバッファリングしてある。

観測できたイベント種別は `TOKEN` / `START` / `END` / `COMPLETE` / `CYOA` / `ERROR`。

### 設定いろいろ

```py
zeta = ZetaClient(
    access_token="...",
    language="ja",              # X-User-Language
    device_type="android",      # ios にもできる
    timeout=30.0,
    auto_refresh=True,          # False で 401 自動リトライを切る
    session=my_requests_session, # プロキシとか刺したい時はセッションごと差し替え
)
```

## エラー

失敗したら例外が飛ぶ。種類で分けて捌けるやつ：

```py
from zetapi import ZetaAuthError, ZetaRateLimitError, ZetaHTTPError

try:
    zeta.users.me()
except ZetaAuthError:
    print("トークン死んだ")
except ZetaRateLimitError:
    print("落ち着け")
except ZetaHTTPError as e:
    print("なんか失敗:", e.status, e.code, e.message, e.body)
```

```
ZetaError
├── ZetaHTTPError                  # 4xx / 5xx
│   ├── .status                    #   HTTP ステータス
│   ├── .code                      #   レスポンスの code
│   ├── .message                   #   レスポンスの message
│   ├── .body                      #   全文（困ったらこれを print）
│   ├── ZetaAuthError              # 401 / 403
│   └── ZetaRateLimitError         # 429
└── ZetaTokenError                 # トークン更新そのものが失敗
```

## 動作確認

### オフライン（トークン不要）

```py
py -3 tests/test_zetapi.py
```

76 項目、**実サーバーには一切繋がない**。偽セッションを刺して、
ヘッダ・URL 組み立て・クエリ直列化・401 リトライ・SSE のチャンク境界復元・
名前空間が参照してる 82 個のエンドポイント名が実在するか、を見てる。

### オンライン（トークン要る）

```py
# ① まず疎通確認だけ。読み取りのみなので安全
py -3 tests/test_online.py --token <アクセストークン>

# ② 生きてる GET を数える（73 本を総当たり）
py -3 tests/test_online.py --token <AT> --sweep --json report.json

# ③ チャットのボディの正解を探る（これが一番知りたい）
py -3 tests/test_online.py --token <AT> --room <ROOM_ID> --probe-chat

# ④ ルーム作成 → 発言 まで通す
py -3 tests/test_online.py --token <AT> --plot <PLOT_ID> --write
```

**既定は読み取りのみ。** `delete` / `purge` / `logout` / 課金 / ブロック / 通報 は
何を指定しても呼ばないようにフィルタしてある（`tests/test_online.py` の `DENY_WORDS`）。
`--sweep` の対象は「GET かつパスパラメータ無しかつ危険語なし」の 73 本だけで、
残り 259 本は自動で除外される。

③ の `--probe-chat` は、チャットのリクエストボディの候補を6パターン順に投げて
**どれが通るか総当たりする**やつ。通った時点で実際にメッセージが送信されるので、
捨てて良いルームでやってね。ここが分かればデフォルトを直せる。
全部落ちたら 400 のレスポンス本文が出るので、それを見せてくれれば直せる。

`--json report.json` を付けると全部の結果（ステータス・エラー本文込み）が残るので、
そのまま投げてくれるのが一番早い。

## トークンはどうやって手に入れる？

先に結論。**メアド＋パスワードでログインする口は無い。**

`/v1/auth/tokens` がトークン発行の唯一の入口で、受け付けるのは
`type: "refresh"`（更新）と `type: "external"`（外部 IdP のトークン）だけ。
`external` に渡す `issuer` に `EMAIL` はあるんだけど、これは
「メールアドレスで認証する IdP が発行した**トークン**」であって、
パスワードを直接投げる口ではない。つまり結局どこかからトークンを貰ってくる必要がある。

ちなみに `/v1/nutty/sms` とか `/v1/nutty/sms/verify` みたいな SMS 認証系のエンドポイントは
生えてるけど、これは旧 Nutty からのアカウント移行用で Zeta のログインには使えない。

なので現実的な入手経路は2つ：

- **mitmproxy 派**：アプリのログイン通信を横取りして `/v1/auth/tokens` のレスポンスから
  `accessToken` / `refreshToken` を抜く。一番早い。
- **IdP 自前で通す派**：Google / Apple / LINE / KAKAO / Facebook の OAuth を自分で完了させて、
  貰った ID トークンを `zeta.auth.login_external("GOOGLE", "<IDトークン>")` に渡す。
  クライアント ID はアプリのバンドルに平文で入ってたので拾える。

どっちにしても `refresh_token` さえ確保しとけば以降は自動更新なので、最初の一回だけ頑張れば勝ち。

## 復元した仕様

出典はアプリ 3.42.4（`com.scatterlab.messenger`）の `assets/index.android.bundle`。

| 項目 | 内容 |
|---|---|
| ベースURL | `https://api.zeta-ai.io` |
| 認証 | `Authorization: Bearer <accessToken>` |
| 共通ヘッダ | `X-Client-Version: 3.42.4` / `X-Client-Native-Version` / `X-Client-Type: app` / `X-Device-Type: android\|ios` / `X-User-Language` / `X-Sticky: <deviceId>` |
| トークン更新 | `POST /v1/auth/tokens` に `{deviceId, type:"refresh", refreshToken}` → `{accessToken, refreshToken}` |
| ログイン | 同じ口に `type:"external"` + `externalToken:{issuer, token}` |
| 新規登録 | `POST /v1/users` に `deviceId, name, username, birthdate, gender, chatProfileDescription, externalToken, language, marketingOptIn, existingToken, timeZone` |

他のホスト：`image.zeta-ai.io`（画像CDN）、`creator-assistant.zeta-ai.io`、`zeta-ai.io`（Web）。

## 分かってないところ

隠さず書いとく。

- **チャット送信のリクエストボディが完全には確定できてない。** 送信フックが呼び出し側から
  body を丸ごと受け取る作りで、バイトコードから最終形まで追い切れなかった。
  ローカルに積まれるメッセージの形 `{"content": {"type", "text", "recommendedMessageId"}}`
  を既定にしてあるけど、足りなかったら `zeta.chat.send_raw(room_id, {...})` で
  好きなボディを丸投げして。`content.type` は `TEXT` / `IMAGE` / `CYOA` / `OPTION` / `SITUATION` / `INTRO`。
- **リクエストボディ全般。** レスポンス型（`RoomApiDto` とか）はバンドルに名前が残ってたけど、
  リクエスト側は残ってない。個別に調べるしかない。
- **課金系**（`/v1/zeta-pass/*`, `/v1/coin-products/*`）はストアのレシートが要るので、
  ラッパー単体では通せない。エンドポイントだけは生えてる。

## 余談：どうやって作ったか

APK を落として展開して、`assets/index.android.bundle` を
[hermes-dec](https://github.com/P1sec/hermes-dec) に食わせた。

このアプリ、中身は React Native + Hermes バイトコードで、Java 側はほぼ空っぽ。
自社コードは `com/scatterlab/messenger/` に 13 ファイルあるだけ。
Google Play の PairIP で保護は掛かってるんだけど、**RN バンドルは暗号化されてない**ので素通り。

で、逆コンパイルした 87MB の擬似 JS を眺めてたら、API 定義がこういう形で丸ごと残ってた：

```js
r1 = {'method': 'GET', 'url': '/v1/rooms/:roomId'};
r6 = r6.RoomApiDto;
r1['responseClass'] = r6;
r2['getRoomApi'] = r1;
```

`r0` `r1` みたいな仮想レジスタと `switch` ジャンプの塊なんだけど、
**この API 定義のところだけ異常に規則的**。ここまで綺麗だと拾ってくれと言われてる気がする。
なので正規表現でレジスタを追いかけて 332 件まるごと抜いた。
`zetapi/endpoints.py` は全部その自動生成物で、手書きしたところは1行も無い。

なお **jadx は 18,302 件のデコンパイルエラー**を吐いてた。Kotlin メタデータと難読化のせい。
でも今回欲しかったものは全部 JS 側にあったので、そっちは特に見なくて済んだ。ラッキー。

逆コンパイル成果物と元の APK はリポジトリに残してない（合計 400MB 超えてたので消した）。
`endpoints.py` を作り直したくなったら APK 取得からやり直してね。

## さらに余談

なんで zetapi なの？って思った？最初は py + Zeta で `zetapy` にするつもりだった。
でも PyPI を見たら**神経科学の ZETA-test のパッケージが先に `zetapy` を取ってた**。
スパイク列の統計解析をするやつで、こっちとは縁もゆかりも無い。
配布名も import 名も被せると、両方入れた人の環境で踏み潰し合って事故る。
なので Zeta + API で zetapi。以上。

## コンタクト / 貢献

バグとか「このメソッド名ダサくない？」とかは Issues に投げて。
PR も歓迎。エンドポイント追加はスクリプト自動生成だったので、
今は `endpoints.py` を直接いじる形になる（1行足すだけ）。

**実サーバーで動いたかどうかの報告が一番ありがたい。** こっちで確認できてないので。

## ライセンス

MIT。好きに使っていいよ。
Zeta の商標とサービス自体は当然 ScatterLab のもので、このライブラリは無関係の第三者製です。
