# いだてん岱明 Google Drive Import Index

Source:
- Shared drive root: [`0APcRf6IAzVPGUk9PVA`](https://drive.google.com/drive/folders/0APcRf6IAzVPGUk9PVA)
- Personal folder いだてん岱明（自分用）: [`1DkMD7BcofiAuUarIi8GoRFeK05KiCosK`](https://drive.google.com/drive/folders/1DkMD7BcofiAuUarIi8GoRFeK05KiCosK)

## Import policy applied
- Google Docs → `.md`; Sheets → `.csv` (text preferred).
- PDFs / images / videos → metadata stub `.md` + Drive `viewUrl` (no PDF binaries; ADR 010).
- 記録データベース/印刷用 stubbed (CSV present).
- Notionバックアップ / 荒玉駅伝歴代: empty.
- Skipped: Index.zip, Colab, 学習指導要領, ランナーズバイブル (not in roots).
- **追補**: `personal/t-tsuchiyama/sb/` — 所有者 t-tsuchiyama の中学生 SB CSV（ADR 012）。正規化先は [`../sb/middle-school/`](../sb/middle-school/INDEX.md)。

## Summary
- Content files: **211** + t-tsuchiyama SB 一式（別カウント。下表追記）
- Sidecar `.meta.json`: **212** + SB メタ
- Saved (full text): **61** + SB CSV
- Stubs (metadata + viewUrl): **150**
- Total content bytes: **1,215,249** (1.16 MiB) + SB 約 2.5 MiB
- By type: `{'markdown-doc': 49, 'csv': 12, 'pdf-stub': 78, 'md-stub': 19, 'media-stub': 53}`

## t-tsuchiyama SB（追補）

| Path | Title | Status | Drive URL |
|---|---|---|---|
| `personal/t-tsuchiyama/sb/SBデータベース.csv` | SBデータベース | saved | https://docs.google.com/spreadsheets/d/1eLkU3YgXolKZL4MLdhWcUdbJ1W3Xf6AMNcxzQr7i9jA/edit |
| `personal/t-tsuchiyama/sb/中学生SB.csv` | 中学生SB | saved | （SBデータベース フィルタ） |
| `personal/t-tsuchiyama/sb/output_all.csv` | output_all.csv | saved | https://drive.google.com/file/d/1ZXVviaRz9L6LqFsS9bIEf33kGcJWHe8S/view |
| `personal/t-tsuchiyama/sb/output_all_中学生.csv` | output_all 中学生 | saved | （フィルタ） |
| `personal/t-tsuchiyama/sb/output_reg_中学生_single_table.csv` | output_reg 中学生 | saved | https://drive.google.com/file/d/1i6gLfxcMJwaHenV8EI_xkAy6cl-WkIQ8/view |
| `personal/t-tsuchiyama/sb/output_reg_中学生_男子.csv` | output_reg 男子 | saved | https://drive.google.com/file/d/1Ojg97ON73IrM480HpdAfQCwQ2x4FOtJr/view |
| `personal/t-tsuchiyama/sb/output_reg_中学生_女子.csv` | output_reg 女子 | saved | https://drive.google.com/file/d/1lghf0GIa2euMEiObj8KPkOC2mFWKlbS6/view |

## Files (212)

| Path | Title | MIME | Bytes | Status | Drive URL |
|---|---|---|---:|---|---|
| `personal/2025年度玉名市の中学生.md` | 2025年度玉名市の中学生 | application/vnd.google-apps.document | 694 | saved | https://docs.google.com/document/d/1DqekTW3LQjJFiWV8LWltCDjJk6T9dnDgiBsSyiuXJDw/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/ATRC.md` | ATRC | application/vnd.google-apps.document | 604 | saved | https://docs.google.com/document/d/1st8oMNVM3CEgRwl_VR1Kubh6AXmF2GI8iSal6yON3ZU/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/Googleドライブマニュアル.md` | Googleドライブマニュアル | application/vnd.google-apps.document | 101 | saved | https://docs.google.com/document/d/1pf0yoivcrhwkreaqvYm8Vt4UcCihrOYaLWF0YzIr4p8/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/いだてん岱明出場予定.md` | いだてん岱明出場予定 | application/vnd.google-apps.document | 1125 | saved | https://docs.google.com/document/d/1cb8_MlNMY5cUhvAhjCuQ0JowG217fzkeSvEW7kk-27c/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/いだてん岱明部員.md` | いだてん岱明部員 | application/vnd.google-apps.document | 355 | saved | https://docs.google.com/document/d/1HSgAPx1BWQiz7pPdmEpoVeKko_oE5wvgtzKpZyRJ7Os/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/ウォーミングアップ.md` | ウォーミングアップ | application/vnd.google-apps.document | 73 | saved | https://docs.google.com/document/d/1pWEZh84r2lx_G_-vJRVB6nkYf1GKS8I1rxshaKOuMZU/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/中体連駅伝.md` | 中体連駅伝 | application/vnd.google-apps.document | 317 | saved | https://docs.google.com/document/d/1Lo575Dx0ggtvN_4-sBbuaTHBENVnk7iiH8_wVOPUI4Y/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/中学生の練習.md` | 中学生の練習 | application/vnd.google-apps.document | 792 | saved | https://docs.google.com/document/d/14VIr5TSM6rAicao-plIlgo4HY475ptfxEoMz75VLw4o/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/中学選手権_のコピー.csv` | 中学選手権 のコピー | application/vnd.google-apps.spreadsheet | 152247 | saved | https://docs.google.com/spreadsheets/d/1P8H1y1MmsuKzO5YiM64Km13SZSWUR6xIWrvqlMdRvac/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/動きづくり.md` | 動きづくり | application/vnd.google-apps.document | 383 | saved | https://docs.google.com/document/d/1R9MisOkaXF4PB4WlfAR05KNErGNmqeJfp12YVI7Z5yo/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/勤怠.md` | 勤怠 | application/vnd.google-apps.document | 354 | saved | https://docs.google.com/document/d/1mwfibCpBdj7T8kGSLO6hKsmWECN5CHU8l5yYlbmGh58/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/参考サイト.md` | 参考サイト | application/vnd.google-apps.document | 172 | saved | https://docs.google.com/document/d/1nXzhrjITEevgHM0FeEV5IAVwkfHK1FDgnuMtUSQgb1I/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/夏休みの練習.md` | 夏休みの練習 | application/vnd.google-apps.document | 236 | saved | https://docs.google.com/document/d/1MhrTb2UPCbqIYPDzbYYGL6MdSFjqfpZw-qeRbYe5rsE/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/早熟と後伸びについて.md` | 早熟と後伸びについて | application/vnd.google-apps.document | 673 | saved | https://docs.google.com/document/d/11WFDJSo5-ADMPS8woZO4XP3OG-Ioyb1C6j4nVsEFmm8/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/謝礼金.md` | 謝礼金 | application/vnd.google-apps.document | 16 | saved | https://docs.google.com/document/d/1wnXhW1ozpI1NY220nAHWAeGkHszSqbJaKIvyN2QGxfE/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/通信陸上.md` | 通信陸上 | application/vnd.google-apps.document | 122 | saved | https://docs.google.com/document/d/1vEmeIripXpH9nwB9tWF_DKN96o8roS-v36Y_nPNFFu4/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/通信陸上_のコピー.csv` | 通信陸上 のコピー | application/vnd.google-apps.spreadsheet | 171229 | saved | https://docs.google.com/spreadsheets/d/1UCw3gtpIAUaAX0YtIw1diueSt8qzSWIgVk_GVL_1ysg/edit?usp=drivesdk&ouid=112681577980405057294 |
| `personal/選手権と通信のタイム差_のコピー.csv` | 選手権と通信のタイム差 のコピー | application/vnd.google-apps.spreadsheet | 35402 | saved | https://docs.google.com/spreadsheets/d/1jFyDp38ouVlpy670FA7Z5mWbK5HEB9bVrBBZ3q6qm_o/edit?usp=drivesdk&ouid=112681577980405057294 |
| `shared/Notionバックアップ/README.md` | README.md | text/markdown | 106 | saved |  |
| `shared/Notionバックアップ/_EMPTY.md` | Notionバックアップ | application/vnd.google-apps.folder | 380 | saved | https://drive.google.com/drive/folders/1VAErCDP0BeXuCHj_WebecGNuoNBeiABw |
| `shared/フォト/20250531_玉名市練習会/1748942808411.jpg.md` | 1748942808411.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1afudfjeNpbpQCO_5oRhqu4gKu2N99kHE/view?usp=drivesdk |
| `shared/フォト/20250531_玉名市練習会/1748942808599.jpg.md` | 1748942808599.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1zUnLF81-0_ApubWao7_QAOPCa5sXpNgN/view?usp=drivesdk |
| `shared/フォト/20250531_玉名市練習会/1748942808656.jpg.md` | 1748942808656.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1sITuFXH-ZnGen_yM63D0mFIU421C-Pum/view?usp=drivesdk |
| `shared/フォト/20250531_玉名市練習会/1748942808688.jpg.md` | 1748942808688.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/110axTcrgaMofukA6ElhRvVfBe4MzTw9J/view?usp=drivesdk |
| `shared/フォト/20250531_玉名市練習会/1748942808721.jpg.md` | 1748942808721.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/11JMsNhHe8Eq8QiRanlB4aJ-48arae2lA/view?usp=drivesdk |
| `shared/フォト/20250531_玉名市練習会/1748950104787.mp4.md` | 1748950104787.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1B12QMmabPxAapd0EMRErAvjzYOf-u5wb/view?usp=drivesdk |
| `shared/フォト/20250531_玉名市練習会/1748950111552.mp4.md` | 1748950111552.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1RcoQluzNijy4iGaGhQ86SZZzFG4Apmh0/view?usp=drivesdk |
| `shared/フォト/20250531_玉名市練習会/1748950117365.mp4.md` | 1748950117365.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1TIDyNWLSQyPHb8aP4JA85WyNf3RocA18/view?usp=drivesdk |
| `shared/フォト/20250531_玉名市練習会/1748950122717.mp4.md` | 1748950122717.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1MPqngxXojgSqXdA4uaDZczOc8taMYp34/view?usp=drivesdk |
| `shared/フォト/20250531_玉名市練習会/1748950151198.mp4.md` | 1748950151198.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/12aTUVcFFnp5jjAlQ0gSj4ISSugSeBbt5/view?usp=drivesdk |
| `shared/フォト/20250531_玉名市練習会/1748950213159.mp4.md` | 1748950213159.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1WPhy4mu77ve3wcWvpBUSMPYWWz4nKF9u/view?usp=drivesdk |
| `shared/フォト/20250531_玉名市練習会/1748950219274.mp4.md` | 1748950219274.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1SyNr6td44yNmEJXWya3GBF843XwVxbef/view?usp=drivesdk |
| `shared/フォト/20250531_玉名市練習会/1748950223437.mp4.md` | 1748950223437.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1KoAM1OWxCoUVyF_T9TeD3wCfowbNSJ_C/view?usp=drivesdk |
| `shared/フォト/20250531_玉名市練習会/1748950232297.mp4.md` | 1748950232297.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1ewUlpRWEnPNRuskYctxcWADmtgp6U4jy/view?usp=drivesdk |
| `shared/フォト/20250531_玉名市練習会/1748950238012.mp4.md` | 1748950238012.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1alOtdAGadVv__qRH6FuhqVFTEzvhB-tR/view?usp=drivesdk |
| `shared/フォト/20250621_玉名市練習会/1750558888023.jpg.md` | 1750558888023.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1bfXEjD_rdPbzcRcrvVD8TnWQesM2y36o/view?usp=drivesdk |
| `shared/フォト/20250621_玉名市練習会/1750558888159.jpg.md` | 1750558888159.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1c7idWXWdO75gYSNHfH7I8dY5Q-K7lj_h/view?usp=drivesdk |
| `shared/フォト/20250621_玉名市練習会/1750558888198.jpg.md` | 1750558888198.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1c52IBwh1XXze5EzlMJ5wsbNH6r15G6Xi/view?usp=drivesdk |
| `shared/フォト/20250621_玉名市練習会/1750558888227.jpg.md` | 1750558888227.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1bXkFLvk57Cxk5KTnU2jzrZoZP7q5w2Pg/view?usp=drivesdk |
| `shared/フォト/20250621_玉名市練習会/1750558888250.jpg.md` | 1750558888250.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1cAyrdIUwtHi0szeAuIGCTB39r2kUhomL/view?usp=drivesdk |
| `shared/フォト/20250621_玉名市練習会/1750558888279.jpg.md` | 1750558888279.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1biJNIp9g69j73XHUSc_X_kSJM9QDRXu7/view?usp=drivesdk |
| `shared/フォト/20250621_玉名市練習会/1750558888302.jpg.md` | 1750558888302.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1biDVICbGc2IdJIuJy9LgzKVIui7MrYdA/view?usp=drivesdk |
| `shared/フォト/20250621_玉名市練習会/1750558888325.jpg.md` | 1750558888325.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1cAHK551sMGSY3RKKn9bGIiRTKxzqsMv4/view?usp=drivesdk |
| `shared/フォト/20250621_玉名市練習会/1750558906926.mp4.md` | 1750558906926.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1bdHPKQ0Nr8unznodGagRzfi1uJbGPb6O/view?usp=drivesdk |
| `shared/フォト/20250621_玉名市練習会/1750558917648.mp4.md` | 1750558917648.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1b_IVnsgTK-xqYSrYtsR_DhYp4kWMS3yZ/view?usp=drivesdk |
| `shared/フォト/20250621_玉名市練習会/1750558921688.mp4.md` | 1750558921688.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1bvPOufS9oXBOJRZ6SOJ_3hJBMSEUoXuj/view?usp=drivesdk |
| `shared/フォト/20250621_玉名市練習会/1750558925025.mp4.md` | 1750558925025.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1boHEsCz5Z4tbDKhurudEESEtp6nf8NYw/view?usp=drivesdk |
| `shared/フォト/20250621_玉名市練習会/1750558938125.mp4.md` | 1750558938125.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1bYZrPGjF5u_zWqCIuyXJT0mOnmMFcSNN/view?usp=drivesdk |
| `shared/フォト/20250621_玉名市練習会/1750558947793.mp4.md` | 1750558947793.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1bY2_T2vOJvVJetBaPuYTRDUIUiX-eMqr/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386144927.jpg.md` | 1752386144927.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1ryk7FDcOHPAwsGJXS02sJeoDypySIf9G/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386145062.jpg.md` | 1752386145062.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1s9Dyuhymebn2ANFQ7xq9iWdYUQjfvqs1/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386145107.jpg.md` | 1752386145107.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1s8Mqt5Fp-gA6JvthPHQTfyVaxAsfA-Sw/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386156662.mp4.md` | 1752386156662.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1sR-TUGSOavpTkwJBoS1xpvEtlg5xpJzl/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386161006.mp4.md` | 1752386161006.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1rb218HeQ4AJk-2FXxu8MDGzXwsJWKY0A/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386164581.mp4.md` | 1752386164581.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1s3YnJI67q89YCLodWwdC89JdOfVOcOKn/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386168015.mp4.md` | 1752386168015.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1s23W7xBRkL0is0g1WhEo8C7WioxNvlKc/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386170576.mp4.md` | 1752386170576.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1sWf4MlSgMXgUmUqyAh2jLA0RKidyDEie/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386172855.mp4.md` | 1752386172855.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1sT--APR9rep0oNmLxZUlcgag6iY2XKFq/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386175604.mp4.md` | 1752386175604.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1rwBJcEwQOVPck2mKhPohWVs5hiEBACQl/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386177969.mp4.md` | 1752386177969.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1roOAXJjM4EFRAtIRbw6Z2g1qMtKIbWUZ/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386180411.mp4.md` | 1752386180411.mp4 | video/mp4 | 350 | stub | https://drive.google.com/file/d/1s7AtzwP7CwMquNV9liwsxtfyr3o_C2TD/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386185287.jpg.md` | 1752386185287.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1s5U1JfVCvCNgJnGQa8dMiUQnCOvhXmMp/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386185349.jpg.md` | 1752386185349.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1sH3t2M6cN8HURgiqqpnQo-YC1-vxdPmg/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386185389.jpg.md` | 1752386185389.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1sCyBPaPP5F3p5ug0tJPc59P6AEKl5g3F/view?usp=drivesdk |
| `shared/フォト/20250712_玉名市練習会/1752386185424.jpg.md` | 1752386185424.jpg | image/jpeg | 350 | stub | https://drive.google.com/file/d/1rz8khh0_vzVo4Iumy9D1PTIcFv7qNl_z/view?usp=drivesdk |
| `shared/フォト/20250927_ジュニア駅伝/IMG_0051.JPG.md` | IMG_0051.JPG | image/jpeg | 345 | stub | https://drive.google.com/file/d/12tGVThplIMdY0Kv2lAQMq1moS1GWsifm/view?usp=drivesdk |
| `shared/フォト/20250927_ジュニア駅伝/IMG_0052.JPG.md` | IMG_0052.JPG | image/jpeg | 345 | stub | https://drive.google.com/file/d/1NfMBSEE3rT21u2rWoEWbrRkk4-YXaihO/view?usp=drivesdk |
| `shared/フォト/20250927_ジュニア駅伝/IMG_0053.JPG.md` | IMG_0053.JPG | image/jpeg | 345 | stub | https://drive.google.com/file/d/1vb_LeenU_HT0w4zpBEE-hUAhbXQSMmdx/view?usp=drivesdk |
| `shared/フォト/20250927_ジュニア駅伝/IMG_0054.JPG.md` | IMG_0054.JPG | image/jpeg | 345 | stub | https://drive.google.com/file/d/1mI6rBFDewG82-07BB26c1rjqHOhZH6DB/view?usp=drivesdk |
| `shared/フォト/20250927_ジュニア駅伝/IMG_0055.JPG.md` | IMG_0055.JPG | image/jpeg | 345 | stub | https://drive.google.com/file/d/1NMRAXOQKBDMdTybJqt9DqDyMR5jyjz_j/view?usp=drivesdk |
| `shared/フォト/20250927_ジュニア駅伝/IMG_0056.JPG.md` | IMG_0056.JPG | image/jpeg | 345 | stub | https://drive.google.com/file/d/1sByEmdUEfBgWVY_0KtdTFaeW_gx11GzA/view?usp=drivesdk |
| `shared/フォト/20250927_ジュニア駅伝/IMG_0057.JPG.md` | IMG_0057.JPG | image/jpeg | 345 | stub | https://drive.google.com/file/d/1zsYWSUOoz2Yr4fJ0JngwcyNXfFPCaO_L/view?usp=drivesdk |
| `shared/フォト/20250927_ジュニア駅伝/IMG_0058.JPG.md` | IMG_0058.JPG | image/jpeg | 345 | stub | https://drive.google.com/file/d/1jSok5zSrQxrzAJq4WsxWSZehpksSjfp1/view?usp=drivesdk |
| `shared/フォト/20250927_ジュニア駅伝/IMG_0059.JPG.md` | IMG_0059.JPG | image/jpeg | 345 | stub | https://drive.google.com/file/d/1nD91LIf6zXUbHbcbSFXXzuI4sy6_cF-M/view?usp=drivesdk |
| `shared/フォト/INDEX.md` | フォト | application/vnd.google-apps.folder | 395 | saved | https://drive.google.com/drive/folders/1T8TFLnPpERek0rjhpgR7-mC_bitcGcGy |
| `shared/フォト/README.md` | README.md | text/markdown | 160 | saved |  |
| `shared/分析/2026年度荒玉男子.pdf.md` | 2026年度荒玉男子.pdf | application/pdf | 343 | stub | https://drive.google.com/file/d/17wQY9f09Y6qPsp1rHkGGoiVMIs7QuuXA/view |
| `shared/分析/2026年荒玉女子.pdf.md` | 2026年荒玉女子.pdf | application/pdf | 340 | stub | https://drive.google.com/file/d/1d1oEtMhvMte6d0JvXhZMNL5GigTYcR-i/view |
| `shared/分析/関係図_2026.pdf.md` | 関係図_2026.pdf | application/pdf | 335 | stub | https://drive.google.com/file/d/13rJOJcdSi15DVBS0o-4g3X3673Y7hFCq/view |
| `shared/名簿/2025年度.csv` | 2025年度 | application/vnd.google-apps.spreadsheet | 3810 | saved | https://docs.google.com/spreadsheets/d/1-KfsP4tl_igL8lFsiNY9AOyUJtXhOBiFGYN0qXTlETY/edit?usp=drivesdk&ouid=112681577980405057294 |
| `shared/名簿/2025年度_岱明中学校陸上競技部_部員名簿.csv` | 2025年度_岱明中学校陸上競技部_部員名簿.csv | text/csv | 1228 | saved | https://drive.google.com/file/d/1DGST4sWNCzH3C7i4mMZiIkSpYeGdaag7/view |
| `shared/大会/2025年度/0228_熊本市駅伝/結果.md` | 結果 | application/vnd.google-apps.document | 250 | saved | https://docs.google.com/document/d/1DvqlKfQq-gKwb-F4csQnhCeI1fQiWYpUBkPMKGrLWsA/edit |
| `shared/大会/2025年度/0315_金栗駅伝/記録.md` | 記録 | application/vnd.google-apps.document | 717 | saved | https://docs.google.com/document/d/1F8dweyCH3SCM2FooiQVRQjwYLgn2vp8bA5hWBfY4Nd0/edit |
| `shared/大会/2025年度/0419_第４４回熊本市陸上競技選手権/女子中学1500m結果.mht.md` | 女子中学 １５００ｍ ﾀｲﾑﾚｰｽ総合結果.mht | multipart/related | 393 | stub | https://drive.google.com/file/d/1LXazqRV54XFAkCJtLd_TkVE09eVb0DRL/view?usp=drivesdk |
| `shared/大会/2025年度/0419_第４４回熊本市陸上競技選手権/男子中学1500m結果.mht.md` | 男子中学 １５００ｍ ﾀｲﾑﾚｰｽ総合結果.mht | multipart/related | 393 | stub | https://drive.google.com/file/d/1eBB9aO6JwJkQmb8eooitSF2JRGPr_Bza/view?usp=drivesdk |
| `shared/大会/2025年度/0419_第４４回熊本市陸上競技選手権/要項.pdf.md` | 要項.pdf | application/pdf | 339 | stub | https://drive.google.com/file/d/1zSTHvlCMTUsImKGAc-tQlATrEbktEx9Z/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/いだてん岱明出場予定.pdf.md` | いだてん岱明出場予定.pdf | application/pdf | 34636 | stub | https://drive.google.com/file/d/13SW2mg8VIqNtC9TYKJxjD2NXag0nO0G-/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/スタートリスト.pdf.md` | スタートリスト.pdf | application/pdf | 342 | stub | https://drive.google.com/file/d/1Dtsw33QtmwK92I_VHiVLZmb2_Cy1znG2/view |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/タイムテーブル.pdf.md` | タイムテーブル.pdf | application/pdf | 354 | stub | https://drive.google.com/file/d/1Vrq0zcbzS3qJiY_VRosV6cMinll17zqU/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/実施要項.pdf.md` | 実施要項.pdf | application/pdf | 332 | stub | https://drive.google.com/file/d/1rfFXTtjVYZtnzcfxg9UVZWvGGNgblrH7/view |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/岱明中参加計画.pdf.md` | 岱明中参加計画.pdf | application/pdf | 354 | stub | https://drive.google.com/file/d/1OZwA87li4tAzsFzokDnpLKtMhzZVLkS0/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/撮影に関する注意事項.pdf.md` | 撮影に関する注意事項.pdf | application/pdf | 363 | stub | https://drive.google.com/file/d/1zSQhEj8fIP2JDGabr0x31lLBHrRuR3s5/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/申し合わせ事項.pdf.md` | 申し合わせ事項.pdf | application/pdf | 354 | stub | https://drive.google.com/file/d/1_yQc2AYJK1qNFFJyepD5Rze8ffLv8198/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/競技注意事項.pdf.md` | 競技注意事項.pdf | application/pdf | 351 | stub | https://drive.google.com/file/d/1A7C9Fk5YhGBBY-6E_f2S9uOoe-kFAM5u/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/結果/いだてん岱明の結果.md` | いだてん岱明の結果 | application/vnd.google-apps.document | 376 | saved | https://docs.google.com/document/d/1euiCKHe_h6_52fBryEE1TVwyVeTzmOM-PWku9FBYh2A/edit |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/結果/女子1年800mタイムレース総合結果.png.md` | 女子1年800mタイムレース総合結果.png | image/png | 382 | stub | https://drive.google.com/file/d/1RVz5erukARNbRk5JoNeC3IJnmCLoyqq7/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/結果/女子2年800mタイムレース総合結果.png.md` | 女子2年800mタイムレース総合結果.png | image/png | 382 | stub | https://drive.google.com/file/d/1RM6bgM8gVxAlHz1AgX3ycLOTjNBJkiy0/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/結果/女子3年800mタイムレース総合結果.png.md` | 女子3年800mタイムレース総合結果.png | image/png | 382 | stub | https://drive.google.com/file/d/1RWzE3gncgYTYD4eHpMSSe0Hu8fKi5c7C/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/結果/女子共通1500mタイムレース総合結果.png.md` | 女子共通1500mタイムレース総合結果.png | image/png | 385 | stub | https://drive.google.com/file/d/1QOK752CCtdbKdoviSnrfMX0Ow0ma7tAY/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/結果/男子1年1500mタイムレース総合結果.png.md` | 男子1年1500mタイムレース総合結果.png | image/png | 384 | stub | https://drive.google.com/file/d/1RLwCB__3WcDBswPVKUMSEdb4ruM_HFCl/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/結果/男子2年1500mタイムレース総合結果.png.md` | 男子2年1500mタイムレース総合結果.png | image/png | 384 | stub | https://drive.google.com/file/d/1RawJMhftRQPzuoSC0Or0g1DufL4rqkuv/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/結果/男子共通3000mタイムレース総合結果.png.md` | 男子共通3000mタイムレース総合結果.png | image/png | 385 | stub | https://drive.google.com/file/d/1QTIll18Wyc8WAJOx1H4yp0zQey5uEFhT/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/結果/男子共通800mタイムレース総合結果.png.md` | 男子共通800mタイムレース総合結果.png | image/png | 384 | stub | https://drive.google.com/file/d/1R_7_uk87PYTh_Jsrl4NLKJoXsEAdd-ZX/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/練習会場図.pdf.md` | 練習会場図.pdf | application/pdf | 348 | stub | https://drive.google.com/file/d/1IxtwY2-aiX-PFyb46VnBSBS2JUmhzcWH/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/衣服運搬について.pdf.md` | 衣服運搬について.pdf | application/pdf | 357 | stub | https://drive.google.com/file/d/1Thyrri2DaSqnFfM_-6YN_6z5pPX62_MX/view?usp=drivesdk |
| `shared/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/重要事項.md` | 重要事項 | application/vnd.google-apps.document | 473 | saved | https://docs.google.com/document/d/1zKNcVZY-LK0U2v38OTFn14rG3ML0a89Fe2r4pTpugAI/edit |
| `shared/大会/2025年度/0614_荒尾選手権（中止）/大会プログラム.pdf.md` | 大会プログラム.pdf | application/pdf | 355 | stub | https://drive.google.com/file/d/1OjvYRGsisuJQnW4Hb7221lOIc9q3ET-C/view?usp=drivesdk |
| `shared/大会/2025年度/0614_荒尾選手権（中止）/岱明中参加計画.pdf.md` | 岱明中参加計画.pdf | application/pdf | 354 | stub | https://drive.google.com/file/d/1OhVixB3UH07jW7tq9VYRcFs9L9-RLNmI/view?usp=drivesdk |
| `shared/大会/2025年度/0614_荒尾選手権（中止）/開催要項.pdf.md` | 開催要項.pdf | application/pdf | 345 | stub | https://drive.google.com/file/d/1AVzqzWhgWu2TF6PuYusH49gi2bUFXZNv/view?usp=drivesdk |
| `shared/大会/2025年度/0628-0629_全日本中学校通信陸上競技大会熊本県大会/いだてん岱明出場予定.md` | いだてん岱明出場予定 | application/vnd.google-apps.document | 764 | saved | https://docs.google.com/document/d/15HqIKAkShqGcQwz82cHQAASQhg-qKka2PMNM2hcoWO8/edit |
| `shared/大会/2025年度/0628-0629_全日本中学校通信陸上競技大会熊本県大会/いだてん岱明結果.md` | いだてん岱明結果 | application/vnd.google-apps.document | 569 | saved | https://docs.google.com/document/d/1_lXdpFSB-RID6XO4bQv0xztyjdlTkmdULI71trH60io/edit |
| `shared/大会/2025年度/0628-0629_全日本中学校通信陸上競技大会熊本県大会/スタートリスト.pdf.md` | スタートリスト.pdf | application/pdf | 342 | stub | https://drive.google.com/file/d/1dAX4qvVP7hdNp8ShczyvpRevmc-WstUb/view |
| `shared/大会/2025年度/0628-0629_全日本中学校通信陸上競技大会熊本県大会/タイムテーブル.md` | タイムテーブル | application/pdf | 349 | stub | https://drive.google.com/file/d/1aJmct0-FnLeZpmJ3XFSdN5imGBTEgztR/view?usp=drivesdk |
| `shared/大会/2025年度/0628-0629_全日本中学校通信陸上競技大会熊本県大会/リレー・オーダー用紙.pdf.md` | リレー・オーダー用紙.pdf | application/pdf | 49088 | stub | https://drive.google.com/file/d/1afWxbJCA0Iud5wVh_9VL1ksTSiEmyHKE/view?usp=drivesdk |
| `shared/大会/2025年度/0628-0629_全日本中学校通信陸上競技大会熊本県大会/大会要項.pdf.md` | 大会要項.pdf | application/pdf | 332 | stub | https://drive.google.com/file/d/1PsIStR7ABS4YvhW1LSpq-FBSse_GS85S/view |
| `shared/大会/2025年度/0628-0629_全日本中学校通信陸上競技大会熊本県大会/撮影に関する注意事項.pdf.md` | 撮影に関する注意事項.pdf | application/pdf | 363 | stub | https://drive.google.com/file/d/1adwigMVZaYEWhoJEUA35Ma2dtDE8ElqT/view?usp=drivesdk |
| `shared/大会/2025年度/0628-0629_全日本中学校通信陸上競技大会熊本県大会/申し合わせ事項.pdf.md` | 申し合わせ事項.pdf | application/pdf | 354 | stub | https://drive.google.com/file/d/1aTM-6Gtf9VGlms1TBq12UmgGeuIY_aNK/view?usp=drivesdk |
| `shared/大会/2025年度/0628-0629_全日本中学校通信陸上競技大会熊本県大会/競技注意事項.pdf.md` | 競技注意事項.pdf | application/pdf | 351 | stub | https://drive.google.com/file/d/1aOrp3as1m0J0mTfUQLsjSwvMrpKtIwM6/view?usp=drivesdk |
| `shared/大会/2025年度/0628-0629_全日本中学校通信陸上競技大会熊本県大会/練習会場図.pdf.md` | 練習会場図.pdf | application/pdf | 348 | stub | https://drive.google.com/file/d/1aZqgTTb52ZkZnlGgiecrs-JwExe--RUq/view?usp=drivesdk |
| `shared/大会/2025年度/0628-0629_全日本中学校通信陸上競技大会熊本県大会/衣服運搬について.pdf.md` | 衣服運搬について.pdf | application/pdf | 357 | stub | https://drive.google.com/file/d/1aeqgO8RtsLsTF5vWVe3kUmT4JSxSEQuX/view?usp=drivesdk |
| `shared/大会/2025年度/0719-0720_熊本県中学校総合体育大会陸上競技大会/いだてん岱明出場.md` | いだてん岱明出場 | application/vnd.google-apps.document | 895 | saved | https://docs.google.com/document/d/1SKYhihtDA7ch64vYxybyLP9e-WlGMas4CjLvVbV7gmY/edit |
| `shared/大会/2025年度/0719-0720_熊本県中学校総合体育大会陸上競技大会/ゴール後の導線について.pdf.md` | ゴール後の導線について.pdf | application/pdf | 366 | stub | https://drive.google.com/file/d/1ta7g9s-KK3e8DVfb8xIXJ5lOLnz6Y8Xv/view?usp=drivesdk |
| `shared/大会/2025年度/0719-0720_熊本県中学校総合体育大会陸上競技大会/スタートリスト.pdf.md` | スタートリスト.pdf | application/pdf | 355 | stub | https://drive.google.com/file/d/1tWnTdof2kLvPWiMLXg4X9RZ1osTBdjk3/view?usp=drivesdk |
| `shared/大会/2025年度/0719-0720_熊本県中学校総合体育大会陸上競技大会/タイムテーブル.pdf.md` | タイムテーブル.pdf | application/pdf | 353 | stub | https://drive.google.com/file/d/1u1L897KlkJK1AsFdr2PZ3BPCJbt2MV2l/view?usp=drivesdk |
| `shared/大会/2025年度/0719-0720_熊本県中学校総合体育大会陸上競技大会/審判編成.pdf.md` | 審判編成.pdf | application/pdf | 345 | stub | https://drive.google.com/file/d/1tXeZz3Rn9CZWgHWBpoXyb_tB-VCcN66r/view?usp=drivesdk |
| `shared/大会/2025年度/0719-0720_熊本県中学校総合体育大会陸上競技大会/撮影に関する注意事項.pdf.md` | 撮影に関する注意事項.pdf | application/pdf | 363 | stub | https://drive.google.com/file/d/1toqaqu1BHR0x0Yw6infEMTjArssYxG5T/view?usp=drivesdk |
| `shared/大会/2025年度/0719-0720_熊本県中学校総合体育大会陸上競技大会/申し合わせ・掃除分担.pdf.md` | 申し合わせ・掃除分担.pdf | application/pdf | 363 | stub | https://drive.google.com/file/d/1twXq9h-w3Lu3xPZiGqqvr7MPKRyvhmO4/view?usp=drivesdk |
| `shared/大会/2025年度/0719-0720_熊本県中学校総合体育大会陸上競技大会/競技注意事項.pdf.md` | 競技注意事項.pdf | application/pdf | 351 | stub | https://drive.google.com/file/d/1tyhuCOSgWoHWSozRYc2p_Yo4KEa1qhO_/view?usp=drivesdk |
| `shared/大会/2025年度/0719-0720_熊本県中学校総合体育大会陸上競技大会/練習会場図.pdf.md` | 練習会場図.pdf | application/pdf | 348 | stub | https://drive.google.com/file/d/1tclsgN9UcVlrw4FcUWd0nPbKVGcKQdmI/view?usp=drivesdk |
| `shared/大会/2025年度/0802_玉名選手権/いだてん岱明結果.md` | いだてん岱明結果 | application/vnd.google-apps.document | 326 | saved | https://docs.google.com/document/d/1ZFOsPWM-kLV0qS1hQst4Yqt-Xk7XikQy1tn57zTpyXY/edit |
| `shared/大会/2025年度/0802_玉名選手権/タイムテーブル.pdf.md` | タイムテーブル.pdf | application/pdf | 30472 | stub | https://drive.google.com/file/d/1-viejsZ98ArceFXt1u_vm2AdmV3LPJ1O/view?usp=drivesdk |
| `shared/大会/2025年度/0802_玉名選手権/トラック.pdf.md` | トラック.pdf | application/pdf | 345 | stub | https://drive.google.com/file/d/100csybdQtlca7-dbMls_5P3ffneusS9z/view?usp=drivesdk |
| `shared/大会/2025年度/0802_玉名選手権/歴代記録.pdf.md` | 歴代記録.pdf | application/pdf | 345 | stub | https://drive.google.com/file/d/101ulNyYlX3uWO1D99zkpEdJVIPKp3bTI/view?usp=drivesdk |
| `shared/大会/2025年度/0802_玉名選手権/要項.pdf.md` | 要項.pdf | application/pdf | 339 | stub | https://drive.google.com/file/d/1-vGfIn3v0Hsxoxc_-wTTQINCPe5bqy4A/view?usp=drivesdk |
| `shared/大会/2025年度/0802_玉名選手権/跳躍.pdf.md` | 跳躍.pdf | application/pdf | 339 | stub | https://drive.google.com/file/d/1-wRsgTV73YDpKiDFn0cFv9XKeS2iNr2l/view?usp=drivesdk |
| `shared/大会/2025年度/0830_玉名郡ナイター/R7タイムテーブル.pdf.md` | ★③R7タイムテーブル.pdf | application/pdf | 67933 | stub | https://drive.google.com/file/d/1PACfxpcUIZWp2xqICu-oTAhvbhKibErX/view?usp=drivesdk |
| `shared/大会/2025年度/0830_玉名郡ナイター/R7選手リスト.pdf.md` | ★④R7選手リスト(訂正).pdf | application/pdf | 364 | stub | https://drive.google.com/file/d/1P572fciy-R_BSBnAd9VRxexE7R2nArVH/view?usp=drivesdk |
| `shared/大会/2025年度/0830_玉名郡ナイター/結果.md` | 結果 | application/vnd.google-apps.document | 461 | saved | https://docs.google.com/document/d/1o8uaK1VGhLgBMc7XSS9yVEUEXPMmEukLZMzkiXrUlOQ/edit |
| `shared/大会/2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会/岱明の結果.md` | 岱明の結果 | application/vnd.google-apps.document | 541 | saved | https://docs.google.com/document/d/1-0bth3QzC2mbI09u2pIzG7WsHcwmbjQvVieJMvd4JFE/edit |
| `shared/大会/2025年度/0927_第２回熊本県ジュニア駅伝競走大会/岱明の結果.md` | 岱明の結果 | application/vnd.google-apps.document | 1109 | saved | https://docs.google.com/document/d/1-G3pIl4f44ZQbVCkEjPR91vsj_a0UY9WXCTJl4h09zo/edit |
| `shared/大会/2025年度/1015_玉名荒尾中体連駅伝/参加計画1.pdf.md` | 参加計画1.pdf | application/pdf | 334 | stub | https://drive.google.com/file/d/13jxQlVp953do7w_Vrb0T9aYjgQE76sYg/view |
| `shared/大会/2025年度/1015_玉名荒尾中体連駅伝/参加計画2.pdf.md` | 参加計画2.pdf | application/pdf | 334 | stub | https://drive.google.com/file/d/1o6SkMOyeNtaEUKRLMRHRkXOLn1SrvNMT/view |
| `shared/大会/2025年度/1015_玉名荒尾中体連駅伝/女子の結果.JPG.md` | 女子の結果.JPG | image/jpeg | 343 | stub | https://drive.google.com/file/d/1Ob_16QTu6vvMbQZzPgtvni7-NBGKteuR/view?usp=drivesdk |
| `shared/大会/2025年度/1015_玉名荒尾中体連駅伝/女子オーダー.md` | 女子オーダー | image/jpeg | 342 | stub | https://drive.google.com/file/d/1LKkiu1FBHQN7ANvHOB0xPWuR5UhT2q1T/view?usp=drivesdk |
| `shared/大会/2025年度/1015_玉名荒尾中体連駅伝/岱明の結果.md` | 岱明の結果 | application/vnd.google-apps.document | 854 | saved | https://docs.google.com/document/d/1-lUDvbgseGmez910dhX9LvRskV_uSDvJ3R7IYbbji1U/edit |
| `shared/大会/2025年度/1015_玉名荒尾中体連駅伝/男子の結果.JPG.md` | 男子の結果.JPG | image/jpeg | 343 | stub | https://drive.google.com/file/d/1G3p7uvkrDO3859IsupLU1EiKKxOifzwV/view?usp=drivesdk |
| `shared/大会/2025年度/1015_玉名荒尾中体連駅伝/男子オーダー.md` | 男子オーダー | image/jpeg | 342 | stub | https://drive.google.com/file/d/143eQA2hcXtmEv5L0P2nsP8GMPT3u1Vxu/view?usp=drivesdk |
| `shared/大会/2025年度/1118_熊本市中長距離選手権/スタートリスト.pdf.md` | スタートリスト.pdf | application/pdf | 354 | stub | https://drive.google.com/file/d/1p_MLy6Qipyz-t9WPTgCfN2SXjuR6zm1o/view?usp=drivesdk |
| `shared/大会/2025年度/1118_熊本市中長距離選手権/岱明の結果.md` | 岱明の結果 | application/vnd.google-apps.document | 619 | saved | https://docs.google.com/document/d/12OnACvygc2k3xLXI_hS81YMpSlpKjKH86tPf2fe4nzo/edit |
| `shared/大会/2025年度/1118_熊本市中長距離選手権/岱明の計画.JPG.md` | 岱明の計画.JPG | image/jpeg | 343 | stub | https://drive.google.com/file/d/17vsh35Jbz1YnhzySCp86nNNNhV6NsqxL/view?usp=drivesdk |
| `shared/大会/2025年度/1118_熊本市中長距離選手権/競技日程・注意事項・審判他.pdf.md` | 競技日程・注意事項・審判他.pdf | application/pdf | 372 | stub | https://drive.google.com/file/d/1MEhmQQTZiuO5PKqCRUR2PwNUJsOuY3Fa/view?usp=drivesdk |
| `shared/大会/2025年度/1118_熊本市中長距離選手権/要項.pdf.md` | 要項.pdf | application/pdf | 105235 | stub | https://drive.google.com/file/d/1FVOuaIVKroQp6Ij43mTENmcq5MYWOoVx/view?usp=drivesdk |
| `shared/大会/2025年度/1130_玉名市民マラソン/IMG_0247.JPG.md` | IMG_0247.JPG | image/jpeg | 336 | stub | https://drive.google.com/file/d/1aXsWXo1zVnUE8evOCTtsgguAi2cTqIih/view?usp=drivesdk |
| `shared/大会/2025年度/1130_玉名市民マラソン/コース.pdf.md` | コース.pdf | application/pdf | 343 | stub | https://drive.google.com/file/d/1GoTv8m5LVqc0CKZXxzdqNoj5AY_PYZFE/view?usp=drivesdk |
| `shared/大会/2025年度/1130_玉名市民マラソン/玉名市民マラソン_岱明の結果.md` | 玉名市民マラソン_岱明の結果 | application/vnd.google-apps.document | 342 | saved | https://docs.google.com/document/d/12ZF_8VJpfKDh4N5rKVl5C0rToAKmSXc1teqqy1RjOJg/edit |
| `shared/大会/2025年度/1130_玉名市民マラソン/要項.pdf.md` | 要項 .pdf | application/pdf | 340 | stub | https://drive.google.com/file/d/1PdD1TkvT3EFDHrECUN5Dn76uo-ZDZzp0/view?usp=drivesdk |
| `shared/大会/2025年度/1130_玉名市民マラソン/駐車券.pdf.md` | 駐車券.pdf | application/pdf | 342 | stub | https://drive.google.com/file/d/1ptLEbD_Pm-NkvZLQMuH4MTIJuy-RIW_-/view?usp=drivesdk |
| `shared/大会/2026年度/0411_第３４回金栗記念選抜陸上中長距離熊本大会/概要.md` | 概要 | application/vnd.google-apps.document | 246 | saved | https://docs.google.com/document/d/101MFazrtVu0c9JStUxQDR74I1SM7ok1itmDO5fsQnVE/edit |
| `shared/大会/2026年度/0411_第３４回金栗記念選抜陸上中長距離熊本大会/結果.md` | 結果 | application/vnd.google-apps.document | 225 | saved | https://docs.google.com/document/d/1QcEZQLx0LEyS8JQ7hz6eLmtQTN4vj1HYZjcA1el4oQM/edit |
| `shared/大会/2026年度/0418_第４５回熊本市陸上競技選手権大会/結果.md` | 結果 | application/vnd.google-apps.document | 760 | saved | https://docs.google.com/document/d/1MC3hi0Y3QDl4qRzHR81gdl1yARO9hK_Qg8ICqqBXFUI/edit |
| `shared/大会/2026年度/0509_第１回熊本県長距離記録会/結果.md` | 結果 | application/vnd.google-apps.document | 593 | saved | https://docs.google.com/document/d/1gwvI5TmbKNbdwJgL7eKvAWNtoMzfmu5Dge3mz88xh3w/edit |
| `shared/大会/2026年度/0523-0524_熊本県中学校陸上選手権・混成/結果.md` | 結果 | application/vnd.google-apps.document | 811 | saved | https://docs.google.com/document/d/1H7Y9CiyUH7HzofuC5HeIO0lsJT-S0iDbFeWPJjbbw_k/edit |
| `shared/大会/2026年度/0613_全日本中学校通信陸上競技大会熊本県大会/結果.md` | 結果 | application/vnd.google-apps.document | 752 | saved | https://docs.google.com/document/d/1gjaw6NSdctUYc1KRKtjipL7e_AvA_pLY-u3OxFxK1-Y/edit |
| `shared/大会/2026年度/0628_荒尾選手権/結果.md` | 結果 | application/vnd.google-apps.document | 676 | saved | https://docs.google.com/document/d/1EkGfA9y59xQBsS4Y2XH8yEEZ6vDglNsnLv1D2kTk1ZU/edit |
| `shared/大会/2026年度/0704_第２回熊本県長距離記録会/結果.md` | 結果 | application/vnd.google-apps.document | 704 | saved | https://docs.google.com/document/d/1Lx1yVCWjfYo5QnCvZdX9_I1zP5-OISZg1OCtFnkcTkw/edit |
| `shared/大会/2026年度/0718-0720_熊本県中学校総合体育大会陸上競技大会/結果.md` | 結果 | application/vnd.google-apps.document | 705 | saved | https://docs.google.com/document/d/1YaYTtu_LO1iBcIkYkvjEywvj1XGtm2cJVgfFcAtGnBw/edit |
| `shared/大会/2026年度/0829_ジュニアオリンピックU16熊本県予選会/結果.md` | 結果 | application/vnd.google-apps.document | 203 | saved | https://docs.google.com/document/d/16xBgqrJR6778tB8CT65s9k9sQ-qc1T7cAC9BkW0Q9-U/edit |
| `shared/大会/2026年度/0829_玉名郡ナイター中・長距離記録会/参加者メモ.md` | 参加者メモ | application/vnd.google-apps.document | 2749 | saved | https://docs.google.com/document/d/1lGhyF4XAOG9B49Nf4NjPCwjKlAhTzwxm1Gc_DbaPCJg/edit |
| `shared/大会/2026年度/0829_玉名郡ナイター中・長距離記録会/結果.md` | 結果 | application/vnd.google-apps.document | 667 | saved | https://docs.google.com/document/d/1k4ka2olKO0ZQPgwTYKxOzMlGaHFjWwAzQsx3uanjMf4/edit |
| `shared/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/開催要項.md` | 開催要項 | application/vnd.google-apps.document | 1889 | saved | https://docs.google.com/document/d/1StOtyLMoZ4NiacdLbUaBG0qE3GwFY7iphFiPgBxmGog/edit |
| `shared/大会/2026年度/1014-1015_荒玉中体連駅伝/概要.md` | 概要 | application/vnd.google-apps.document | 149 | saved | https://docs.google.com/document/d/1mmhH_q4gvFt6EMPD8EywW39zAdh9nIGteEStxM5ifk0/edit |
| `shared/大会/2026年度/1211_岱明中校内駅伝大会/概要.md` | 概要 | application/vnd.google-apps.document | 153 | saved | https://docs.google.com/document/d/1JaxpOQFqSJGUbNDwQ4OrkVkzP1tTL7MxhcdyAueqDmk/edit |
| `shared/大会/荒玉駅伝歴代/_EMPTY.md` | 荒玉駅伝歴代 | application/vnd.google-apps.folder | 55 | saved | https://drive.google.com/drive/folders/1XRxBeG1wkG3c92Y-h5ycPgbBL7Ep1ief |
| `shared/指導者研修会/20250516/R7年度玉名市地域部活動一覧.pdf.md` | R7年度玉名市地域部活動一覧.pdf | application/pdf | 358 | stub | https://drive.google.com/file/d/1Z_mQQUaT5r90T80Jnj7R9aq7kBBFVsCF/view |
| `shared/指導者研修会/20250516/「地域部活動」（玉名モデル）がめざすもの.pdf.md` | 「地域部活動」（玉名モデル）がめざすもの.pdf | application/pdf | 380 | stub | https://drive.google.com/file/d/1FGVA4TSg-hyCuYsf9Ot5jErDDXVCuaRK/view |
| `shared/指導者研修会/20250516/不適切行為を根絶！1.pdf.md` | 不適切行為を根絶！1.pdf | application/pdf | 349 | stub | https://drive.google.com/file/d/1EvaV6ugy5kK7yybZQlozymf-gK_mB8eN/view |
| `shared/指導者研修会/20250516/不適切行為を根絶！2.pdf.md` | 不適切行為を根絶！2.pdf | application/pdf | 349 | stub | https://drive.google.com/file/d/16vDq4WIlovTtAobeTHbF3N4_EsQkouwf/view |
| `shared/指導者研修会/20250516/不適切行為を根絶！3.pdf.md` | 不適切行為を根絶！3.pdf | application/pdf | 349 | stub | https://drive.google.com/file/d/11Ly7ZZsOFLHNfNZ-SR1myi_iPeQ_1hEn/view |
| `shared/指導者研修会/20250516/不適切行為を根絶！4.pdf.md` | 不適切行為を根絶！4.pdf | application/pdf | 349 | stub | https://drive.google.com/file/d/1-2r9TfgzLNCw1K34vTPlP0uojBbL_co-/view |
| `shared/指導者研修会/20250516/事故発生状況報告書兼現認証明書.pdf.md` | 事故発生状況報告書兼現認証明書.pdf | application/pdf | 365 | stub | https://drive.google.com/file/d/1xUJjwR6lFl3I3r6XRy-lVH6DEiUQ465i/view |
| `shared/指導者研修会/20250516/令和7年度地域部活動（玉名モデル）実施状況1.pdf.md` | 令和7年度地域部活動（玉名モデル）実施状況1.pdf | application/pdf | 383 | stub | https://drive.google.com/file/d/1MBL4nmNtPKaNzT_l6Mm8VwBIcTL-DSHg/view |
| `shared/指導者研修会/20250516/令和7年度地域部活動（玉名モデル）実施状況2.pdf.md` | 令和7年度地域部活動（玉名モデル）実施状況2.pdf | application/pdf | 383 | stub | https://drive.google.com/file/d/1ysqksWHqY0nANgb8VlmgN0UgkxLtD4_8/view |
| `shared/指導者研修会/20250516/令和7年度玉名市「地域部活動」募集について.pdf.md` | 令和7年度玉名市「地域部活動」募集について.pdf | application/pdf | 382 | stub | https://drive.google.com/file/d/1aZ-wNfdBX0mMohgGgh-1wXaDabLhaTtf/view |
| `shared/指導者研修会/20250516/業務月報.pdf.md` | 業務月報.pdf | application/pdf | 332 | stub | https://drive.google.com/file/d/1GptYCmVyvSQobKftvN8QztY9hN0os_Eh/view |
| `shared/指導者研修会/20250516/業務月報に関するお願い.pdf.md` | 業務月報に関するお願い.pdf | application/pdf | 353 | stub | https://drive.google.com/file/d/1glFGD5OPhtImx4WIfwY2dlgc6jogbKSt/view |
| `shared/指導者研修会/20250516/流れ1.pdf.md` | 流れ1.pdf | application/pdf | 327 | stub | https://drive.google.com/file/d/1p3wlXwz_FEpdG-ZQwhfbjaQbN9Y6e60-/view |
| `shared/指導者研修会/20250516/流れ2.pdf.md` | 流れ2.pdf | application/pdf | 327 | stub | https://drive.google.com/file/d/182OsLJZjIi1goQhHYJJwcA5-vRH9YlRN/view |
| `shared/指導者研修会/20250516/玉名市地域部活動への参加申込.pdf.md` | 玉名市地域部活動への参加申込.pdf | application/pdf | 362 | stub | https://drive.google.com/file/d/1rFv7yhdpbFhvk_kDS12nKwMyIULky0Ua/view |
| `shared/指導者研修会/20250516/部活アプリ使い方1.pdf.md` | 部活アプリ使い方1.pdf | application/pdf | 346 | stub | https://drive.google.com/file/d/1eYfL-NnrSyJaybZHA4ESSGcAqY37qHPx/view |
| `shared/指導者研修会/20250516/部活アプリ使い方2.pdf.md` | 部活アプリ使い方2.pdf | application/pdf | 345 | stub | https://drive.google.com/file/d/1to_GjgGhxHja30ovCSceUn5PRUmvHkpI/view |
| `shared/指導者研修会/20251008/オンライン集金機能の使い方.pdf.md` | オンライン集金機能の使い方.pdf | application/pdf | 360 | stub | https://drive.google.com/file/d/1ncdY7ommOfbNl9R1KyO_bdETVfSKVJtx/view |
| `shared/指導者研修会/20251008/スライド1.pdf.md` | スライド1.pdf | application/pdf | 334 | stub | https://drive.google.com/file/d/1XeSex79F6y4wDhwcafpaVQ3JYqQIe5Je/view |
| `shared/指導者研修会/20251008/スライド2.pdf.md` | スライド2.pdf | application/pdf | 334 | stub | https://drive.google.com/file/d/1oIkGdgZBgLZG8fwDMf_BlCZPvQ18RPlN/view |
| `shared/指導者研修会/20251008/会議次第.pdf.md` | 会議次第.pdf | application/pdf | 333 | stub | https://drive.google.com/file/d/149OiJHxydU2tBXh5myvgUxwkurSAl5pL/view |
| `shared/指導者研修会/20251008/講演会の案内1.pdf.md` | 講演会の案内1.pdf | application/pdf | 340 | stub | https://drive.google.com/file/d/1oqPuWfbnmse4sNLJTIc_3srpn38ZaAAx/view |
| `shared/指導者研修会/20251008/講演会の案内2.pdf.md` | 講演会の案内2.pdf | application/pdf | 340 | stub | https://drive.google.com/file/d/1xK8rkVAhbsgPCB_rUurKw1uhtx6YMzTa/view |
| `shared/指導者研修会/20251008/運営会議案内.pdf.md` | 運営会議案内.pdf | application/pdf | 97895 | stub | https://drive.google.com/file/d/1RGwybNbQXJPRLmsy53tufqWZEuTH_SIP/view?usp=drivesdk |
| `shared/競技規則/厚さ20mm以下レース用シューズ.md` | 厚さ20mm以下レース用シューズ | application/vnd.google-apps.document | 1172 | saved | https://docs.google.com/document/d/1XE1scOfu6F8HR1z9yq8STcuutNaHa3qe9R1yDrrlHms/edit |
| `shared/競技規則/陸上競技ルールブック2025.pdf.md` | 陸上競技ルールブック2025.pdf | application/pdf | 355 | stub | https://drive.google.com/file/d/1UXixVRjyJCG8g25RdaAFLfl0gVtLDxEg/view |
| `shared/練習/玉名市練習会/2025-12-30.md` | 2025/12/30 | application/vnd.google-apps.document | 248 | saved | https://docs.google.com/document/d/1-rvillAOSAvL-GqawchbJZIfpIoCbL9b7ZZF6fdbUsU/edit |
| `shared/練習/練習の記録.csv` | 練習の記録 | application/vnd.google-apps.spreadsheet | 2687 | saved | https://docs.google.com/spreadsheets/d/1QZCWaJN-bV4GW26ZONWNXlguTCJ-dSWaGCfgRh3yJ0I/edit |
| `shared/練習/練習の記録.md` | 練習の記録 | application/vnd.google-apps.document | 8023 | saved | https://docs.google.com/document/d/1HpUIWr6zjIvdHU8wRgwIVRBn0yJ_yppNMpKRORasyCk/edit |
| `shared/練習/駅伝試走/2025.pdf.md` | 2025.pdf | application/pdf | 324 | stub | https://drive.google.com/file/d/1h45jCS2qdXU-_LdebUQkcnDDYpTUtALm/view |
| `shared/記録データベース/2025年度/3000m予想タイムランキング.csv` | 3000m予想タイムランキング | application/vnd.google-apps.spreadsheet | 100860 | saved | https://docs.google.com/spreadsheets/d/1f-JAd8J_v0UJ63T5L-LemUXeaa7i8sKCjfql8kulnc0/edit?usp=drivesdk&ouid=112681577980405057294 |
| `shared/記録データベース/2025年度/中学選手権.csv` | 中学選手権 | application/vnd.google-apps.spreadsheet | 152247 | saved | https://docs.google.com/spreadsheets/d/1TVfRDM96-KNy9cUVKUVrDx3C96uDsIw1Ay9JqOX0Cic/edit?usp=drivesdk&ouid=112681577980405057294 |
| `shared/記録データベース/2025年度/県中体連.csv` | 県中体連 | application/vnd.google-apps.spreadsheet | 130203 | saved | https://docs.google.com/spreadsheets/d/19RukTEYL5_ZpjdD3N_oOau8m-8qdo8gxaWW54ENYrv0/edit?usp=drivesdk&ouid=112681577980405057294 |
| `shared/記録データベース/2025年度/通信陸上.csv` | 通信陸上 | application/vnd.google-apps.spreadsheet | 171229 | saved | https://docs.google.com/spreadsheets/d/1OhKHdfRDDDUOEeKA2ERTkaLh-P3K2CECSH31DA3tQck/edit?usp=drivesdk&ouid=112681577980405057294 |
| `shared/記録データベース/2025年度/選手権と通信のタイム差.csv` | 選手権と通信のタイム差 | application/vnd.google-apps.spreadsheet | 35402 | saved | https://docs.google.com/spreadsheets/d/1dGJ37mg0B0TBmfF8_Vx_DZapg60O-9LRiZKLsnLj-qE/edit?usp=drivesdk&ouid=112681577980405057294 |
| `shared/記録データベース/2026年度/中学生記録.csv` | 中学生記録 | application/vnd.google-apps.spreadsheet | 170668 | saved | https://docs.google.com/spreadsheets/d/1JTy7bHPLOTD3rwteRhEQCxdlyKlVMxeccqrb8PYDXfc/edit |
| `shared/記録データベース/印刷用/中学選手権.md` | 中学選手権.pdf | application/pdf | 379 | saved | https://drive.google.com/file/d/1I7QT4i5wm9OvcfuYTn3OzimpXK2xC_VB/view?usp=drivesdk |
| `shared/記録データベース/印刷用/通信陸上.md` | 通信陸上.pdf | application/pdf | 376 | saved | https://drive.google.com/file/d/1sxpVLWCg5TRRWq0N_pSJBIlreecMfaUY/view?usp=drivesdk |
| `shared/記録データベース/印刷用/選手権と通信のタイム差.md` | 選手権と通信のタイム差 .pdf | application/pdf | 398 | saved | https://drive.google.com/file/d/1Sav31Rh_MQPm0dKD4ed-RYlc2OAH7s84/view?usp=drivesdk |
