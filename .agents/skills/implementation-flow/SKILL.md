---
name: implementation-flow
description: >
  エンドユーザーの機能要求を入力とし、調査・UX設計・アーキテクチャ設計・UI設計・
  フロントデザイン・TypeScript実装を一気通貫で実行する統合実装ワークフロー。
  各フェーズ完了時に improve-flow による品質改善と bug-finder による潜在バグ検出を
  実行した上で review スキルによるフェーズレビューを必ず実施し、
  品質を確認してから次フェーズに進む「品質強化駆動開発」方式を採用。
  bug-finder でバグが発見された場合は bug-triage-fix で修正してからレビューに進む。
  deep-research / ux-psychology / flow-architecture /
  software-architecture / decision-framework / ui-design / front-design /
  effective-typescript / test / improve-flow / bug-finder / bug-triage-fix / refactor /
  review の14スキルを最適な順序で連鎖させ、
  1つの機能要求から完成品を生成する。ドメイン層 TDD（Red→Green→Refactor）をデフォルトとし、
  test スキルを Phase 1〜6 に統合する。Phase 0 で作業種別（新規/拡張/破壊的改修/レガシー統合）を判定し、
  バグ修正・パフォーマンス改善のみは別スキルへリダイレクト、改修系は Lite Path で実行する。
  QE5-7 でリポジトリ永続ドキュメント（specs/ または docs/）を実装に合わせて差分更新する。
  完了時（Phase 6 Approved 後）に git diff / git log を参照したコミットメッセージ案をユーザー応答に返す（自動コミットはしない）。
  Use when user says「機能を実装して」「この機能を作って」「要件から実装まで一気にやって」
  「フルスタックで機能を開発して」「implementation-flow で作って」「エンドツーエンドで実装して」
  「要件だけ伝えるから完成させて」「この画面を一から作って」「実装フローを実行して」
  「機能開発ワークフローを実行して」。
  Do NOT use for: バグ修正のみ（→ bug-triage-fix）、パフォーマンス/UX改善のみ（→ improve-flow）、
  既存コードのレビューのみ（→ review）、単独のテスト追加のみ（→ test）、
  調査のみ（→ deep-research）、デザインのみ（→ ui-design / front-design）、
  アーキテクチャ設計のみ（→ software-architecture / flow-architecture）。
metadata:
  author: KC-Prop-Foundry
  version: 1.7.0
  category: workflow
  pattern: "sequential"
  secondary-pattern: "iterative"
  based-on: "prompt-craft 設計手法に基づくマルチスキル統合ワークフロー"
---

# Skill: Implementation Flow（機能要求 → 完成品の一気通貫実装ワークフロー）

> **要件を受け取り、調査し、設計し、テストファーストで実装し、レビューで品質を証明せよ — 「機能完成」がゴールだ**

## Instructions

### 品質ゲートサマリー

> **原則**: 各フェーズのチェックリスト通過後、**improve-flow による品質改善** と **bug-finder による潜在バグ検出** を実行し、
> その上で **review スキルによるフェーズレビュー**を必ず実施する。
> bug-finder でバグが発見された場合は **bug-triage-fix で修正**してからレビューに進む。
> レビューで Approved を得てから次のフェーズに進む。Rejected の場合は該当フェーズを修正し、再レビューを行う。

| ゲート | Phase 間 | 品質強化ステップ | 通過条件 | 不合格時 |
|:---|:---|:---|:---|:---|
| G-0 | 0 → QE0 → R0 → 1 | improve-flow + bug-finder | スコープが 1 ワークフローに収まる + **作業種別記録完了** + レビュー Approved（リダイレクト時は記録で G-0 完了） | 機能を分割 |
| G-1 | 1 → QE1 → R1 → 2 | improve-flow + bug-finder | ユーザーストーリー + 受け入れ条件（3 つ以上）+ テストマッピング定義済み + レビュー Approved | Phase 1 継続 |
| G-2 | 2 → QE2 → R2 → 3 | improve-flow + bug-finder | ユーザーフロー + デザイン原則 + 倒理チェック合格 + レビュー Approved | Phase 2 継続 |
| G-3 | 3 → QE3 → R3 → 4 | improve-flow + bug-finder | コンポーネント構成 + ADR 1 本以上 + テスト戦略 ADR + レビュー Approved | Phase 3 継続 |
| G-4 | 4 → QE4 → R4 → 5 | improve-flow + bug-finder | UI 仕様 + デザイントークン（CSS 変数）定義済み + レビュー Approved | Phase 4 継続 |
| G-5 | 5 → QE5 → R5 → 6 | improve-flow + bug-finder + refactor + test | 全コード実装 + **検証実行合格**（vitest + 対象パッケージ build + frontend lint）+ **QE5-7 Docs Sync 完了**（Docs Sync 有効時）+ Phase 5 チェックリスト通過 + コード構造改善済み + レビュー Approved | Phase 5 継続 |
| G-6 | 6 (Final) | improve-flow + bug-finder + refactor + test | 最終統合レビュー: Critical=0, Major=0, A-5/B-6/B-7 合格, **検証実行合格** | 差し戻し（最大 2 回） |

> **QE0〜QE5** は各フェーズ末の「品質強化ステップ（Quality Enhancement）」を示す。
> improve-flow で成果物の品質を向上させ、bug-finder で潜在バグを検出する。
> バグが発見された場合は bug-triage-fix で修正し、コード成果物がある Phase（Phase 5 以降）では refactor でコード構造を改善してからレビューに進む。
> **R0〜R5** は各フェーズ末の review スキルによるフェーズレビューを示す。

### ワークフロー全体像

```
エンドユーザーの機能要求（自然言語）
  │
  ▼
Phase 0: ワークフロー初期化 ──────── スコープ・技術スタック・**作業種別判定**
  │     bug-fix / perf-only → 別スキルへリダイレクト（workflow 終了）
  │     extend / modify-breaking / legacy-integration → Lite Path
  │     greenfield-new → Full Path
  │
  ▼
◆ QE0: 品質強化 ──────────────────── [improve-flow] ─ スコープ定義の改善
  │                                  [bug-finder]    ─ スコープ定義の潜在問題検出
  │                                  [bug-triage-fix] ─ バグ発見時のみ修正
  ▼
★ R0: フェーズレビュー ──────────── [review] ─ スコープ・スキップ判定の妥当性検証
  │     ├─ Approved ──→ Phase 1 へ
  │     └─ Rejected ──→ Phase 0 修正
  ▼
Phase 1: 要求分析 & 調査 ─────────── [deep-research]
  │
  ▼
◆ QE1: 品質強化 ──────────────────── [improve-flow] ─ 要件・調査結果の改善
  │                                  [bug-finder]    ─ 要件の矛盾・潜在リスク検出
  │                                  [bug-triage-fix] ─ バグ発見時のみ修正
  ▼
★ R1: フェーズレビュー ──────────── [review] ─ 要件完全性・受け入れ条件の検証
  │     ├─ Approved ──→ Phase 2 へ
  │     └─ Rejected ──→ Phase 1 修正
  ▼
Phase 2: UX 設計 ─────────────────── [ux-psychology]
  │
  ▼
◆ QE2: 品質強化 ──────────────────── [improve-flow] ─ UX 設計の洗練・改善
  │                                  [bug-finder]    ─ UX 設計の潜在問題検出
  │                                  [bug-triage-fix] ─ バグ発見時のみ修正
  ▼
★ R2: フェーズレビュー ──────────── [review] ─ UX 設計の整合性・倫理チェック
  │     ├─ Approved ──→ Phase 3 へ
  │     └─ Rejected ──→ Phase 2 修正
  ▼
Phase 3: アーキテクチャ設計 ────────── [flow-architecture + software-architecture + decision-framework]
  │
  ▼
◆ QE3: 品質強化 ──────────────────── [improve-flow] ─ アーキテクチャ設計の改善
  │                                  [bug-finder]    ─ 設計上の潜在バグ・欠陥検出
  │                                  [bug-triage-fix] ─ バグ発見時のみ修正
  ▼
★ R3: フェーズレビュー ──────────── [review] ─ アーキテクチャ整合性・ADR 検証
  │     ├─ Approved ──→ Phase 4 へ
  │     └─ Rejected ──→ Phase 3 修正
  ▼
Phase 4: UI / ビジュアル設計 ─────── [ui-design + front-design]
  │
  ▼
◆ QE4: 品質強化 ──────────────────── [improve-flow] ─ UI 設計の洗練・ブラッシュアップ
  │                                  [bug-finder]    ─ UI 仕様の潜在問題検出
  │                                  [bug-triage-fix] ─ バグ発見時のみ修正
  ▼
★ R4: フェーズレビュー ──────────── [review] ─ UI 仕様・デザイントークン検証
  │     ├─ Approved ──→ Phase 5 へ
  │     └─ Rejected ──→ Phase 4 修正
  ▼
Phase 5: TypeScript 実装 ─────────── [effective-typescript + test]
  │     ドメイン層: Red → Green → Refactor（TDD）
  │     UI 層: 実装後に振る舞いテスト
  ▼
◆ QE5: 品質強化 ──────────────────── [verify]        ─ test + build + lint（対象パッケージ）
  │                                  [test]         ─ 4 本柱レビュー・アンチパターン検出
  │                                  [improve-flow] ─ 実装コードの品質改善
  │                                  [bug-finder]    ─ 実装コードの潜在バグ検出
  │                                  [bug-triage-fix] ─ バグ・テスト品質問題の修正
  │                                  [refactor]      ─ 本番・テストコードの構造改善 + 退行検証再実行
  │                                  [docs-sync]     ─ QE5-7: specs/ or docs/ 差分更新 + ADR 永続化
  ▼
★ R5: フェーズレビュー ──────────── [review] ─ コード品質・設計準拠・永続ドキュメント整合検証
  │     ├─ Approved ──→ Phase 6 へ
  │     └─ Rejected ──→ Phase 5 修正
  ▼
Phase 6: 最終統合レビュー ─────────── [verify] + [test] + [improve-flow] + [bug-finder] + [bug-triage-fix] + [refactor] + [review]
  │     ├─ Approved ──→ Phase 6e へ           全 Phase 横断の品質強化 + 統合検証
  │     └─ Rejected ──→ 該当 Phase に差し戻し（Iterative）
  ▼
Phase 6e: コミットメッセージ案 ───── git status / git diff / git log 参照（自動コミットしない）
  ▼
完成（ユーザー応答にコミットメッセージ案を必ず含める）
```

