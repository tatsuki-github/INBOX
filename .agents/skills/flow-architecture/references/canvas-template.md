# Architecture for Flow Canvas Template

> Source: Architecture for Flow (Susanne Kaiser, Pearson Addison-Wesley 2025), Chapter 8
> Purpose: As-Is 評価から To-Be 設計までの構造化ガイド

---

## Canvas Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                 ARCHITECTURE FOR FLOW CANVAS                    │
├─────────────────────────────┬───────────────────────────────────┤
│      AS-IS (現状評価)        │      TO-BE (将来設計)             │
├─────────────────────────────┼───────────────────────────────────┤
│ 1. Teams & Way of Working   │ 5. Modularized Solution Space     │
│ 2. Flow of Change Assessment│ 6. Future Business Landscape      │
│ 3. Current Business Landscape│ 7. Future Team Organization      │
│ 4. Problem Space Categories  │                                   │
└─────────────────────────────┴───────────────────────────────────┘
```

---

## Part A: As-Is Assessment

### A1. Purpose

| Item | Description |
|:---|:---|
| **Purpose (Why)** | _[ビジネスの存在理由]_ |
| **Core Values** | _[基本的な価値観（3-5個）]_ |
| **Vision** | _[達成したい将来像]_ |
| **Scope** | _[今回の Canvas の分析対象範囲]_ |

### A2. Current Teams & Way of Working

#### Team Structure

| Team | Size | Responsibilities | Team Type |
|:---|:---|:---|:---|
| _[Team 1]_ | _[n]_ | _[責任範囲]_ | _[Silo/SA/Platform/...]_ |
| _[Team 2]_ | _[n]_ | _[責任範囲]_ | _[Silo/SA/Platform/...]_ |

#### Blockers to Flow

| Category | Description | Impact |
|:---|:---|:---|
| **Blockers** | _[フローを阻害するもの]_ | _[影響度: High/Medium/Low]_ |
| **Supporters** | _[フローを支えるもの]_ | - |
| **Minimize** | _[排除・軽減すべきもの]_ | _[影響度]_ |
| **Preserve** | _[保持すべきもの]_ | - |

#### Dependencies

| Type | From | To | Description | Severity |
|:---|:---|:---|:---|:---|
| Architecture | _[Team/Component]_ | _[Team/Component]_ | _[内容]_ | _[High/Med/Low]_ |
| Expertise | _[Team]_ | _[Person/Team]_ | _[内容]_ | _[High/Med/Low]_ |
| Activity | _[Team]_ | _[Team]_ | _[内容]_ | _[High/Med/Low]_ |

### A3. Flow of Change Assessment

#### Value Stream Map

```
[Process Step 1] → [Process Step 2] → [Process Step 3] → ... → [Delivered]
  CT: _d          CT: _d             CT: _d
  WT: _d          WT: _d             WT: _d
