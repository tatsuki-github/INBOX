#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""荒玉駅伝 数式予想・旧SB予想の予実ギャップ分析（レース後用スタブ）。

公式成績到着後に、なごみ ADR 052 と同様の差＝実績−予想表を生成する。
現時点ではプレースホルダ MD のみ書き出す。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/analysis/aragyoku_sb_gap_analysis.md"
MEET = ROOT / "input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝"
SHARED_MEET = ROOT / "input/external/drive/shared/大会/2026年度/1014-1015_荒玉中体連駅伝"


def main() -> int:
    text = """# 荒玉駅伝 数式予想・旧SB予想の予実ギャップ分析

ステータス: **レース前スタブ**（2026-10-14 開催予定）

## 予定ワークフロー

1. 成績を `岱明の結果.md` および男女成績表に転記する。
2. レース前の `区間オーダー_数式予想.json` と旧 `区間オーダー_SB予想.md` を固定する。
3. 本スクリプトを拡張し、差＝実績−数式予想、実績−旧SB予想の表／HTML を生成する（なごみ ADR 052 準拠）。
4. 男女別の数式係数と `calibrate_aragyoku_sb_preview.py` の区間バイアスを更新する。

## 現状の事前材料

- 現行予想: `{meet}/区間オーダー_数式予想.json`
- 現行展開: `{meet}/校別展開_数式予想.md`
- 旧SB比較値: `{meet}/区間オーダー_SB予想.md`
- ジュニア予実（参考）: ジュニア大会フォルダの `岱明の結果.md`
""".format(
        meet=MEET.as_posix()
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    for meet_dir in (MEET, SHARED_MEET):
        (meet_dir / "予実比較.md").write_text(text, encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
