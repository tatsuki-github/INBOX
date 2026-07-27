# Evolution Stages Cheatsheet

> Source: Architecture for Flow (Susanne Kaiser, Pearson Addison-Wesley 2025), Chapter 1 & 6
> Purpose: Wardley Map の Evolution Stages 特性 + Cynefin マッピング + 認知負荷ヒューリスティクス

---

## Evolution Stages Overview

```
← High Change Rate / High Uncertainty          Low Change Rate / Stable →
← Undefined Market                              Mature Market →
← Novel Practices                               Best Practices →

  Genesis        Custom-Built     Product (+rental)   Commodity (+utility)
  ─────────────────────────────────────────────────────────────────────────→
                              Evolution (X-axis)
```

---

## Characteristics by Stage

| Characteristic | Genesis | Custom-Built | Product (+rental) | Commodity (+utility) |
|:---|:---|:---|:---|:---|
| **Ubiquity** | Rare | Slowly increasing | Rapidly increasing | Widespread, stabilizing |
| **Certainty** | Poorly understood | Rapid learning | Rapid use/fit increases | Commonly understood |
| **Market** | Undefined | Forming | Growing | Mature |
| **Knowledge** | Uncertain | Learning on use | Learning on operation | Known, accepted |
| **Perception** | Chaotic, nonlinear | Domain of experts | Increasing expectation | Ordered, trivial |
| **User Perception** | Different, exciting | Leading edge | Common, expected | Standard |
| **Industry Perception** | Competitive advantage, unpredictable | ROI, case examples | Advantage through features | Cost of doing business |
| **Focus of Value** | High future worth | Seeking profit | High profitability | High volume, reducing margin |
| **Failure** | High, tolerated | Moderate, unsurprising | Not tolerated, improve | Operational failure critical |
| **Comparison** | Constantly changing, differential | Learning, testing water | Feature difference | Essential, operational advantage |

---

## Cynefin Domain Mapping

| Evolution Stage | Cynefin Domain | Cause-Effect | Response Pattern |
|:---|:---|:---|:---|
| **Genesis** | Chaotic → Complex | None / Retrospective only | Act → Sense → Respond |
| **Custom-Built** | Complex | Retrospective only | Probe → Sense → Respond |
| **Product (+rental)** | Complicated | Discoverable with analysis | Sense → Analyze → Respond |
| **Commodity (+utility)** | Clear | Obvious, known | Sense → Categorize → Respond |

### Practice Types

| Evolution Stage | Practice Type | Description |
|:---|:---|:---|
| Genesis | **Novel** | 前例のない新しいアプローチ。実験と探索が中心 |
| Custom-Built | **Emergent** | パターンが現れ始めるが確立されていない。学習が中心 |
| Product (+rental) | **Good** | 確立されたパターンが存在。改善と最適化が中心 |
| Commodity (+utility) | **Best** | 業界標準のベストプラクティス。効率化と運用が中心 |

---

## Cognitive Load Heuristics

### Evolution Stage vs. Cognitive Load

```
Genesis:        ████████████████████  Very High
Custom-Built:   ██████████████        High
Product:        █████████             Medium
Commodity:      ████                  Low
```

| Evolution Stage | Cognitive Load | BCs per Team | Rationale |
|:---|:---|:---|:---|
| **Genesis** | Very High | 1 BC | Unknown unknowns, constant change, novel practices required |
| **Custom-Built** | High | 1-2 BCs | Emerging understanding, significant learning curve |
| **Product (+rental)** | Medium | 2-3 BCs | Good practices available, clearer path to action |
| **Commodity (+utility)** | Low | 3+ BCs | Best practices, standardized, well-understood |

### Key Principle

- 進化段階が左（Genesis）にあるほど、認知負荷は高い
- 認知負荷が高いほど、1チームが担当できる BC の数は少ない
- このヒューリスティクスは**初期近似**であり、他のフレームワーク（Cynefin 等）で補完すべき

---

## Subdomain Type vs. Evolution Stage

