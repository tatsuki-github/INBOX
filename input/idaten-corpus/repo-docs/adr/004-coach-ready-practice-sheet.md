# ADR 004: 指導者が採用できる現場1枚

## Status

Accepted

## Context

AI 生成の `practice` YAML は lint 可能だが、指導者はグラウンドで YAML を読めない。採用されている夕練は 8/15 型の `description`（読み上げ文）が正である。GZ 表記だけでは秒指示ができず、前後の練習会・天候も人手補完になっていた。

## Decision

1. **既定出力は現場1枚**（ヘッダ + 読み上げ文 + 切上げ + 確認）。`--format yaml|json` は機械用として残す
2. **秒タイム**は LLM 禁止。[`pace_calculator.py`](../../scripts/ai/pace_calculator.py) で GZ/T を距離別秒レンジにする
3. **読み上げ文**は LLM 禁止。[`practice_renderer.py`](../../scripts/practice_renderer.py) を土台にする
4. **切上げ**は決定論ルール（記録会前後・湿度・降水・気温）。練習会は負荷に数えない（ADR 006）
5. **`--apply`** は `practice` と `description`（読み上げ + 切上げ）を同時更新。信頼度ヘッダはカレンダーに書かない
6. 選手名の例外は推測せず、確認チェックリストのみ

## Consequences

- 指導者はシートを見て採用 / ジョグのみ / 中止を判断できる
- `practice.abort_if` を任意追加（additive）
- 選手個別 T ペースは `--t-pace` のまま

## Alternatives Considered

- LLM に現場文を書かせる: 却下 — 表記ゆれと秒の算数ミス
- abort を notes 自由文のみ: 却下 — 再現性が低い
