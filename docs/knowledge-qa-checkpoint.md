# ナレッジQA追加の区切り

ユーザーの区切りでコミット・mainへマージする指示に合わせ、全チャンク完了前の確認済み分を公開する。

- AGENTS.md・README.md・カレンダーの36チャンクを文脈と既存QAに照らして確認した。
- 各チャンク3問の108候補から、謝礼関連の2問を除いた106問を想定QAへ追加した。
- 謝礼関連の既存QA2件を削除し、混在する研修QA2件から謝金情報を削除した。
- カレンダー原本、外部データのリポジトリ内スナップショット、コーパス、検索索引、ナレッジグラフから謝礼額を除去した。
- 謝礼・謝金・報酬の質問は定型回答・検索・LLMより前に回答対象外とする。

追加QAの質問・回答・根拠引用・手動確認記録は `input/faq/knowledge-chunk-reviewed.json` に残す。自動監査は承認済みQAとの一致と原文引用の一致を検証する。比較・計算の妥当性は文脈を読んだ手動確認であり、自動的な意味証明ではない。

全ナレッジ（2781チャンク）について、各チャンク3問の想定QA（計8343問）を `input/faq/full-knowledge-qa/reviewed-*.json` に追加し、`scripts/validate_full_knowledge_qa.py --publish-reviewed` で `input/faq/prepared-qa.v1.yaml` へ公開済み（43539件）。区切り再生成は `scripts/prepare_knowledge_qa_chunks.py --write`、未カバー分の候補生成は `scripts/generate_chunk_manual_context_qas.py`。
