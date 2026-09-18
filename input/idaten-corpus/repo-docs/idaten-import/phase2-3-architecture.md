# Phase 2/3（Lite）— 取り込み配置

## UX（簡略）
- ユーザーは `input/external/**/INDEX.md` からソースを辿る
- 巨大バイナリは viewUrl メタで不安を減らす（「閉じてよい」＝ローカルに無い明示）

## アーキテクチャ
- ADR: `docs/adr/010-external-idaten-import.md`
- KG `SOURCE_GLOBS` に INDEX と主要スナップショットを登録

## テスト戦略
- `tests/test_external_import.py`（単体・存在/パース/KG 参照）
- 回帰: 既存 KG テスト + `build_knowledge_graph.py --check`
