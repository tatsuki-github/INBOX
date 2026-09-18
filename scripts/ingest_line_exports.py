#!/usr/bin/env python3
"""LINE トーク履歴テキストを衛生化して out/analysis/line-chats/ に Markdown 化する。

- 参加通知・スタンプ・写真のみの行は落とす
- 電話番号・郵便番号・住所らしい行はマスク
- 生徒の性格・人物評（特徴）っぽい短文は落とす（別途削除方針）
- 運用・大会・練習・集合の連絡は残す

Usage:
  python3 scripts/ingest_line_exports.py
  python3 scripts/ingest_line_exports.py --raw-dir input/external/line/raw
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "input" / "external" / "line" / "raw"
OUT_DIR = ROOT / "out" / "analysis" / "line-chats"

PHONE_RE = re.compile(r"0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4}")
POSTAL_RE = re.compile(r"\b\d{3}-?\d{4}\b")
JOIN_RE = re.compile(r"がグループに参加しました|をグループに追加しました|プロフィール画像を変更|アナウンスしました|送信を取り消しました|グループ通話")
MEDIA_ONLY_RE = re.compile(r"^\[(写真|スタンプ|ファイル|動画|アルバム|投票|投票終了)\]")
DATE_RE = re.compile(r"^(\d{4}/\d{2}/\d{2})\([日月火水木金土]\)$")
MSG_RE = re.compile(r"^(\d{1,2}:\d{2})\t(.+?)\t(.*)$")
TRAIT_HINT_RE = re.compile(
    r"^(本番に強い|礼儀正しい|素直|積極的|スマートに走る|コツコツ型|伸び代|気持ちが強|あんまり速くない)"
)

SKIP_SENDERS = {"システム"}


@dataclass
class Message:
    date: str
    time: str
    sender: str
    text: str


def redact(text: str) -> str:
    text = PHONE_RE.sub("[電話番号]", text)
    text = POSTAL_RE.sub("[郵便番号]", text)
    # 住所らしき連続（市…町…数字）
    text = re.sub(r"玉名市[^\n]{0,40}\d{1,4}-\d{1,3}", "[住所]", text)
    return text


def should_keep(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if MEDIA_ONLY_RE.match(t):
        return False
    if JOIN_RE.search(t) and len(t) < 80:
        return False
    if TRAIT_HINT_RE.search(t) and len(t) < 40:
        return False
    # 挨拶のみ
    if re.fullmatch(r"(よろしく|よろしくお願いします|お疲れ様(?:でした|です)?|了解(?:です|しました)?|承知しました)[。．!！]*", t):
        return False
    return True


def parse_line_export(text: str) -> tuple[str, str, list[Message]]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    title = ""
    saved = ""
    messages: list[Message] = []
    current_date = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("[LINE]"):
            title = line.replace("[LINE]", "").strip()
            i += 1
            continue
        if line.startswith("保存日時："):
            saved = line.split("：", 1)[-1].strip()
            i += 1
            continue
        mdate = DATE_RE.match(line.strip())
        if mdate:
            current_date = mdate.group(1).replace("/", "-")
            i += 1
            continue
        mmsg = MSG_RE.match(line)
        if mmsg and current_date:
            time_s, sender, body = mmsg.group(1), mmsg.group(2).strip(), mmsg.group(3)
            # multiline quoted bodies continue until next time/date/empty pattern
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if DATE_RE.match(nxt.strip()) or MSG_RE.match(nxt) or nxt.startswith("[LINE]"):
                    break
                if nxt.startswith('"') or (body.startswith('"') and not body.rstrip().endswith('"')):
                    body += "\n" + nxt
                    i += 1
                    continue
                if nxt.strip() == "" and i + 1 < len(lines) and (
                    DATE_RE.match(lines[i + 1].strip()) or MSG_RE.match(lines[i + 1])
                ):
                    break
                if nxt.strip() and not nxt.startswith("\t") and not MSG_RE.match(nxt):
                    # continuation without tab (rare)
                    if body.startswith('"') and not body.rstrip().endswith('"'):
                        body += "\n" + nxt
                        i += 1
                        continue
                break
            body = body.strip().strip('"').strip()
            body = redact(body)
            if should_keep(body):
                messages.append(Message(current_date, time_s, sender, body))
            continue
        i += 1
    return title, saved, messages


def to_markdown(title: str, saved: str, messages: list[Message], slug: str) -> str:
    lines = [
        f"# LINE: {title}",
        "",
        f"- スラッグ: `{slug}`",
        f"- 保存日時: {saved or '不明'}",
        "- 注意: 電話番号・郵便番号・住所はマスク済み。参加通知・スタンプ・写真のみは除外。",
        "- 用途: 岱明中長距離の予定・大会・連絡の Q&A 根拠。",
        "",
        "## 時系列抜粋",
        "",
    ]
    by_date: dict[str, list[Message]] = {}
    for m in messages:
        by_date.setdefault(m.date, []).append(m)
    for date in sorted(by_date):
        lines.append(f"### {date}")
        lines.append("")
        for m in by_date[date]:
            text = m.text.replace("\n", " / ")
            lines.append(f"- {m.time} **{m.sender}**: {text}")
        lines.append("")
    return "\n".join(lines)


KNOWN_FILES = {
    "daiming-parents.txt": "daiming-parents.md",
    "daiming-staff.txt": "daiming-staff.md",
    "arita-taisho.txt": "arita-taisho.md",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for raw_name, out_name in KNOWN_FILES.items():
        path = args.raw_dir / raw_name
        if not path.is_file():
            print(f"skip missing {path}")
            continue
        title, saved, messages = parse_line_export(path.read_text(encoding="utf-8"))
        md = to_markdown(title or raw_name, saved, messages, out_name.replace(".md", ""))
        out = args.out_dir / out_name
        out.write_text(md, encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)} ({len(messages)} messages, {len(md)} chars)")
        written += 1

    # Preserve curated digests when raw exports are absent.
    if written == 0 and (args.out_dir / "daiming-parents.md").is_file():
        print("kept curated digests (no raw exports)")
        return 0

    index = args.out_dir / "INDEX.md"
    index.write_text(
        "\n".join(
            [
                "# LINE チャット衛生化抜粋（岱明）",
                "",
                "- `daiming-parents.md` — 保護者グループ「岱明中長距離」",
                "- `daiming-staff.md` — 指導者グループ「まさ　と愉快な仲間達」",
                "- `arita-taisho.md` — 有田大将（ゆくゆく指導）× 土山の指導・荒玉準備メモ",
                "",
                "再生成: `python3 scripts/ingest_line_exports.py`",
                "生テキストは `input/external/line/raw/`（git 対象外推奨）。",
                "有田メモは衛生化キュレーション優先（生ログ再生成で上書きしない運用可）。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"wrote {index.relative_to(ROOT)} ({written} chats)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
