# ADR 035: 区間選手質問と LINE 運用メモの衝突回避

- Status: Accepted
- Date: 2026-09-19

## Context

「2025年岱明男子5区は誰？」のような短縮形の区間選手質問で、指導者 LINE ダイジェスト
（`line-chats/daiming-staff.md` の 2区/5区=2.855km メモ）が preferred 先頭になり、
チーム別結果・focus 分析の区間表がオフライン回答に現れないことがあった。

crush100-v4 は「荒玉駅伝」付きかつ 1–3 区中心だったため、この短縮形ギャップを見逃していた。

## Decision

1. **Leg-athlete 判定**（`isLegAthleteQuestion`）: `\d区` + 誰/選手 等で、地点分担・2.855・朝練等の運用意図がない質問を結果系とみなす。
2. **LINE ブースト抑制**: 結果系では `boostDaimingLineSources` が line-chats を先頭に入れない。retrieve の path bonus も 2区/5区単独では staff digest を上げない。
3. **オフライン preview**: 結果系は年見出しの後の `| N | 選手 |` 行を優先ウィンドウにする（前年比サマリーの `| 2025 |` に寄らない）。
4. **評価**: `questions-crush100-v5.json` で短縮形・4–6 区・LINE 非衝突を all_of 厳格に 100/100。

## Consequences

- 地点分担・2.855 距離・朝練の質問は従来どおり line-chats を優先。
- 短縮形「○年○校○区は誰」は aragyoku-teams / focus が勝つ。
- 大会名なしの「何区を走った」は [ADR 047](047-unnamed-leg-athlete-routing.md)。
