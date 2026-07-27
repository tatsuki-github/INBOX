# Architecture Styles Reference

> Source: Fundamentals of Software Architecture, 2nd Edition (Mark Richards & Neal Ford, O'Reilly 2025)
> Progressive Disclosure: Step 4（スタイル選定）で参照する詳細比較資料

---

## Style Characteristics Rating (1-5 Stars)

| Characteristic | Layered | Modular Monolith | Pipeline | Microkernel | Service-Based | Event-Driven | Space-Based | Microservices |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Partitioning Type** | Technical | Domain | Data flow | Core+Plugin | Domain | Event | Processing unit | Bounded context |
| **Quanta** | 1 | 1 | 1 | 1 | 1-few | Many | Many | Many |
| **Deployability** | 1 | 2 | 2 | 2 | 4 | 4 | 3 | 5 |
| **Elasticity** | 1 | 1 | 1 | 1 | 2 | 4 | 5 | 5 |
| **Evolutionary** | 1 | 2 | 2 | 3 | 3 | 4 | 3 | 5 |
| **Fault Tolerance** | 1 | 1 | 1 | 1 | 4 | 5 | 3 | 5 |
| **Modularity** | 1 | 3 | 3 | 3 | 4 | 4 | 3 | 5 |
| **Overall Cost** | 5 | 4 | 5 | 4 | 3 | 2 | 2 | 1 |
| **Performance** | 3 | 3 | 2 | 3 | 3 | 5 | 5 | 3 |
| **Reliability** | 3 | 3 | 3 | 3 | 4 | 3 | 3 | 4 |
| **Scalability** | 1 | 1 | 1 | 1 | 3 | 5 | 5 | 5 |
| **Simplicity** | 5 | 4 | 5 | 4 | 3 | 2 | 1 | 1 |
| **Testability** | 2 | 3 | 3 | 3 | 4 | 3 | 2 | 4 |

> Note: Ratings are approximate generalizations. Actual characteristics depend on implementation details.

---

## Detailed Style Profiles

### 1. Layered Architecture

**Topology**: Horizontal technical layers (Presentation → Business → Persistence → Database)

**Key Concepts**:
- Layers of isolation: closed layers enforce separation; open layers allow bypass
- Architecture Sinkhole antipattern: requests pass through layers with no transformation
- Rule of thumb: if >20% of requests are sinkholes, consider restructuring

**When to Use**:
- Small, simple applications or websites
- Very tight budget and time constraints
- Starting point when final architecture is undetermined

**When Not to Use**:
- Large applications (characteristics degrade with size)
- High scalability/elasticity requirements
- Systems needing high deployability

**Data Topology**: Single shared database (monolithic)

**Cloud Considerations**: Limited cloud benefit; can be deployed as a container but does not leverage cloud-native features

---

### 2. Modular Monolith

**Topology**: Domain-partitioned modules within a single deployment unit

**Key Concepts**:
- Domain modules replace technical layers as the primary structural unit
- Inter-module communication via function calls, shared data, or internal events
- Facilitates future migration to distributed architecture

**When to Use**:
- Medium-complexity applications with clear domain boundaries
- Teams planning eventual migration to distributed architecture
- When monolith simplicity is desired but domain separation is important

**When Not to Use**:
- High scalability/elasticity requirements per domain
- Independent deployment requirements
- Very large teams needing independent release cycles

**Data Topology**: Shared database with logical separation by domain (or schema-per-module)

**Cloud Considerations**: Can be containerized; benefits from cloud CI/CD but does not leverage fine-grained cloud scaling

---

### 3. Pipeline Architecture

**Topology**: Unidirectional data flow through pipes and filters

**Key Concepts**:
- **Filters**: Producer (source), Transformer (modify data), Tester (validate/filter), Consumer (sink)
- **Pipes**: Unidirectional, point-to-point connections between filters
- Pure functional decomposition of data processing

**When to Use**:
- ETL/ELT pipelines
- Data processing and transformation workflows
- Simple orchestration of sequential operations

**When Not to Use**:
- Interactive applications
- Bidirectional communication requirements
- Complex branching workflows

**Data Topology**: Data flows through the pipeline; typically file or stream-based

---

### 4. Microkernel (Plug-in) Architecture

**Topology**: Core system + extensible plug-in components

**Key Concepts**:
- **Core system**: Minimal essential functionality; stable and well-defined
- **Plug-in components**: Independent extensions registered via a registry
- **Contracts**: Define the interface between core and plug-ins
- Spectrum of "microkern-ality": ranges from monolithic core to highly modular

**When to Use**:
- Product-based applications requiring customization (IDE, browsers, CMS)
- Business rules that vary per client/region/context
- Systems needing runtime extensibility

**When Not to Use**:
- High scalability requirements
- Systems with many inter-plugin dependencies
- Distributed deployment requirements

**Data Topology**: Core database + optional plug-in databases

---

### 5. Service-Based Architecture

**Topology**: Coarse-grained domain services (typically 4-12), optional shared database

**Key Concepts**:
- "Pragmatic middle ground" between monolith and microservices
- Services are domain-scoped but larger than microservices (4-12 services typical)
- Can share a database or have per-service databases
- API gateway for external access; internal communication typically synchronous

**When to Use**:
- Domain-driven applications needing moderate scalability
- Teams transitioning from monolith to distributed
- When microservices complexity is not justified

**When Not to Use**:
- Requirements demanding fine-grained independent scaling
- Very high elasticity requirements
- Large-scale event-driven processing

**Data Topology**: Shared database (common) or partitioned per service

---

### 6. Event-Driven Architecture

**Topology**: Event processors connected by brokers (choreography) or mediators (orchestration)

**Key Concepts**:
- **Broker topology**: Decentralized, event processors subscribe to events. High responsiveness but no central control
- **Mediator topology**: Central event mediator orchestrates workflow. Control but potential bottleneck
- Events vs Messages: events = notification of something that happened; messages = commands to do something
- Error handling: async error channels, compensating transactions
- Data loss prevention: persistent message queues, client acknowledge mode

**When to Use**:
- High-throughput asynchronous processing
- Complex event workflows with many participants
- Real-time data processing and reactions
- Systems requiring high fault tolerance

**When Not to Use**:
- Simple CRUD applications
- Request-response dominant workflows
- Strong transactional consistency requirements
- Debugging and testing simplicity is critical

**Data Topology**: Domain database (per processor) or dedicated data per event processor

---

### 7. Space-Based Architecture

**Topology**: Processing units with in-memory data grids, data pumps, and data writers/readers

**Key Concepts**:
- Removes the database as a bottleneck by using in-memory data grids
- Processing units contain application logic + in-memory data cache
- Data replication between processing units for fault tolerance
- Data pumps synchronize in-memory data to persistent storage asynchronously
- Data collisions: must handle concurrent updates to the same data

**When to Use**:
- Extreme scalability with variable/spiky load patterns
- Ticketing systems, auctions, social media feeds
- When database becomes the primary bottleneck

**When Not to Use**:
- Low concurrency applications
- Systems requiring strong relational data integrity
- Tight budget constraints (infrastructure costs are high)
- Large amounts of data that cannot fit in memory

**Data Topology**: In-memory data grid + asynchronous database synchronization

---

### 8. Orchestration-Driven SOA (Service-Oriented Architecture)

**Topology**: Enterprise Service Bus (ESB) with taxonomy-driven services

**Key Concepts**:
- Taxonomy: Business Services → Enterprise Services → Application Services → Infrastructure Services
- Enterprise-wide reuse via shared services and ESB
- Heavy governance and standardization

**Status**: **Largely deprecated**. The pursuit of maximum reuse led to excessive coupling and reduced agility.

**Lesson Learned**: Reuse is a trade-off. Maximizing reuse often conflicts with agility, deployability, and team autonomy.

---

### 9. Microservices Architecture

**Topology**: Fine-grained services based on bounded contexts, each with independent data

**Key Concepts**:
- **Bounded context**: Each service owns its domain model and data
- **Data isolation**: Each service has its own database (no shared databases)
- **Sidecar pattern**: Attach operational concerns (logging, security) as a companion process
- **Service mesh**: Infrastructure layer handling service-to-service communication
- **Communication**: Choreography (events) or orchestration (saga pattern)
- **Saga pattern**: Manage distributed transactions through compensating actions

**When to Use**:
- Maximum agility and independent deployment
- Fine-grained scalability per service
- Large teams needing independent release cycles
- Systems where domain boundaries are well-defined

**When Not to Use**:
- Small teams (< 5-10 developers)
- Simple domains with low complexity
- Tight budgets (operational overhead is significant)
- Systems requiring strong transactional consistency across services

**Data Topology**: Database per service (strict data isolation)

---

## Style Selection Quick Reference

```
            Low Complexity                    High Complexity
            Low Scale                         High Scale
            Small Team                        Large Team
            ────────────────────────────────────────────►

Monolithic  Layered  →  Modular   →  Pipeline  →  Microkernel
                        Monolith

Distributed           Service-   →  Event-     →  Microservices
                      Based          Driven
                                       ↕
                                  Space-Based
```

---

## 8 Fallacies of Distributed Computing

Any distributed architecture must account for these realities:

| # | Fallacy | Impact |
|:---|:---|:---|
| 1 | The network is reliable | Timeouts, retries, circuit breakers needed |
| 2 | Latency is zero | Inter-service calls add latency; minimize chattiness |
| 3 | Bandwidth is infinite | Payload size matters; use appropriate serialization |
| 4 | The network is secure | Service-to-service authentication, encryption |
| 5 | The topology never changes | Service discovery, load balancing must be dynamic |
| 6 | There is only one administrator | Multiple teams manage different parts |
| 7 | Transport cost is zero | Serialization, deserialization have CPU/memory cost |
| 8 | The network is homogeneous | Different protocols, formats across services |
