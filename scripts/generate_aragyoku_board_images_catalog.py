#!/usr/bin/env python3
"""transcripts の source_drive_id から LINE 用ボード画像カタログを生成する。

出力: backend/data/aragyoku-board-images.json
公開フォルダ: https://drive.google.com/drive/folders/1XRxBeG1wkG3c92Y-h5ycPgbBL7Ep1ief
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPTS = ROOT / "input" / "aragyoku" / "transcripts"
OUT = ROOT / "backend" / "data" / "aragyoku-board-images.json"
FOLDER_ID = "1XRxBeG1wkG3c92Y-h5ycPgbBL7Ep1ief"


def main() -> None:
    items: list[dict] = []
    for path in sorted(TRANSCRIPTS.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        fid = data.get("source_drive_id")
        year = data.get("year")
        gender = data.get("gender")
        if not isinstance(fid, str) or not fid.strip():
            continue
        if not isinstance(year, int) or gender not in ("男子", "女子"):
            continue
        fid = fid.strip()
        items.append(
            {
                "year": year,
                "gender": gender,
                "driveFileId": fid,
                "originalContentUrl": f"https://lh3.googleusercontent.com/d/{fid}",
                "previewImageUrl": f"https://lh3.googleusercontent.com/d/{fid}=w480",
            }
        )

    payload = {
        "version": 1,
        "folderId": FOLDER_ID,
        "folderUrl": f"https://drive.google.com/drive/folders/{FOLDER_ID}",
        "note": (
            "荒玉駅伝結果ボード画像。source_drive_id は transcripts 正本。"
            "LINE Image 用に lh3.googleusercontent.com 直リンク。"
        ),
        "images": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(items)} images)")


if __name__ == "__main__":
    main()
