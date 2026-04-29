# System 2 Modeling: Interoperability & Design Decisions

## System 2 Role
**Alerta Temprana y Notificación Masiva** — Early Warning & Mass Notification system that:
- Ingests sensor events from **S1** (Data Acquisition) + manual reports from **S5** (C4I)
- Processes rules/correlations to generate alerts
- Distributes alerts to **S4** (Personnel), public, and external agencies via multiple channels

---

## Critical Interoperability Points

### 1. **Input Sources (Inbound Connectors)**

#### From S1: Sensor Events (ASYNC - Kafka/AMQP)
- **Decision**: Use **Event Broker** (Kafka) as single source of truth
- **What to model**:
  - Topic subscriptions: `sensor-events`, `manual-reports`
  - Protocol: AMQP (from S1 architecture)
  - Component: `Event_Broker` (communication tier)
  - Make it **critical availability** (realtime performance)
  - Add circuit breaker for resilience

#### From S5: Manual Reports + Feedback (REST - Bidirectional)
- **Decision**: Use **API Gateway** for REST endpoints
- **What to model**:
  - API Gateway endpoint (communication tier)
  - Bidirectional data_stream connector to S5
  - Protocol: REST/gRPC
  - Support operational feedback loops (alerts → validation → rules update)

---

### 2. **Core Processing Pipeline (Internals)**

Model as **Pipe-and-Filter** (sequential rule engine):
```
Event Normalizer → Spatio-Temporal Correlator → Rules Evaluator → Decision Maker
     ↓                      ↓                         ↓               ↓
  Normalize          Correlate events          Query rules cache   Create alerts
```

**What to model**:
- Each stage = `microservice` component (logic tier)
- **Cache (Redis)**: Distributed cache for rules/templates (data tier, `critical` availability)
- **Rules Repository**: Persistent rules storage (data tier, `standard` availability)
- Use `dependency` connectors between stages (RequestResponse style)

**Critical Decision**: 
- Rules must be **loadable/refreshable** without restart (Redis cache + repository pattern)
- Model Redis as separate component with high availability (2+ replicas)

---

### 3. **Output/Dispatch (Outbound Connectors)**

