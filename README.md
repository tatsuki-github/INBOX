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
| `out/YYYY/events.json` | 全イベント JSON（`practice` フィールド含む） |
| `out/YYYY/practice.json` | 練習イベント + パース状態 |
| `out/YYYY/practice_items.csv` | 1行 = 1メニュー項目（`absentees` 列付き） |
| `out/YYYY/practice_absentees.csv` | 1行 = 1欠席者（セッション×選手） |
| `out/YYYY/practice-summary.md` | 月別集計・未パース一覧 |
| `out/daiming-practice-menus-kpace.md` | 岱明練習 k/pace 一覧 |
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

### 岱明練習（構造化メニュー）

練習メニューは `practice` フィールドで構造化できます（`description` は表示用）。

```yaml
  - title: いだてん岱明夕練
    date: 2026-08-14
    all_day: false
    start_time: "18:00"
    end_time: "19:30"
    category: 予定
    status: scheduled
    tags: [ランニング, いだてん岱明練習, practice:daiming, session:evening]
    practice:
      warmup: 動きづくり
      absentees: [松野, 塚原]  # 任意。空配列 [] = 欠席者なし
      items:
        - type: interval
          distance_m: 600
          reps: 2
          intensity: 1500mRP
          rest_sec: 480
    description: |
      動きづくり
      600m×2（1500mRP、レスト8分）
```

関連ファイル:

- `input/practice_templates.yaml` — メニューテンプレート集
- `input/practice_schedules.yaml` — 朝練/夕練スケジュール
- `docs/data-model.md` — データ辞書

```bash
# 練習タグ正規化
python3 scripts/normalize_practice_tags.py --apply --year 2026

# description から practice をバックフィル（2025–2026）
python3 scripts/backfill_practice.py --dry-run --year 2026
python3 scripts/backfill_practice.py --apply --year 2026

# description から practice.absentees をバックフィル
python3 scripts/backfill_absentees.py --dry-run --year 2025
python3 scripts/backfill_absentees.py --apply --year 2025

# YAML lint（JSON Schema）
python3 scripts/lint_events.py --year 2026

# 練習データのみエクスポート
python3 scripts/export_practice.py --year 2026
```

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

## 荒尾・玉名 中学生記録 PDF

Notion「2026年度中学生記録」から荒尾・玉名地区の全記録（SB採用フィルタなし）を取得し、所属別に整理した PDF を生成します。

### 前提

1. [Notion Integration](https://www.notion.so/my-integrations) を作成し、対象データベースへ接続
2. 環境変数 `NOTION_TOKEN` に Integration Token を設定

```bash
export NOTION_TOKEN=secret_xxxxxxxx
```

### 実行

```bash
# Notion から取得 → PDF 生成
python3 scripts/generate_arato_tamana_pdf.py

# 設定・出力先を指定
python3 scripts/generate_arato_tamana_pdf.py \
  --config input/arato_tamana_report.yaml \
  --output out/analysis/2026年度_荒尾玉名中学生記録一覧.pdf

# 取得結果をキャッシュして再利用
python3 scripts/generate_arato_tamana_pdf.py \
  --cache out/analysis/notion_records_2026.json

# キャッシュから PDF のみ再生成（オフライン）
python3 scripts/generate_arato_tamana_pdf.py \
  --from-cache out/analysis/notion_records_2026.json
```

出力:

| ファイル | 内容 |
|---|---|
| `out/analysis/2026年度_荒尾玉名中学生記録一覧.pdf` | ランキング + 全記録一覧 |
| `out/analysis/2026年度_荒尾玉名中学生_所属別ランキング.pdf` | **ランキングのみ** |

GitHub から直接ダウンロード:

- [記録一覧 PDF（ランキング付き）](https://github.com/tatsuki-github/INBOX/raw/main/out/analysis/2026年度_荒尾玉名中学生記録一覧.pdf)
- [所属別ランキング PDF（ランキングのみ）](https://github.com/tatsuki-github/INBOX/raw/main/out/analysis/2026年度_荒尾玉名中学生_所属別ランキング.pdf)

PDF 先頭に **所属別ランキング** を掲載します。

| 種目 | 内容 |
|---|---|
| 800m 実記録 | 各選手の 800m SB（なければベスト） |
| 1500m 実記録 | 各選手の 1500m SB（なければベスト） |
| 3000m 実記録 | 各選手の 3000m SB（なければベスト） |
| 3000m 予想タイム | 3000m SB → 1500m SB 換算 → 800m SB 換算の順 |

| 性別 | 平均列 | ランキング対象 |
|---|---|---|
| 男子 | 上位4人 / 5人 / 6人平均 | 6人以上 |
| 女子 | 上位3人 / 4人 / 5人平均 | 5人以上 |

| 列 | 内容 |
|---|---|
| 名前 / 学年 / 性別 / 距離 / 記録 / 日付 / URL | Notion の各列。`SB採用=true` の行は記録に `★` 付与 |

### Google Drive へのアップロード

PDF はリポジトリ内に生成されます。Drive の「分析」フォルダへは **最新版を上書きアップロード** してください（古いファイルのままだとランキングが表示されません）。

- [分析フォルダ（Google Drive）](https://drive.google.com/drive/folders/18J1Yy52SRn1oB23I0jOoCrbiXwIZTqpC)
- 推奨: 上記2ファイル（記録一覧 + 所属別ランキング）を両方アップロード

### テスト

```bash
python3 -m pytest tests/test_arato_tamana_records.py -q
```

## AI 練習計画生成

自然言語から `practice` YAML を生成（テンプレ参照 + lint + Norwegian Method）。詳細: [`docs/ai-practice-generation.md`](docs/ai-practice-generation.md)

```bash
python3 scripts/generate_practice.py --input "夕練、軽いポイント" --date 2026-08-21 --dry-run
python3 scripts/generate_weekly_plan.py --week 2026-03-09 --dry-run
python3 scripts/build_rag_index.py
```

## 注意

- Google と Notion で日付形式が異なるため、CSVは別ファイルです
- Notionへの再インポートは追記のみ（重複に注意）
- Google CSVは公式ヘッダー・`MM/DD/YYYY` 形式です
- 日付なしメモは Notion / source のみ。Google からは自動除外されます
- `status` の値は自由です。運用例: `inbox` → `next` → `done`
