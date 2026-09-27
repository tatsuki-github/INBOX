# Phase 1: 岱明 set_sec（簡略）

## ユーザーストーリー

コーチとして、岱明の松野・田上・山﨑の予想を実力線の絶対秒に固定したい。データ層のブレンドより人間判断を優先するため。

## 受け入れ条件

1. 松野凛空の予想が **9:20（560s）**
2. 田上颯人（岱明4区）の予想が **9:40（580s）**
3. 山﨑莉奈（岱明2区）の予想が **6:50（410s）**
4. Drive / コーパスの `人間考慮_*.yaml` が dual-write で一致
5. 上記を単体テストで検証

## テストマッピング

| AC | テスト |
|:---|:---|
| 1–3 | `test_taimei_set_sec_matsuno_tagami_yamasaki` |
| 4 | YAML dual-write + `load_human_notes` |
| 5 | 同上 |

## In / Out

- In: 人間考慮 `set_sec`、ensure seed、再生成 MD/CSV、ADR 追記
- Out: オーダー変更、他校の調整
