# Docs Sync ガイド（QE5-7）

implementation-flow の **QE5-7: Docs Sync** で、リポジトリ内の永続ドキュメント（`specs/` / `docs/`）を実装に合わせて差分更新するためのリファレンス。

> **フル再生成は [repo-spec](../../repo-spec/SKILL.md) に委譲**。本ガイドは変更スコープに限定した同期のみを扱う。

---

## Docs Root 検出（Phase 0）

Phase 0 で検出し、作業種別記録に残す。QE5-7 はこの記録に従う。

### 検出手順（上から評価）

1. リポジトリルートに `specs/` と `docs/` の有無を確認
2. **マッピングファイル**（優先度順）:
   - `specs/INVENTORY.md`
   - `docs/INVENTORY.md`
   - `specs/README.md` / `docs/README.md` のインデックス節
3. **ADR ディレクトリ**（最初に見つかったもの）:
   - `specs/backend/decisions/`
   - `docs/adr/`
   - `docs/decisions/`
   - `docs/architecture/decisions/`
4. ユーザー明示のドキュメント出力先があれば上書き

### 検出結果の記録

| 項目 | 例 |
|:---|:---|
| **Docs Sync** | 有効 / 無効（理由） |
| **Docs Root(s)** | `specs` / `docs` / `specs+docs` |
| **マッピング参照** | `specs/INVENTORY.md` または「README インデックス + 慣例」 |
| **ADR 永続化先** | `specs/backend/decisions/` |

### 無効化条件

- `specs/` も `docs/` もなく、新規ルート作成も Out of Scope
- ユーザーが明示的にドキュメント更新を除外

### `specs/` と `docs/` 併存時の更新先

| 変更の性質 | 優先更新先 |
|:---|:---|
| API / コンポーネント / ページの振る舞い仕様 | `specs/`（存在すれば） |
| 運用手順、デプロイ、オンボーディング | `docs/` |
| アーキテクチャ横断・認証フロー | 既存 doc の置き場所に合わせる |
| ADR | Phase 0 で決めた **1 箇所を正本**、他はリンクのみ |

---

## マッピング規則

### INVENTORY あり（推奨）

`INVENTORY.md` の表から変更コードパス → doc ファイルを解決する。

| 表の種別 | コード側の例 | doc 側の例 |
|:---|:---|:---|
| Backend routes | `backend/src/routes/users.ts` | `specs/backend/api/users.md` |
| Frontend pages | `frontend/src/pages/SigninPage/` | `specs/frontend/pages/SigninPage.md` |
| Frontend components | `frontend/src/components/Header/` | `specs/frontend/components/Header.md` |
| Utils | `frontend/src/utils/api.ts` | `specs/frontend/utils/api.md` |

### INVENTORY なし（フォールバック）

1. 変更ファイルのディレクトリ構造から doc パスを推定
2. 既存 doc の「実装」節に記載されたソースパスを逆引き
3. 見つからない場合は README のディレクトリ慣例に従い新規作成

**慣例の例（プロジェクトにより異なる）**:

| コード | doc（`specs/` レイアウト） |
|:---|:---|
| `backend/src/routes/<name>.ts` | `specs/backend/api/<kebab-name>.md` |
| `frontend/src/pages/<Name>Page/` | `specs/frontend/pages/<Name>Page.md` |
| `frontend/src/components/<Name>/` | `specs/frontend/components/<Name>.md` |

**`docs/` レイアウト**は README の章構成に従う（例: `docs/api/`, `docs/guides/`）。

---

## QE5-7 実施手順

**タイミング**: QE5-6 完了後、**R5 の直前**（コード・リファクタ・退行検証が確定した後）。

1. **対象特定**: `git diff` の変更ファイル × マッピング（Phase 1 の影響 doc 一覧と突合）
2. **差分更新**: 各 doc を既存トーン・見出し構成で更新
3. **横断 doc**: 認証/API 共通変更時は architecture / authentication / utils 相当も更新
4. **ADR 永続化**: Phase 3 の ADR → `<adr-dir>/NNN-<slug>.md`（採番は既存最大 + 1）
5. **インデックス更新**: `INVENTORY.md` または README の目次・クイックリンク
6. **削除・非推奨**: コード削除時は「削除済み / 履歴」注記を残す

### 更新しないもの（Out of Scope）

