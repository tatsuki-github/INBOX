# 年次カレンダー CSV

指定年のカレンダーCSVを生成し、**Googleカレンダー**と**Notion**にインポートできます。

- 日本の祝日を自動追加（`jpholiday`）
- `input/events.YYYY.yaml` に自分の予定を追加可能
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
| `out/YYYY/google.csv` | Googleカレンダー用 |
| `out/YYYY/notion.csv` | Notion用 |
| `out/YYYY/source.csv` | 確認用（共通ビュー） |

## 予定の追加

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
```

編集後、再度 `python scripts/generate_calendar.py --year 2026` を実行してください。

## インポート手順

### Googleカレンダー

1. [Googleカレンダー](https://calendar.google.com/) → 設定 → **インポート/エクスポート**
2. `out/YYYY/google.csv` を選択
3. 投入先カレンダーを選んでインポート

### Notion

1. Notion → 設定 → **Import** → CSV（または既存DBへマージ）
2. `out/YYYY/notion.csv` を選択
3. `Date` を Date 型にし、Calendar ビューを追加

## 注意

- Google と Notion で日付形式が異なるため、CSVは別ファイルです
- Notionへの再インポートは追記のみ（重複に注意）
- Google CSVは公式ヘッダー・`MM/DD/YYYY` 形式です