### 入力

| 入力 | 説明 | 例 |
|:---|:---|:---|
| 機能要求 | エンドユーザーが求める機能の自然言語記述 | 「ダッシュボードに売上グラフを追加して」 |
| プロジェクト情報（任意） | 既存の技術スタック・コードベース情報 | 「Next.js + Tailwind CSS + Prisma」 |
| ブランドガイドライン（任意） | 既存のデザインシステム・カラー・フォント | ブランドカラー、Tailwind config |
| 制約条件（任意） | 期限、対応デバイス、パフォーマンス要件 | 「モバイルファースト、3秒以内に表示」 |

### 出力

| 出力 | Phase | 形式 |
|:---|:---|:---|
| 作業種別記録 | Phase 0 | Markdown（Full / Lite / Redirected） |
| 調査レポート | Phase 1 | Markdown |
| UX 設計書 | Phase 2 | Markdown |
| アーキテクチャ設計書 + ADR | Phase 3 | Markdown |
| UI デザイン仕様 + CSS アセット | Phase 4 | Markdown + CSS |
| 実装コード + テストコード | Phase 5 | TypeScript / TSX / CSS + Vitest |
| テスト戦略 | Phase 3 | ADR（テスト・ピラミッド・配置規約） |
| レビュー結果 | Phase 6 | Markdown |
| コミットメッセージ案 | Phase 6e | Markdown（コピー用コードブロック） |
| フェーズレビュー結果 | R0〜R5 | Markdown（各フェーズのレビュー判定） |
| 品質強化レポート | QE0〜QE5 | Markdown（improve-flow 改善内容 + bug-finder 検出結果 + refactor 変更レポート（QE5 のみ）） |
| Docs 同期レポート | QE5-7 | Markdown（更新ファイル一覧 + 使用した Docs Root） |
| 永続 ADR | QE5-7 | `<adr-dir>/NNN-*.md`（Phase 0 で検出した ADR ディレクトリ） |

各 Phase の出力テンプレートは [phase-output-templates.md](references/phase-output-templates.md) を参照。永続ドキュメント同期の詳細は [docs-sync-guide.md](references/docs-sync-guide.md) を参照。

> **ワークフロー原則**: 各 Phase のチェックリストが全て通過した後、**improve-flow による品質改善**と
> **bug-finder による潜在バグ検出**を実行する。バグが発見された場合は **bug-triage-fix で修正**した後、
> コード成果物がある Phase（Phase 5 以降）では **refactor によるコード構造改善**を実施してから
> **review スキルによるフェーズレビューを必ず実施**し、Approved を得てから次の Phase に進むこと。
> Rejected の場合は該当 Phase を修正し、再度品質強化ステップから再実行する。
> 品質ゲートが不合格の場合は該当 Phase を継続する。

---

## Phase 0: ワークフロー初期化

機能要求を受け取り、ワークフロー全体のスコープとゴールを定義する。

### 0a. 要求の受領と確認

| 確認項目 | デフォルト |
|:---|:---|
| **機能スコープ**: 1 機能に収まるか？分割が必要か？ | 1 機能として扱う |
| **技術スタック**: 既存プロジェクトの技術構成は？ | Next.js + TypeScript + Tailwind |
| **デザインシステム**: 既存のデザイントークン・ガイドラインはあるか？ | なし（新規設計） |
| **対象デバイス**: モバイル / デスクトップ / 両方？ | レスポンシブ（両方） |
| **優先特性**: パフォーマンス / UX / 開発速度 の優先順位は？ | UX > パフォーマンス > 開発速度 |
| **開発方式**: TDD（ドメイン層優先） | **デフォルト有効**（Phase 5 で Red→Green→Refactor） |
| **検証対象パッケージ** | `backend` / `frontend` / `both`（本リポジトリは `both` がデフォルト） |
| **Docs Sync** | `specs/` または `docs/` が存在する場合 **有効**（詳細は 0d） |

> **検証実行（verify）**: Phase 5 以降の品質ゲートで、変更のあったパッケージに対し `npm test`・`npm run build`・（frontend のみ）`npm run lint` をシェルで実行し、全て成功すること。詳細は [typescript-implementation-guide.md](references/typescript-implementation-guide.md) の「検証実行規約」を参照。

### 0d. Docs Root 検出（Docs Sync）

Phase 0a の直後に実施。`specs/` / `docs/` のどちらを永続ドキュメントの正本とするかを検出し、作業種別記録に残す。詳細は [docs-sync-guide.md](references/docs-sync-guide.md) を参照。

**検出手順（上から評価）**:

1. リポジトリルートに `specs/` と `docs/` の有無を確認
2. **マッピングファイル**（優先度順）: `specs/INVENTORY.md` → `docs/INVENTORY.md` → 各 README のインデックス節
3. **ADR ディレクトリ**（最初に見つかったもの）: `specs/backend/decisions/`、`docs/adr/`、`docs/decisions/`、`docs/architecture/decisions/`
4. ユーザー明示のドキュメント出力先があれば上書き

**両方存在する場合の更新先ルール**:

| 変更の性質 | 優先更新先 |
|:---|:---|
| API / コンポーネント / ページの振る舞い仕様 | `specs/`（存在すれば） |
| 運用手順、デプロイ、オンボーディング | `docs/` |
| ADR | Phase 0 で決めた **1 箇所を正本**、他はリンクのみ |

**無効化**: `specs/` も `docs/` もなく、新規ルート作成も Out of Scope のときのみ。

### 0c. 作業種別ルーター

Phase 0a の直後に実施。**上から順に 4 問を評価**し、最初に該当した種別で確定する。
詳細・Lite Path マトリクスは [work-type-routing.md](references/work-type-routing.md) を参照。

| # | 質問 | Yes → | 扱い |
|:--|:-----|:------|:-----|
| 1 | 再現可能な不具合か？（期待 vs 実際の乖離） | `bug-fix` | **中断** → [bug-triage-fix](../bug-triage-fix/SKILL.md) |
| 2 | 新機能なし、既存の速さ/UX/品質改善のみか？ | `perf-only` | **中断** → [improve-flow](../improve-flow/SKILL.md) |
| 3 | 既存コードベースへの変更か？ | No → `greenfield-new` | Full Path |
| 4a | 既存契約（API/型/DB）を破壊するか？ | Yes → `modify-breaking` | Lite Path |
| 4b | レガシー層へ段階的に差し込むか？ | Yes → `legacy-integration` | Lite Path |
| 4c | 上記以外の既存変更 | — | `extend`（Lite Path） |

**リダイレクト時**: 作業種別記録（[phase-output-templates.md](references/phase-output-templates.md) Phase 0 テンプレート）を残し、**implementation-flow は Phase 0 で終了**（G-0 完了）。

**エスカレーション**: bug-triage-fix / improve-flow 実行中に新規設計が必要と判明 → Phase 0c を再実行し Lite Path へ。

### 0b. フェーズスキップ判定

| 条件 | スキップ対象 |
|:---|:---|
| 要求が十分に明確で技術的にシンプル | Phase 1（調査）を簡略化 |
| バックエンドのみの機能（UI なし） | Phase 2（UX）、Phase 4（UI）をスキップ（**TDD はスキップしない**） |
| 既存アーキテクチャに追加する小機能 | Phase 3（アーキテクチャ）を簡略化 |
| 既存デザインシステムがある | Phase 4（UI/ビジュアル）を簡略化 |
| **Lite Path `extend`** | Phase 1/3 簡略化、Phase 2/4 は新規タッチ箇所のみ |
| **Lite Path `modify-breaking`**（API のみ） | Phase 2/4 スキップ可 |
| **Lite Path `legacy-integration`**（UI 非接触スライス） | Phase 2/4 スキップ可 |

> **原則**: スキップ判定は Phase 0 で行い、理由を記録する。迷ったらスキップしない。
> Lite Path の詳細は [work-type-routing.md](references/work-type-routing.md) を参照。

**チェックリスト**:
- [ ] 作業種別（6 種）を判定し、記録した
- [ ] `bug-fix` / `perf-only` の場合、**implementation-flow を中断**し適切スキルへ誘導した
- [ ] Lite Path の場合、スキップ対象 Phase と理由を記録した
- [ ] `package.json` / 既存ディレクトリを読み、技術スタックデフォルトを上書きした
- [ ] 機能要求を具体的なゴールとして言語化した
- [ ] フェーズスキップの判定を行い、理由を記録した
- [ ] 1 つの機能要求が 1 ワークフロー実行に対応することを確認した
- [ ] 検証対象パッケージ（`backend` / `frontend` / `both`）を記録した
- [ ] Docs Sync の有効/無効、Docs Root(s)、マッピング参照、ADR 永続化先を記録した（0d）

### QE0: 品質強化ステップ（improve-flow + bug-finder に委譲）

Phase 0 の成果物に対し、レビュー前に品質強化を実施する。

| ステップ | スキル | 実施内容 |
|:---|:---|:---|
| **QE0-1: 品質改善** | [improve-flow] | スコープ定義・ゴール記述の明確性を改善、スキップ判定の妥当性を再検証 |
| **QE0-2: 潜在バグ検出** | [bug-finder] | スコープ定義の矛盾・曖昧性・潜在リスクを検出 |
| **QE0-3: バグ修正** | [bug-triage-fix] | QE0-2 でバグが発見された場合のみ、原因特定と修正を実施 |

> **注意**: QE0 は設計ドキュメントレベルの品質強化。コード成果物がないため bug-finder はスコープ定義の論理的欠陥に焦点を当てる。

### R0: フェーズレビュー（review に委譲）

Phase 0 の成果物（QE0 による品質強化済み）を review スキルで検証する。

| レビュー観点 | 検証内容 |
|:---|:---|
| **スコープ妥当性** | 1 ワークフローに収まる規模か、分割が必要ではないか |
| **スキップ判定の合理性** | フェーズスキップの理由が合理的か、必要なフェーズを不当に省略していないか |
| **技術スタックの適切性** | 選定した技術スタックが要件に対して適切か |
| **ゴールの明確性** | 機能要求が具体的かつ検証可能なゴールとして言語化されているか |
| **作業種別の妥当性** | 判定 4 問の結果と要求内容が一致しているか |
| **リダイレクトの正当性** | bug-fix / perf-only で implementation-flow を続行していないか |
| **Lite Path の過不足** | 破壊的変更なのに extend を選んでいないか |
| **Docs Sync 設定** | Docs Root 検出と有効/無効の理由が妥当か |

