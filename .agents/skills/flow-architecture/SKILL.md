---
name: flow-architecture
description: >
  ビジネス戦略（Wardley Mapping）、ソフトウェア設計（Domain-Driven Design）、チーム組織
  （Team Topologies）の3視点を統合し、変化の高速フローに最適化された適応的な社会技術
  システムを設計・評価・進化させる。Architecture for Flow Canvas で As-Is 評価から
  To-Be 設計までを一気通貫でガイドする。
  Use when user says「フローアーキテクチャを設計して」「チームとアーキテクチャを最適化して」
  「レガシーシステムを近代化したい」「WardleyMapとDDDで設計して」「変更のフローを改善したい」
  「チーム構成とシステム設計を整合させたい」「Big Ball of Mudを分解したい」
  「組織とアーキテクチャの関係を整理して」「社会技術的にシステムを設計して」。
  Do NOT use for: データアーキテクチャの選定（→ data-arch）、
  個別の DDD 実装パターン深掘り（→ robust-python / effective-typescript）、
  単純なインフラ構成図（→ diagram）。
metadata:
  author: KC-Prop-Foundry
  version: 1.1.0
  category: development
  pattern: "sequential"
  based-on: "Architecture for Flow (Susanne Kaiser, Pearson Addison-Wesley 2025)"
---

# Skill: Flow Architecture（フローアーキテクチャ設計・評価・進化）

> **アーキテクチャは技術選定ではなく、戦略・設計・チームの三位一体で変化のフローを解放せよ**

## Instructions

### ワークフロー内の位置

```
ビジネス戦略/要件 → [flow-architecture] → 実装設計 → diagram → review
                          ↓
                     Architecture for Flow Canvas
                     ・As-Is 現状評価
                     ・To-Be 将来設計
                     ・移行ロードマップ
```

### 入力

| 入力 | 説明 | 例 |
|:---|:---|:---|
| ビジネス目的 | 組織の Purpose / Why | 「若い学習者にアクセシブルな教育を提供」 |
| 現状チーム構造 | チーム編成・責任分担・阻害要因 | FE/BE/Ops の機能サイロ |
| 現行アーキテクチャ | システム構造・技術スタック | モノリス + オンプレミス |
| 変更要求・課題 | 改善したい問題・目標 | 「デプロイに2週間かかる」 |

### 出力

| 出力 | 形式 | 説明 |
|:---|:---|:---|
| Architecture for Flow Canvas | Markdown | As-Is/To-Be の統合分析結果 |
| Wardley Map 記述 | テキスト/図面指示 | Value Chain + Evolution Stages |
| Subdomain 分類 | テーブル | Core/Supporting/Generic の分類と投資判断 |
| Bounded Context 設計 | テーブル + 説明 | BC 一覧・Context Map パターン |
| Team Constellation | テーブル + 説明 | チームタイプ・所有権境界・インタラクション |
| Transition Roadmap | Markdown | インクリメンタル移行計画 |

---

## Step 1: Purpose & Context Assessment

ビジネスの Purpose（存在理由）を確認し、Architecture for Flow Canvas のスコープを定義する。

### 1a. Purpose の確認

ユーザーに以下を確認する:

- **Purpose**: 「なぜこのビジネスが存在するのか?」
- **Core Values**: 基本的な価値観
- **Vision**: 達成したい将来像
- **Scope**: 今回の分析対象範囲

### 1b. Canvas のスコープ定義

- 対象ユーザータイプを決定（外部顧客 / 内部チーム / 両方）
- 分析の粒度を決定（全社 / 特定プロダクト / 特定ドメイン）

**チェックリスト**:
- [ ] Purpose が明確に言語化されている
- [ ] 分析スコープが定義されている
- [ ] 主要ステークホルダーが特定されている

---

## Step 2: As-Is Team Assessment

現在のチーム構造、フロー阻害要因、依存関係を分析する。

### 2a. チーム構造の記述

現在のチーム編成を整理:
- チーム名・メンバー数・責任範囲
- 機能サイロか、ストリーム指向か
- チーム間のハンドオフ・依存関係

### 2b. フロー阻害要因の特定

チームの視点から収集:
- **何がフローを阻害しているか?** — 待ち時間、ハンドオフ、依存、技術的負債
- **何がフローを支えているか?** — うまくいっていること
- **最小化すべきもの** — 排除または軽減すべき問題
- **保持すべきもの** — 維持すべき強み

