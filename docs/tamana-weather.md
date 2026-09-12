# 玉名市の天気データ更新

## 更新方針

`scripts/update_tamana_weather.py` は、指定期間の予報を Open-Meteo から取得します。

- 開始日が今日から3日以上先: 3時間間隔
- 開始日が今日から2日以内: 1時間間隔
- 保存先: `weather/tamana-forecast.json` / `weather/tamana-forecast.csv`
- 収録項目: 天気、気温、湿度、降水量、風向、風速

## 実行例

来週分を先行登録:

    python3 scripts/update_tamana_weather.py --start 2026-09-14 --end 2026-09-20

対象日が近づいたら、同じコマンドを再実行すると1時間間隔へ更新されます。取得時点の予報を上書きするため、カレンダー生成前に実行してください。

    python3 scripts/generate_calendar.py --year 2026
