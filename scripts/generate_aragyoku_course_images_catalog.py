#!/usr/bin/env python3
"""course-points.json の drive_file_id から LINE 用コース画像カタログを生成する。

出力: backend/data/aragyoku-course-images.json
正本: input/aragyoku/course-points.json
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COURSE_POINTS = ROOT / "input" / "aragyoku" / "course-points.json"
OUT = ROOT / "backend" / "data" / "aragyoku-course-images.json"


def main() -> None:
    data = json.loads(COURSE_POINTS.read_text(encoding="utf-8"))
    fid = data.get("drive_file_id")
    if not isinstance(fid, str) or not fid.strip():
        raise SystemExit(f"missing drive_file_id in {COURSE_POINTS}")
    fid = fid.strip()
    drive_url = data.get("drive_url") or f"https://drive.google.com/file/d/{fid}/view"
    parent = data.get("drive_parent_folder_id")
    image_path = data.get("image_path") or "input/aragyoku/course-points/aragyoku-course-common-points.png"
    title = data.get("title") or "荒玉駅伝 男女コースの共通ポイント"

    item = {
        "id": "common-points",
        "title": title,
        "driveFileId": fid,
        "driveUrl": drive_url,
        "imagePath": image_path,
        "originalContentUrl": f"https://lh3.googleusercontent.com/d/{fid}",
        "previewImageUrl": f"https://lh3.googleusercontent.com/d/{fid}=w480",
    }

    payload = {
        "version": 1,
        "driveFileId": fid,
        "driveUrl": drive_url,
        "parentFolderId": parent if isinstance(parent, str) else None,
        "parentFolderUrl": (
            f"https://drive.google.com/drive/folders/{parent}"
            if isinstance(parent, str) and parent.strip()
            else None
        ),
        "source": "input/aragyoku/course-points.json",
        "note": (
            "荒玉駅伝 男女コース共通ポイント図解。"
            "LINE Image 用に lh3.googleusercontent.com 直リンク。"
            "正本 drive_file_id は course-points.json。"
        ),
        "images": [item],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(payload['images'])} images)")


if __name__ == "__main__":
    main()
