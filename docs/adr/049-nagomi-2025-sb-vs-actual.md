# ADR 049: 2025 なごみ成績表とレース前 SB 予実

- Status: Accepted
- Date: 2026-09-19

## Context

2026 なごみは区間オーダーに今年度 SB を載せた予想 MD/PDF がある
（`scripts/generate_nagomi_order_sb_preview.py`、ADR 045）。
2025-09-21 の成績は Drive 上で stub（binary deferred）のままだった。
ユーザーが女子成績表写真と男子結果 PDF 2 枚を提供し、
「去年の予想が実績からどれだけ外れたか」を見たい。

2025-sb-adopted.json には 2025-09-21 以降（県中学駅伝・11月以降）の記録も含まれる。
レース後の SB で予想すると後知恵になる。

## Decision

1. 成績表を構造化して `scripts/nagomi_2025_results_data.py` を正本とし、
   `女子成績表.md` / `男子成績表.md` / `成績表.json` を Drive とコーパスへ書く。
2. 予想は 2026 と同じ換算式。SB は `2025-sb-adopted.json` の **2025-09-20 以前** かつ同性別のみ。
   Notion・玉名郡ナイター上書きは使わない。
3. 出力は 2026 と同じ `女子/男子区間オーダー_SB予想.md/.pdf` に加え、`予実比較.md/.pdf`
   （差 = 実績 − 予想）。
4. `load_sb_index()` に `as_of` / `gender` / `include_nighter` / `include_notion` を追加する。
   2026 生成のデフォルトは従来どおり。
5. 岱明B 1区は成績表の **山本哲瑠** を正とする（メモの「悟瑠」は誤記）。

## Consequences

- 欠測 SB の区間は中央値補完（※）。レース前に 1500/800 が無い選手は予想空欄。
- スキャン PDF/JPEG は Drive フォルダに原本として置く。LINE コーパスは Markdown。
- 再生成: `python3 scripts/generate_nagomi_2025_sb_vs_actual.py`