- 変更のない doc の全文書き換え
- repo-spec 相当の全ファイル再生成
- `.env` 実値の記載
- `docs/` と `specs/` への同一内容の二重メンテ（リンクで接続）

---

## レイヤ別更新チェックリスト

| レイヤ | 更新する内容 |
|:---|:---|
| **API** | パス、メソッド、リクエスト/レスポンス、認証、エラーコード |
| **認証** | フロー、Cookie/ヘッダ、外部サービス連携、環境変数（名前のみ） |
| **ページ** | ルーティング、動作、リダイレクト、関連コンポーネント |
| **コンポーネント** | Props、主要機能、依存 Context |
| **状態管理** | Context の責務、初期化、401 時の挙動 |
| **アーキテクチャ** | データフロー、システム境界、技術スタック変更 |

---

## 横断更新トリガー

| 変更シグナル | 追加で確認する doc |
|:---|:---|
| 認証・セッション | `*/authentication/*`, `*/central-auth*`, `*/auth-context*` |
| 新規/削除 API ルート | `INVENTORY.md` の routes 表、該当 `api/*.md` |
| 環境変数追加 | `*/deployment/environment-setup*`, `.env.example` との整合（値は書かない） |
| 破壊的 API 変更 | 互換性 ADR、旧契約の履歴注記 |
| 新規ページ/コンポーネント | 対応 doc 新規作成 + INVENTORY / README |

---

## ADR 永続化

### 採番・ファイル名

- 形式: `NNN-<kebab-slug>.md`（例: `002-central-auth-session.md`）
- `NNN`: 既存 ADR の最大番号 + 1（3 桁ゼロ埋め推奨）

### セクション構成（既存 ADR に準拠）

```markdown
# ADR-NNN: [タイトル]

## ステータス
Accepted（YYYY-MM-DD）

## コンテキスト
[背景]

## 決定
[採用した判断]

## 理由
[なぜその判断か]

## 影響
[実装・運用への影響]

## 不採用案（任意）
[検討したが採用しなかった案]
```

Phase 3 で会話内ドラフトを確定し、**QE5-7 でファイル作成**（実装確定後）。

---

## 新規 doc 雛形

### `specs/` — ページ（例: SigninPage）

```markdown
# [PageName]

[1 行概要]

## 概要
[役割・ユーザー向け説明]

## ルーティング
- パス: `/path`
- 認証: 要 / 不要

## 動作
1. [ステップ]

## 実装
- `frontend/src/pages/[PageName]/[PageName].tsx`
- [関連 utils]

## 関連
- [リンク]
```

### `specs/` — コンポーネント（例: Header）

```markdown
# [ComponentName]

[1 行概要]

## Props
[TypeScript interface]

## 機能
### [機能名]
[説明]

## 実装
- `frontend/src/components/[Name]/[Name].tsx`

## 関連
- [リンク]
```

### `docs/` — ガイド（一般的）

```markdown
# [タイトル]

## 概要
[目的]

## 前提条件
[必要な設定・権限]

## 手順
1. [ステップ]

## 関連
- [リンク]
```

新規作成時は**同ディレクトリの既存 doc**を読み、見出し構成を合わせる。

---

## Docs Sync レポートテンプレート

```markdown
# Docs Sync レポート: [機能名]

## 設定（Phase 0 から）
- Docs Sync: 有効
- Docs Root(s): [specs / docs / specs+docs]
- マッピング: [INVENTORY パス or 慣例]
- ADR 永続化先: [パス]

## 更新ファイル
| ファイル | 操作 | 概要 |
|:---------|:-----|:-----|
| [path] | 更新 / 新規 / 履歴化 | [1 行] |

## ADR
- [NNN-slug.md]: [タイトル]

## インデックス
- [INVENTORY.md / README.md]: [変更内容]

## 未更新（理由）
- [path]: 変更なし / Out of Scope

## 整合確認
- [ ] 変更コードと doc が 1:1 対応
- [ ] 受け入れ条件が doc に反映
- [ ] 幽霊仕様なし（削除コードの doc は履歴化）
```

---

## repo-spec との使い分け

| 状況 | 推奨 |
|:---|:---|
| 機能実装に伴う差分更新 | **QE5-7（本ガイド）** |
| 仕様書が広範に陳腐化、INVENTORY も未整備 | **repo-spec** で逆生成後、以降は QE5-7 |
| 新規プロジェクトで doc ルート未作成 | Phase 0 で In Scope に含め、初回のみ repo-spec または手動雛形 |
