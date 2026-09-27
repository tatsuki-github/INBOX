# Phase 5–6: 岱明 set_sec

## 実装

- `人間考慮_男子.yaml`: 松野 `set_sec: 560`、田上4区 `set_sec: 580`（delta -5 を置換）
- `人間考慮_女子.yaml`: 山﨑2区 `set_sec: 410`
- `ensure_human_notes_files` シード同期
- テスト追加・再生成

## 検証

```bash
.venv/bin/python -m unittest tests.test_aragyoku_sb_preview
.venv/bin/python scripts/generate_aragyoku_ekiden_sb_preview.py --as-of 2026-09-27
```