**判定**: Approved → Phase 1 へ、Rejected → Phase 0 の指摘箇所を修正し再レビュー

---

## Phase 1: 要求分析 & 調査（deep-research に委譲）

> **深さレベル「概要〜標準」で、機能実装に必要十分な調査を行う**

### 1a. 要求の分解と明確化

| 分解軸 | 確認内容 | 出力 |
|:---|:---|:---|
| **ユーザーストーリー** | 誰が・何を・なぜ | 「〇〇として、△△したい、なぜなら□□」 |
| **受け入れ条件** | どうなったら完了か | 検証可能な条件リスト（3 つ以上） |
| **テストマッピング** | 受け入れ条件をどのテストで検証するか | 単体(TDD) / 統合(実装後) の対応表 |
| **スコープ境界** | 何を含み、何を含まないか | In / Out of Scope テーブル |
| **依存関係** | 他機能・外部サービスへの依存 | 依存一覧 |
| **影響ドキュメント一覧** | 変更コードに対応する永続 doc（Docs Sync 有効時） | `INVENTORY.md` または README 慣例から列挙 |

### 1b. 技術調査（deep-research 適用）

| 調査項目 | 目的 | 手法 |
|:---|:---|:---|
| 類似実装パターン | 業界のベストプラクティス把握 | Web 検索、OSS 調査 |
| 技術的制約 | 選定技術の制約・落とし穴の把握 | 公式ドキュメント、Issue 検索 |
| UX パターン | 類似機能の UX パターン収集 | 競合サイト・アプリの調査 |
| アクセシビリティ | WCAG 準拠ポイントの特定 | ガイドライン確認 |

**チェックリスト**:
- [ ] ユーザーストーリーが「誰が・何を・なぜ」の形式で記述されている
- [ ] 受け入れ条件が検証可能な形で 3 つ以上列挙されている
- [ ] 全受け入れ条件にテストマッピング（単体 TDD / 統合）が定義されている
- [ ] In / Out of Scope が明確に定義されている
- [ ] 技術的な実現アプローチが 1 つ以上特定されている
- [ ] UX パターンの参考情報が収集されている
- [ ] Docs Sync 有効時、影響ドキュメント一覧が定義されている（新規 doc 含む）

**→ Phase 2 への受け渡し**: 調査レポート（ユーザーストーリー、UX パターン調査結果、影響ドキュメント一覧）

### QE1: 品質強化ステップ（improve-flow + bug-finder に委譲）

Phase 1 の成果物に対し、レビュー前に品質強化を実施する。

| ステップ | スキル | 実施内容 |
|:---|:---|:---|
| **QE1-1: 品質改善** | [improve-flow] | ユーザーストーリーの明確性・受け入れ条件の検証可能性を改善、調査結果の網羅性を強化 |
| **QE1-2: 潜在バグ検出** | [bug-finder] | 要件の矛盾・欠落・技術的リスクを検出 |
| **QE1-3: バグ修正** | [bug-triage-fix] | QE1-2 でバグが発見された場合のみ、原因特定と修正を実施 |

> **注意**: QE1 は要件ドキュメントレベルの品質強化。bug-finder は要件の論理的欠陥・スコープの曖昧性に焦点を当てる。

### R1: フェーズレビュー（review に委譲）

Phase 1 の成果物（QE1 による品質強化済み）を review スキルで検証する。

| レビュー観点 | 検証内容 |
|:---|:---|
| **要件完全性** | ユーザーストーリーが「誰が・何を・なぜ」で明確に記述されているか |
| **受け入れ条件の検証可能性** | 受け入れ条件が具体的かつ検証可能な形式か |
| **スコープ境界** | In / Out of Scope が明確で、Phase 0 のゴールと整合しているか |
| **調査の十分性** | 技術アプローチと UX パターンが次フェーズで使える十分な質か |
| **テストマッピングの完全性** | 全受け入れ条件にテスト種別・対象層が対応付けられているか |

**判定**: Approved → Phase 2 へ、Rejected → Phase 1 の指摘箇所を修正し再レビュー

---

## Phase 2: UX 設計（ux-psychology に委譲）

> **Laws of UX 10 法則から機能に関連する 2-4 法則を選び、焦点評価で UX 設計を行う**

### 2a. 適用法則の選定（2-4 法則）

機能タイプに応じて関連する法則を選ぶ。全 10 法則を適用しようとしない。

| 機能タイプ | 推奨法則 |
|:---|:---|
| データ表示系（ダッシュボード、一覧） | Miller's Law, Von Restorff, Doherty |
| フォーム入力系（登録、編集） | Postel's Law, Miller's Law, Peak-End |
| 検索・フィルタ系 | Hick's Law, Jakob's Law, Doherty |
| 通知・フィードバック系 | Von Restorff, Doherty, Peak-End |
| ウィザード・ステップ系 | Tesler's Law, Miller's Law, Peak-End |

### 2b. ユーザーコンテキスト分析

Phase 1 のユーザーストーリーを入力とし、心理学に裏付けられた分析を行う。
詳細な法則適用マトリクスは [ux-architecture-integration.md](references/ux-architecture-integration.md) を参照。

| 分析項目 | 適用法則 | 出力 |
|:---|:---|:---|
| 既存メンタルモデルとの一致 | Jakob's Law | メンタルモデル準拠度チェック |
| タスクのインタラクション効率 | Fitts's Law | タッチターゲット・配置設計 |
| 情報量と認知負荷 | Miller's Law + Hick's Law | チャンキング戦略・選択肢最適化 |
| 入力の柔軟性と堅牢性 | Postel's Law | バリデーション設計 |

### 2c. ユーザーフロー & 感情設計

- ユーザーフロー: エントリーポイント → 操作列 → 完了状態（+ エラーリカバリパス）
- 感情設計: Peak-End Rule に基づくポジティブピーク配置 + ネガティブピーク軽減
  - 各ステップに感情スコア（-3 ～ +3）を付与し、ピーク配置を設計する
  - 詳細テンプレートは [ux-architecture-integration.md](references/ux-architecture-integration.md) を参照
- 応答性: Doherty Threshold 準拠（クリック < 100ms、データ取得 < 400ms、重処理 < 10s）

### 2d. 倫理チェック

- [ ] ダークパターンなし（確認ダイアログの悪用、退出困難な動線がない）
- [ ] 過度な行動操作なし（通知の過剰利用、損失回避の乱用がない）

**チェックリスト**:
- [ ] ユーザーフローが全ステップで定義されている
- [ ] 各ステップに心理学的根拠（Laws of UX）が紐付いている
- [ ] エラーリカバリパスが設計されている
- [ ] ピーク体験が意図的に設計されている
- [ ] 応答性の目標値が Doherty Threshold に基づき設定されている
- [ ] 倫理チェックに合格している

**→ Phase 3 への受け渡し**: UX 設計書（ユーザーフロー、デザイン原則、応答性要件）

### QE2: 品質強化ステップ（improve-flow + bug-finder に委譲）

Phase 2 の成果物に対し、レビュー前に品質強化を実施する。

| ステップ | スキル | 実施内容 |
|:---|:---|:---|
| **QE2-1: 品質改善** | [improve-flow] | UX フローの洗練、感情設計の最適化、倒理チェックの強化 |
| **QE2-2: 潜在バグ検出** | [bug-finder] | UX 設計の矛盾・ユーザーフローのデッドエンド・アクセシビリティ問題を検出 |
| **QE2-3: バグ修正** | [bug-triage-fix] | QE2-2 でバグが発見された場合のみ、原因特定と修正を実施 |

> **注意**: QE2 は UX 設計ドキュメントレベルの品質強化。bug-finder はユーザーフローの論理的欠陥・エッジケース未考慮に焦点を当てる。

### R2: フェーズレビュー（review に委譲）

Phase 2 の成果物（QE2 による品質強化済み）を review スキルで検証する。

| レビュー観点 | 検証内容 |
|:---|:---|
| **UX 設計の整合性** | ユーザーフローが Phase 1 のユーザーストーリー・受け入れ条件と整合しているか |
| **法則適用の妥当性** | 選定した Laws of UX（2-4 法則）が機能タイプに対して適切か、過不足ないか |
| **感情設計の合理性** | Peak-End Rule のピーク配置が自然で、ユーザー体験を向上させるか |
| **倫理チェック** | ダークパターンや過度な行動操作がないか |
| **応答性要件** | Doherty Threshold に基づく目標値が具体的で現実的か |

**判定**: Approved → Phase 3 へ、Rejected → Phase 2 の指摘箇所を修正し再レビュー

---

## Phase 3: アーキテクチャ設計（flow-architecture + software-architecture + decision-framework に委譲）

> **「全てはトレードオフ」— アーキテクチャ特性を 7 個以内に絞り、ADR で判断根拠を残す**

### 3a. アーキテクチャ特性の抽出（software-architecture）

Phase 1-2 の成果から必要なアーキテクチャ特性を導出する。詳細は [ux-architecture-integration.md](references/ux-architecture-integration.md) を参照。

| 評価項目 | 判定基準 | 該当時のアクション |
|:---|:---|:---|
| 既存アーキテクチャへの追加 | 既存プロジェクトにコード追加 | 既存スタイルに準拠して設計 |
| 新規コンポーネントの追加 | 新しい Bounded Context / モジュール | ドメイン分析 + BC 設計を実施 |
| アーキテクチャ変更が必要 | 既存構造では要件を満たせない | 全面的なアーキテクチャ評価を実施 |

### 3b. コンポーネント設計（3 層構造）

```
[機能名]/
├── UI Layer        — Page / Container / Presentational コンポーネント
├── Business Logic  — ドメインモデル / ユースケース / バリデーション
├── Data Access     — API クライアント / キャッシュ / DTO 変換
└── Shared          — 共有型 / ユーティリティ / 定数
```

### 3c. 意思決定記録（ADR）

主要な設計判断を ADR として記録する。ADR テンプレートは [phase-output-templates.md](references/phase-output-templates.md) を参照。最低 1 本、重要な判断ごとに作成。**テスト戦略 ADR を最低 1 本**含める（既存 ADR と併記可）。

**テスト戦略 ADR に含める項目**:
- [test](../test/SKILL.md) Step 1 による 4 分類（ドメイン / コントローラ / 取るに足らない / 過度に複雑）
- テスト・ピラミッド配分（単体 : 統合 : E2E の目安）
- テストファイル配置規約（例: `backend/tests/unit/`, `frontend/src/**/*.test.ts`）

