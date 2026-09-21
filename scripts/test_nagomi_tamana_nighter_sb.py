#!/usr/bin/env python3
"""玉名郡ナイターの SB 明記行だけを SB upsert する単体テスト。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import generate_nagomi_order_sb_preview as g


class TamanaNighterSbTest(unittest.TestCase):
    def test_only_sb_marked_rows_and_only_when_faster(self) -> None:
        md = """大会名: テスト
## 1500m 男子
速い 子 2年 4:30.0 SB
遅い 子 2年 5:00.0
新規 子 1年 5:20.0 SB
"""
        by_name: dict[str, g.AthleteSB] = {}

        def upsert(name, distance, seconds, text, url, date, source):
            key = g.norm_name(name)
            ath = by_name.setdefault(key, g.AthleteSB(name=name))
            cur = ath.marks.get(distance)
            if cur is None or seconds < cur.seconds:
                ath.marks[distance] = g.Mark(
                    seconds=seconds, text=text, url=url or "", date=date or "", source=source
                )

        upsert("速い 子", "1500m", g.parse_seconds("4:20.0"), "4:20.0", "", "", "sb-adopted")
        upsert("遅い 子", "1500m", g.parse_seconds("5:10.0"), "5:10.0", "", "", "sb-adopted")

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "全結果.md"
            path.write_text(md, encoding="utf-8")
            with mock.patch.object(g, "TAMANA_NIGHTER_FULL_MD", path):
                with mock.patch.object(g, "TAMANA_NIGHTER_DAIMYO_MD", Path(td) / "missing.md"):
                    updates = g.apply_tamana_nighter_sb(by_name, upsert)

        self.assertEqual(by_name[g.norm_name("速い 子")].marks["1500m"].text, "4:20.0")
        self.assertEqual(by_name[g.norm_name("速い 子")].marks["1500m"].source, "sb-adopted")
        self.assertEqual(by_name[g.norm_name("遅い 子")].marks["1500m"].text, "5:10.0")
        self.assertEqual(by_name[g.norm_name("遅い 子")].marks["1500m"].source, "sb-adopted")
        self.assertEqual(by_name[g.norm_name("新規 子")].marks["1500m"].text, "5:20.0")
        self.assertEqual(len(updates), 1)

    def test_norm_name_variants(self) -> None:
        self.assertEqual(g.norm_name("松野　凜空"), g.norm_name("松野 凛空"))
        self.assertEqual(g.norm_name("明瀨七跳"), g.norm_name("明瀬七跳"))

    def test_gender_filter(self) -> None:
        md = """大会名: テスト
1500m 男子
男子 子 3年 4:30.0 SB
1500m 女子
女子 子 3年 5:30.0 SB
"""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "岱明の結果.md"
            path.write_text(md, encoding="utf-8")
            with mock.patch.object(g, "TAMANA_NIGHTER_FULL_MD", Path(td) / "missing.md"):
                with mock.patch.object(g, "TAMANA_NIGHTER_DAIMYO_MD", path):
                    self.assertEqual(
                        g.iter_tamana_nighter_marks(gender="男子"),
                        [("男子 子", "1500m", "4:30.0")],
                    )
                    self.assertEqual(
                        g.iter_tamana_nighter_marks(gender="女子"),
                        [("女子 子", "1500m", "5:30.0")],
                    )


if __name__ == "__main__":
    unittest.main()
