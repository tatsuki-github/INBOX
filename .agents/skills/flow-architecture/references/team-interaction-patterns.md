# Team Interaction Patterns Reference

> Team Topologies の 4 チームタイプ・3 インタラクションモード、Wardley Map 連動のチーム設計、DDD Bounded Context との整合、逆コンウェイ戦略の実践リファレンス

---

## 1. Team Topologies: 4 チームタイプ

### 概要マトリクス

| チームタイプ | 目的 | 所有するもの | 認知負荷の性質 | 典型的な規模 |
|:---|:---|:---|:---|:---|
| **Stream-aligned (SA)** | ビジネス価値の単一ストリームへの高速デリバリー | 1-2 Bounded Context、エンドツーエンドのサービス | ドメイン複雑性（本質的） | 5-9 人 |
| **Platform** | SA Team の認知負荷を軽減するセルフサービス基盤 | インフラ、共通サービス、開発者体験 | 技術的複雑性（横断的） | 5-9 人 |
| **Enabling** | スキルギャップの橋渡し、ベストプラクティスの伝播 | なし（コーチングを提供） | 学習支援（一時的） | 3-6 人 |
| **Complicated-subsystem** | 高度な専門知識を要する領域の隔離 | 専門的なサブシステム | 専門的複雑性（深い） | 3-8 人 |

### チームタイプ選択の判断フロー

```
対象の BC / コンポーネントについて:

Q1. この領域は顧客価値を直接届けるか?
  → Yes → Stream-aligned Team

Q2. 複数の SA Team が共通に必要とするか?
  → Yes → Q2a. セルフサービスで提供可能か?
              → Yes → Platform Team
              → No  → Enabling Team（一時的にコーチング）

Q3. 深い専門知識（ML/暗号/リアルタイム制御等）が必要か?
  → Yes → Complicated-subsystem Team

Q4. SA Team がスキルを獲得中か?
  → Yes → Enabling Team（期限付き）
```

---

## 2. 3 インタラクションモード

### モード定義

| モード | 方向性 | 期間 | 適する場面 |
|:---|:---|:---|:---|
| **Collaboration** | 双方向・密結合 | 一時的（発見フェーズ） | 新ドメインの探索、BC 境界の発見、Genesis/Custom-Built コンポーネント |
| **X-as-a-Service (XaaS)** | 提供者→消費者（API 契約） | 恒久的（安定フェーズ） | Platform の成熟後、Product/Commodity コンポーネント |
| **Facilitating** | コーチ→被コーチ | 一時的（学習フェーズ） | 新技術の導入、Enabling Team のスキル移転 |

### インタラクションモードの進化パターン

```
典型的な進化の流れ:

Collaboration（探索）
    ↓ BC 境界が明確になったら
X-as-a-Service（安定運用）

Facilitating（学習）
    ↓ SA Team がスキルを獲得したら
X-as-a-Service（自律運用）

Collaboration（共同開発）
    ↓ Platform が成熟したら
X-as-a-Service（セルフサービス）
```

### 移行タイミングの判断基準

| 現在のモード | 移行先 | トリガー |
|:---|:---|:---|
| Collaboration → XaaS | BC 境界が安定し、API 契約が定義できる | SA Team が独力でタスクを完遂できる |
| Collaboration → Facilitating | 一方のチームがスキル不足で貢献できない | 「教える」関係が自然に発生している |
| Facilitating → XaaS | スキル移転が完了した | Enabling Team の介入なしで運用可能 |
| XaaS → Collaboration | 大きな技術的変革が必要 | 既存 API では新しい要件を満たせない |

---

## 3. Wardley Map × チーム構成

### Evolution Stage とチームタイプの対応

| Evolution Stage | 推奨チームタイプ | BC / Team | インタラクション | 根拠 |
|:---|:---|:---|:---|:---|
| **Genesis** | SA Team（小規模） | 1 BC / Team | Collaboration | 高い不確実性。密な協働で素早い学習 |
| **Custom-Built** | SA Team | 1-2 BCs / Team | Collaboration → XaaS | 学習が進み、境界が明確化してくる |
| **Product** | SA Team + Platform | 2-3 BCs / Team | XaaS | パターンが確立。プラットフォーム化の余地 |
| **Commodity** | Platform Team | 3+ BCs / Team | XaaS | 標準化済み。セルフサービスで提供 |

### 認知負荷ヒューリスティクス（Stage 別）

| Stage | ドメイン複雑性 | 技術的不確実性 | 推奨 BC/Team | 理由 |
|:---|:---|:---|:---|:---|
| Genesis | 極めて高い | 極めて高い | 1 | 探索的開発に集中が必要 |
| Custom-Built | 高い | 高い | 1-2 | 学習しながらの構築 |
| Product | 中程度 | 中程度 | 2-3 | パターンが見え、効率化可能 |
| Commodity | 低い | 低い | 3+ | 運用中心。標準化されている |

---

## 4. DDD Bounded Context とチーム境界

### BC → Team マッピングの原則

```
原則 1: 1 BC = 1 Team が基本（逆は必ずしも真ではない）
  → 1 Team が複数 BC を持つことはある（認知負荷の範囲内で）
  → 1 BC を複数 Team で共有するのは避ける（所有権の曖昧化）

原則 2: BC 間の Context Map パターンがチーム間インタラクションを決定する
  → OHS + ACL = XaaS に対応
  → Shared Kernel = Collaboration が必要
  → Separate Ways = インタラクション不要

原則 3: ユビキタス言語の一貫性がチーム境界の妥当性を検証する
  → チーム内で用語が統一されている = 境界が適切
  → 同じ用語が異なる意味で使われる = 境界の見直しが必要
```

