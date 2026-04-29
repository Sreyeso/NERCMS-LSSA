# System 2: Minimal-Impact Design Decisions

## Core Requirement (from Scenario)
**System 2 must:**
1. Detect S5 unavailability
2. Bypass S5 → send notifications directly to S4 (personnel) & S3 (logistics)
3. Operate autonomously: evaluate events + issue alerts without S5 coordination
4. Resume coordination with S5 once it recovers
5. Never lose alerts or events (at-least-once semantics)

---

## Decision 1: Protocol Consistency (AMQP for All Internal Async)

### The Problem
- S1 → S2: AMQP ✓
- S2 → S4: Tcp (from cross-connectors) ✗

### The Least Impactful Solution
**Use AMQP for both S1 input AND S2 output to S4.** 

Why minimal impact:
- S4 already expects AMQP input (see cross-connectors: S5 → S4 uses AMQP)
- Single broker technology (easier ops, one expertise needed)
- Already in S1's model (no new tech debt)
- S4 can accept alerts as `event_notification` (not just commands)

### How to Model
```
// In cross-connectors/model.arch
connector event_notification S2_early_warning_notification.Broker_Out -> S4_personnel_orchestration.BrokerIn {
    style = MessageQueue
    protocol = AMQP      // Changed from Tcp
    encrypted = true
    timeout_ms = 1000
}

// S2 → S3 (direct, when S5 unavailable)
connector event_notification S2_early_warning_notification.Broker_Out -> S3_supply_resource_logistics {
    style = MessageQueue
    protocol = AMQP
    encrypted = true
    timeout_ms = 1000
}
```

**Result**: Single AMQP broker, no dual-broker complexity. S2 publishes once; AMQP routes to both S4 and S3.

---

## Decision 2: S5 Availability Detection (Lightweight)

### The Requirement
S2 must detect when S5 is down and switch to autonomous mode.

### The Least Impactful Solution
**Add a `Health_Check_Listener` component (minimal)** that monitors:
- REST API health endpoint on S5
- Timeout on S2 → S5 REST requests
- Falls back after N consecutive failures (configurable, e.g., 3)

### How to Model
```
component S5_Health_Monitor : communication microservice {
    availability = high
    performance = realtime
    recoverability = fast
    auth = token
    security = internal
    port = 6501
}

connector dependency S5_Health_Monitor -> S5_central_command_core {
    style = RequestResponse
    protocol = REST
    timeout_ms = 500
}
```

