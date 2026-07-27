# ADR Template & Guide

> Source: Fundamentals of Software Architecture, 2nd Edition (Mark Richards & Neal Ford, O'Reilly 2025)
> Progressive Disclosure: Step 6（ADR 生成）で参照するテンプレートとガイド

---

## ADR Template

```markdown
# ADR-NNN: [Short descriptive title]

## Status

[Proposed | Accepted | Superseded by ADR-NNN | RFC (deadline: YYYY-MM-DD)]

## Context

[Describe the forces at play. What situation is forcing this decision?
 Include the specific area of the architecture affected.
 List the alternatives being considered, concisely.]

## Decision

[State the decision in affirmative, commanding voice.
 "We will use..." NOT "I think we should..."
 Include the full justification -- WHY this decision was made.
 This is the most important section.]

## Consequences

### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Trade-off 1]
- [Trade-off 2]

### Risks
- [Risk and mitigation strategy]

## Compliance

[How will this decision be governed and enforced?]
- [ ] Manual: [Code review, architecture review, etc.]
- [ ] Automated: [Fitness function, CI/CD check, etc.]

## Alternatives

### Alternative 1: [Name]
- **Pros**: [advantages]
- **Cons**: [disadvantages]
- **Rejected because**: [reason]

### Alternative 2: [Name]
- **Pros**: [advantages]
- **Cons**: [disadvantages]
- **Rejected because**: [reason]

## Notes

- **Author**: [name]
- **Approved by**: [name or governance body]
- **Date**: [YYYY-MM-DD]
- **Related ADRs**: [ADR-NNN, ADR-NNN]
```

---

## Section Guide

### Title

- Sequential number + short descriptive phrase
- Be specific: "42. Use of Async Messaging Between Order and Payment" (good)
- Avoid vague: "42. Communication Decision" (bad)

### Status

| Status | Meaning |
|:---|:---|
| **RFC** | Request for Comments -- open for feedback until deadline |
| **Proposed** | Needs approval from governance body |
| **Accepted** | Approved and ready for implementation |
| **Superseded by NNN** | Replaced by a newer ADR; retains historical context |

**Lifecycle**:
```
[RFC] → [Proposed] → [Accepted] → [Superseded by NNN]
                  └→ [Rejected]
```

**Superseded Example**:
```
ADR-42: Use of Async Messaging Between Order and Payment
Status: Superseded by ADR-68

ADR-68: Use of REST Between Order and Payment
Status: Accepted, supersedes ADR-42
```

### Context

- Describe the **forces** driving the decision
- Include the architectural area affected
- List alternatives **concisely** (detailed analysis goes in Alternatives section)
- Example: "The Order service must pass information to the Payment service. This could be done using REST or asynchronous messaging."

### Decision

- **Affirmative voice**: "We will use..." not "I think..."
- Focus on **WHY**, not just WHAT
- Justify the decision with trade-offs and business context
- This is the most valuable section of the ADR

### Consequences

- List **both** positive and negative impacts
- Include trade-offs explicitly
- Identify residual risks with mitigation strategies

### Compliance

- Specify **how** the decision will be enforced
- Prefer automated compliance (fitness functions) over manual
- Examples:
  - CI/CD pipeline check for cyclic dependencies
  - ArchUnit test for layer violations
  - Runtime monitoring for performance SLOs

### Alternatives

- Document at least 2 alternatives
- For each: Pros, Cons, and reason for rejection
- This prevents the "Groundhog Day" antipattern (revisiting the same decision)

### Notes

- Author, approver, date
- Links to related ADRs
- Links to supporting documentation

---

## Self-Approval Criteria

Three dimensions determine whether an architect can approve their own ADR:

| Dimension | Self-Approve | Escalate |
|:---|:---|:---|
| **Cost** | Within budget threshold (e.g., < $5,000 implementation cost) | Exceeds threshold |
| **Cross-team Impact** | No impact on other teams | Affects other teams or systems |
| **Security** | No security implications | Any security impact |

Establish these thresholds with your organization **before** creating ADRs.

---

## Decision Antipatterns to Avoid

| Antipattern | Symptom | Solution |
|:---|:---|:---|
| **Covering Your Assets** | Avoiding decisions, endless analysis | Decide at the "last responsible moment" |
| **Groundhog Day** | Same decisions revisited repeatedly | Use ADRs -- document context and rationale |
| **Email-Driven Architecture** | Decisions buried in email threads | ADRs as single source of truth; email for announcements only |
| **Out of Context** | Applying decisions from different contexts | ADR Context section forces contextual awareness |

---

## Example ADR

```markdown
# ADR-042: Use of Asynchronous Messaging Between Order and Payment Services

## Status

Accepted

## Context

The Order service must pass information to the Payment service to process
payments for orders being placed. This communication could use synchronous
REST calls or asynchronous messaging via a message broker.

The system currently handles ~500 orders/minute during peak hours, with
projected growth to 2,000 orders/minute within 12 months. Payment processing
takes 2-5 seconds per transaction.

## Decision

We will use asynchronous messaging (via Amazon SQS) between the Order and
Payment services.

**Justification**: Synchronous REST calls would create a blocking dependency
between Order and Payment, meaning users would wait 2-5 seconds for payment
processing to complete before seeing their order confirmation. Asynchronous
messaging decouples these services, allowing the Order service to return
immediately (reducing response time from ~3,100ms to ~25ms) while payment
is processed in the background.

This trade-off sacrifices immediate payment confirmation for improved user
experience and system resilience. Users will see payment status updates via
polling or WebSocket notifications.

## Consequences

### Positive
- Response time reduced from 3,100ms to 25ms
- Order and Payment services are decoupled (independent scaling and deployment)
- If Payment service is temporarily down, orders are queued (improved reliability)

### Negative
- Users do not get immediate payment confirmation (eventual consistency)
- Added complexity: message broker, dead-letter queue, retry logic
- Debugging is harder (no single request trace)

### Risks
- Message loss: Mitigated by using SQS with at-least-once delivery + idempotent payment processing
- Out-of-order processing: Mitigated by FIFO queue or order-level sequencing

## Compliance

- [ ] Automated: Integration test verifying message delivery and processing
- [ ] Automated: CloudWatch alarm for SQS queue depth > 1000
- [ ] Manual: Monthly review of dead-letter queue contents

## Alternatives

### Alternative 1: Synchronous REST
- **Pros**: Simpler implementation, immediate confirmation
- **Cons**: 3,100ms response time, tight coupling, cascading failures
- **Rejected because**: Does not meet our performance target (< 200ms response)
  and creates fragile coupling that will worsen as we scale

### Alternative 2: Event-Driven with Kafka
- **Pros**: Higher throughput, event replay, stream processing
- **Cons**: Higher operational complexity, higher cost, team has no Kafka experience
- **Rejected because**: SQS meets our throughput needs at lower operational cost
  and our team can adopt it faster

## Notes

- **Author**: Jane Smith, Lead Architect
- **Approved by**: Architecture Review Board
- **Date**: 2026-01-15
- **Related ADRs**: ADR-038 (Service Communication Strategy)
```

---

## Storage Best Practices

| Approach | Pros | Cons | Recommended |
|:---|:---|:---|:---:|
| **In the code repository** (e.g., `/docs/adr/`) | Version controlled, close to code, easy to find | May be overlooked in large repos | Yes |
| **Wiki** | Easy to browse, rich formatting | Disconnected from code, versioning issues | No |
| **Shared drive** | Accessible to non-developers | No version control, easy to lose | No |
| **ADR management tool** (adr-tools) | Automated numbering, cross-linking | Additional tooling dependency | Optional |

> **Recommendation**: Store ADRs in the code repository under `docs/adr/` or `architecture/decisions/`.
> This ensures they are version-controlled and reviewed alongside code changes.
