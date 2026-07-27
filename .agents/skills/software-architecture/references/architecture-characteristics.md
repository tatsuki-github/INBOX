# Architecture Characteristics (-ilities) Reference

> Source: Fundamentals of Software Architecture, 2nd Edition (Mark Richards & Neal Ford, O'Reilly 2025)
> Progressive Disclosure: Step 2（特性の抽出と優先順位付け）で参照する網羅リスト

---

## Definition

An **architecture characteristic** is a quality attribute that:
1. Specifies a **non-domain design consideration** (how, not what)
2. Influences some **structural aspect** of the architecture
3. Is **critical or important** to application success

---

## Operational Characteristics

System runtime behavior and capabilities.

| Characteristic | Definition | Measurement Examples |
|:---|:---|:---|
| **Availability** | Percentage of time the system is operational and accessible | Uptime % (99.9%, 99.99%), MTBF, MTTR |
| **Continuity** | Disaster recovery capability; ability to resume operations after failures | RTO (Recovery Time Objective), RPO (Recovery Point Objective) |
| **Performance** | System responsiveness under various conditions | Response time (p50, p95, p99), throughput (TPS), latency |
| **Recoverability** | Ability to restore the system to a working state after failure | Time to recover, backup frequency, restore success rate |
| **Reliability** | Probability of failure-free operation over a given period | MTBF, failure rate, error rate |
| **Robustness** | Ability to handle error and boundary conditions during operation | Graceful degradation under stress, error recovery |
| **Scalability** | Ability to handle increased load by adding resources | Max concurrent users, requests/sec at scale |
| **Elasticity** | Ability to dynamically scale up and down based on demand | Auto-scaling response time, scale-down efficiency |

---

## Structural Characteristics

Internal code quality and architecture structure.

| Characteristic | Definition | Measurement Examples |
|:---|:---|:---|
| **Configurability** | Ease with which end users can change software configuration | Number of configurable parameters, configuration UI |
| **Extensibility** | How well the architecture accommodates new functionality | Time to add a new feature type, plug-in support |
| **Installability** | Ease of installation on target platforms | Installation steps, automation level |
| **Leverageability / Reuse** | Extent to which common components can be shared | Number of shared components, duplication ratio |
| **Localization** | Support for multiple languages and regions | Number of supported locales, i18n coverage |
| **Maintainability** | Ease of applying changes and enhancements | Cyclomatic complexity, code churn, time to fix |
| **Portability** | Ability to run on multiple platforms | Number of supported platforms, abstraction level |
| **Upgradeability** | Ease and speed of upgrading to newer versions | Upgrade time, backward compatibility |

---

## Cloud Characteristics

Specific to cloud-based deployments.

| Characteristic | Definition | Measurement Examples |
|:---|:---|:---|
| **On-demand Scalability** | Cloud provider's ability to scale resources dynamically | Auto-scaling configuration, scaling speed |
| **On-demand Elasticity** | Flexibility as resource demands spike | Scale-up/down response time, cost efficiency |
| **Zone-based Availability** | Separation by computing zones for resilience | Number of availability zones, failover time |
| **Region-based Privacy** | Legal ability to store data per regional regulations | Supported regions, data residency compliance |

---

## Cross-Cutting Characteristics

Span multiple categories or defy easy categorization.

| Characteristic | Definition | Measurement Examples |
|:---|:---|:---|
| **Accessibility** | Usability for all users, including those with disabilities | WCAG compliance level, accessibility audit score |
| **Archivability** | Constraints around data archiving or deletion | Retention policy compliance, archive automation |
| **Authentication** | Verifying user identity | Auth method strength, MFA coverage |
| **Authorization** | Controlling access to specific functions/data | RBAC/ABAC coverage, permission granularity |
| **Legal** | Legislative constraints (GDPR, SOX, etc.) | Compliance audit results, regulatory coverage |
| **Privacy** | Encryption and hiding of transactions from internal personnel | Encryption coverage, data masking, audit logging |
| **Security** | Protection from unauthorized access | Vulnerability scan results, penetration test findings |
| **Supportability** | Level of technical support capability | Logging coverage, debuggability, monitoring depth |
| **Usability** | Effectiveness, efficiency, and satisfaction for end users | User task completion rate, SUS score |

---

## ISO 25010 Aligned Characteristics

Additional characteristics from the ISO standard:

| Characteristic | Definition |
|:---|:---|
| **Performance Efficiency** | Performance relative to resources used (time behavior, resource utilization, capacity) |
| **Compatibility** | Ability to exchange information with other systems (coexistence, interoperability) |
| **Functional Suitability** | Degree to which functions meet stated and implied needs |
| **Modifiability** | Ease of changing the system without introducing defects |

---

## Composite Characteristics

Some characteristics are composites of multiple underlying characteristics:

| Composite | Underlying Characteristics |
|:---|:---|
| **Agility** | Deployability + Testability + Maintainability |
| **Operability** | Availability + Reliability + Recoverability + Robustness |
| **DevOps-Readiness** | Deployability + Testability + Configurability + Supportability |

---

## Business-to-Characteristic Translation Guide

| Business Concern | Primary Characteristics | Secondary Characteristics |
|:---|:---|:---|
| Time to market | Agility, Deployability, Testability | Maintainability, Simplicity |
| Sustained user growth | Scalability, Elasticity | Performance, Availability |
| User satisfaction | Performance, Availability | Usability, Reliability |
| Cost reduction | Simplicity, Overall Cost | Maintainability |
| Competitive advantage | Agility, Extensibility | Evolutionary |
| Regulatory compliance | Security, Legal, Privacy | Archivability, Authorization |
| Global expansion | Localization, Zone-based Availability | Region-based Privacy |
| Merger/acquisition | Interoperability, Portability | Extensibility |
| 24/7 operations | Availability, Reliability | Recoverability, Robustness |
| High-frequency events | Performance, Elasticity | Scalability, Fault Tolerance |

---

## Prioritization Framework

### The "Fewest Possible" Principle

> Each architectural characteristic supported by the system adds complexity.
> Architects should strive to choose the **fewest** possible, not the most.

### Prioritization Process

1. **List** all candidate characteristics from business requirements
2. **Classify** as Explicit (stated in requirements) or Implicit (unstated but necessary)
3. **Score** each by business impact: High (3), Medium (2), Low (1)
4. **Select** the top 3-7 characteristics (never more than 7 primary)
5. **Validate** with stakeholders and document rationale

### Warning Signs of Over-Selection

- More than 7 primary characteristics selected
- All characteristics rated as "High" priority
- No clear distinction between "must-have" and "nice-to-have"
- Architecture becomes overly complex trying to satisfy all characteristics

---

## Implicit vs Explicit Checklist

### Always Implicit (verify these even if not in requirements)

- [ ] **Availability** -- What uptime percentage is acceptable?
- [ ] **Security** -- What authentication/authorization is needed?
- [ ] **Reliability** -- What is the acceptable failure rate?

### Often Implicit (check based on domain)

- [ ] **Performance** -- Are there latency requirements?
- [ ] **Scalability** -- Will load increase significantly?
- [ ] **Maintainability** -- How often will the system change?
- [ ] **Legal/Compliance** -- Are there regulatory requirements?
