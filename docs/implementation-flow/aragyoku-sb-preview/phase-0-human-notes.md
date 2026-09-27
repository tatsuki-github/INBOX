# 作業種別記録: 荒玉SB予想・人間考慮メモ（男女）

## 判定結果
- **作業種別**: extend
- **実行パス**: Lite
- **リダイレクト先**: なし
- **検証対象パッケージ**: Python scripts + `tests/`（UI なし）

## Docs Sync
| 項目 | 記録 |
|:-----|:-----|
| Docs Sync | 有効 |
| Docs Root | docs |
| ADR | docs/adr/056-aragyoku-sb-preview.md |

## Lite Path スキップ
| Phase | 実行 | 理由 |
|:------|:-----|:-----|
| 1 | 簡略化 | 要求明確（男女別メモ→予想調整） |
| 2/4 | スキップ | UI なし（YAML + MD） |
| 3 | 簡略化 | 既存パイプラインに調整層を追加 |
| 5 | 実行 | load/apply + テスト + 再生成 |
| 6 | 実行 | 受け入れ条件検証 |

## ゴール
1. 男女それぞれの人間考慮 YAML（メモ＋選手/区間調整）を編集できる。
2. 生成時に参照し、`delta_sec` / `set_sec` / `min_sec` / `max_sec` で予想を調整する。
3. 予想 MD にメモ本文と適用理由を残す。
