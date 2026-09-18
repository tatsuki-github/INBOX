# Phase 0: 作業種別 — LINE userId 拒否リスト

| 項目 | 値 |
|:---|:---|
| 作業種別 | `extend`（Lite Path） |
| ゴール | Vercel ログで userId 確認可 + `LINE_DENIED_USER_IDS` のユーザーには無応答 |
| 検証 | `backend` test + build |
| Docs Sync | `docs/adr/018`、`backend/README.md` |
| スキップ | Phase 2 / 4（UI なし） |

## 判定

既存 Express LINE バックエンドへの非破壊拡張。拒否時は reply / LLM を呼ばない。