### Context Map パターンとインタラクションモードの対応

| Context Map パターン | インタラクションモード | 変更結合度 | 備考 |
|:---|:---|:---|:---|
| **OHS + ACL** | XaaS | 低 | 理想的。ACL が翻訳層として機能 |
| **OHS + PL + CF** | XaaS | 低 | Published Language で安定した契約 |
| **Shared Kernel** | Collaboration | 高（要注意） | 共有コードは密な協働が必要 |
| **Customer-Supplier** | XaaS（非対称） | 中 | Upstream が Downstream の要求に応える |
| **Separate Ways** | なし | なし | 統合不要。独立して進化 |

---

## 5. コンウェイの法則と逆コンウェイ戦略

### コンウェイの法則

```
「システムを設計する組織は、自らの組織のコミュニケーション構造を
 模倣した構造を持つ設計を生み出す」 — Melvin Conway (1968)
```

### 逆コンウェイ戦略（Inverse Conway Maneuver）

```
目標: 望ましいアーキテクチャに合わせてチーム構造を意図的に設計する

Step 1: 将来のアーキテクチャ（To-Be）を定義する
  → Wardley Map + BC 設計で将来像を描く

Step 2: アーキテクチャに整合するチーム構造を設計する
  → 1 BC = 1 SA Team のマッピング
  → 共有コンポーネントは Platform Team に

Step 3: チーム間のインタラクションを設計する
  → Context Map パターン → インタラクションモード

Step 4: 段階的にチームを再編成する
  → Dynamic Reteaming で少しずつ移行
  → Big-bang 再編成は避ける
```

### 逆コンウェイ戦略の適用パターン

| 現状 | 目標 | 逆コンウェイアクション |
|:---|:---|:---|
| 機能サイロ（FE/BE/DB） | ストリーム指向 | BC 単位で cross-functional SA Team を編成 |
| モノリス + 1 チーム | マイクロサービス | BC ごとに SA Team を分割、Platform Team を新設 |
| 外部ベンダー依存 | 内製化 | Core BC の SA Team を内部に構築、Generic は外部のまま |
| 1 つの巨大 Platform | 軽量 Platform | TVP に絞り込み、不要機能を SA Team に移管 |

---

## 6. チーム認知負荷の評価

### 3 種類の認知負荷

| 種別 | 定義 | 削減方法 |
|:---|:---|:---|
| **Intrinsic（内在的）** | ドメイン自体の複雑さ | BC の適切な分割、DDD の適用 |
| **Extraneous（外在的）** | ツール・プロセス・インフラの複雑さ | Platform Team による抽象化、セルフサービス化 |
| **Germane（関連的）** | 新しいスキル・知識の習得 | Enabling Team のコーチング、ペアプログラミング |

### 認知負荷の警告サイン

| 警告サイン | 検出方法 | 対処法 |
|:---|:---|:---|
| チームが「すべてを知る必要がある」 | チームメンバーへのヒアリング | BC の分割を検討。1 チーム 1-2 BC に絞る |
| 頻繁な Context Switching | タスクボードの並列タスク数 | WIP 制限の導入。チームのフォーカスを 1 ストリームに |
| 新メンバーの立ち上げに 3 ヶ月以上 | オンボーディング期間の計測 | ドメインの分割。ドキュメントの改善 |
| デプロイ頻度の低下 | DORA メトリクス | 依存関係の削減。デプロイパイプラインの改善 |
| チーム間の待ち時間が増加 | Lead Time の分析 | インタラクションモードの見直し。API 契約の明確化 |

### Team Cognitive Load Assessment

| 評価項目 | 質問 | スコア（1-5） |
|:---|:---|:---|
| ドメイン理解 | チーム全員がドメインの主要概念を説明できるか? | ___ |
| 技術スタック | 使用技術の全体を把握できているか? | ___ |
| 運用負荷 | オンコール・監視・障害対応の頻度と負荷は? | ___ |
| 外部依存 | 他チームへの依存でブロックされる頻度は? | ___ |
| 変更の速度 | 小さな変更を 1 日以内にデプロイできるか? | ___ |
| **合計** | 25: 過負荷 / 15-20: 注意 / <15: 適切 | ___ |

---

## 7. Platform Team の設計原則

### Thinnest Viable Platform (TVP)

```
TVP の原則:
  → 「作れるものを全部作る」のではなく「SA Team が最も必要としているもの」から始める
  → Wiki ページ + 手順書でも Platform の一部
  → 過剰なプラットフォーム化は新たな認知負荷を生む

TVP の進化:
  Phase 0: ドキュメント + 手動手順
  Phase 1: スクリプト + テンプレート
  Phase 2: セルフサービス API + CLI
  Phase 3: 完全自動化 + 開発者ポータル
```

### Platform の Value Chain

```
SA Team（ユーザー）
  ├── ニーズ: Build & Release
  │     → CI/CD パイプライン、ビルドツール、アーティファクト管理
  ├── ニーズ: Operation & Monitoring
  │     → 監視、ログ、アラート、ダッシュボード
  ├── ニーズ: Infrastructure
  │     → コンピュート、ネットワーク、ストレージ、データベース
  └── ニーズ: Developer Experience
        → 開発環境、テンプレート、ドキュメント
```