### 2c. 依存関係の分析

3種の依存を特定:
- **アーキテクチャ依存**: 変更が他の部分に波及する
- **専門知識依存**: 特定の人/チームの知識がボトルネック
- **活動依存**: 他チームの完了を待つ必要がある

**チェックリスト**:
- [ ] 全チームの構造と責任が記述されている
- [ ] フロー阻害要因が具体的に列挙されている
- [ ] 3種の依存関係が分析されている
- [ ] 現在の DORA メトリクスの概況が把握されている

---

## Step 3: Flow of Change Assessment

Value Stream Mapping でボトルネックを特定する。

### 3a. 主要な変更ストリームの特定

ユーザーニーズから顧客駆動の変更ストリームを導出:
- 最も重要な価値提供の流れは何か?
- 変更が最も頻繁に発生する領域は?

### 3b. Value Stream Map の作成

各プロセスステップについて:
- **Cycle Time (VA)**: 実際に作業している時間
- **Wait Time (NVA)**: 待機・キュー・アイドル時間
- **Lead Time**: VA + NVA の合計

### 3c. 制約の特定（TOC 5 Steps）

1. **特定**: 最もキューが溜まっている場所、最も長い待ち時間
2. **活用**: 制約が最優先タスクに集中できるようにする
3. **従属**: 非制約領域のペースを制約に合わせる
4. **向上**: 制約の能力を拡大する投資
5. **繰り返し**: 次の制約を探す

**チェックリスト**:
- [ ] 主要な変更ストリームが特定されている
- [ ] Lead Time と Cycle Time のギャップが計測/推定されている
- [ ] ボトルネックが特定されている
- [ ] 制約の根本原因が分析されている

---

## Step 4: Wardley Map Creation

現在のビジネスランドスケープを Wardley Map で可視化する。

### 4a. Value Chain の構築

以下の手順で Value Chain を導出:

1. **ユーザーを特定** — 外部顧客・内部チーム
2. **ユーザーニーズを特定** — JTBD / User Journey
3. **コンポーネントを特定** — ニーズを満たす要素
4. **依存関係とポジションを決定** — Y軸（可視性）

### 4b. Evolution Stages のマッピング

各コンポーネントを X 軸にマッピング:

| Stage | 特徴 | Market | Practice |
|:---|:---|:---|:---|
| Genesis | 不確実・稀少・急変 | 未定義 | Novel |
| Custom-Built | 学習中・消費増加 | 形成中 | Emergent |
| Product (+rental) | 急速消費増・改善中 | 成長中 | Good |
| Commodity (+utility) | 標準化・安定 | 成熟 | Best |

参照: [evolution-stages-cheatsheet.md](references/evolution-stages-cheatsheet.md)

### 4c. Climatic Patterns の適用

主要な Climatic Patterns を確認:
- すべてのものは供給と需要の競争を通じて進化する
- 特性は進化段階とともに変化する
- 効率化がイノベーションを可能にする
- 過去の成功が慣性を生み、慣性は組織を殺す

**チェックリスト**:
- [ ] ユーザーとユーザーニーズがマップのアンカーとして定義されている
- [ ] 全コンポーネントが Evolution Stage にマッピングされている
- [ ] 依存関係が明示されている
- [ ] 効率ギャップが識別されている

---

## Step 5: Problem Space Categorization

問題ドメインを Subdomain タイプに分類する。

### 5a. Subdomain の発見と分類

各ユーザーニーズ/ドメイン領域を以下に分類:

| Subdomain Type | 判断基準 | 投資方針 |
|:---|:---|:---|
| **Core Domain** | 競争優位の源泉か? 差別化要因か? | Build in-house（最大投資） |
| **Supporting** | コアを支援するが非差別化か? 専門的か? | Evaluate（Build or Buy） |
| **Generic** | 非専門・非差別化か? | Buy or Outsource |

### 5b. Core Domain の検証

Core Domain の判定質問:
- この領域がなくなったら競争優位を失うか?
- 競合他社もこの領域に投資しているか?
- この領域の改善が直接的にビジネス成果に影響するか?

