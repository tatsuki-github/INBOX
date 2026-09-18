# データモデル

INBOX / 年次カレンダーシステムのデータ構造と、岱明練習の分析向け規約。

## カレンダーイベント（共通）

ソース: `input/events.YYYY.yaml`

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `title` | string | ✓ | 件名 |
| `date` | YYYY-MM-DD | | 省略時は日付なしメモ |
| `end_date` | YYYY-MM-DD | | 複数日予定 |
| `all_day` | bool | | デフォルト `true` |
| `start_time` / `end_time` | HH:MM | | 終日でない場合 |
| `category` | string | | `予定` / `メモ` / `祝日` |
| `status` | string | | `scheduled`, `done`, `inbox` 等 |
| `tags` | string[] | | 分類タグ |
| `description` | string | | 人間向け表示本文 |
| `practice` | object | | 機械向け練習メニュー（後述） |
| `template_ref` | string | | `input/practice_templates.yaml` の参照 ID |

## 練習メニュー（`practice` フィールド）

**`practice` が正（ソース・オブ・トゥルース）**。`description` は表示用。

```yaml
practice:
  warmup: 動きづくり
  notes: コーチメモ（任意）
  absentees: [松野, 塚原]  # 欠席者名リスト（任意、空配列=欠席者なし）
  items:
    - type: jog
      group: 男子
      distance_km_min: 4.0
      distance_km_max: 6.0
      pace_min: k/4:00
      pace_max: k/4:10
    - type: interval
      distance_m: 300
      reps: "6-10"
      intensity: RP
      rest_sec: 60
    - type: set
      group: 男子
      segments:
        - { distance_m: 2100 }
        - { distance_m: 900 }
```

### `type`（controlled vocabulary）

| 値 | 意味 |
|---|---|
| `jog` | ジョグ / イージーラン |
| `interval` | インターバル（距離指定） |
| `set` | 複数距離のセット |
| `strides` | 流し / ストライド |
| `warmup` | ウォームアップ単体 |
| `rest` | 休憩 |
| `other` | その他 |

### `intensity`

`E`, `T`, `I`, `R`, `RP`, `1500mRP`, `3000mRP`, `GZ`

### ペース表記

- 形式: `k/M:SS`（km あたり分:秒）
- 例: `k/4:16` = 4分16秒/km
- トラック **1周 = 560m**

## タグ命名規則

既存の日本語タグに加え、機械用タグを付与する。

| タグ | 条件 |
|---|---|
| `practice:daiming` | いだてん岱明練習 / 岱明朝練 / 岱明夕練 |
| `practice:personal` | 自分の練習 |
| `session:morning` | タイトルに「朝練」 |
| `session:evening` | タイトルに「夕練」 |

## テンプレート

`input/practice_templates.yaml` — 日付なしの練習バリエーション集。

## スケジュール

`input/practice_schedules.yaml` — 朝練/夕練の開催スケジュール。

## エクスポート

| ファイル | 用途 |
|---|---|
| `out/YYYY/events.json` | 全イベント（JSON） |
| `out/YYYY/practice.json` | 練習イベント + パース状態 |
| `out/YYYY/practice_items.csv` | 1行 = 1メニュー項目（`absentees` 列付き） |
| `out/YYYY/practice_absentees.csv` | 1行 = 1欠席者（セッション×選手） |
| `out/YYYY/practice-summary.md` | 月別集計・未パース一覧 |
| `out/daiming-practice-menus-kpace.md` | k/pace 換算一覧 |

## HTML コメント（レガシー互換）

`description` 内に埋め込み可能:

```html
<!-- practice-menu:v1
warmup: 動きづくり
items:
  - type: interval
    distance_m: 600
    reps: 2
    intensity: 1500mRP
    rest_sec: 480
-->
```

パース優先度: `practice` フィールド > HTML コメント > `description` 自由文。

## AI 生成メタデータ

AI 生成 CLI（[`docs/ai-practice-generation.md`](ai-practice-generation.md)）利用時:

| フィールド | 説明 |
|---|---|
| `template_ref` | 参照した [`practice_templates.yaml`](../input/practice_templates.yaml) の ID |
| `practice` | 生成結果（lint 通過済み） |

CLI 出力 JSON の `metadata` 例:

```yaml
metadata:
  template_id: evening-light-600x2
  template_ids: [evening-light-600x2]
  attempts: 1
  llm_used: false
  dry_run: true
  is_experiment: false
```

週1 実験セッションは `notes` が `【実験】` で始まること（[`input/ai_generation_rules.yaml`](../input/ai_generation_rules.yaml)）。

### 現場1枚 / `abort_if`

`--apply` は読み上げ文 + 切上げを `description` に書き、`practice.abort_if`（任意）に構造化切上げを保存する。信頼度ヘッダはカレンダーに書かない。

```yaml
practice:
  abort_if:
    - when: 翌日が記録会
      then: 追い込み禁止。本数を増やさない
```
