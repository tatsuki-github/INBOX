# 年次カレンダー / INBOX CSV

指定年のカレンダーCSVを生成し、**Googleカレンダー**と**Notion**にインポートできます。
日付なしメモと、`status` / `tags` / `urls` などの INBOX メタデータも同じYAMLで管理できます。

- 日本の祝日を自動追加（`jpholiday`）
- `input/events.YYYY.yaml` に自分の予定・メモを追加可能
- 出力は年フォルダごと（`out/YYYY/`）

## セットアップ

```bash
pip install -r requirements.txt
```

## 使い方

```bash
# 2026年（祝日 + input/events.2026.yaml があれば自動マージ）
python3 scripts/generate_calendar.py --year 2026

# 全年分を一括生成
python3 scripts/generate_calendar.py --all-years

# 祝日のみ（カスタムYAMLが無い年）
python3 scripts/generate_calendar.py --year 2028

# カスタム予定のみ（祝日なし）
python3 scripts/generate_calendar.py --year 2026 --no-include-holidays --input input/events.2026.yaml

# 入力ファイルを明示
python3 scripts/generate_calendar.py --year 2026 --input input/events.2026.yaml
```

出力:

| ファイル | 用途 |
|---|---|
| `out/YYYY/google.csv` | Googleカレンダー用（**日付付きのみ**。メモは除外。status/tags/urls は Description に付記） |
| `out/YYYY/notion.csv` | Notion用（予定 + メモ + Status / Tags / URLs 列） |
| `out/YYYY/source.csv` | 確認用（共通ビュー。`kind` で event / memo を区別） |
| `out/YYYY/calendar.md` | GitHub閲覧用（月次 Markdown カレンダー。予定がある日のみ表示） |
| `calendar.md` | **今年**のカレンダー（`out/YYYY/calendar.md` と同一内容をルートにも配置） |

## 予定・メモの追加

### 手編集

`input/events.2026.yaml` を編集します（雛形: `input/events.YYYY.yaml.example`）。

```yaml
year: 2026
events:
  - title: 健康診断
    date: 2026-03-10
    all_day: true
    category: 予定
    status: next
    tags: [health, personal]
    urls:
      - https://example.com/health-check

  - title: 定例ミーティング
    date: 2026-01-15
    all_day: false
    start_time: "10:00"
    end_time: "11:00"
    category: 予定
    status: scheduled
    tags: [work, meeting]
    location: オンライン

  # date を省略すると日付なしメモ
  - title: 買い物リスト
    category: メモ
    status: inbox
    tags: [errand]
    description: |
      - 牛乳
      - 卵
```

| フィールド | 必須 | 説明 |
|---|---|---|
| `title` | 必須 | 件名 |
| `date` | 任意 | 開始日。**省略すると日付なしメモ** |
| `end_date` | 任意 | 終了日（メモには不可） |
| `all_day` | 任意 | 終日か（デフォルト: true） |
| `start_time` / `end_time` | 条件付き | 時刻付き予定用（メモには不可） |
| `category` | 任意 | デフォルトは予定=`予定` / メモ=`メモ` |
| `status` | 任意 | `inbox` / `next` / `waiting` / `done` / `scheduled` など自由記述。メモのデフォルトは `inbox` |
| `tags` | 任意 | リスト、またはカンマ区切り文字列 |
| `urls` / `url` | 任意 | 関連URL（リスト・カンマ区切り・単数 `url` 可） |
| `description` | 任意 | 説明・メモ本文 |
| `description_file` | 任意 | 本文を別ファイルから読み込む（`input/` からの相対パス可）。`description` と併用時は説明が先頭に付く |
| `location` / `private` | 任意 | 場所 / Google Private |

編集後、再度 `python3 scripts/generate_calendar.py --year 2026` を実行してください。

### GitHub でカレンダー形式で見る

`out/YYYY/calendar.md` またはルートの `calendar.md`（**今年分のみ**）を GitHub 上で開くと、月ごとの表形式で予定を確認できます。
先頭に月別ジャンプリンクがあり、各月見出しへ移動できます。
表内の予定名をクリックすると、その月末尾の「予定詳細」セクションへ移動し、`<details>` を開いて件名・日付・時刻・タグ・URL・説明など**全フィールド**を確認できます。
各月の詳細セクション末尾に `[↑2026年8月]` `[↑ページトップ]` リンクがあり、月表や先頭へ戻れます。
日付なしメモも同様に `<details>` で全文を確認できます。
この形式は `out/YYYY/calendar.md` の**全年分**に出力されます（ルートの `calendar.md` は今年分のコピー）。
予定がある日だけが表示され、時刻付き予定は `HH:MM` 付きでリンクテキストに含まれます。

