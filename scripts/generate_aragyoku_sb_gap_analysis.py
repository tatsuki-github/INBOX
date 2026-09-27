#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""荒玉駅伝 SB 予実ギャップ分析（レース後用スタブ）。

公式成績到着後に、なごみ ADR 052 と同様の差＝実績−予想表を生成する。
現時点ではプレースホルダ MD のみ書き出す。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/analysis/aragyoku_sb_gap_analysis.md"
MEET = ROOT / "input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝"


def main() -> int:
    text = """# 荒玉駅伝 SB 予実ギャップ分析

ステータス: **レース前スタブ**（2026-10-14 開催予定）

## 予定ワークフロー

1. 成績を `岱明の結果.md` および男女成績表に転記する。
2. レース前の `区間オーダー_SB予想.md`（as_of＝大会前日）を固定する。
3. 本スクリプトを拡張し、差＝実績−予想の表／HTML を生成する（なごみ ADR 052 準拠）。
4. `calibrate_aragyoku_sb_preview.py` に2026を加えて区間バイアスを更新する。

## 現状の事前材料

- 予想: `{meet}/区間オーダー_SB予想.md`
- 展開: `{meet}/校別展開予想.md`
- ジュニア予実（参考）: ジュニア大会フォルダの `岱明の結果.md`
""".format(
        meet=MEET.as_posix()
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    (MEET / "予実比較.md").write_text(text, encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
