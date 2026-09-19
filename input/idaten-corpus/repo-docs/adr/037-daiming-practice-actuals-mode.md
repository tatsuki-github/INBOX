# ADR 037: いだてん岱明・練習メニューは予定廃止・実績入力へ

- Status: Accepted
- Date: 2026-09-19

## Context

2026 年夏期は `practice_schedules.yaml` と日別計画メモで朝練/夕練メニューを事前配置していた。
現場運用を「今日から先は予定を置かず、実施後に実績を入れる」へ切り替える。

## Decision

1. **`actuals_mode_from: "2026-09-19"`** を `input/practice_schedules.yaml` に置く。
2. 当日以降の**練習メニュー予定**（朝練/夕練シェル、日別計画メモの未来セクション）を削除／アーカイブする。大会・市練習会は残す。
3. **`apply_practice_schedule.py`** は cutoff 以降の日付を生成しない。
4. **`lint_events.py`** は cutoff 以降の `status: scheduled` な岱明練習メニューをエラーにする。
5. **`generate_practice.py --apply`** は cutoff 以降を `status: done` で書く。
6. 実績の正本は `input/events.YYYY.yaml` の `practice` ブロック。

## Consequences

- カレンダー／RAG は「これから何をするか」ではなく「何をしたか」を主に返す。
- 夏期スケジュールの再適用で未来予定が復活しない。
- 予定と実績の取り違えを lint で早期検出できる。