**永続 ADR（Docs Sync 有効時）**:
- Phase 3 で会話内 ADR ドラフトを確定する
- 永続化先は Phase 0 で記録した ADR ディレクトリ（例: `specs/backend/decisions/NNN-<slug>.md` または `docs/adr/NNN-<slug>.md`）
- 採番は既存最大番号 + 1。**ファイル作成は QE5-7**（実装確定後）

**チェックリスト**:
- [ ] アーキテクチャ特性が 7 個以内で優先順位付きで抽出されている
- [ ] コンポーネント構成が UI / Business Logic / Data Access の 3 層で設計されている
- [ ] 主要な設計判断が ADR として記録されている（最低 1 本）
- [ ] テスト戦略 ADR が記録されている（4 分類・ピラミッド・配置規約）
- [ ] ファイル構成計画に `*.test.ts` / `*.spec.ts` が含まれている
- [ ] ADR に「なぜその判断をしたか」と「不採用理由」が具体的に記述されている
- [ ] ファイル構成計画が作成されている
- [ ] 既存プロジェクトとの整合性が確認されている

**→ Phase 4 への受け渡し**: アーキテクチャ設計書（コンポーネント構成、ファイル計画、ADR）

### QE3: 品質強化ステップ（improve-flow + bug-finder に委譲）

Phase 3 の成果物に対し、レビュー前に品質強化を実施する。

| ステップ | スキル | 実施内容 |
|:---|:---|:---|
| **QE3-1: 品質改善** | [improve-flow] | アーキテクチャ設計の整合性強化、ADR の論理性改善、コンポーネント分割の最適化 |
| **QE3-2: 潜在バグ検出** | [bug-finder] | 設計上の潜在バグ（循環依存・データフローの欠陥・セキュリティホール）を検出 |
| **QE3-3: バグ修正** | [bug-triage-fix] | QE3-2 でバグが発見された場合のみ、原因特定と修正を実施 |

> **注意**: QE3 からはコードレベルの設計成果物が含まれるため、bug-finder のスキャン対象にコンポーネント構成・データフロー設計も含める。

### R3: フェーズレビュー（review に委譲）

Phase 3 の成果物（QE3 による品質強化済み）を review スキルで検証する。

| レビュー観点 | 検証内容 |
|:---|:---|
| **アーキテクチャ特性の妥当性** | 抽出した特性が Phase 1-2 の要件・UX 設計と整合しているか |
| **コンポーネント構成** | 3 層構造（UI / Business Logic / Data Access）が適切に分離されているか |
| **ADR の品質** | 判断根拠と不採用理由が具体的に記述され、トレードオフが明確か |
| **既存プロジェクトとの整合性** | 既存のコーディング規約・ディレクトリ構造と矛盾しないか |
| **Phase 1-2 との章間整合性** | 要件・UX 設計とアーキテクチャ設計に矛盾がないか |
| **テスト戦略の妥当性** | テスト戦略 ADR が Phase 1 のテストマッピングと整合しているか |

**判定**: Approved → Phase 4 へ、Rejected → Phase 3 の指摘箇所を修正し再レビュー

---

## Phase 4: UI / ビジュアル設計（ui-design + front-design に委譲）

> **Refactoring UI の原則で視覚的階層を設計し、CSS 変数でデザイントークンを定義する**

### 4a. デザインシステムの確認

| 状況 | アクション |
|:---|:---|
| 既存デザインシステムがある | そのトークン・コンポーネントに準拠 |
| 既存がない or 新規プロジェクト | front-design で戦略策定 → ui-design で設計 |
| 部分的に既存がある | 足りない部分を補完 |

### 4b. 視覚的階層 & カラーシステム設計

- **視覚的階層**: Primary（ページタイトル、キー数値、主要 CTA）→ Secondary → Tertiary の 3 段階
- **カラー**: Primary + Neutrals（8-10 段階）+ Semantic（Success/Warning/Error/Info）
- **品質基準**: WCAG AA コントラスト比 4.5:1 以上、CSS 変数で全色定義、ハードコード禁止

### 4c. コンポーネント UI 設計

Phase 3 の構成に対し、各コンポーネントの UI を設計する。UX 法則との対応は [ux-architecture-integration.md](references/ux-architecture-integration.md) を参照。

#### 一覧（テーブル/リスト）の操作 UI 指針（運用で効く）

- 一括操作（削除など）は、**選択の有無で一覧レイアウトを押し下げない**（ガタつき＝ダサい、視線が暴れる）。
  - 推奨: スクロール領域内に **フローティング（absolute / sticky）** で表示し、下端に **一定の余白（padding）** を常時確保して最終行が隠れないようにする。
- 長時間処理（例: ベクトル化/取り込み）が走る UI では、ユーザーが不安にならないよう **「閉じても処理は継続する」** を明示する。
  - 表示場所: 主要 CTA（開始ボタン）付近 or 進捗/ステータス付近（文言は短く、繰り返し表示しない）。

**UI スニペットライブラリの活用**:
`snippets/html/ui/` に 80+ の検証済み UI コンポーネントスニペット（HTML）がある。Phase 4 のコンポーネント設計時に該当するスニペットを特定し、Phase 5 で積極的に活用する。スニペットは HTML をベースとしており、出力先のスタック（HTML/CSS、React、Vue 等）に合わせてマークアップを変換して実装する。

| 設計要素 | 対応スニペット例 |
|:---|:---|
| フォーム入力 | `Input.html`, `Select.html`, `Checkbox.html`, `RadioGroup.html`, `Form.html`, `DatePicker.html` |
| データ表示 | `DataTable.html`, `DataList.html`, `Card.html`, `Stat.html`, `Badge.html` |
| ナビゲーション | `Navbar.html`, `Sidebar.html`, `Breadcrumb.html`, `Tabs.html`, `Pagination.html` |
| フィードバック | `Toast.html`, `Alert.html`, `Dialog.html`, `Loading.html`, `Spinner.html`, `Skeleton.html` |
| レイアウト | `Modal.html`, `Drawer.html`, `Sheet.html`, `Accordion.html`, `Collapsible.html` |
| 状態表現 | `EmptyState.html`, `ProgressBar.html`, `Stepper.html`, `StatusDot.html` |

> **原則**: スニペットが存在するコンポーネントは、ゼロから書かずにスニペットをベースにカスタマイズする。スニペットには Refactoring UI + Laws of UX の設計原則が組み込まれており、品質基準を満たしている。

### 4d. レスポンシブ設計

Mobile First → Tablet（768px）→ Desktop（1024px+）。モバイルはタッチターゲット 44px 以上。

**ツールチップ**: ツールチップを `position: fixed` で表示する場合は、[ui-design](../ui-design/SKILL.md) の [component-patterns.md](../ui-design/references/component-patterns.md) §9（ツールチップ）を参照し、ビューポート内収め・長いラベル省略・スクロール時消去を設計に含める。

**チェックリスト**:
- [ ] 視覚的階層が 3 段階（Primary / Secondary / Tertiary）で定義されている
- [ ] カラーシステムが CSS 変数で定義されている（ハードコード色値なし）
- [ ] WCAG AA コントラスト比 4.5:1 以上を満たしている
- [ ] 全コンポーネントの UI が設計されている（バリアント・状態含む）
- [ ] 活用可能な UI スニペット（`snippets/html/ui/`）を特定済み
- [ ] レスポンシブ対応が設計されている（最低 2 ブレイクポイント）
- [ ] スペーシングが 4px ベースの制約スケールに従っている
- [ ] Phase 2 の UX デザイン原則と整合している

**→ Phase 5 への受け渡し**: UI 設計仕様（デザイントークン、コンポーネント設計、レイアウト）

### QE4: 品質強化ステップ（improve-flow + bug-finder に委譲）

Phase 4 の成果物に対し、レビュー前に品質強化を実施する。

| ステップ | スキル | 実施内容 |
|:---|:---|:---|
| **QE4-1: 品質改善** | [improve-flow] | UI デザインの視覚的階層・カラーシステム・レスポンシブ設計をブラッシュアップ |
| **QE4-2: 潜在バグ検出** | [bug-finder] | UI 仕様の矛盾・WCAG 準拠漏れ・デザイントークンの不整合を検出 |
| **QE4-3: バグ修正** | [bug-triage-fix] | QE4-2 でバグが発見された場合のみ、原因特定と修正を実施 |

> **注意**: QE4 では特に WCAG AA 準拠、コントラスト比、タッチターゲットサイズなどのアクセシビリティ問題を重点的に検出する。

### R4: フェーズレビュー（review に委譲）

Phase 4 の成果物（QE4 による品質強化済み）を review スキルで検証する。

| レビュー観点 | 検証内容 |
|:---|:---|
| **デザイントークンの完全性** | CSS 変数で全色・スペーシングが定義され、ハードコード値がないか |
| **WCAG AA 準拠** | コントラスト比 4.5:1 以上、タッチターゲット 44px 以上を満たしているか |
| **Phase 2 UX 設計との整合性** | UI 設計が UX デザイン原則（Laws of UX）と整合しているか |
| **Phase 3 コンポーネント構成との対応** | アーキテクチャ設計のコンポーネント構成と UI 設計が 1:1 で対応しているか |
| **レスポンシブ設計** | モバイル・デスクトップ両方で適切に表示されるか |
| **スニペット活用計画** | 活用可能な UI スニペットが適切に特定されているか |

**判定**: Approved → Phase 5 へ、Rejected → Phase 4 の指摘箇所を修正し再レビュー

---

## Phase 5: TypeScript 実装（effective-typescript + test に委譲）

> **ドメイン層は TDD（Red→Green→Refactor）、UI 層は実装後に振る舞いテスト。型安全とテストで品質を証明する**

### 5a. 型設計（最重要工程）

タグ付きユニオンで状態を表現し、不正な状態を型レベルで排除する。
詳細な型設計パターン・TDD サイクル・Vitest 規約は [typescript-implementation-guide.md](references/typescript-implementation-guide.md) を参照。

**核心ルール**:
- タグ付きユニオンで有効な状態のみ表現（`isLoading + error + data` の boolean フラグ禁止）
- `any` 使用禁止（`unknown` + 型ガードで代替）
- `enum` 禁止（文字列リテラルユニオンで代替）
- パブリック API には戻り値型を明示
- `switch` 文に `never` 型で網羅性チェック

### 5b. 型・定数の実装（TDD 対象外）

コンパイル時検証で十分なため、テストは書かない。

```
1. types/      → 全ドメイン型（タグ付きユニオン、ブランド型）
2. constants/  → マジックナンバー排除、設定値定義
```

