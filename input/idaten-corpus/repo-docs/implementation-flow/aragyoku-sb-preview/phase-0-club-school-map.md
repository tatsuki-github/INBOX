# 作業種別記録: クラブ→学校マッピング再分配

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

## 判定根拠
| # | 質問 | 回答 |
|:--|:-----|:-----|
| 1 | バグのみ？ | No（分配ロジックの拡張） |
| 2 | 改善のみ？ | No（学校プール再構築が新規） |
| 3 | 既存変更？ | Yes |
| 4 | 契約破壊？ | No → **extend** |

## スキップ
Phase 2/4 スキップ（UI なし）。Phase 1/3 簡略化。

## ゴール
`input/arato_tamana_report.yaml` の所属／選手→学校マッピングで ATRC・金栗PROJECT・アスリーツ等を各校に分配し、荒玉 SB 予想を再生成する。
