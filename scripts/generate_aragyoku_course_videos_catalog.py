#!/usr/bin/env python3
"""荒玉駅伝コース動画の LINE Video 用カタログを生成する。

Drive フォルダ（男女別）の既知ファイル ID を正本とし、
HEAD で Content-Type が video/mp4 かつ size ≤ 200MB のとき lineEligible=true。

出力: backend/data/aragyoku-course-videos.json
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backend" / "data" / "aragyoku-course-videos.json"

LINE_MAX_BYTES = 200 * 1024 * 1024

WOMEN_FOLDER_ID = "1no2bVU7GeyVbXFsCG8V8uwM0IuaFoOhi"
MEN_FOLDER_ID = "17MrxiZ_0CsDBgVrS_O3uZm3Oypu70Uoo"

# Drive 調査時点の固定 ID（フォルダ中身が変わったら再実行）
ENTRIES: list[dict[str, Any]] = [
    # 女子
    {
        "gender": "女子",
        "leg": None,
        "kind": "full",
        "driveFileId": "1DGnC7VndbXOgmuZ8uNEIoT6Y-vhz_Zfs",
        "title": "荒玉駅伝女子_全区間コース動画.mp4",
        "fileSizeBytes": 151620746,
        "folderId": WOMEN_FOLDER_ID,
    },
    {
        "gender": "女子",
        "leg": 1,
        "kind": "leg",
        "driveFileId": "1WZTaKEIN-A4z9GSgAxxkrHh7uud2OgCi",
        "title": "荒玉駅伝女子1区_コース動画.mp4",
        "fileSizeBytes": 38180432,
        "folderId": WOMEN_FOLDER_ID,
    },
    {
        "gender": "女子",
        "leg": 2,
        "kind": "leg",
        "driveFileId": "1FIAnfts0hEuNQIhWifkCIVNEENJ8Re_q",
        "title": "荒玉駅伝女子2区_コース動画.mp4",
        "fileSizeBytes": 28169528,
        "folderId": WOMEN_FOLDER_ID,
    },
    {
        "gender": "女子",
        "leg": 3,
        "kind": "leg",
        "driveFileId": "1E-5Kp8OCAXKEq7oNq1F7pZjM8a70mjXx",
        "title": "荒玉駅伝女子3区_コース動画.mp4",
        "fileSizeBytes": 25433052,
        "folderId": WOMEN_FOLDER_ID,
    },
    {
        "gender": "女子",
        "leg": 4,
        "kind": "leg",
        "driveFileId": "1feBlYuavwaq2oUmNmvRth6L2upHxxGnH",
        "title": "荒玉駅伝女子4区_コース動画.mp4",
        "fileSizeBytes": 26217094,
        "folderId": WOMEN_FOLDER_ID,
    },
    {
        "gender": "女子",
        "leg": 5,
        "kind": "leg",
        "driveFileId": "1O_pr7JySX5BExamEpdE5iv42WTlMI6SZ",
        "title": "荒玉駅伝女子5区_コース動画.mp4",
        "fileSizeBytes": 44280771,
        "folderId": WOMEN_FOLDER_ID,
    },
    # 男子
    {
        "gender": "男子",
        "leg": None,
        "kind": "full",
        "driveFileId": "1mELp4cUjLQtnRQ0D4Gb-_ckdtNs7ATHo",
        "title": "荒玉駅伝男子_全区間コース動画.mp4",
        "fileSizeBytes": 229340846,
        "folderId": MEN_FOLDER_ID,
    },
    {
        "gender": "男子",
        "leg": 1,
        "kind": "leg",
        "driveFileId": "1-zMyoSiGzBqn4s5OAFRBFnCjgSdyL4ce",
        "title": "荒玉駅伝男子1区_コース動画.mp4",
        "fileSizeBytes": 41928819,
        "folderId": MEN_FOLDER_ID,
    },
    {
        "gender": "男子",
        "leg": 2,
        "kind": "leg",
        "driveFileId": "17TlTT2XLGGG1YBDhySbo5aP3bfeSWDEE",
        "title": "荒玉駅伝男子2区_コース動画.mp4",
        "fileSizeBytes": 41124166,
        "folderId": MEN_FOLDER_ID,
    },
    {
        "gender": "男子",
        "leg": 3,
        "kind": "leg",
        "driveFileId": "16QtGUWBTyeIjw5OLpbgUUt_JWqpmeA3b",
        "title": "荒玉駅伝男子3区_コース動画.mp4",
        "fileSizeBytes": 38103843,
        "folderId": MEN_FOLDER_ID,
    },
    {
        "gender": "男子",
        "leg": 4,
        "kind": "leg",
        "driveFileId": "1lNejkKSMW16YJDEX-nc_Eui52PO1Li3E",
        "title": "荒玉駅伝男子4区_コース動画.mp4",
        "fileSizeBytes": 45471220,
        "folderId": MEN_FOLDER_ID,
    },
    {
        "gender": "男子",
        "leg": 5,
        "kind": "leg",
        "driveFileId": "1qsxXzNaygbVWqp2Aw70TkgHtCepSusvt",
        "title": "荒玉駅伝男子5区_コース動画.mp4",
        "fileSizeBytes": 35380618,
        "folderId": MEN_FOLDER_ID,
    },
    {
        "gender": "男子",
        "leg": 6,
        "kind": "leg",
        "driveFileId": "1Vg8eEhQW25LRCpN7fdVQZ3iaWABYrCDR",
        "title": "荒玉駅伝男子6区_コース動画.mp4",
        "fileSizeBytes": 44228178,
        "folderId": MEN_FOLDER_ID,
    },
]


def download_url(file_id: str) -> str:
    return f"https://drive.usercontent.google.com/download?id={file_id}&export=download"


def preview_url(file_id: str) -> str:
    return f"https://lh3.googleusercontent.com/d/{file_id}"


def probe_line_eligible(file_id: str, file_size: int) -> bool:
    if file_size > LINE_MAX_BYTES:
        return False
    url = download_url(file_id)
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            return ctype == "video/mp4"
    except urllib.error.HTTPError as e:
        ctype = (e.headers.get("Content-Type") or "").split(";")[0].strip().lower() if e.headers else ""
        return ctype == "video/mp4"
    except Exception as exc:  # noqa: BLE001 — カタログ生成時は失敗を非適格扱い
        print(f"  warn: HEAD failed for {file_id}: {exc}")
        return False


def main() -> None:
    videos: list[dict[str, Any]] = []
    for raw in ENTRIES:
        fid = raw["driveFileId"]
        size = int(raw["fileSizeBytes"])
        eligible = probe_line_eligible(fid, size)
        print(f"  {raw['title']}: lineEligible={eligible} size={size}")
        videos.append(
            {
                "gender": raw["gender"],
                "leg": raw["leg"],
                "kind": raw["kind"],
                "driveFileId": fid,
                "title": raw["title"],
                "fileSizeBytes": size,
                "folderId": raw["folderId"],
                "originalContentUrl": download_url(fid),
                "previewImageUrl": preview_url(fid),
                "lineEligible": eligible,
            }
        )

    payload = {
        "version": 1,
        "folders": {
            "女子": {
                "folderId": WOMEN_FOLDER_ID,
                "folderUrl": f"https://drive.google.com/drive/folders/{WOMEN_FOLDER_ID}",
            },
            "男子": {
                "folderId": MEN_FOLDER_ID,
                "folderUrl": f"https://drive.google.com/drive/folders/{MEN_FOLDER_ID}",
            },
        },
        "note": (
            "荒玉駅伝コース動画。LINE Video は lineEligible=true のみ添付。"
            "originalContentUrl は drive.usercontent 直リンク、"
            "previewImageUrl は lh3 サムネ（動画でも JPEG）。"
        ),
        "videos": videos,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    eligible_n = sum(1 for v in videos if v["lineEligible"])
    print(f"wrote {OUT.relative_to(ROOT)} ({len(videos)} videos, {eligible_n} lineEligible)")


if __name__ == "__main__":
    main()