各ステップで型エラーが 0 であることを確認してから次へ進む。

### 5c. ドメイン層 TDD サイクル（各モジュールごとに反復）

対象: `utils/` → `services/`（ドメイン重要度が高いものから）

| ステップ | スキル | 内容 |
|:---|:---|:---|
| **Red** | [test] | Step 1-4: 対象分析 → 失敗するテスト作成 → `vitest` で失敗確認 |
| **Green** | [effective-typescript] | テストを通す最小実装 |
| **Refactor** | [refactor] + [test] | 本番コード構造改善。テストは Green を維持 |

> **TDD 中断条件**: [test](../test/SKILL.md) Step 1 で「取るに足らない」と判定されたコードには Red を書かない。

### 5d. UI / コントローラ層の実装（実装ファースト）

TDD 対象外。依存関係に従い実装する。

```
3. hooks/      → カスタムフック（状態管理、副作用）
4. components/ → UI スニペット適用 → Presentational → Container
5. pages/      → ページコンポーネント（ルーティング）
6. styles/     → CSS → CSS Modules / Tailwind 統合
7. index.ts    → Public API の Re-export（バレルファイル）
```

**ステップ 4 の UI スニペット適用ルール**:
1. Phase 4c で特定したスニペットを `snippets/html/ui/` から読み込む
2. スニペットの属性・バリアント・セマンティック HTML をベースに、出力先の言語・フレームワークに合わせて実装する
3. プロジェクト固有のデザイントークン（カラー、スペーシング）のみカスタマイズする
4. スニペットにないコンポーネントのみゼロから実装する

### 5e. 振る舞いテスト追加（実装後）

UI / コントローラ層および Phase 1 テストマッピングの統合テストを追加する。

| ステップ | スキル | 内容 |
|:---|:---|:---|
| 分析 | [test] Step 1 | コントローラ層を統合テスト対象として分類 |
| 作成 | [test] Step 2-5 | 出力値/状態ベース優先。モックはシステム境界のみ |
| 検証 | `vitest` | 全テスト Green 確認 |

### 5f. CSS 実装

- Phase 4 のデザイントークンを CSS 変数（`:root`）で定義
- `clamp()` でフルード設計、メディアクエリでブレイクポイント対応
- `prefers-reduced-motion`、`prefers-color-scheme` でアクセシビリティ対応

**チェックリスト**:
- [ ] 型設計がタグ付きユニオンで有効な状態のみ表現している
- [ ] `any` が使用されていない
- [ ] `enum` が使用されていない（文字列リテラルユニオンで置換）
- [ ] パブリック API に戻り値型が明示されている
- [ ] `switch` 文に `never` 型の網羅性チェックがある
- [ ] 該当する UI スニペット（`snippets/html/ui/`）を適用済み
- [ ] CSS が Phase 4 のデザイントークンを変数として使用している
- [ ] レスポンシブ対応が実装されている
- [ ] アクセシビリティ対応（コントラスト、モーション、セマンティック HTML）がある
- [ ] ファイル構成が Phase 3 の計画に準拠している
- [ ] ドメイン層の公開関数に Red ファーストで作成されたテストがある
- [ ] 受け入れ条件マッピングの統合テストが実装されている
- [ ] 検証実行合格（対象パッケージの `npm test`・`npm run build`・frontend `npm run lint` が全て成功）
- [ ] `vitest` 全件パス（Red が残っていない）
- [ ] test スキル 4 本柱の自己レビュー完了

**→ Phase 6 への受け渡し**: 全実装コード + テストコード + Phase 1-4 の設計ドキュメント

### QE5: 品質強化ステップ（test + improve-flow + bug-finder + refactor に委譲）

Phase 5 の成果物に対し、レビュー前に品質強化を実施する。

| ステップ | スキル | 実施内容 |
|:---|:---|:---|
| **QE5-0: 検証実行** | verify | 対象パッケージで `npm test` →（frontend のみ）`npm run lint` → `npm run build` をシェル実行し、全て成功すること（Red が残っていないこと） |
| **QE5-1: 品質改善** | [improve-flow] | コード品質の改善（型設計・エラーハンドリング・命名規則・パフォーマンス） |
| **QE5-2: 潜在バグ検出** | [bug-finder] | Null 参照・型エラー・競合状態・セキュリティ欠陥・ロジックミスを検出 |
| **QE5-3: バグ修正** | [bug-triage-fix] | QE5-2 でバグが発見された場合、原因特定→修正→リグレッション確認を実施 |
| **QE5-4: コード構造改善** | [refactor] | バグ修正後の本番・テストコードに対し、コードスメル検出・技術的負債解消（振る舞いを変えずに構造を改善）。**完了時に QE5-0 と同じ検証実行を再実行**（退行検証） |
| **QE5-5: テスト品質レビュー** | [test] Step 6 | 4 本柱 + アンチパターン検出 |
| **QE5-6: テスト品質修正** | [bug-triage-fix] | QE5-5 で検出されたテスト品質問題の修正（偽陽性・過剰モック等）。修正後は検証実行を再実行 |
| **QE5-7: Docs Sync** | [docs-sync-guide](references/docs-sync-guide.md) | Phase 0 で Docs Sync 有効の場合、**QE5-4 退行検証後・R5 直前**に永続ドキュメント（`specs/` / `docs/`）を差分更新。ADR 永続化、INVENTORY / README 整合。無効時はスキップ |

> **重要**: QE5 は全 QE ステップの中で最も重要。実装コードに対して bug-finder の全 Step（Null 安全性・ロジックフロー・非同期処理・セキュリティ）を完全に実行する。
> 発見されたバグは全件 bug-triage-fix で修正し、Critical / High が 0 件になってから refactor を実施する。
> refactor では本番コードとテストコードの両方について、振る舞いを変えずに構造を改善し、**R5 の直前に検証実行（test + build + lint）を再実行**してからレビューに進む。
>
> **bug-finder との役割分担**: ドメイン層は TDD テストが退行防止の主役。bug-finder はセキュリティ・競合状態等の補完。UI 層は振る舞いテスト + bug-finder が主役。

### R5: フェーズレビュー（review に委譲）

Phase 5 の成果物（QE5 による品質強化済み）を review スキルで検証する。

| レビュー観点 | 検証内容 |
|:---|:---|
| **型設計の品質** | タグ付きユニオンで有効な状態のみ表現、`any`/`enum` 不使用、`never` 網羅性チェック |
| **設計準拠（Semantic Drift）** | 実装が Phase 3 のアーキテクチャ設計・Phase 4 の UI 仕様から逸脱していないか |
| **コード品質** | パブリック API の戻り値型明示、適切なエラーハンドリング、命名規則の一貫性 |
| **CSS / デザイントークン準拠** | Phase 4 のデザイントークンが CSS 変数で正しく使用されているか |
| **アクセシビリティ** | セマンティック HTML、コントラスト、`prefers-reduced-motion` 対応 |
| **Phase 1 受け入れ条件との照合** | 受け入れ条件が全て実装で満たされているか |
| **テスト品質** | 振る舞いベースか、受け入れ条件がテストで検証されているか |
| **ドメイン層カバレッジ** | 境界値・異常系がテストされているか |
| **検証実行** | 対象パッケージの test / build / lint をシェルで実行済みで、全て成功しているか（未実行・口頭合格は不可） |
| **Docs ↔ 実装整合** | Docs Sync 有効時、QE5-7 で変更コードに対応する doc が更新され、API/UX 記述が実装と一致しているか |

**判定**: Approved → Phase 6 へ、Rejected → Phase 5 の指摘箇所を修正し再レビュー

---

## Phase 6: 最終統合レビュー（test + improve-flow + bug-finder + bug-triage-fix + refactor + review に委譲）

> **「完璧であると論理的に証明できない限り承認しない」— Trust, but Verify**
> R0〜R5 の各フェーズレビューを経た成果物を、全 Phase 横断で品質強化と統合検証を行う。

全 Phase の成果物を統合的にレビューする。各フェーズレビュー（R0〜R5）で個別の品質は検証済みだが、ここでは **Phase 間の整合性** と **全体としての完成度** を検証する。テスト品質は B-6、ビルド・Lint は B-7 基準で検証する。詳細なレビュー基準は [review-criteria-detail.md](references/review-criteria-detail.md) を参照。

### 6a. 最終品質強化（test + improve-flow + bug-finder + bug-triage-fix + refactor）

最終統合レビューの前に、全 Phase の成果物を横断的に品質強化する。

| ステップ | スキル | 実施内容 |
|:---|:---|:---|
| **QE6-0: 検証実行** | verify | 対象パッケージで `npm test` →（frontend のみ）`npm run lint` → `npm run build` を最終実行 |
| **QE6-1: 全体品質改善** | [improve-flow] | 全 Phase 横断の整合性改善、設計⇔実装の乖離修正、コード全体の品質底上げ |
| **QE6-2: 最終バグスキャン** | [bug-finder] | 全実装コードの完全スキャン（Null 安全性・ロジック・非同期・セキュリティ・境界値） |
| **QE6-3: バグ修正** | [bug-triage-fix] | QE6-2 で発見された全バグの原因特定・修正・リグレッション確認 |
| **QE6-4: 最終リファクタリング** | [refactor] | バグ修正完了後のコード全体に対し、最終的なコードスメル解消・技術的負債クリーンアップを実施（振る舞いを変えずに構造を改善） |

> **通過条件**: bug-finder で Critical = 0、High = 0 になってから refactor を実施する。
> refactor でコードスメル（P1 優先度）が解消されてから統合レビューに進む。
> improve-flow で Phase 間の整合性問題が解消されていること。

### 6b. 設計ドキュメントレビュー（review Part A）

| 基準 | チェック内容 |
|:---|:---|
| **A-1 要件カバレッジ** | Phase 1 の受け入れ条件が全て実装で満たされているか |
| **A-2 章間整合性** | Phase 1-5 の全ドキュメント間に矛盾がないか |
| **A-3 数値・データの妥当性** | 応答性目標値、レイアウト数値に根拠があるか |
| **A-4 可読性** | 第三者が設計意図を理解できるか |
| **A-5 Docs ↔ Code 整合** | 永続ドキュメントが実装・受け入れ条件と一致しているか（詳細は review-criteria-detail.md） |

### 6c. コードレビュー（review Part B）