**チェックリスト**:
- [ ] 全てのドメイン領域が3種のいずれかに分類されている
- [ ] Core Domain が明確に特定され、根拠が示されている
- [ ] Build/Buy/Outsource の方針が各 Subdomain に設定されている

---

## Step 6: Solution Space Design

Bounded Context の設計と Context Map の作成を行う。

### 6a. Bounded Context の設計

モデリング手法を適用して BC 候補を特定:
- **Big Picture EventStorming**: ドメインイベントのクラスタリング → BC 候補
- **Domain Storytelling**: ワークフロー可視化 → 境界の発見
- **Example Mapping**: ビジネスルールの具体化

各 BC について記述:
- 名前・責任範囲・ユビキタス言語
- 関連する Subdomain Type
- Evolution Stage 上の位置

### 6b. Context Map の設計

BC 間の統合パターンを決定:

| Pattern | 用途 | 変更結合度 |
|:---|:---|:---|
| OHS + ACL | Core 同士の統合 | 低（翻訳層で吸収） |
| OHS + PL + CF | Supporting/Generic からの消費 | 低（PL は安定） |
| Separate Ways | 統合不要 | なし |
| SK | 共有コード（高リスク） | 最高 |

### 6c. 変更結合度の評価

Wardley Map 上に BC をマッピングし、潜在的に問題のある関係を可視化:
- Core BC（Custom-Built/Genesis）間の CF はリスク
- Generic BC への過度な依存はリスク

**チェックリスト**:
- [ ] 全 BC が明確な境界と責任を持っている
- [ ] 各 BC の Context Map パターンが定義されている
- [ ] 変更結合度のリスク評価が完了している
- [ ] BC が Wardley Map の Evolution Stage にマッピングされている

---

## Step 7: Future Landscape & Team Design

将来のビジネスランドスケープとチーム組織を設計する。

### 7a. 将来 Wardley Map の作成

- 効率ギャップの解消: コモディティ化可能なコンポーネントを特定
- 戦略的投資の優先順位付け: Core → Supporting → Generic の順
- 進化の方向を矢印で示す

### 7b. Team Topologies の適用

BC と Value Chain コンポーネントにチームタイプを割り当て:

| 領域 | チームタイプ | 根拠 |
|:---|:---|:---|
| Core BC | Stream-aligned Team | 顧客価値の変更ストリームに整合 |
| 複数 Core BC | 複数の SA Team | 認知負荷を分散 |
| Infrastructure | Platform Team | セルフサービス基盤の提供 |
| 専門領域 | Complicated-subsystem Team | 専門知識の集約 |
| スキルギャップ | Enabling Team | コーチング・ファシリテーション |

### 7c. 認知負荷の検証

参照: [evolution-stages-cheatsheet.md](references/evolution-stages-cheatsheet.md)

各チームの認知負荷を検証:
- Genesis BC: 1 BC/team（高い不確実性）
- Custom-Built BC: 1-2 BCs/team
- Product BC: 2-3 BCs/team
- Commodity BC: 3+ BCs/team

### 7d. インタラクションモードの設計

チーム間のインタラクションとその進化を計画:
- 初期: Collaboration（発見・探索）
- 安定化後: XaaS（セルフサービス提供）
- スキルギャップ時: Facilitating（コーチング）

**チェックリスト**:
- [ ] 将来 Wardley Map が作成されている
- [ ] 全 BC にチームタイプが割り当てられている
- [ ] 各チームの認知負荷が Evolution Stage ベースで検証されている
- [ ] チーム間インタラクションモードとその進化が計画されている
- [ ] Platform Team の TVP（Thinnest Viable Platform）が定義されている

---

## Step 8: Transition Roadmap

As-Is から To-Be へのインクリメンタル移行計画を策定する。

### 8a. 移行原則の確認

- **Big-bang 再編成は避ける** — 小さな意図的ステップで移行
- **早期フィードバック** — 各ステップで学びと軌道修正
- **Dynamic Reteaming** — チーム構成を段階的に変更
- **Strangler Fig Pattern** — BC 単位で段階的に抽出

### 8b. 移行フェーズの設計

