# Phase 0–6: 長洲女子 2村里 / 3濱北 / 5中村（Lite extend）

## ゴール

長洲女子を `猿渡→村里→濱北→山川→中村` に固定（中村アンカー）。

## 検証

```bash
.venv/bin/python -m unittest tests.test_aragyoku_sb_preview
.venv/bin/python scripts/generate_aragyoku_ekiden_sb_preview.py --as-of 2026-09-27
```