| 基準 | チェック内容 |
|:---|:---|
| **B-1 Semantic Drift** | 実装が Phase 1-4 の設計から逸脱していないか |
| **B-2 Accounting Integrity** | 数値計算の精度、通貨処理、丸め処理 |
| **B-3 Edge Case Attack** | Null/Undefined、境界値、型攻撃、並行アクセス |
| **B-4 Privacy Violation** | ログに PII なし、エラーメッセージに内部情報なし |
| **B-5 Performance** | N+1 問題なし、適切なメモ化、不要な再レンダリングなし |
| **B-6 Test Coverage** | ドメイン層テスト完備、正常系+異常系+エッジケース、振る舞いベース検証（詳細は review-criteria-detail.md） |
| **B-7 Build & Lint** | 対象パッケージの build 成功、frontend 変更時は lint 成功、検証コマンド未実行は不可（詳細は review-criteria-detail.md） |

### 6d. 差し戻しフロー（Iterative パターン）

| レビュー結果 | アクション |
|:---|:---|
| **Approved**（Critical=0, Major=0） | Phase 6e（コミットメッセージ案生成）へ進む |
| **Rejected — コード品質** | Phase 5 に差し戻し → 修正 → QE5 再実行 → R5 再レビュー → Phase 6 再実行 |
| **Rejected — 設計不整合** | Phase 3 or 4 に差し戻し → 修正 → 該当 QE + R レビュー → 後続 Phase 再実行 |
| **Rejected — ドキュメント不整合** | QE5-7 に差し戻し → doc 修正 → R5 再レビュー → Phase 6 再実行 |
| **Rejected — 要件不足** | Phase 1 に差し戻し → 要件補完 → QE1 + R1 再レビュー → 全 Phase 再実行 |

> **原則**: 最終統合レビューでの差し戻しは最大 2 回。3 回目が必要な場合、Phase 0 のスコープ定義に問題がある。
> 各フェーズレビュー（R0〜R5）で早期に問題を検出するため、最終統合レビューでの差し戻しは最小限になることを目指す。

**チェックリスト**:
- [ ] 最終品質強化（QE6）が完了し、bug-finder で Critical=0, High=0 を確認済み
- [ ] refactor で最終的なコードスメル解消・技術的負債クリーンアップを実施済み
- [ ] improve-flow で Phase 間の整合性問題が解消済み
- [ ] 設計ドキュメントレビュー A-1〜A-5 に全て合格（Docs Sync 無効時は A-5 を N/A）
- [ ] QE5-7 Docs Sync 完了（Docs Sync 有効時）
- [ ] 検証実行合格（対象パッケージの test / build / lint が全て成功）を確認済み
- [ ] vitest 全件パスを確認済み
- [ ] コードレビュー B-1〜B-7 に全て合格
- [ ] TypeScript 品質チェック合格（型設計、any 排除、enum 排除、never 網羅性）
- [ ] UI/UX 品質チェック合格（WCAG AA、レスポンシブ、視覚的階層、CSS 変数）
- [ ] Critical 指摘 = 0 件
- [ ] Major 指摘 = 0 件（全件修正済み）
- [ ] Phase 1 の受け入れ条件が全て満たされている
- [ ] 成果物に機密情報（PII）が含まれていない
- [ ] Phase 6e: git diff / git log を参照したコミットメッセージ案をユーザー応答に含めた

### Phase 6e: コミットメッセージ案生成

> Phase 6 で `Approved` を得た後、ユーザーへの最終応答にコピー可能なコミットメッセージ案を含める。
> **品質ゲートではない**（QE / R レビュー対象外）。`git commit` はユーザーが明示依頼するまで実行しない。

**適用条件**:
- Phase 6 `Approved` 後に実施
- Phase 0 で `bug-fix` / `perf-only` にリダイレクトした場合は **適用外**（workflow は Phase 0 で終了）
- `git diff` が空（変更なし）の場合はメッセージ案を出さず「変更なし」と明記

**手順（readonly git コマンド）**:
1. 並列実行: `git status`, `git diff`, `git log -10 --oneline`
2. Phase 0 の作業種別・Phase 1 のユーザーストーリー・実際の変更ファイルを突合
3. リポジトリの既存スタイルに合わせて 1 案を生成（必要なら代替案 1 つ）

**メッセージ作成ルール**:

| 項目 | ルール |
|:---|:---|
| 言語 | リポジトリの `git log` に合わせる（本リポジトリは日本語がデフォルト） |
| 長さ | 1〜2 文。subject のみで完結させる（body は変更が大きい場合のみ任意） |
| 焦点 | **なぜ**変更したか（ユーザー価値・不具合の影響）を優先。ファイル名列挙は避ける |
| 作業種別との対応 | `greenfield-new`/`extend` → 機能追加、`modify-breaking` → 破壊的変更の理由明示、`legacy-integration` → 移行スライスの範囲を簡潔に |
| プレフィックス | リポジトリが Conventional Commits を使っていない場合は付けない（`feat:` 等は log に合わせて判断） |
| 機密 | `.env` / credentials 系はコミット対象外であることを注記 |

**ユーザー応答フォーマット（必須）**:

最終応答の末尾に以下セクションを **必ず** 含める（`git diff` が空の場合を除く）:

```markdown
## コミットメッセージ案

```
（ここにコピー可能なメッセージ）
```

> コミットは行っていません。コミットする場合は上記メッセージをご利用ください。
```

出力テンプレートは [phase-output-templates.md](references/phase-output-templates.md) の Phase 6e を参照。

---

## Examples

### Example 1: ダッシュボードに売上グラフを追加（Recharts）

```
「ダッシュボードに月次売上の推移グラフを追加して。棒グラフと折れ線グラフを
 切り替えられるようにしたい。直近12ヶ月分を表示」

→ Phase 0: スコープ=グラフコンポーネント追加、技術=Next.js+Recharts
→ QE0: [improve-flow] スコープ明確化 + [bug-finder] 問題なし
→ R0: フェーズレビュー → Approved
→ Phase 1: 受け入れ条件定義、Recharts vs Chart.js の技術調査
→ QE1: [improve-flow] 調査結果補強 + [bug-finder] 要件の曖昧性 1 件検出 → 修正
→ R1: フェーズレビュー → Approved
→ Phase 2: グラフ切替の認知負荷分析（Hick's Law）、
           ホバー時のツールチップ設計（Doherty Threshold < 100ms）
→ QE2: [improve-flow] UX フロー洗練 + [bug-finder] 問題なし
→ R2: フェーズレビュー → Approved
→ Phase 3: SalesChart コンポーネント設計、API エンドポイント設計、
           ADR「Recharts を採用（バンドルサイズ vs 機能性のトレードオフ）」
→ QE3: [improve-flow] ADR 論理性強化 + [bug-finder] データフロー欠陥 1 件 → [bug-triage-fix] 修正
→ R3: フェーズレビュー → Approved
→ Phase 4: グラフカラー（Primary 系 5 段階）、切替 UI（セグメントコントロール）、
           レスポンシブ対応（モバイルは横スクロール）
→ QE4: [improve-flow] カラーコントラスト改善 + [bug-finder] 問題なし
→ R4: フェーズレビュー → Approved
→ Phase 5: 集計 utils を TDD（Red→Green→Refactor）、ChartType 型、useSalesData + コンポーネント実装後に振る舞いテスト
→ QE5: [verify] 合格 + [test] 4本柱レビュー + [bug-finder] 境界値未処理 1 件 → [bug-triage-fix] 修正
→ R5: フェーズレビュー → Approved
→ Phase 6: QE6 最終品質強化 → 最終統合レビュー → Approved
→ Phase 6e: コミットメッセージ案「ダッシュボードに月次売上の推移グラフを追加し、棒グラフと折れ線グラフを切り替えられるようにした」を返却
```

### Example 2: ユーザープロフィール編集画面（React Hook Form）

```
「ユーザーが自分のプロフィール（名前、メール、アバター）を編集できる画面を作って」

→ Phase 0: スコープ=プロフィール編集 CRUD、技術=React+TypeScript+REST API
→ QE0: [improve-flow] ゴール明確化 + [bug-finder] 問題なし
→ R0: フェーズレビュー → Approved
→ Phase 1: 要件分解（表示・編集・バリデーション・保存）、類似実装調査
→ QE1: [improve-flow] 受け入れ条件強化 + [bug-finder] 問題なし
→ R1: フェーズレビュー → Approved
→ Phase 2: Postel's Law 適用（柔軟なバリデーション）、Peak-End Rule（保存成功の演出）
→ QE2: [improve-flow] エラーリカバリパス追加 + [bug-finder] 問題なし
→ R2: フェーズレビュー → Approved
→ Phase 3: ProfileForm / AvatarUploader / ProfileService の 3 コンポーネント設計、
           ADR「楽観的更新を採用（UX > 整合性のトレードオフ）」
→ QE3: [improve-flow] コンポーネント分割最適化 + [bug-finder] 問題なし
→ R3: フェーズレビュー → Approved
→ Phase 4: フォームレイアウト（ラベル上配置）、アバタープレビュー、エラー表示設計、
           スニペット特定（Input / Avatar / Button / Form / Toast）
→ QE4: [improve-flow] WCAG AA コントラスト改善 + [bug-finder] タッチターゲット不足 1 件 → [bug-triage-fix] 修正
→ R4: フェーズレビュー → Approved
→ Phase 5: バリデーション utils を TDD、ProfileFormData 型、useProfileForm + UI 実装後に振る舞いテスト
→ QE5: [verify] 合格 + [improve-flow] エラーハンドリング強化 + [bug-finder] メールバリデーション不備 Major 1 件
           → [bug-triage-fix] 修正 → bug-finder 再スキャン Critical/High = 0
→ R5: フェーズレビュー → Approved
→ Phase 6: QE6 最終品質強化 → 最終統合レビュー → Approved
```

### Example 3: EC サイトの検索フィルタ機能（URL 駆動）

```
「商品一覧に価格帯・カテゴリ・在庫ありの3つのフィルタを追加して」

→ Phase 0: 既存商品一覧への追加、デザインシステムあり → Phase 4 簡略化
→ QE0 + R0: フェーズレビュー → Approved
→ Phase 1: フィルタ要件定義、URL クエリパラメータによる状態管理の調査
→ QE1 + R1: フェーズレビュー → Approved
→ Phase 2: Hick's Law（フィルタ段階的開示）、Jakob's Law（EC 標準フィルタ UI 準拠）
→ QE2 + R2: フェーズレビュー → Approved
→ Phase 3: FilterPanel + useProductFilters + API クエリ設計、
           ADR「URL パラメータで状態管理（ブックマーク・共有性のため）」
→ QE3: [bug-finder] URL エンコーディングの潜在問題 1 件 → [bug-triage-fix] 修正
→ R3: フェーズレビュー → Approved
→ Phase 4: 既存デザインシステム準拠、モバイルはボトムシートで表示
→ QE4 + R4: フェーズレビュー → Approved
→ Phase 5: URL パース utils を TDD、FilterState 型、useProductFilters 実装後に統合テスト
→ QE5: [verify] 合格 + [bug-finder] 問題なし + R5: フェーズレビュー → Approved
→ Phase 6: QE6 最終品質強化 → 最終統合レビュー → Approved
```

