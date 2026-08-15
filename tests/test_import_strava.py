from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import import_strava as strava  # noqa: E402


SAMPLE_ACTIVITY = {
    "id": 987654321,
    "name": "Evening Run",
    "distance": 10000.0,
    "moving_time": 2700,
    "elapsed_time": 2800,
    "total_elevation_gain": 42.0,
    "type": "Run",
    "sport_type": "Run",
    "start_date": "2026-08-10T10:00:00Z",
    "start_date_local": "2026-08-10T19:00:00Z",
    "average_speed": 10000.0 / 2700.0,
    "average_heartrate": 152.3,
    "description": "ジョグ＋流し",
}


class ActivityConversionTests(unittest.TestCase):
    def test_format_pace(self) -> None:
        # 4:30 /km = 1000/270 m/s
        pace = strava.format_pace_min_per_km(1000 / 270)
        self.assertEqual(pace, "4'30\"/km")

    def test_activity_to_event_personal(self) -> None:
        event = strava.activity_to_event(SAMPLE_ACTIVITY, title_mode="personal")
        self.assertEqual(event["title"], "自分の練習")
        self.assertEqual(event["date"], "2026-08-10")
        self.assertEqual(event["start_time"], "19:00")
        self.assertEqual(event["end_time"], "19:46")  # +2800s
        self.assertEqual(event["status"], "done")
        self.assertFalse(event["all_day"])
        self.assertIn("自分の練習", event["tags"])
        self.assertIn("strava", event["tags"])
        self.assertIn("ラン", event["tags"])
        self.assertEqual(event["urls"], ["https://www.strava.com/activities/987654321"])
        desc = str(event["description"])
        self.assertIn("距離: 10.00km", desc)
        self.assertIn("平均ペース:", desc)
        self.assertIn("ジョグ＋流し", desc)

    def test_activity_to_event_strava_title(self) -> None:
        event = strava.activity_to_event(SAMPLE_ACTIVITY, title_mode="strava")
        self.assertEqual(event["title"], "Evening Run")

    def test_overnight_end_date(self) -> None:
        activity = dict(SAMPLE_ACTIVITY)
        activity["start_date_local"] = "2026-08-10T23:30:00Z"
        activity["elapsed_time"] = 3600
        event = strava.activity_to_event(activity)
        self.assertEqual(event["date"], "2026-08-10")
        self.assertEqual(event["end_date"], "2026-08-11")
        self.assertEqual(event["end_time"], "00:30")


class MergeTests(unittest.TestCase):
    def test_merge_adds_and_updates_by_strava_id(self) -> None:
        existing = [
            {
                "title": "自分の練習",
                "date": "2026-08-10",
                "urls": ["https://www.strava.com/activities/987654321"],
                "description": "old",
            },
            {"title": " unrelated", "date": "2026-08-11"},
        ]
        incoming = [
            strava.activity_to_event(SAMPLE_ACTIVITY),
            strava.activity_to_event(
                {
                    **SAMPLE_ACTIVITY,
                    "id": 111,
                    "start_date_local": "2026-08-12T07:00:00Z",
                    "elapsed_time": 1800,
                }
            ),
        ]
        merged, added, updated = strava.merge_strava_events(
            existing, incoming, update_existing=True
        )
        self.assertEqual(added, 1)
        self.assertEqual(updated, 1)
        self.assertEqual(len(merged), 3)
        self.assertIn("距離: 10.00km", str(merged[0]["description"]))

    def test_import_writes_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            seed = out_dir / "events.2026.yaml"
            seed.write_text(
                "# カスタム予定・メモ（2026年）\n"
                "# 祝日は scripts/generate_calendar.py が自動追加します。\n"
                "# 件数: 1\n"
                "year: 2026\n"
                "events:\n"
                "- title: 既存\n"
                "  date: '2026-01-01'\n"
                "  all_day: true\n"
                "  category: 予定\n",
                encoding="utf-8",
            )
            results = strava.import_activities(
                [SAMPLE_ACTIVITY],
                out_dir,
                merge=True,
                update_existing=True,
                title_mode="personal",
                dry_run=False,
            )
            self.assertEqual(results[2026][1], 1)  # added
            text = (out_dir / "events.2026.yaml").read_text(encoding="utf-8")
            self.assertIn("自分の練習", text)
            self.assertIn("https://www.strava.com/activities/987654321", text)
            self.assertIn("既存", text)


