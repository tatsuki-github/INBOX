# Phase 5–6: 大会命名統一

## 実装サマリー

- 全大会のクラブ結果を `岱明の結果.md` に統一（external + corpus）
- 出場・計画ファイルを `岱明の*` に正規化
- `1015_荒玉中体連駅伝（玉名荒尾）` にフォルダ改名（検索トークン「荒玉」）
- `meetDriveTokens("other", query)` で市民マラソン等のパス語を抽出
- KG `_node` refs のソートをやめ、preferred（`岱明の結果.md`）を先頭維持
- ADR 019 / `NAMING.md` / 実装フロー Phase 0–1

## 検証

- `npm test`（backend）80 passed
- `npm run build` 成功
- KG クエリ「去年の玉名市民マラソンの岱明の結果」→ meet ノードヒット、hint に結果本文、refs 2 番目が `岱明の結果.md`
- 別名ファイル残存 0、`岱明の結果.md` = 20 件

## レビュー

**Approved**（Critical=0, Major=0）