```

| Metric | Value |
|:---|:---|
| **Total Lead Time** | _[n days]_ |
| **Total VA (Cycle Time)** | _[n days]_ |
| **Total NVA (Wait Time)** | _[n days]_ |
| **Flow Efficiency** | _[VA / Lead Time × 100]_ % |

#### Identified Constraints

| Constraint | Location | Root Cause | Proposed Action |
|:---|:---|:---|:---|
| _[制約1]_ | _[場所]_ | _[原因]_ | _[対策]_ |

#### DORA Metrics (Current)

| Metric | Current | Target |
|:---|:---|:---|
| Deployment Frequency | _[頻度]_ | _[目標]_ |
| Lead Time for Changes | _[時間]_ | _[目標]_ |
| MTTR | _[時間]_ | _[目標]_ |
| Change Failure Rate | _[%]_ | _[目標]_ |

### A4. Current Business Landscape (Wardley Map)

#### Users & User Needs

| User | User Needs |
|:---|:---|
| _[User 1]_ | _[Need 1, Need 2, ...]_ |
| _[User 2]_ | _[Need 1, Need 2, ...]_ |

#### Value Chain Components

| Component | Depends On | Visibility | Evolution Stage | Notes |
|:---|:---|:---|:---|:---|
| _[Component 1]_ | _[依存先]_ | High/Med/Low | Genesis/Custom/Product/Commodity | _[備考]_ |

#### Efficiency Gaps

| Component | Current Stage | Potential Stage | Action |
|:---|:---|:---|:---|
| _[Component]_ | _[現在]_ | _[移行先]_ | _[アクション]_ |

### A5. Problem Space Categorization

| Domain Area | Subdomain Type | Rationale | Investment Decision |
|:---|:---|:---|:---|
| _[領域1]_ | Core / Supporting / Generic | _[根拠]_ | Build / Buy / Outsource |

---

## Part B: To-Be Design

### B1. Modularized Solution Space

#### Bounded Contexts

| BC Name | Subdomain Type | Evolution Stage | Key Domain Events | Ubiquitous Language Terms |
|:---|:---|:---|:---|:---|
| _[BC 1]_ | _[Type]_ | _[Stage]_ | _[Events]_ | _[Terms]_ |

#### Context Map

| Upstream BC | Pattern | Downstream BC | Pattern | Change Coupling | Risk |
|:---|:---|:---|:---|:---|:---|
| _[BC A]_ | OHS | _[BC B]_ | ACL | Low | Low |

### B2. Future Business Landscape

#### Strategic Investment Priorities

| Priority | BC / Component | Action | Rationale |
|:---|:---|:---|:---|
| 1 | _[Core BC]_ | Build in-house | _[差別化要因]_ |
| 2 | _[Generic Component]_ | Migrate to managed service | _[効率ギャップ解消]_ |

#### Efficiency Gap Resolution

| Component | From | To | Expected Benefit |
|:---|:---|:---|:---|
| _[Component]_ | Custom-Built (on-prem) | Commodity (managed) | _[運用負荷 -X%, コスト -Y%]_ |

### B3. Future Team Organization

#### Team Constellation

| Team | Type | Owns (BCs/Components) | Size | Interaction Mode |
|:---|:---|:---|:---|:---|
| _[Team 1]_ | Stream-aligned | _[BC list]_ | _[5-9]_ | - |
| _[Platform]_ | Platform | _[Component list]_ | _[5-9]_ | XaaS to SA Teams |
| _[Enabling]_ | Enabling | - | _[3-5]_ | Facilitating to SA Teams |

#### Cognitive Load Verification

| Team | BCs Owned | Avg Evolution Stage | Estimated Cognitive Load | Status |
|:---|:---|:---|:---|:---|
| _[Team 1]_ | _[n]_ | _[Stage]_ | _[High/Med/Low]_ | _[OK/At Risk/Overloaded]_ |

#### Interaction Mode Evolution

| Phase | Teams | Mode | Duration | Trigger to Next Phase |
|:---|:---|:---|:---|:---|
| Phase 1 | SA Team 1 ↔ Platform | Collaboration | 4-8 weeks | Platform can provide XaaS |
| Phase 2 | SA Team 1 ← Platform | XaaS | Ongoing | - |

### B4. Transition Roadmap

#### Phase Plan

| Phase | Timeframe | Key Actions | Success Criteria | Risks |
|:---|:---|:---|:---|:---|
| 1: Foundation | _[期間]_ | _[アクション]_ | _[基準]_ | _[リスク]_ |
| 2: First Stream | _[期間]_ | _[アクション]_ | _[基準]_ | _[リスク]_ |
| 3: Expand | _[期間]_ | _[アクション]_ | _[基準]_ | _[リスク]_ |
| 4: Optimize | _[期間]_ | _[アクション]_ | _[基準]_ | _[リスク]_ |

#### Blocker Resolution Tracking

| Original Blocker | Phase Addressed | Status | New Challenges |
|:---|:---|:---|:---|
| _[Blocker 1]_ | _[Phase]_ | Resolved / In Progress / New | _[新たな課題]_ |

---

## Quality Checklist

- [ ] Purpose が明確に定義されている
- [ ] 全チームの現状が記述されている
- [ ] フロー阻害要因が具体的に特定されている
- [ ] Wardley Map のアンカー（ユーザー・ニーズ）が定義されている
- [ ] 全 Subdomain が Core/Supporting/Generic に分類されている
- [ ] BC が設計され Context Map が作成されている
- [ ] 将来チーム構成が Team Topologies に沿っている
- [ ] 認知負荷が検証されている
- [ ] インクリメンタルな移行計画がある
- [ ] Big-bang アプローチを避けている