```
Phase 1: Foundation（基盤整備）
  - Purpose の共有と合意
  - 最初の Wardley Map 作成
  - Platform Team の組成開始（TVP）

Phase 2: First Stream（最初のストリーム）
  - 最も価値の高い BC を選択
  - 最初の Stream-aligned Team を組成
  - ACL でレガシーとの境界を設定
  - Collaboration モードで開始

Phase 3: Expand（拡張）
  - 次の BC を段階的に抽出
  - Platform を XaaS に進化
  - 追加の SA Team を組成
  - Enabling Team の検討

Phase 4: Optimize（最適化）
  - フロー指標の継続的計測
  - ボトルネックの再評価
  - チームインタラクションの進化
  - 継続的改善サイクルの確立
```

### 8c. Architecture for Flow Canvas の統合

全ステップの成果を Canvas に統合:

参照: [canvas-template.md](references/canvas-template.md)

### Flow Architecture Slop 防止チェック（Distributional Convergence 対策）

フローアーキテクチャ設計は Wardley Mapping・DDD・Team Topologies の 3 視点を統合するが、LLM は各フレームワークの「最も一般的な適用パターン」に収束しやすい。特に Strangler Fig の万能視、Stream-Aligned Team のデフォルト推奨、Wardley Map の Evolution Stage の画一的な配置が頻発する。

| # | Flow Architecture Slop パターン | 検出方法 | 対策 |
|:---|:---|:---|:---|
| FA-1 | **Wardley Map の Evolution Stage 固定** | コンポーネントが毎回同じステージに配置される | 市場の成熟度・消費パターン・実践の種類で個別判定。Cheatsheet を参照し、チームで議論 |
| FA-2 | **組織図 = Bounded Context の誤解** | BC 境界が部門境界とそのまま一致 | EventStorming でドメインイベントをクラスタリングし、BC をビジネス能力から導出 |
| FA-3 | **Stream-Aligned Team のデフォルト推奨** | 全チームを Stream-Aligned に分類 | Enabling / Complicated-Subsystem / Platform の役割を評価。認知負荷に基づいてチームタイプを選定 |
| FA-4 | **Platform Team のスコープ膨張** | 「全部プラットフォーム化」または「最小限のみ」の極端 | TVP（Thinnest Viable Platform）から開始し、SA Team のニーズに基づいて段階的に拡大 |
| FA-5 | **Interaction Mode の静的固定** | Collaboration / XaaS / Facilitating が時間軸で変化しない | チーム間関係は進化する。Collaboration → XaaS への移行タイミングを明確に設計 |
| FA-6 | **認知負荷の汎用チェックリスト** | 全チームに同じ認知負荷評価を適用 | Evolution Stage ヒューリスティクスでチームごとの認知負荷を個別評価。ドメイン複雑性を加味 |
| FA-7 | **Strangler Fig の万能視** | モダナイゼーション戦略が常に Strangler Fig | Branch by Abstraction / Parallel Run / Event Interception も選択肢。既存システムの結合度で判断 |
| FA-8 | **顧客ジャーニーのテンプレ化** | Wardley Map のアンカーが毎回同じ顧客ニーズ | 実際のユーザーリサーチ・ドメインエキスパートのインプットからアンカーを導出 |

> **核心原則**: **地図は領土ではない — Wardley Map も Team Topologies も現実の「近似」であり、テンプレートではない** — フレームワークを機械的に適用するのではなく、現場の文脈に合わせて解釈する。「別の組織・別のドメインに同じ Canvas を渡しても違和感がないか？」→ 違和感がないなら Flow Architecture Slop である。

**チェックリスト**:
- [ ] 移行フェーズが明確に定義されている
- [ ] 各フェーズの成功基準が設定されている
- [ ] リスクと緩和策が特定されている
- [ ] Architecture for Flow Canvas が完成している
- [ ] フロー阻害要因の改善計画が含まれている
- [ ] Flow Architecture Slop チェック（FA-1〜FA-8）に 2 つ以上該当しない
- [ ] 出力がドメイン固有の要素を含み、汎用テンプレートに見えない

---

## Examples

### Example 1: カンファレンスイベントプランナーの Canvas 作成

```
「カンファレンスイベント管理ツールの Architecture for Flow Canvas を作成して」

→ Step 1 で Purpose を確認:「高品質なカンファレンスコンテンツのキュレーション支援」
→ Step 4 で Wardley Map 作成: CfP 管理・セッション評価・スケジュール管理等を可視化
→ Step 5 で Core Domain 特定: CfP 管理・セッション評価（差別化要因）
→ Step 6 で BC 設計: Submission Handling, CfP Management, Session Evaluation 等
→ Step 7 で SA Team × 4 + Platform Team の構成を導出
→ 成果物: Architecture for Flow Canvas（As-Is/To-Be 統合）
```