class ClientTests(unittest.TestCase):
    def test_ensure_access_token_refreshes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_path = Path(tmp) / "tokens.json"
            token_path.write_text(
                json.dumps(
                    {
                        "access_token": "old",
                        "refresh_token": "refresh-1",
                        "expires_at": 1,
                    }
                ),
                encoding="utf-8",
            )

            def fake_http(method, url, headers=None, form=None, timeout=30.0):
                self.assertEqual(method, "POST")
                self.assertEqual(form["grant_type"], "refresh_token")
                return {
                    "access_token": "new-access",
                    "refresh_token": "refresh-2",
                    "expires_at": int(datetime.now(timezone.utc).timestamp()) + 3600,
                    "expires_in": 3600,
                    "token_type": "Bearer",
                }

            client = strava.StravaClient(
                client_id="cid",
                client_secret="sec",
                token_path=token_path,
                http=fake_http,
            )
            with mock.patch.dict("os.environ", {}, clear=True):
                # Keep PATH-independent; only clear Strava env vars
                pass
            with mock.patch.dict(
                "os.environ",
                {
                    "STRAVA_ACCESS_TOKEN": "",
                    "STRAVA_REFRESH_TOKEN": "",
                },
                clear=False,
            ):
                token = client.ensure_access_token()
            self.assertEqual(token, "new-access")
            saved = json.loads(token_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["refresh_token"], "refresh-2")

    def test_list_activities_paginates(self) -> None:
        calls: list[str] = []

        def fake_http(method, url, headers=None, form=None, timeout=30.0):
            calls.append(url)
            if "page=1" in url:
                return [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
            if "page=2" in url:
                return [{"id": 3, "name": "c"}]
            return []

        with tempfile.TemporaryDirectory() as tmp:
            token_path = Path(tmp) / "tokens.json"
            future = int(datetime.now(timezone.utc).timestamp()) + 10_000
            token_path.write_text(
                json.dumps(
                    {
                        "access_token": "tok",
                        "refresh_token": "r",
                        "expires_at": future,
                    }
                ),
                encoding="utf-8",
            )
            client = strava.StravaClient(
                client_id="cid",
                client_secret="sec",
                token_path=token_path,
                http=fake_http,
            )
            with mock.patch.dict(
                "os.environ",
                {"STRAVA_ACCESS_TOKEN": "", "STRAVA_REFRESH_TOKEN": ""},
                clear=False,
            ):
                items = client.list_activities(per_page=2)
            self.assertEqual([i["id"] for i in items], [1, 2, 3])
            self.assertEqual(len(calls), 2)


class CliTests(unittest.TestCase):
    def test_import_from_json_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "acts.json"
            json_path.write_text(json.dumps([SAMPLE_ACTIVITY]), encoding="utf-8")
            out_dir = Path(tmp) / "input"
            out_dir.mkdir()
            code = strava.main(
                [
                    "import",
                    "--from-json",
                    str(json_path),
                    "--out-dir",
                    str(out_dir),
                    "--dry-run",
                ]
            )
            self.assertEqual(code, 0)
            self.assertFalse((out_dir / "events.2026.yaml").exists())

    def test_auth_prints_url(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {"STRAVA_CLIENT_ID": "123", "STRAVA_CLIENT_SECRET": "secret"},
            clear=False,
        ):
            code = strava.main(["auth"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