#### To S4: Operative Orders (ASYNC - Kafka/TCP)
- **Decision**: Use **Event Broker** to fan out alerts as control_command events
- **What to model**:
  - Connector type: `control_command` (not event_notification — S4 acts on these)
  - Protocol: AMQP (consistent with S1 protocol)
  - Availability: `critical` (operational orders can't be lost)

#### To Public & Agencies: Multi-Channel Dispatch
- **Decision**: Fan-out dispatcher + scalable worker pool per channel
- **What to model**:
  - `Dispatcher` component: queues alerts by channel/region (logic tier)
  - Worker components (4 types):
    - `SMS_Worker`: SMS/Cell-Broadcast (communication tier)
    - `Mobile_Worker`: Push notifications (communication tier)
    - `Radio_Worker`: Radio/TV (EAS/CAP) (communication tier)
    - `Official_Worker`: Official channels (communication tier)
  - Each worker: `microservice` with high availability (scalable replicas)
  - Model connectivity to external systems as `external_agency` components
  - Connector type: `data_stream` (unidirectional delivery)

#### Delivery Monitoring
- **Decision**: Separate `Delivery_Monitor` microservice for ACK tracking
- **What to model**:
  - Tracks delivery status per channel
  - Aggregates metrics back to alert system
  - Database: `Delivery_Metrics_DB` (audit + compliance)

---

## Architectural Patterns to Model

### A. Resilience & Fault Tolerance

| Pattern | Component | How to Model |
|---------|-----------|--------------|
| Circuit Breaker | API Gateway | Property: `availability = critical` |
| Distributed Cache | Redis | Property: `min_replicas = 2` |
| Message Queue Buffering | Event Broker | Property: `availability = critical` |
| Dead Letter Queue | Alert Manager | Implicit in historical DB |
| Graceful Degradation | Workers | Property: `recoverability = fast` |

### B. Data & State Management

| Item | Decision | How to Model |
|------|----------|--------------|
| **Alert History** | Persistent DB (audit trail) | `Alert_History_DB` database component |
| **Rules Cache** | Redis TTL + periodic refresh | Cache component + dependency to repo |
| **i18n Templates** | Template Service (separate) | `Template_Service` microservice |
| **Deduplication State** | In-memory + DB fallback | Part of Alert Manager logic |

### C. Scaling & Performance

- **Workers are scalable** → Property: `min_replicas = 1, max_replicas = N` per channel
- **Correlator is CPU-intensive** → Property: `cpu_limit = "2000m"` (example)
- **Normalizer is I/O-heavy** → Use async pipes between stages

---

## Connector Patterns (How to Connect S2 ↔ Other Systems)

### S1 → S2: Sensor Events
```
Subsystem S1:
  connector event_notification publisher -> S2.Event_Broker
    { protocol = AMQP, style = Pub/Sub, encrypted = true }
```

### S2 → S4: Operative Orders
```
Subsystem S2:
  connector control_command Alert_Manager -> S4.BrokerIn
    { protocol = AMQP, style = MessageQueue, encrypted = true }
```

### S5 ↔ S2: Manual Reports (Bidirectional)
```
Subsystem S2:
  connector data_stream API_Gateway -> S5.C4I_Interface
    { protocol = REST, style = RequestResponse, encrypted = true }
```

### S2 → External: Multi-Channel Delivery
```
Subsystem S2:
  connector data_stream SMS_Worker -> externalSystems.PublicNetwork
    { protocol = Http, style = RequestResponse, encrypted = true }
```

---

## Key Modeling Decisions

### **Decision 1: Message Broker Technology**
- **Choose**: Kafka (shown in design)
- **Why**: Durable, high-throughput, multi-consumer pub/sub
- **Model as**: `Event_Broker` component with properties:
  - `availability = critical`
  - `protocol = AMQP`
  - `min_replicas = 3` (for prod)

### **Decision 2: Rules Engine Architecture**
- **Choose**: Pipe-and-filter (not monolithic rules engine)
- **Why**: Separates concerns, allows independent scaling
- **Model as**: 4 sequential microservices with data_stream connectors

### **Decision 3: Distributed Cache Strategy**
- **Choose**: Redis for rules/templates
- **Why**: Fast cache, distributed, TTL support, refresh capability
- **Model as**: Separate `Cache_Distribuido` component with high availability

### **Decision 4: Worker Pool Pattern**
- **Choose**: Dispatcher + scalable workers per channel
- **Why**: Channels have different throughput/reliability needs
- **Model as**: 1 Dispatcher (logic) + 4 Worker microservices (communication)

### **Decision 5: Bidirectional Flow with S5**
- **Choose**: REST API Gateway (not async)
- **Why**: C4I needs synchronous feedback (operator validation, rules feedback)
- **Model as**: API Gateway with bidirectional data_stream

---

## Properties to Define Per Component

### Event Broker (Critical Path)
```
availability = critical
recoverability = fast
performance = realtime
security = internal
min_replicas = 3
encrypted = true
```

### Rules Evaluator (Compute-Intensive)
```
availability = high
performance = realtime
cpu_limit = "2000m"
auth = token
security = restricted
```

### Workers (Scalable)
```
availability = high
performance = interactive
min_replicas = 1
max_replicas = 10
recoverability = fast
```

### Databases
```
availability = high (Alert_History_DB)
recoverability = fast
security = restricted
```

---

## Questions to Resolve Before Modeling

1. **How are rules updated?** (Runtime reloading from S5 via API?)
2. **What's the SLA for alert delivery?** (Affects worker availability/replicas)
3. **Must S4 acknowledge receipt of operative orders?** (Affects connector bidirectionality)
4. **How many geographic regions?** (Affects dispatcher queue granularity)
5. **Fallback if Kafka fails?** (Direct REST? Circuit breaker pattern?)
6. **Who manages templates and i18n?** (S5 C4I or embedded in S2?)

---

## Next Steps for Modeling

1. **Start with cross-connectors** between S1 ↔ S2, S2 ↔ S4, S2 ↔ S5
2. **Define Event_Broker** as the hub (Kafka, critical availability)
3. **Model the pipe-and-filter chain** (4 microservices)
4. **Add the dispatcher + 4 workers**
5. **Define all database components** (Alert_History, Rules_Repo, Cache)
6. **Validate against S1, S4, S5 models** for protocol/availability compatibility
