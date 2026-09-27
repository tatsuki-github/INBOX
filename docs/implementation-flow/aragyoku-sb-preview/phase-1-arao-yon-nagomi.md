# Phase 1: 荒尾第四・なごみで6人揃え（簡略）

## ユーザーストーリー

コーチとして、荒尾第四中男子の仮オーダーが6区欠測のままでは展開が読めない。なごみOPに出た選手を見れば揃うはずなので、それを反映したい。

## 受け入れ条件

1. 荒尾第四中男子の仮オーダーが6人すべて埋まっている
2. 6区に藤井祐吏（なごみOP）が入っている
3. `RECENT_EKIDEN_MARKS` に藤井のなごみ10:15がある
4. `build_report` で `complete=True` かつ総合タイムがある
5. Drive / corpus dual-write 再生成済み

## テストマッピング

| AC | テスト |
|:---|:---|
| 1–2 | `test_redistribute_builds_nagasu_men_and_women_clubs` の yondai 断言 |
| 3–4 | `test_arao_yon_men_complete_from_nagomi` |
| 5 | 生成スクリプト実行 |

## In / Out

| In | Out |
|:---|:---|
| PROVISIONAL + LOCKED 荒尾第四男子 | 女子荒尾四（層が足りず今回は対象外） |
| RECENT 藤井／松岡／浦本 | 他校オーダー大幅変更 |
| ADR 056 | 新規 ADR |