### Example 2: レガシーオンラインスクールの近代化

```
「モノリスのオンラインスクールをマイクロサービス化したい」

→ Step 2 で FE/BE/Ops のサイロ構造と阻害要因を特定
→ Step 3 で VSM: デプロイに2週間、待ち時間が60%
→ Step 4 で Wardley Map: BBoM が Custom-Built に位置
→ Step 6 で EventStorming → 7 BC に分解
→ Step 7 で SA Team 構成 + Platform Team（クラウド基盤）
→ Step 8 で Strangler Fig による段階的移行計画
→ 成果物: 移行ロードマップ + Canvas
```

### Example 3: E コマースの Wardley Map + DDD 統合分析

```
「EC サイトのアーキテクチャを戦略的に見直したい」

→ Step 1 で Purpose 確認と分析スコープ定義
→ Step 4 で Value Chain 構築: 商品カタログ・注文・決済・配送・CRM
→ Step 5 で分類: 商品レコメンド=Core、決済=Generic、在庫管理=Supporting
→ Step 6 で BC 設計 + Context Map（決済は OHS+PL で外部サービスに CF）
→ 成果物: Subdomain 分類 + 投資優先順位
```

### Example 4: マイクロサービス移行時の認知負荷最適化

```
「チームがマイクロサービスの運用に疲弊している」

→ Step 2 で認知負荷の評価: 1チームが12サービス + インフラを担当
→ Step 4 で Platform 視点の Wardley Map 作成
→ Step 7 で認知負荷ヒューリスティクスを適用 → 3 SA Team に分割
→ Step 7 で Platform Team を組成 → DB/MQ/Monitoring を XaaS 化
→ 成果物: 再編成計画 + Platform TVP 定義
```

### Example 5: スタートアップから Scale-up への進化

```
「チームが10人から50人に成長。組織とアーキテクチャを再設計したい」

→ Step 1 で成長に伴う Purpose の再確認
→ Step 2 で現在の1チーム体制の限界を分析
→ Step 5 で Core Domain を再特定
→ Step 7 で 3-4 SA Team + Platform Team の編成
→ Step 7 で Dunbar の信頼境界を考慮した規模設計
→ 成果物: 成長段階に応じたチーム編成計画
```

### Example 6: プラットフォームチームの Value Chain 設計

```
「Platform Team の役割と提供サービスを設計したい」

→ Step 4 で内部視点の Wardley Map: SA Team がユーザー
→ ユーザーニーズ: Build/Test/Deploy/Monitor/Manage Infrastructure
→ Platform 分類: Build-and-Release / Operation-and-Monitoring / Infrastructure
→ Step 7 で TVP 定義 + XaaS インターフェース設計
→ 成果物: Platform Value Chain + セルフサービスカタログ
```

### Example 7: Big Ball of Mud の段階的分解

```
「技術的負債が溜まったモノリスを整理したい」

→ Step 3 で最も変更頻度が高い領域を特定
→ Step 6 で EventStorming → BC 境界の発見
→ Step 6 で ACL パターンでレガシーとの境界設定
→ Step 8 で Strangler Fig: 最も価値の高い BC から段階的に抽出
→ 成果物: 分解優先順位付きロードマップ
```

### Example 8: Cloud Migration の効率ギャップ評価

```
「オンプレミスからクラウドへの移行を戦略的に計画したい」

→ Step 4 で現状 Wardley Map: DB/MQ/Search が Product 段階にオンプレ運用
→ Step 4 で効率ギャップ評価: DBaaS/MBaaS/SEaaS で Commodity 化可能
→ Step 7 で Platform Team の運用負荷削減を試算
→ Step 8 で Replatforming → Cloud Migration のフェーズ設計
→ 成果物: 効率ギャップ分析 + Cloud Migration 計画
```

---

## Troubleshooting