### Example 4: リアルタイム通知センター（ポーリング方式）

```
「ヘッダーに通知ベルを追加して、未読通知の一覧をドロップダウンで表示して」

→ Phase 0: 新規コンポーネント追加、WebSocket は Phase 3 で判断
→ QE0 + R0: フェーズレビュー → Approved
→ Phase 1: 通知の種類分析、既読管理、リアルタイム vs ポーリングの調査
→ QE1 + R1: フェーズレビュー → Approved
→ Phase 2: Von Restorff（未読バッジの視覚的強調）、Miller's Law（種別グルーピング）
→ QE2 + R2: フェーズレビュー → Approved
→ Phase 3: NotificationBell / NotificationList / NotificationItem 設計、
           ADR「ポーリング 30s 採用（WebSocket 運用コスト vs UX のトレードオフ）」
→ QE3: [bug-finder] ポーリング間隔の競合リスク 1 件 → [bug-triage-fix] 設計修正
→ R3: フェーズレビュー → Approved
→ Phase 4: ドロップダウン位置（右端基準）、未読/既読の視覚的区別、空の状態デザイン
→ QE4 + R4: フェーズレビュー → Approved
→ Phase 5: Notification 型、polling utils を TDD、useNotifications 実装後に振る舞いテスト
→ QE5: [verify] 合格 + [improve-flow] エラーハンドリング強化 + [bug-finder] 問題なし
→ R5: フェーズレビュー → Minor「空の状態コピー改善可能」→ Info 記録 → Approved
→ Phase 6: QE6 最終品質強化 → 最終統合レビュー → Approved
```

### Example 5: マルチステップウィザードフォーム（Zod バリデーション）

```
「3ステップの申込フォームを作って。個人情報→プラン選択→確認の流れで」

→ Phase 0: スコープ=3 ステップウィザード、技術=Next.js+Zod+React Hook Form
→ QE0 + R0: フェーズレビュー → Approved
→ Phase 1: 各ステップの入力項目定義、戻る・進む・保存の状態遷移調査
→ QE1 + R1: フェーズレビュー → Approved
→ Phase 2: Miller's Law（1 ステップ 5±2 項目）、Tesler's Law（複雑さの引き受け）、
           Peak-End Rule（確認画面での安心感設計）
→ QE2 + R2: フェーズレビュー → Approved
→ Phase 3: WizardContainer / StepForm / StepIndicator 設計、
           ADR「ステップ間状態を Context + useReducer で管理」
→ QE3: [bug-finder] ステップ間状態のデータ不整合リスク 1 件 → [bug-triage-fix] 設計修正
→ R3: フェーズレビュー → Approved
→ Phase 4: ステップインジケーター（完了/現在/未到達の 3 状態）、プログレスバー、
           スニペット特定（Stepper / Input / Select / Button / ProgressBar）
→ QE4 + R4: フェーズレビュー → Approved
→ Phase 5: バリデーション utils を TDD、WizardStep 型、useWizard + UI 実装後に振る舞いテスト
→ QE5: [verify] 合格 + [improve-flow] 型安全性強化 + [bug-finder] ブラウザバック時の状態復元漏れ Major 1 件
           → [bug-triage-fix] 修正 → bug-finder 再スキャン Critical/High = 0
→ R5: フェーズレビュー → Approved
→ Phase 6: QE6 最終品質強化 → 最終統合レビュー → Approved
```

### Example 6: バックエンド API のみ（UI スキップ）

```
「ユーザーの行動ログを集計する API エンドポイントを作って」

→ Phase 0: バックエンドのみ → Phase 2（UX）、Phase 4（UI）をスキップ
→ QE0 + R0: フェーズレビュー → スキップ判定の妥当性確認 → Approved
→ Phase 1: 集計対象の行動イベント定義、時間粒度（日/週/月）の調査
→ QE1 + R1: フェーズレビュー → Approved
→ Phase 3: ActivityLog / AggregationService / TimeSeriesRepository 設計、
           ADR「時間粒度ごとにプリアグリゲーションテーブルを用意（クエリ高速化のため）」
→ QE3: [bug-finder] データアクセス層の境界値問題 1 件 → [bug-triage-fix] 設計修正
→ R3: フェーズレビュー → Approved
→ Phase 5: ActivityEvent 型、AggregationService を TDD（集計ロジック Red→Green→Refactor）、API ルート実装後に統合テスト
→ QE5: [verify] 合格 + [improve-flow] エラーハンドリング強化 + [bug-finder] N+1 問題 Major 1 件
           → [bug-triage-fix] バッチクエリに変更 → bug-finder 再スキャン Critical/High = 0
→ R5: フェーズレビュー → Approved
→ Phase 6: QE6 最終品質強化 → 最終統合レビュー → Approved
```

### Example 7: 既存 API にフィールド追加（非破壊・extend）

```
「ユーザー API のレスポンスに lastLoginAt フィールドを追加して（後方互換）」

→ Phase 0c: extend（Lite Path）— 契約非破壊、既存 consumer 影響なし
→ Phase 1: 既存 API 調査 + 差分受け入れ条件 + 回帰テストマッピング
→ Phase 3 簡略化: DTO 拡張 ADR + テスト戦略 ADR
→ Phase 5: DTO 変換 utils を TDD、API route 更新、既存テスト Green 維持 + 契約テスト追加
→ QE5: [verify] 合格 → QE5-7: `specs/backend/api/users.md` に lastLoginAt 追記 + INVENTORY 確認
→ Phase 6: 既存振る舞い退行なし確認 → Approved
→ Phase 6e: コミットメッセージ案「ユーザー API のレスポンスに lastLoginAt フィールドを追加した」を返却
```

### Example 8: API レスポンス形式の破壊的変更（modify-breaking）

```
「/api/orders のレスポンスを { items, total } から { data, pagination } に変更したい」

→ Phase 0c: modify-breaking（Lite Path）— Phase 2/4 スキップ（API のみ）
→ Phase 1: 互換性計画（v1/v2 並行 3 ヶ月、影響 consumer 一覧）
→ Phase 3: 互換性 ADR（並行稼働採用）+ テスト戦略 ADR
→ Phase 5: 新 DTO utils を TDD、/api/v2/orders 追加、契約テスト（v1 退行 + v2 新形式）
→ QE5: [verify] 合格 → Phase 6: B-3 互換期間境界値 → Approved
```

### Example 9: レガシー集計ロジックの Strangler（legacy-integration）

```
「legacy/aggregateLogs.ts の集計を新 AggregationService に段階的に移行して」

→ Phase 0c: legacy-integration（Lite Path）— スライス 1: 日次集計のみ
→ Phase 1: レガシー境界診断 + Strangler スライス定義（全置換は Out of Scope）
→ Phase 3: Strangler/Adapter ADR + テスト戦略 ADR
→ Phase 5: adapter/ を TDD → 新 AggregationService TDD → 呼び出し 1 箇所を adapter 経由に切替
→ QE5: [verify] 合格 → Phase 6: スライス完了定義の充足 → Approved
```

---

## Decision Criteria

### implementation-flow を使うべき場面

| 条件 | 推奨 |
|:---|:---|
| 新規機能の要件定義 → 実装 → レビューまで一括で実行したい | **implementation-flow** |
| 複数の設計ドメイン（UX + アーキテクチャ + UI）を統合的に扱う | **implementation-flow** |
| 1 つの機能が 1-3 日で実装可能な規模 | **implementation-flow** |
| 設計判断の根拠（ADR）を残しながら開発したい | **implementation-flow** |

### 個別スキルを使うべき場面

| 条件 | 推奨 |
|:---|:---|
| 再現可能な不具合（バグ修正のみ） | → **bug-triage-fix** |
| 既存の質・速度・UX 改善（新機能なし） | → **improve-flow** |
| 既存コードのレビューのみ | → **review** |
| 技術調査や情報収集のみ | → **deep-research** |
| 既存 UI のリファクタリングのみ | → **ui-design** |
| アーキテクチャ評価のみ（コード変更なし） | → **software-architecture** |
| 大規模な複数機能の優先順位決め | → **story-map** で分解後に個別 implementation-flow |

### 作業種別ルーター（Phase 0c）

| 要求の性質 | 推奨 |
|:---|:---|
| 完全新規（グリーンfield） | implementation-flow **Full** (`greenfield-new`) |
| 既存機能への非破壊拡張 | implementation-flow **Lite extend** |
| API / 契約の破壊的変更 | implementation-flow **Lite modify-breaking** |
| レガシーへの段階的組み込み | implementation-flow **Lite legacy-integration** |
| バグ修正のみ | **bug-triage-fix**（Phase 0c でリダイレクト） |
| パフォーマンス / UX 改善のみ | **improve-flow**（Phase 0c でリダイレクト） |

### ワークフローの境界

| 判断ポイント | 基準 |
|:---|:---|
| 1 ワークフローの最大規模 | コンポーネント 10 個以内、ファイル 20 個以内 |
| 複数機能をまたぐ場合 | story-map で分解 → 機能ごとに implementation-flow を個別実行 |
| テストコードの実装 | Phase 5 に統合（ドメイン層 TDD + UI 層振る舞いテスト） |
| バックエンドのみの機能 | Phase 2（UX）・Phase 4（UI）をスキップ。TDD は Phase 5 で実施 |

---

## Troubleshooting

