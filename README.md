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

### 実サーバーで通してあります（v0.2.0〜）
v0.1.0 は「バイトコードから読んだ仕様」だけで作っていて疎通未確認だった。
v0.2.0 で実際に叩いて確かめ、**間違っていた3箇所を直した**（[何が変わったか](#v020-で直したこと)）。

## Let's Go!

#### example.py

```py
from zetapi import ZetaClient

# ① いきなり動かしたいならこれ。ログイン不要で 1 行
zeta = ZetaClient.anonymous(language="ja")

# ② トークン持ってるならこっち
zeta = ZetaClient(
    access_token="...",
    refresh_token="...",
    device_id="...",      # 固定してね（省くと毎回別端末扱い）
    language="ja",        # ko / en も通る（JAPANESE 等に自動変換される）
)

# ③ 外部 IdP から本ログインすることも出来る
zeta = ZetaClient(device_id="...")
zeta.auth.login_external("GOOGLE", "IdPから貰ったcodeかIDトークン")
# issuer は GOOGLE / APPLE / KAKAO / LINE / FACEBOOK
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
zeta.plots.ranking("DAILY")             # WEEKLY なども。省略時は DAILY
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
# 流れてくる文字をそのまま出したいなら iter_text（増えた分だけ来る）
for delta in zeta.chat.iter_text(zeta.chat.send(room_id, "こんにちは")):
    print(delta, end="", flush=True)

# 全部溜めて文字列で欲しいだけなら
text = zeta.chat.collect(zeta.chat.send(room_id, "元気？"))

# 生イベントが要るなら send() をそのまま回す
for event in zeta.chat.send(room_id, "やあ"):
    print(event["event"])       # IN_PROGRESS ... IN_PROGRESS, CHAT_COMPLETE

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
JSON パースする、という素朴な作り（アプリも Web もそうしてる）。
チャンク境界がイベント境界とズレても大丈夫なようにバッファリングしてある。

イベントは 2 種類だけ。実際に流れてくるのはこういう形：

```jsonc
// 生成中（何十回も来る）
{"event":"IN_PROGRESS","chunkMessage":{"contents":[{"type":"TEXT","speakerName":"ナレーター","position":"NARRATOR","text":"*その声は、廃墟の奥から"}]},"index":null}

// 完了（最後に 1 回だけ）
{"event":"CHAT_COMPLETE","replyMessage":{"contents":[ ...話者ごとに分かれた最終形... ],"id":"MESSAGE-...","candidateId":"..."},"requestMessage":{...},"shouldGenerateConsecutive":false}
```

**`IN_PROGRESS` の `text` は差分ではなく毎回「その時点の全文」**。
素朴に繋ぐと同じ文が何重にもなるので、`iter_text()`（差分だけ）か
`collect()`（最終形だけ）を使ってほしい。

最終的な返信は `CHAT_COMPLETE` の `replyMessage.contents[]` に、
キャラごとに `speakerName` / `position`（`NARRATOR` / `LEFT` など）付きで入っている。

### 言語コードに注意

`X-User-Language` に入るのは **`JAPANESE` / `KOREAN` / `ENGLISH`**。
ここに `ja` を入れると API が **500 を返す**（400 じゃなくて 500 なので気付きにくい）。
`language="ja"` と書いても内部で `JAPANESE` に直すようにしてあるので普段は気にしなくていい。

```py
from zetapi import normalize_language
normalize_language("ja")        # 'JAPANESE'
normalize_language("ENGLISH")   # 'ENGLISH'
```

### 設定いろいろ

```py
zeta = ZetaClient(
    access_token="...",
    language="ja",              # X-User-Language（JAPANESE に正規化される）
    device_type="android",      # ios / web / pc_web にもできる
    client_type="app",          # web にもできる
    timeout=30.0,
    auto_refresh=True,          # False で 401 自動リトライを切る
    session=my_requests_session, # プロキシとか刺したい時はセッションごと差し替え
)
```

トークンの中身は API を叩かずに読める（JWT なので）：

```py
zeta.token_claims    # {'uid': ..., 'did': ..., 'ano': True, 'cty': 'JAPANESE', 'tz': ..., 'exp': ...}
zeta.user_id         # uid
zeta.is_anonymous    # ano
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

### オンライン（トークン不要になりました）

```py
# ① 匿名トークンを自動で取って疎通確認。何も用意しなくていい
py -3 tests/test_online.py

# ② 生きてる GET を数える（73 本を総当たり）
py -3 tests/test_online.py --sweep --json report.json

# ③ 自分のアカウントで試すなら従来どおりトークンを渡す
py -3 tests/test_online.py --token <アクセストークン> --sweep

# ④ ルーム作成 → 発言 まで通す
py -3 tests/test_online.py --plot <PLOT_ID> --write
```

**既定は読み取りのみ。** `delete` / `purge` / `logout` / 課金 / ブロック / 通報 は
何を指定しても呼ばないようにフィルタしてある（`tests/test_online.py` の `DENY_WORDS`）。
`--sweep` の対象は「GET かつパスパラメータ無しかつ危険語なし」の 73 本だけで、
残り 259 本は自動で除外される。

`--json report.json` を付けると全部の結果（ステータス・エラー本文込み）が残るので、
そのまま投げてくれるのが一番早い。

匿名アカウントは実行のたびに新しく生えるので、`--write` で書き込んでも
自分のアカウントは汚れない。

## トークンはどうやって手に入れる？

### いちばん簡単：匿名トークン（ログイン不要）

Web（`zeta-ai.io`）は**未ログインの訪問者にもアカウントを1つ発行している**。
ただ GET するだけで `TOKEN` / `REFRESH_TOKEN` / `DEVICE_ID` が Set-Cookie で降ってくるので、
それをそのまま使う。

```py
zeta = ZetaClient.anonymous(language="ja")
zeta.is_anonymous       # True
zeta.users.me()         # {'username': 'AntsyGoose3091', ...}  勝手に名前が付いてる
```

既存のクライアントに載せたいなら `zeta.auth.login_anonymous()`。

**匿名で出来ること／出来ないこと**（実際に叩いて確認した）：

| | |
|---|---|
| 出来る | プロフィール取得 / ランキング / 検索 / 補完 / ホーム / ジャンル / 無限プロット / **ルーム作成** / **チャット送信** / トークン更新 |
| 出来ない | コイン残高・デイリー報酬 / スクラップ（お気に入り） / クリエイター統計 / チャットプロフィール |

出来ない側は `401 ANONYMOUS_NOT_ALLOWED` が返る。つまり
**「読む・喋る」だけなら匿名で足りて、「所有物が絡む」と本ログインが要る**。

### ちゃんとログインする：外部 IdP

`/v1/auth/tokens` がトークン発行の唯一の入口で、受け付けるのは
`type: "refresh"`（更新）と `type: "external"`（外部 IdP）の2つだけ。
`anonymous` や `guest` みたいな type は試したけど 400 で弾かれた（匿名は上の Web 経由が唯一の入口）。

**メアド＋パスワードでログインする口は無い。** どこかから IdP のトークンを貰ってくる必要がある。

Web 版のログイン画面が使っているクライアント ID は全部拾ってあるので、認可 URL は組み立てられる：

```py
from zetapi import authorize_url

authorize_url("GOOGLE")   # ブラウザで開く → 認証 → ?code=... で戻ってくる
authorize_url("LINE")
authorize_url("KAKAO")
authorize_url("APPLE")

zeta.auth.login_external("GOOGLE", "<戻ってきた code>")
```

| issuer | 種別 | 値 |
|---|---|---|
| GOOGLE | OAuth client ID | `525134294958-mljfskqips16vo9so99v3eroniqi85gf.apps.googleusercontent.com` |
| LINE | channel ID | `2002675299` |
| KAKAO | JavaScript key | `a910522abf6591852f96f59c651723f5` |
| APPLE | Services ID | `io.zeta-ai` |

いずれも Web のバンドルに平文で置かれている公開値で、秘密鍵ではない。

Web 版は取得した `code` を Next.js の Server Action（`externalLogin`）に渡していて、
そこから先はサーバー側で `/v1/auth/tokens` に流している。なので
**`login_external` に code をそのまま渡して通るかは未検証**（有効な IdP アカウントが要るので試せていない）。
ID トークンを持っているならそちらを渡すのが確実。ここは動作報告が欲しいところ。

もう一つ確実なのは **mitmproxy 派**：アプリか Web のログイン通信を横取りして
`accessToken` / `refreshToken` を抜く。一番早い。

ちなみに `/v1/nutty/sms` みたいな SMS 認証系のエンドポイントは生えてるけど、
これは旧 Nutty からのアカウント移行用で Zeta のログインには使えない。

どの経路でも `refresh_token` さえ確保しとけば以降は自動更新なので、最初の一回だけ頑張れば勝ち。

## 復元した仕様

出典は2つ。アプリ 3.42.4（`com.scatterlab.messenger`）の `assets/index.android.bundle` と、
Web 3.44.7（`zeta-ai.io`）の Next.js チャンク。

| 項目 | 内容 |
|---|---|
| ベースURL | `https://api.zeta-ai.io` |
| 認証 | `Authorization: Bearer <accessToken>` |
| 共通ヘッダ | `X-Client-Version` / `X-Client-Native-Version` / `X-Client-Type: app\|web` / `X-Device-Type: android\|ios\|web\|pc_web` / `X-User-Language: JAPANESE\|KOREAN\|ENGLISH` / `X-Sticky: <deviceId>` |
| アクセストークン | JWT。`uid` / `did` / `ano`（匿名か） / `cty` / `tz` / `exp` が入っている。有効期限は7日 |
| トークン更新 | `POST /v1/auth/tokens` に `{deviceId, type:"refresh", refreshToken}` → `{accessToken, refreshToken}` |
| ログイン | 同じ口に `type:"external"` + `externalToken:{issuer, token}` |
| 匿名発行 | API に口は無い。`GET https://zeta-ai.io/<lang>` の Set-Cookie で降ってくる |
| 新規登録 | `POST /v1/users` に `deviceId, name, username, birthdate, gender, chatProfileDescription, externalToken, language, marketingOptIn, existingToken, timeZone` |
| チャット | `POST /v1/rooms/:roomId/messages/stream` に `{"type":"TEXT","text":"..."}`、`Accept: text/event-stream` |

他のホスト：`image.zeta-ai.io`（画像CDN）、`creator-assistant.zeta-ai.io`、
`zeta-ai.io`（Web）、`web-cdn.zeta-ai.io`（Web の静的ファイル）。

## v0.2.0 で直したこと

実サーバーに通して初めて分かった間違いが3つあった。どれも 0.1.0 では致命的だった。

| 直したもの | 0.1.0（誤） | 0.2.0（正） | 症状 |
|---|---|---|---|
| `X-User-Language` | `ja` | `JAPANESE` | **全リクエストが 500**。0.1.0 は事実上何も動いていなかった |
| チャット送信ボディ | `{"content":{"type","text"}}` | `{"type","text"}` | 400 `Failed to read HTTP message` |
| 検索のクエリ名 | `query=` | `keyword=` | 400 `Required query parameter 'keyword' is not present` |

加えて `chat.collect()` は `TOKEN` イベントを連結する実装だったが、実際のイベントは
`IN_PROGRESS` で中身が累積のため、連結すると壊れる。最終形を返すよう直した上で、
差分だけ流す `chat.iter_text()` を足した。
`plots.ranking()` は必須の `type` を送っていなかったので既定 `DAILY` を入れた。

新しく入ったもの：`ZetaClient.anonymous()` / `auth.login_anonymous()` /
`authorize_url()` / `token_claims` / `user_id` / `is_anonymous` / `normalize_language()`。

## 分かってないところ

隠さず書いとく。

- **本ログインの疎通が未確認。** 認可 URL は組めるし `login_external` も実装してあるけど、
  IdP から貰った `code` をそのまま渡して通るのか、ID トークンに交換してからなのかを
  確かめられていない（有効な IdP アカウントが要るので）。動いた／動かなかったの報告が欲しい。
- **匿名で弾かれる領域が未検証。** コイン・スクラップ・クリエイター系は
  `ANONYMOUS_NOT_ALLOWED` で入れないので、本ログインしないと確認できない。
- **再生成・選択肢（CYOA）のボディ。** `chat.regenerate()` / `chat.options()` は
  ボディ無しで投げている。チャット本体が入れ子なしで通ったので同じ形かもしれないが未確認。
  足りなかったら `zeta.chat.send_raw(room_id, {...})` で好きなボディを丸投げして。
  `type` は `TEXT` / `IMAGE` / `CYOA` / `OPTION` / `SITUATION` / `INTRO`。
- **書き込み系のリクエストボディ全般。** プロット作成・ロアブック・プロフィール更新あたりは
  レスポンス型の名前しか分かっていない。Web のチャンクに DTO のフィールド名は残っているので、
  必要になったら掘れる。
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

### v0.2.0 では Web 版も見た

APK だけ見ていたのが 0.1.0 の敗因だった。`zeta-ai.io` は Next.js で、
チャンクを辿れば **難読化されていても構造がそのまま読める**。しかも
Sentry 用の `data-sentry-source-file` が残っているので、
`SocialLoginArea.tsx` `ExternalLogin.tsx` みたいな**元のファイル名で目的の場所を探せる**。

Hermes バイトコードと違って、こっちには

- リクエスト DTO のフィールド名（アプリ側には残っていなかったもの）
- 各 IdP のクライアント ID とログインの流れ
- API クライアントのヘッダ構成（`X-Client-Type: web` など）
- `TokenIssuer` / `Language` などの enum の実際の値

が全部揃っていた。**同じサービスの別クライアントを見る**のが一番効いた、という話。

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