| 問題 | 原因 | 解決策 |
|:---|:---|:---|
| Wardley Map を作り始められない | スコープが広すぎる・ユーザーが不明確 | 1人のユーザーと1つのニーズから始める。完璧さではなく有用性を目指す |
| Core Domain が特定できない | 差別化要因の理解が不足 | 「これがなくなったら競争優位を失うか?」を各領域に問う。ドメインエキスパートと協議 |
| Bounded Context の粒度がわからない | ドメイン理解の深度が不足 | EventStorming でドメインイベントをクラスタリング。1 BC = 1 ユビキタス言語のスコープ |
| Context Map パターンの選択に迷う | 変更結合度の評価が不十分 | Core 同士は OHS+ACL、Generic/Supporting は OHS+PL+CF を基本パターンとする |
| チーム認知負荷の評価が難しい | 定量的な指標がない | Evolution Stage ヒューリスティクスを初期近似として使用。Team Cognitive Load Assessment ツールを補完的に活用 |
| どの BC から抽出を始めるべきか | 優先順位の判断基準がない | 最も価値が高く、変更頻度が高く、依存関係が少ない BC から。Strangler Fig で段階的に |
| Platform Team の責任範囲が不明確 | 役割の定義が曖昧 | SA Team のユーザーニーズ（Build/Deploy/Monitor/Manage）から逆算。TVP で最小限から開始 |
| Collaboration→XaaS 移行のタイミング | 明確な基準がない | SA Team が自律的にタスクを完遂できるようになったら移行。フィードバックループで判断 |
| Wardley Map が複雑になりすぎる | スコープが広すぎる・粒度が細かすぎる | スコープを絞る。詳細は別の Map に分離。Map はあくまで近似 |
| Subdomain 分類に合意が得られない | ステークホルダー間の視点の違い | ビジネスインパクトと差別化の観点で議論。Wardley Map 上の位置で客観的に整理 |
| Big-bang 移行を求められる | 経営層の期待・時間的制約 | リスクを定量的に提示。インクリメンタル移行の早期成果を示す。早期フィードバックの価値を説明 |
| Evolution Stage の判定に自信がない | 特性の理解が不十分 | Cheatsheet を参照。市場の成熟度・消費パターン・実践の種類で判定。他者との議論で検証 |

---

## References

| ファイル | 内容 |
|:---|:---|
| [canvas-template.md](references/canvas-template.md) | Architecture for Flow Canvas テンプレート（As-Is/To-Be 構造化ガイド） |
| [evolution-stages-cheatsheet.md](references/evolution-stages-cheatsheet.md) | Evolution Stages 特性 + Cynefin マッピング + 認知負荷ヒューリスティクス |
| [team-interaction-patterns.md](references/team-interaction-patterns.md) | Team Topologies 4 チームタイプ・3 インタラクションモード、Wardley Map 連動チーム設計、BC 境界整合、逆コンウェイ戦略、認知負荷評価、TVP 設計原則 |

---

## Related Skills

| スキル | 関係 | 説明 |
|:---|:---|:---|
| **data-arch** | Complementary | データアーキテクチャの選定・設計。flow-architecture はシステム全体のフロー設計を担当し、data-arch はデータ基盤層を設計 |
| **diagram** | Downstream | Architecture for Flow Canvas・Wardley Map・Context Map 等の成果物を draw.io 図面として可視化 |
| **review** | Downstream | 設計結果（Canvas・Wardley Map・BC 設計・チーム編成）のクリティカルレビュー |
| **story-map** | Upstream | ユーザーニーズの構造化。Wardley Map のアンカー定義に活用可能 |
| **test** | Downstream | BC 実装時の Ports and Adapters パターンに沿ったテスト設計 |
| **agent-craft** | Complementary | Architecture for Flow の原則を適用してエージェントの社会技術的設計に応用 |
| **databricks** | Complementary | データプラットフォーム設計時に Platform Team 視点の Value Chain と統合 |
| **software-architecture** | Downstream | flow-architecture の戦略的方向性（Wardley Map、Subdomain 分類）を受けて、software-architecture が具体的なアーキテクチャスタイルを選定 |
| **decision-framework** | Downstream | Wardley Map の Evolution Stage 判断や Context Map パターン選定の意思決定を ADR として記録・管理 |
| **project-ops** | Downstream（運用） | flow-architecture の Step 7 (Team Design) の戦略設計を project-ops が実際の移行計画・DORA 改善・チーム再編成として実行 |
