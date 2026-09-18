# 調査レポート: 大会フォルダ・結果ファイル命名の統一

## ユーザーストーリー
コーチ／エージェントとして、任意の大会の岱明結果をパスとファイル名だけで特定したい。なぜなら「結果.md」「いだてん岱明結果.md」「大会名_岱明の結果.md」が混在すると KG の preferred refs と path boost が外れ、Q&A がコーチ定型に落ちるからだ。

## 受け入れ条件
1. [ ] 全大会のクラブ結果が `…/大会/{年度}/{MMDD}_*/岱明の結果.md` に揃う（別名ファイルが残らない）
2. [ ] KG meet ノードの refs 先頭付近に `岱明の結果.md` が載る（玉名市民マラソン含む）
3. [ ] `meetResultPathBoost` / `meetDriveTokens` が「玉名市民マラソン」等の other 大会でもパス優先できる
4. [ ] backend の meets / 関連テストが Green、KG 再生成済み

## 受け入れ条件 → テストマッピング

| # | 受け入れ条件 | テスト種別 | 対象層 | テスト意図 |
|:--|:-------------|:-----------|:-------|:-----------|
| 1 | 正規ファイル名存在 | 統合（シェル/パス検査） | corpus | 別名が残っていない |
| 2 | KG refs | 単体/スクリプト | builder | preferred に岱明の結果 |
| 3 | other トークン | 単体(TDD) | meets.ts | クエリ語が drive token になる |
| 4 | 回帰 | 単体 | meets / answer | junior/荒玉が壊れない |

## スコープ

| In Scope | Out of Scope |
|:---------|:-------------|
| external + corpus の結果/出場ファイルリネーム | Google Drive 本体のリネーム |
| 荒玉フォルダ名のトークン補完 | OCR 種目別ファイルの全面改名 |
| meets.ts / KG builder の preferred 拡充 | LINE UI |
| ADR + 命名 README | Drive 再同期パイプラインの自動リネーム（将来） |

## 現状の問題（根拠）

- KG builder は `岱明の結果.md` のみを preferred（`scripts/knowledge_graph/builder.py`）
- `meetResultPathBoost` はパスに `岱明の結果` があると +60
- 別名: `結果.md`, `いだてん岱明結果.md`, `玉名市民マラソン_岱明の結果.md`, `結果/いだてん岱明の結果.md`
- 2025 `1015_玉名荒尾中体連駅伝` に「荒玉」トークンがなく aragyoku drive boost と不一致

## 影響ドキュメント一覧
- `docs/adr/019-meet-naming-convention.md`（新規）
- `docs/adr/017-meet-disambiguation-kg.md`（リンク）
- `input/idaten-corpus/drive-text/大会/NAMING.md`（新規）
- `input/external/INDEX.md`（必要なら一言）