| 問題 | 原因 | 解決策 |
|:---|:---|:---|
| 機能要求が大きすぎて 1 ワークフローに収まらない | Phase 0 のスコープ定義不足 | 機能を独立した小機能に分割し、それぞれ別ワークフローで実行 |
| Phase 1 の調査が長すぎる | deep-research の深さレベル誤判定 | 機能実装の調査は「概要〜標準」レベルで十分。「徹底」は不要 |
| Phase 2 で全 10 法則を適用しようとする | スコープの拡大 | 機能に関連する 2-4 法則に絞る。焦点評価で実施 |
| Phase 3 でアーキテクチャを大幅変更しようとする | 既存アーキテクチャとの乖離 | 既存への段階的追加を原則。大規模変更は別ワークフロー |
| Phase 4 で既存デザインと統一感がない | デザイントークン非参照 | Phase 0 で既存 CSS 変数を必ず読み込み、Phase 4 で準拠 |
| Phase 5 の型設計が複雑すぎる（5 行超の型定義） | 過度な型レベルプログラミング | 実用的な型安全性を優先。Conditional Type の多段ネストは避ける |
| Phase 6 で差し戻しが 3 回以上 | 要件理解の根本的な齟齬 | Phase 0 に戻り、ユーザーとスコープ・受け入れ条件を再合意 |
| Phase 間の整合性が取れない | フェーズ間の受け渡し情報が不足 | 各 Phase の出力テンプレートに従い必要情報を漏れなく記録 |
| 既存コードベースとの統合で問題 | Phase 0 でのコードベース分析不足 | 実装前に既存のコーディング規約・ディレクトリ構造を読み込む |
| レビューが形骸化する | 全て Minor/Info で通過させる | 「完璧であると論理的に証明できない限り承認しない」原則を厳守 |
| フェーズレビュー（R0〜R5）で繰り返し Rejected になる | 該当フェーズの成果物品質が根本的に不足 | Phase の入力情報（前フェーズの成果物）を再確認し、不足があれば前フェーズに遡る |
| フェーズレビューに時間がかかりすぎる | レビュー観点が過多 or 成果物が大きすぎる | 各フェーズレビューは該当フェーズ固有の観点に絞る。全体整合性は Phase 6 で検証 |
| フェーズレビューで検出すべき問題が Phase 6 で初めて発覚 | フェーズレビューの観点が不十分 | 各 R（R0〜R5）のレビュー観点テーブルを見直し、検出漏れの観点を追加 |
| Phase 5 で implementation drift が発生 | Phase 3-4 の設計書を参照せず実装 | 実装開始前に Phase 3 の ADR と Phase 4 の UI 仕様を再読する |
| UI コンポーネントをゼロから実装して品質が低い | UI スニペットライブラリ未活用 | `snippets/html/ui/` の該当スニペットをベースにカスタマイズする |
| QE ステップで improve-flow がスコープを超えた改善をしようとする | improve-flow の対象が正しく絞られていない | QE ステップの improve-flow は「該当フェーズの成果物のみ」を対象とする。新機能追加はしない |
| bug-finder が大量の偽陽性を出す | スキャンスコープが広すぎる | bug-finder のスキャン対象を該当フェーズの新規・変更ファイルに絞る |
| bug-triage-fix が別のバグを生むリグレッション | 修正の影響範囲分析が不十分 | bug-triage-fix の Step 7（検証・テスト）を必ず実行し、修正後に verify（test + build + lint）+ bug-finder を再実行 |
| テストは通るがデプロイで失敗する | build / lint を検証していない | QE5-0 / QE5-4 完了時・QE6-0 で対象パッケージの build（frontend は lint → build）を実行 |
| refactor 後に型エラーだけ残る | refactor 後の退行検証未実施 | QE5-4 完了条件の検証実行再実行を必須化 |
| TDD で UI コンポーネントまで Red ファーストにしようとする | スコープの誤解 | ドメイン層（utils/services）のみ TDD。hooks/components は実装後テスト |
| テストが実装詳細に結合して頻繁に壊れる | 振る舞いではなく HOW を検証 | test スキル Step 6 でリファクタリング耐性を再評価し、観察可能な振る舞いのみ検証 |
| bug-finder と TDD テストの役割が重複 | 品質担保の二重化 | ドメイン層は TDD が退行防止の主役。bug-finder はセキュリティ・競合状態の補完に特化 |
| バグ修正なのに全 Phase を実行 | Phase 0c 未実施 | bug-fix と判定し bug-triage-fix へリダイレクト |
| 破壊的変更で extend を選択 | 作業種別の誤判定 | R0 で差し戻し、互換性計画を要求 |
| レガシー全置換を 1 ワークフローに | スコープ過大 | スライス分割し legacy-integration を複数回実行 |
| 変更がないのに完了した | 実装が既にコミット済み | `git diff` が空の場合は「変更なし」と明記し、メッセージ案は出さない |
| `specs/` も `docs/` もない | Docs Root 未整備 | Phase 0 で Docs Sync 無効化、または greenfield でルート作成を In Scope に含める |
| マッピングファイルがない | INVENTORY 未作成 | README 構造 + コード慣例で推定。初回は [repo-spec](../repo-spec/SKILL.md) 検討 |
| 両方に似た仕様が存在 | 正本が不明 | Phase 0 で正本を決め、QE5-7 は正本のみ更新し他方はリンク |
| INVENTORY に未登録の新規ファイル | マッピング漏れ | QE5-7 で doc 新規作成 + インデックス更新 |

---

## References

### スキル参照（Phase 別の委譲先）

| スキル | Phase | 委譲内容 |
|:---|:---|:---|
| [deep-research](../deep-research/SKILL.md) | Phase 1 | 技術調査・類似実装リサーチ（深さ: 概要〜標準） |
| [ux-psychology](../ux-psychology/SKILL.md) | Phase 2 | Laws of UX 10 法則に基づく UX 設計 |
| [flow-architecture](../flow-architecture/SKILL.md) | Phase 3 | Wardley Mapping + DDD ドメイン分析 |
| [software-architecture](../software-architecture/SKILL.md) | Phase 3 | アーキテクチャスタイル選定・コンポーネント設計 |
| [decision-framework](../decision-framework/SKILL.md) | Phase 3 | トレードオフ分析・ADR による意思決定記録 |
| [ui-design](../ui-design/SKILL.md) | Phase 4 | Refactoring UI に基づく UI 設計・改善 |
| [front-design](../front-design/SKILL.md) | Phase 4 | ビジュアル戦略・カラー・タイポ・CSS アセット生成 |
| [effective-typescript](../effective-typescript/SKILL.md) | Phase 5 | Effective TypeScript 83 項目に基づく実装 |
| [test](../test/SKILL.md) | Phase 1, 3, 5, QE5, Phase 6 | テストマッピング・TDD（Red→Green→Refactor）・振る舞いテスト・4 本柱レビュー |
| [improve-flow](../improve-flow/SKILL.md) | QE0〜QE6 | 各フェーズ成果物の品質改善（レビュー前の品質強化） |
| [bug-finder](../bug-finder/SKILL.md) | QE0〜QE6 | 各フェーズ成果物の潜在バグ検出（レビュー前の品質強化） |
| [bug-triage-fix](../bug-triage-fix/SKILL.md) | QE0〜QE6 | bug-finder で発見されたバグの原因特定・修正 |
| [refactor](../refactor/SKILL.md) | QE5, QE6 | コード実装後のコードスメル検出・Fowler パターン適用・技術的負債解消（振る舞いを変えずに構造を改善） |
| [review](../review/SKILL.md) | R0〜R5, Phase 6 | 各フェーズレビュー（R0〜R5）+ 最終統合レビュー（Phase 6） |

### 詳細リファレンス

| ファイル | 内容 |
|:---|:---|
| [work-type-routing.md](references/work-type-routing.md) | Phase 0c 作業種別判定・Lite Path マトリクス |
| [phase-output-templates.md](references/phase-output-templates.md) | Phase 0-6e の成果物テンプレート（ADR テンプレート含む） |
| [typescript-implementation-guide.md](references/typescript-implementation-guide.md) | 型設計パターン・コーディング規約・実装順序の詳細ガイド |
| [review-criteria-detail.md](references/review-criteria-detail.md) | Phase 6 レビューの詳細基準（TypeScript 品質・UI/UX 品質・承認条件） |
| [ux-architecture-integration.md](references/ux-architecture-integration.md) | UX 法則 → UI コンポーネント対応表、アーキテクチャ特性導出マトリクス |
| [docs-sync-guide.md](references/docs-sync-guide.md) | Docs Root 検出、QE5-7 差分同期、ADR 永続化、マッピング規則 |

---

## Related Skills

| スキル | 関係 | 連携シナリオ |
|:---|:---|:---|
| **improve-flow** | リダイレクト / エスカレーション / QE0〜QE6 | Phase 0c で perf-only → improve-flow へリダイレクト。各フェーズ QE で品質改善。新規設計必要時 → Lite extend へエスカレーション |
| **bug-triage-fix** | リダイレクト / エスカレーション / QE0〜QE6 | Phase 0c で bug-fix → リダイレクト。QE で bug-finder 検出時に修正。設計変更必要時 → Lite extend / modify-breaking へエスカレーション |
| **bug-finder** | 統合（QE0〜QE6） | 各フェーズ完了後・レビュー前に発動し、成果物の潜在バグを検出する。特に QE5（実装後）では全 Step を完全実行する |
| **refactor** | 統合（QE5, QE6） | bug-triage-fix でバグ修正完了後に発動し、コードスメル検出（Long Method・Duplicate Code・Large Class 等）・Fowler パターン適用・技術的負債解消を行う。振る舞いを変えずに内部構造を改善してからレビューに進む |
| **test** | 統合（Phase 1, 3, 5, QE5, Phase 6） | Phase 1 でテストマッピング、Phase 3 でテスト戦略 ADR、Phase 5 でドメイン層 TDD + UI 層振る舞いテスト、QE5/Phase 6 で 4 本柱レビューと B-6/B-7 検証 |
| **diagram** | 補助（Phase 2-3） | Phase 2 のユーザーフロー図や Phase 3 のコンポーネント構成図を draw.io 形式で可視化したい場合に diagram スキルを並行発動する |
| **distill** | 前段（Phase 0） | 既存の仕様書や RFP がある場合、先に distill で知識蒸留し `02_notes/` に構造化してから implementation-flow の Phase 1 入力とする |
| **story-map** | 前段（Phase 0） | 大規模な機能群がある場合、story-map で全体のユーザーストーリーマップを生成し、MVP スコープを確定してから個別機能を implementation-flow で実装する |
| **repo-spec** | 補助 / エスカレーション | 通常の機能実装は QE5-7 で差分同期。仕様書が広範に陳腐化した場合のみ repo-spec で逆生成後、以降は QE5-7 |
| **prompt-craft** | 設計基盤 | 本スキル自体が prompt-craft の Sequential + CoT + Role-play パターンで設計された統合ワークフロー |