### Notion CSV から一括取り込み

NotionでエクスポートしたCSVを年ごとのYAMLに変換できます。

対応列の例:

- カレンダー系: `名前`, `日時`, `メモ`, `場所`, `URL`, `タグ`
- INBOX系: `名前`, `日付`, `メモ`, `URL`, `タグ`, `状態`, `領域`

`日付`/`日時` がある行は予定、空の行は日付なしメモとして取り込みます（メモは `--memo-year` の年ファイルへ）。

```bash
# 既存データに追記マージ（デフォルト）
python3 scripts/import_notion_csv.py --csv path/to/notion_export.csv --memo-year 2026
python3 scripts/generate_calendar.py --all-years
```

### Strava API から自分の練習を取り込む

[Strava API](https://developers.strava.com/) で自分のアクティビティを取得し、`input/events.YYYY.yaml` に追記できます。重複は Strava のアクティビティ URL で判定します。

#### 1. アプリ作成と環境変数

1. [Strava API 設定](https://www.strava.com/settings/api) でアプリを作成（サブスクリプションが必要）
2. Authorization Callback Domain に `localhost` を設定
3. 環境変数を設定:

```bash
export STRAVA_CLIENT_ID=xxxxx
export STRAVA_CLIENT_SECRET=xxxxx
```

#### 2. 初回認可（トークン取得）

```bash
python3 scripts/import_strava.py auth
# 表示されたURLをブラウザで開き、認可後のリダイレクトURLから code= をコピー
python3 scripts/import_strava.py auth --code YOUR_CODE
```

トークンは `.strava_tokens.json` に保存されます（gitignore 済み。コミットしないでください）。

#### 3. 取り込み → カレンダー再生成

```bash
# 例: 2026-01-01 以降のアクティビティ
python3 scripts/import_strava.py import --after 2026-01-01

# Run のみ
python3 scripts/import_strava.py import --after 2026-08-01 --sport Run

# 書き込まず件数確認
python3 scripts/import_strava.py import --after 2026-08-01 --dry-run

# カレンダー再生成
python3 scripts/generate_calendar.py --year 2026
```

| オプション | 説明 |
|---|---|
| `--after` / `--before` | 期間フィルタ（`YYYY-MM-DD`） |
| `--sport` | `sport_type` で絞り込み（複数可） |
| `--title-mode` | `personal`（デフォルト: 件名「自分の練習」）/ `strava` / `sport` |
| `--update` / `--no-update` | 同一 Strava ID の更新（デフォルト: 更新する） |
| `--from-json` | API の代わりに保存済み JSON 配列を使う |

取り込まれた予定はタグ `自分の練習` / `strava` / 種別名、URL に Strava へのリンク、説明に距離・ペース等を付与します。

定期実行するなら、同梱の GitHub Actions（`.github/workflows/import-strava.yml`）を使えます。

1. ローカルで `auth` を完了し、`.strava_tokens.json` の `refresh_token` を控える
2. リポジトリ Secrets に `STRAVA_CLIENT_ID` / `STRAVA_CLIENT_SECRET` / `STRAVA_REFRESH_TOKEN` を登録
3. Actions の **Import Strava practices** を手動実行、または毎日 21:00 JST の schedule を待つ

Strava が refresh_token をローテーションした場合は、ジョブログの注意に従い Secrets を更新してください。

## インポート手順

### Googleカレンダー

1. [Googleカレンダー](https://calendar.google.com/) → 設定 → **インポート/エクスポート**
2. `out/YYYY/google.csv` を選択
3. 投入先カレンダーを選んでインポート

※ Googleは開始日が必要なため、日付なしメモは含まれません。
※ `status` / `tags` / `urls` は Description 本文に付記されます。

### Notion

1. Notion → 設定 → **Import** → CSV（または既存DBへマージ）
2. `out/YYYY/notion.csv` を選択
3. 型の目安:
   - `Date` / `End Date` → Date
   - `Status` → Status または Select
   - `Tags` → Multi-select（カンマ区切り）
   - `URLs` → URL または Text（複数行の場合は Text）
4. Calendar ビュー（日付あり）と Table / List ビュー（メモ含む）を用意

## 注意

- Google と Notion で日付形式が異なるため、CSVは別ファイルです
- Notionへの再インポートは追記のみ（重複に注意）
- Google CSVは公式ヘッダー・`MM/DD/YYYY` 形式です
- 日付なしメモは Notion / source のみ。Google からは自動除外されます
- `status` の値は自由です。運用例: `inbox` → `next` → `done`