**Why minimal impact:**
- Passive monitoring only (doesn't change S2 logic)
- Single dedicated component (easy to test/isolate)
- Sets a flag: `s5_available = true/false` consumed by other components
- No extra data storage needed (in-memory flag)

---

## Decision 3: Autonomous Rules Engine (Strengthen, Don't Rebuild)

### The Requirement
Rules engine must make **complete decisions** based on thresholds, not query S5.

### The Least Impactful Solution
**Enhance the existing Rules Evaluator with:**
1. **Local threshold evaluation** (already have: rules in Redis cache)
2. **Severity levels** (add to each rule: LOW/MEDIUM/HIGH/CRITICAL)
3. **Default actions** (if S5 unavailable, fire alert with severity-based action)

### Current Architecture (Correct)
```
Event_Normalizer → Spatio_Temporal_Correlator → Rules_Evaluator → Decision_Maker
```

### Enhanced (Minimal Change)
Rules_Evaluator now includes:
- Threshold matching ✓ (already there)
- Severity calculation (add this)
- S5 availability check (from Health_Monitor flag)
- **IF S5_available=false THEN use default action ELSE query S5 for override**

### How to Model
```
component Rules_Evaluator : logic microservice {
    availability = critical
    performance = realtime
    recoverability = fast
    auth = token
    security = internal
    port = 6502
    tech = "rule-engine (Drools/Easy-Rules)" // Support severity levels
}

// Add dependency: Rules_Evaluator reads S5_Health_Monitor flag
connector dependency Rules_Evaluator -> S5_Health_Monitor {
    style = RequestResponse  // Pull latest health status
    protocol = REST
    timeout_ms = 100       // Fast, cached
}
```

**Why minimal impact:**
- No architectural change (same pipe-and-filter)
- Uses existing Redis cache (no new storage)
- Fallback logic is localized to one component
- Can be toggled (S5 available → use S5 override, S5 down → use local decision)

---

## Decision 4: Direct S2 → S4 / S2 → S3 Communication

### The Requirement
When S5 is down, S2 must send alerts directly to S4 (personnel) and S3 (logistics).

### Current State
- S2 → S5 (REST, S5 orchestrates everything)
- S5 → S4, S5 → S3

### The Least Impactful Solution
**Add direct AMQP connections from S2 to S4 and S3** (use same broker as S1 input):

```
component Broker_Central : communication event_broker {
    tech = "AMQP (Kafka/RabbitMQ cluster)"
    availability = critical
    recoverability = fast
    min_replicas = 3
    port = 6672
}

// S1 already publishes to this
connector event_notification S1_data_acquisition_edge.publisher -> Broker_Central {
    style = Pub/Sub
    protocol = AMQP
}

// S2 consumes from this
connector event_notification Broker_Central -> S2_early_warning_notification.Broker_In {
    style = Pub/Sub
    protocol = AMQP
}

// S2 publishes back to this (alerts + commands)
connector event_notification S2_early_warning_notification.Broker_Out -> Broker_Central {
    style = Pub/Sub
    protocol = AMQP
}

// S4 subscribes
connector event_notification Broker_Central -> S4_personnel_orchestration.BrokerIn {
    style = Pub/Sub
    protocol = AMQP
}

// S3 subscribes (new connection)
connector event_notification Broker_Central -> S3_supply_resource_logistics {
    style = Pub/Sub
    protocol = AMQP
}
```

**Message Routing (by topic):**
- `sensor-events`: S1 → Broker (existing)
- `alerts-critical`: S2 → Broker → S4 always
- `alerts-resource-needed`: S2 → Broker → S3 always
- S5 is optional: consumes topics for audit/approval, but doesn't block delivery

**Why minimal impact:**
- Single broker (no operational complexity)
- Pub/Sub naturally decouples (S4/S3 don't care if S2 or S5 published)
- S5 can still subscribe to audit/approve (asynchronously)
- No new components needed (reuse existing S2 broker model)

---

## Decision 5: Event Buffering for S5 Sync (Lightweight)

### The Requirement
When S5 recovers, send sync report of actions taken during downtime.

### The Least Impactful Solution
**Use Alert_History_DB (already exists) as the audit trail:**

```
component Alert_History_DB : data database {
    availability = high
    recoverability = fast
    performance = interactive
    auth = password
    security = restricted
    port = 6434
    tech = "PostgreSQL"
}
```

Every alert gets logged:
```
{
  alert_id: UUID,
  timestamp: ISO8601,
  sensor_events: [list],
  rule_applied: string,
  severity: CRITICAL|HIGH|MEDIUM|LOW,
  dispatched_to: [S4, S3, channels],
  s5_available: boolean,  // Flag at time of alert
  s5_approval: null|approved|rejected,  // Filled in later
  synced: false  // Set true after S5 recovery sync
}
```

When S5 recovers:
1. S2 queries: `SELECT * FROM alerts WHERE synced=false AND s5_available=false`
2. Sends report to S5 (REST API call)
3. Updates: `UPDATE alerts SET synced=true`

**Why minimal impact:**
- No new storage (Alert_History_DB already modeled)
- Just add two columns to schema (`s5_available`, `synced`)
- No complex event replay (simple DB query)
- S5 gets clear audit trail of autonomous decisions

```
component Sync_Manager : logic microservice {
    availability = standard
    performance = batch
    recoverability = normal
    auth = token
    security = internal
    port = 6503
}

connector dependency Sync_Manager -> Alert_History_DB {
    style = RequestResponse
    protocol = REST  // Query unsync'd alerts
}

connector data_stream Sync_Manager -> S5_central_command_core {
    style = RequestResponse
    protocol = REST
    timeout_ms = 5000  // Slower, batch operation
}
```

**Why minimal impact:**
- Separate microservice (doesn't block alert processing)
- Batch operation (not realtime critical)
- Uses existing database (no new tech)

---

## Decision 6: Load Control & Backpressure

### The Requirement
Avoid saturation during notification peaks.

### The Least Impactful Solution
**Implement queue size limits + drop low-priority alerts** (in Alert_Manager):

```
component Alert_Manager : logic microservice {
    availability = high
    performance = realtime
    recoverability = fast
    auth = token
    security = internal
    port = 6504
    // Queue config (via env vars or config file):
    // QUEUE_MAX_SIZE = 10000
    // DROP_POLICY = drop_lowest_priority_when_full
}
```

**Logic:**
- CRITICAL alerts: never drop, buffer indefinitely
- HIGH: buffer up to 5000, drop if queue full
- MEDIUM/LOW: buffer up to 1000 each, drop if queue full

**Why minimal impact:**
- Single component change (Alert_Manager)
- No new architecture (queuing already exists)
- Preserves critical alerts (most important in emergencies)
- Graceful degradation (lower priority dropped, not system crash)

---

## Summary: Least-Impact Design

| Gap | Decision | Impact | Effort |
|-----|----------|--------|--------|
| **Protocol mismatch** | Use AMQP for S1→S2→S4/S3 | Removes dual-broker complexity | Low (config change) |
| **S5 detection** | Add lightweight Health_Monitor | Passive health check only | Low (1 microservice) |
| **Autonomous rules** | Add severity levels + fallback logic | Enhance Rules_Evaluator, no rewrite | Medium (logic change) |
| **Direct S2→S4/S3** | Use same AMQP broker, Pub/Sub routing | No new broker, natural decoupling | Low (topic routing) |
| **S5 sync** | Query Alert_History_DB on S5 recovery | Lightweight Sync_Manager | Low (batch queries) |
| **Backpressure** | Queue size limits + drop policy | Config-based load shedding | Low (policy logic) |

**Total new components:** 2 (Health_Monitor, Sync_Manager)
**Total modified components:** 2 (Rules_Evaluator, Alert_Manager)
**New infrastructure:** None (reuse AMQP, PostgreSQL)

---

## Resulting S2 Model Structure

```
subsystem S2_early_warning_notification {
    // === Communication ===
    component API_Gateway : communication api_gateway {
        tech = "REST/gRPC"
        availability = high
        security = internal
    }
    
    component Broker_In : communication event_broker {
        tech = "AMQP (Kafka/RabbitMQ)"
        availability = critical
        min_replicas = 3
    }
    
    component Broker_Out : communication event_broker {
        tech = "AMQP (shared with Broker_In)"
        availability = critical
    }
    
    component S5_Health_Monitor : communication microservice {
        availability = high
    }
    
    // === Logic ===
    component Event_Normalizer : logic microservice
    component Spatio_Temporal_Correlator : logic microservice
    component Rules_Evaluator : logic microservice {
        // Decides autonomously if S5 unavailable
    }
    component Decision_Maker : logic microservice
    component Alert_Manager : logic microservice {
        // Handles backpressure + prioritization
    }
    component Dispatcher : logic microservice
    component Sync_Manager : logic microservice
    
    // === Channel Workers ===
    component SMS_Worker : communication microservice { min_replicas = 2 }
    component Mobile_Worker : communication microservice { min_replicas = 2 }
    component Radio_Worker : communication microservice { min_replicas = 1 }
    component Official_Worker : communication microservice { min_replicas = 1 }
    
    // === Data ===
    component Alert_History_DB : data database { tech = "PostgreSQL" }
    component Rules_Repository : data database { tech = "PostgreSQL" }
    component Redis_Cache : data bucket { tech = "Redis", min_replicas = 2 }
    component Template_Service : logic microservice
    
    // === Connectors (Internal) ===
    [pipe-and-filter: Normalizer → Correlator → Evaluator → Decision → Manager]
}
```

---

## Cross-System Connectors (Revised)

```
// S1 → S2: Sensor Events (existing, unchanged)
connector event_notification S1_data_acquisition_edge.publisher -> S2_early_warning_notification.Broker_In {
    protocol = AMQP
    style = Pub/Sub
    timeout_ms = 500
    encrypted = true
}

// S2 → S4: Alerts (autonomous + coordinated)
connector event_notification S2_early_warning_notification.Broker_Out -> S4_personnel_orchestration.BrokerIn {
    protocol = AMQP    // Changed from Tcp
    style = Pub/Sub
    timeout_ms = 1000
    encrypted = true
}

// S2 → S3: Resource Requests (autonomous + coordinated)
connector event_notification S2_early_warning_notification.Broker_Out -> S3_supply_resource_logistics {
    protocol = AMQP
    style = Pub/Sub
    timeout_ms = 1000
    encrypted = true
}

// S2 ↔ S5: Manual Reports + Feedback (REST, optional if S5 down)
connector data_stream S5_central_command_core -> S2_early_warning_notification.API_Gateway {
    protocol = REST
    style = RequestResponse
    timeout_ms = 2000
    encrypted = true
}

connector data_stream S2_early_warning_notification.API_Gateway -> S5_central_command_core {
    protocol = REST
    style = RequestResponse
    timeout_ms = 2000
    encrypted = true
}

// S2 → S1: Historical Data Queries (optional, batch)
connector data_stream S2_early_warning_notification -> S1_data_acquisition_edge.interface {
    protocol = REST
    style = RequestResponse
    timeout_ms = 3000
    encrypted = true
}
```

---

## Quality Attributes Achieved

| Attribute | How | Evidence |
|-----------|-----|----------|
| **Availability** | AMQP broker + alert buffering + autonomous rules | Works even if S5 at 50% |
| **Reliability** | at-least-once semantics (broker + DB logging) | No alerts lost |
| **Performance** | Realtime rules engine + async dispatch | <100ms alert to S4/S3 |
| **Resilience** | Graceful degradation + load shedding | Degrades (lowers priority) vs crashes |
| **Scalability** | Workers scale independently; queue-based | Handles peak load via buffering |
| **Auditability** | Alert_History_DB + sync report | S5 sees autonomous decisions post-recovery |

---

## Next Steps

1. **Update cross-connectors/model.arch** with new S2↔S4, S2↔S3 connectors
2. **Create team-2b/model.arch** (System 2 internal components)
3. **Define event schemas:**
   - `sensor_event`: {sensor_id, timestamp, value, quality, location}
   - `alert`: {id, severity, region, action_required, timestamp}
   - `manual_report`: {operator_id, type, location, override}
4. **Model Database schema**: Alert_History_DB with `s5_available` + `synced` columns
5. **Validate with S4 & S3 teams:** Do they accept AMQP direct alerts? What format?
