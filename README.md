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
| `location` / `private` | 任意 | 場所 / Google Private |

編集後、再度 `python3 scripts/generate_calendar.py --year 2026` を実行してください。

### GitHub でカレンダー形式で見る

`out/YYYY/calendar.md` またはルートの `calendar.md`（**今年分のみ**）を GitHub 上で開くと、月ごとの表形式で予定を確認できます。
先頭に月別ジャンプリンクがあり、各月見出しへ移動できます。
表内の予定名をクリックすると、その月末尾の「予定詳細」セクションへ移動し、件名・日付・時刻・タグ・URL・説明など**全フィールド**を確認できます。
各月の詳細セクション末尾に `[↑2026年8月]` `[↑ページトップ]` リンクがあり、月表や先頭へ戻れます。
日付なしメモも同様にリンクと「メモ詳細」セクションで全文を確認できます。
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