| Subdomain Type | Typical Evolution Stage | Investment Decision |
|:---|:---|:---|
| **Core Domain** | Genesis / Custom-Built | Build in-house（最大投資） |
| **Supporting Subdomain** | Custom-Built / Product | Evaluate（Build or Buy） |
| **Generic Subdomain** | Product / Commodity | Buy or Outsource |

### Build-or-Buy Decision Tree

```
Is it a Core Domain (competitive differentiator)?
  ├── YES → Build in-house (invest heavily)
  └── NO → Is it specialized (Supporting)?
        ├── YES → Can it be addressed by customizable products?
        │     ├── YES → Buy / Use off-the-shelf
        │     └── NO  → Custom-build (but limit investment)
        └── NO (Generic) → Is a commodity/utility available?
              ├── YES → Outsource to utility supplier
              └── NO  → Buy off-the-shelf product
```

---

## Doctrinal Principles Checklist

Wardley Mapping の Doctrinal Principles — 組織の適応力を高める普遍的原則:

### Category: Communication

- [ ] **Know your users** — ユーザーを知る
- [ ] **Focus on user needs** — ユーザーニーズに焦点
- [ ] **Know the details** — 詳細を把握する
- [ ] **Challenge assumptions** — 前提を疑う
- [ ] **Use a common language** — 共通言語を使う
- [ ] **Focus on high situational awareness** — 高い状況認識

### Category: Development

- [ ] **Use appropriate methods per evolution stage** — 進化段階に応じた手法
- [ ] **Think small (as in contracts)** — 小さく考える（契約）
- [ ] **Think small teams** — 小さなチーム
- [ ] **Provide purpose, mastery, and autonomy** — 目的・熟達・自律性

### Category: Operation

- [ ] **Think aptitude and attitude** — 適性と姿勢
- [ ] **There is no one culture** — 単一の文化はない
- [ ] **Optimize flow** — フローを最適化
- [ ] **Design for constant evolution** — 絶え間ない進化のために設計

---

## Context Map Pattern Selection Guide

### Quick Reference

| Upstream | Downstream | Recommended Pattern | Change Coupling |
|:---|:---|:---|:---|
| Core BC | Core BC | OHS (up) + ACL (down) | **Low** — 翻訳層で変更を吸収 |
| Supporting BC | Core BC | OHS+PL (up) + CF (down) | **Low** — PL は安定的 |
| Generic BC | Core BC | OHS+PL (up) + CF (down) | **Low** — PL は安定的 |
| Core BC | Core BC | SK (shared) | **Very High** — 避けるべき |
| Any BC | Any BC | SW (separate) | **None** — 統合しない |

### Risk Assessment

```
LOW RISK:   OHS+ACL, OHS+PL+CF, SW
MEDIUM RISK: Customer-Supplier, Partnership
HIGH RISK:  Conformist (to changing upstream), Shared Kernel
CRITICAL:   Big Ball of Mud
```

---

## Value Stream Mapping Quick Guide

### Metrics to Collect per Step

| Metric | Definition | How to Measure |
|:---|:---|:---|
| **Cycle Time (CT)** | 1ステップの作業時間（VA） | タスク開始→完了 |
| **Wait Time (WT)** | ステップ間の待機時間（NVA） | 前ステップ完了→次ステップ開始 |
| **Lead Time (LT)** | 全体のリードタイム | 受付→完了の合計 |
| **%C&A** | 完全かつ正確な結果の割合 | 再作業なしで次ステップに渡せた割合 |

### Flow Efficiency

```
Flow Efficiency = Total VA / Total Lead Time × 100%
```

- 30% 以上: 良好
- 15-30%: 改善の余地あり
- 15% 未満: 重大なフローの問題

### Theory of Constraints (5 Steps)

1. **Identify** — 最もキューが溜まっている場所を特定
2. **Exploit** — 制約が最優先タスクに集中できるようにする
3. **Subordinate** — 非制約領域のペースを制約に合わせる
4. **Elevate** — 制約の能力を拡大する投資（人員追加・プロセス改善等）
5. **Repeat** — 制約が解消されたら次の制約を探す
