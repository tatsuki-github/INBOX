# 年次カレンダー CSV

指定年のカレンダーCSVを生成し、**Googleカレンダー**と**Notion**にインポートできます。
日付なしのメモも同じYAMLに書けます（Notion / 確認用CSV向け）。

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
python scripts/generate_calendar.py --year 2026

# 祝日のみ（カスタムYAMLが無い年、または別パスを指定しない場合）
python scripts/generate_calendar.py --year 2027

# カスタム予定のみ（祝日なし）
python scripts/generate_calendar.py --year 2026 --no-include-holidays --input input/events.2026.yaml

# 入力ファイルを明示
python scripts/generate_calendar.py --year 2026 --input input/events.2026.yaml
```

出力:

| ファイル | 用途 |
|---|---|
| `out/YYYY/google.csv` | Googleカレンダー用（**日付付きのみ**。メモは除外） |
| `out/YYYY/notion.csv` | Notion用（予定 + 日付なしメモ） |
| `out/YYYY/source.csv` | 確認用（共通ビュー。`kind` 列で event / memo を区別） |

## 予定・メモの追加

`input/events.2026.yaml` を編集します（雛形: `input/events.YYYY.yaml.example`）。

```yaml
year: 2026
events:
  - title: 健康診断
    date: 2026-03-10
    all_day: true
    category: 予定

  - title: 定例ミーティング
    date: 2026-01-15
    all_day: false
    start_time: "10:00"
    end_time: "11:00"
    category: 予定
    location: オンライン

  # date を省略すると日付なしメモ
  - title: 買い物リスト
    category: メモ
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
| `description` | 任意 | 説明・メモ本文 |
| `location` / `private` | 任意 | 場所 / Google Private |

編集後、再度 `python scripts/generate_calendar.py --year 2026` を実行してください。

## インポート手順

### Googleカレンダー

1. [Googleカレンダー](https://calendar.google.com/) → 設定 → **インポート/エクスポート**
2. `out/YYYY/google.csv` を選択
3. 投入先カレンダーを選んでインポート

※ Googleは開始日が必要なため、日付なしメモは含まれません。

### Notion

1. Notion → 設定 → **Import** → CSV（または既存DBへマージ）
2. `out/YYYY/notion.csv` を選択
3. `Date` を Date 型にし、Calendar ビューを追加
4. 日付なしメモは Table / List ビューで一覧する（`Date` が空の行）

## 注意

- Google と Notion で日付形式が異なるため、CSVは別ファイルです
- Notionへの再インポートは追記のみ（重複に注意）
- Google CSVは公式ヘッダー・`MM/DD/YYYY` 形式です
- 日付なしメモは Notion / source のみ。Google からは自動除外されます
