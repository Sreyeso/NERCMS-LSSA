# System 2: Operational Modes Design (Simplified)

## Validation Against Scenario Document

Your proposal directly addresses key scenario requirements:

| Scenario Requirement | Mode Design | Status |
|---|---|---|
| "S2 detecta indisponibilidad... puede realizar fan out si no recibe confirmación" | Degraded mode shortens windows, activates direct channels | ✓ Precise |
| "S2 se duerme" (goes silent when S5 down) | Autonomous mode skips windows, makes decisions solo | ✓ Prevents silence |
| "almacenamiento temporal para sincronización posterior" | Decision journal + reconciliation mode | ✓ Explicit |
| "establecer comunicación directa con S3 y S4" | sys2.direct.logistics & sys2.direct.personnel topics | ✓ Direct bypass |
| "priorización y control de carga" | Weighted scheduler (P0:70%, P1:20%, P2:10%) | ✓ Prevents saturation |

**Verdict**: Your design is operationally sound. It's not minimal but it's not over-engineered either. It directly implements the scenario's state machine.

---

## Simplified Version (Still Complete)

We can reduce implementation complexity while keeping the architecture sound:

### What's Essential (Keep)
1. **3 operational modes** (Normal/Degraded/Autonomous) — state machine is the core
2. **Sliding window health monitor** (10-beat window, 80%/50%/0% thresholds) — simple math, high value
3. **Direct communication channels** (2 Kafka topics) — dormant routing, low overhead
4. **Decision journal** (append-only log) — lightweight, proven pattern
5. **Hysteresis** (30s threshold hold) — prevents flapping, essential for stability

### What's Optional (Simplify)
1. **Weighted scheduler** → **Simplified**: 2-tier priority (CRITICAL/STANDARD) + FIFO within tier
   - Still prevents saturation, cleaner logic
   - Easier to test/reason about
2. **Reconciling mode** → **Simplified**: Auto-transition back to Normal on recovery
   - Decision journal drain is async (background job)
   - Don't need explicit intermediate state

---

## Simplified Architecture

### 1. Operational Modes State Machine

```
┌─────────────────────────────────────────────────────────┐
│                   System 2 Mode State Machine           │
└─────────────────────────────────────────────────────────┘

                        ┌──────────┐
                        │  NORMAL  │
                        │(S5: 80%+)│
                        └────┬─────┘
                             │
              S5 < 80% for 30s│     S5 recovers & journal drained
                             ↓     (async background)
                        ┌──────────┐
    ┌─────────────────→ │ DEGRADED │ ←─────────────────┐
    │                   │(S5: 50%) │                   │
    │                   └────┬─────┘                   │
    │                        │                         │
    │         S5 < 50% for 30s│     S5 < 50% for 30s   │
    │                        ↓                         │
    │                   ┌──────────┐                   │
    │                   │AUTONOMOUS│                   │
    │                   │(S5: 0%)  │                   │
    │                   └────┬─────┘                   │
    │                        │                         │
    │     S5 responds (any beat)│                       │
    │     for 3s straight       │                       │
    └────────────────────────────┘                       │
                                                        │
                         S5 fully recovers after 10s idle
                         (drain decision journal async)
                                                        │
                         ↑─────────────────────────────┘
```

### 2. Health Score Calculation (Lightweight)

```python
# Pseudo-code
class HealthMonitor:
    def __init__(self):
        self.heartbeat_window = deque(maxlen=10)  # Last 10 beats
        self.last_mode = "NORMAL"
        self.mode_hold_time = 0
        self.threshold_hold_duration = 30  # seconds
    
    def record_heartbeat(self, success: bool):
        self.heartbeat_window.append(success)
        self.health_score = sum(self.heartbeat_window) / len(self.heartbeat_window)
    
    def get_target_mode(self) -> str:
        if self.health_score >= 0.80:
            target = "NORMAL"
        elif self.health_score >= 0.50:
            target = "DEGRADED"
        else:
            target = "AUTONOMOUS"
        
        # Hysteresis: 30s hold before transition
        if target != self.last_mode:
            self.mode_hold_time += 1
            if self.mode_hold_time >= 30:
                self.last_mode = target
                self.mode_hold_time = 0
        else:
            self.mode_hold_time = 0
        
        return self.last_mode
```

**Key properties to model:**
- Health check interval: 10 seconds
- Window size: 10 beats (100 seconds total window)
- Hysteresis: 30 seconds sustained below threshold
- **Total detection time**: S5 full down → 50s heartbeat timeout + 30s hysteresis = ~80s to Autonomous mode

### 3. Mode-Based Alert Processing (Simplified State Machine)

#### Normal Mode (S5 ≥ 80% healthy)
```
Sensor Events
    ↓
[Normalizer → Correlator → Rules Evaluator → Decision Maker]
    ↓
Alert → [Abort window = 120s]
    ↓
S5: "Approve/Reject/Override?"  (S5 orchestrates dispatch)
    ↓
[Dispatcher → Workers]
```

#### Degraded Mode (S5: 50-79% healthy)
```
Sensor Events
    ↓
[Normalizer → Correlator → Rules Evaluator → Decision Maker]
    ↓
Alert → [Abort window = 60s]  // Shortened
    ↓
┌─ S5: "Approve?"  (if responds quickly)
│  NO → proceed autonomously
│
└─ If S5 silent: proceed immediately to:
   [Decision Journal] (record decision)
       ↓
       ├→ [sys2.direct.logistics topic] (S3 consumes)
       │
       └→ [sys2.direct.personnel topic] (S4 consumes)
            ↓
       [Dispatcher → Workers]
```

#### Autonomous Mode (S5: 0% healthy)
```
Sensor Events
    ↓
[Normalizer → Correlator → Rules Evaluator → Decision Maker]
    ↓
Alert → [Abort window = 0s]  // No window, immediate
    ↓
[Decision Journal] (record decision)
    ↓
├→ [sys2.direct.logistics topic] (S3 consumes)
├→ [sys2.direct.personnel topic] (S4 consumes)
└→ [Dispatcher → Workers]
```

---

## Component Model (Simplified)

### New Components

```
component Heartbeat_Monitor : communication microservice {
    availability = high
    performance = realtime
    recoverability = fast
    auth = token
    security = internal
    port = 6505
    // Config:
    // HEARTBEAT_INTERVAL = 10s
    // WINDOW_SIZE = 10
    // HEALTH_THRESHOLDS = [0.80, 0.50, 0.0]
    // MODE_HOLD_DURATION = 30s
}

component Decision_Journal : data database {
    availability = high
    recoverability = fast
    performance = interactive
    auth = password
    security = restricted
    tech = "PostgreSQL"
    port = 6435
}

component Journal_Drainer : logic microservice {
    availability = standard
    recoverability = normal
    performance = batch
    auth = token
    security = internal
    port = 6506
    // Runs async when S5 recovers
}

component Mode_Controller : logic microservice {
    availability = high
    performance = realtime
    auth = token
    security = internal
    port = 6507
    // Manages state machine, decides abort_window duration
}
```

### Modified Components

**Rules_Evaluator** (now mode-aware):
```
component Rules_Evaluator : logic microservice {
    availability = critical
    performance = realtime
    auth = token
    security = internal
    port = 6502
    // Reads current_mode from Mode_Controller
    // Decision logic same, but behavior changes based on mode:
    //   NORMAL: query S5 for approval
    //   DEGRADED: try S5, fallback to autonomous
    //   AUTONOMOUS: always autonomous
}
```

**Alert_Manager** (simplified priority):
```
component Alert_Manager : logic microservice {
    availability = high
    performance = realtime
    auth = token
    security = internal
    port = 6504
    // 2-tier priority:
    //   CRITICAL: process immediately, reserve 70% capacity
    //   STANDARD: FIFO, use remaining capacity
    //   DROP_POLICY: Drop STANDARD alerts if queue > 5000
}
```

### Kafka Topics (Dormant Routing)

```
// Always exist, behavior changes based on mode
topic: sys2.direct.logistics {
    partitions: 3 (by region/zone)
    replication_factor: 2
    retention_ms: 86400000  // 24h
    subscribers: [S3_supply_resource_logistics]
    // Messages: {"alert_id", "severity", "zone", "resource_type", "quantity", "timestamp"}
}

topic: sys2.direct.personnel {
    partitions: 3 (by region/zone)
    replication_factor: 2
    retention_ms: 86400000  // 24h
    subscribers: [S4_personnel_orchestration]
    // Messages: {"alert_id", "severity", "zone", "action", "responder_type", "timestamp"}
}
```

### Decision Journal Schema

```sql
CREATE TABLE decision_journal (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    alert_id UUID NOT NULL,
    sensor_events JSONB NOT NULL,
    rule_applied VARCHAR(255) NOT NULL,
    severity VARCHAR(20) NOT NULL,  -- CRITICAL, HIGH, MEDIUM, LOW
    
    -- Mode context
    system_mode VARCHAR(20) NOT NULL,  -- NORMAL, DEGRADED, AUTONOMOUS
    s5_health_score FLOAT,
    s5_available BOOLEAN,
    
    -- Decision
    decision_time_ms INT NOT NULL,  -- How long to decide
    abort_window_ms INT,  -- NULL if autonomous mode
    
    -- Action taken
    dispatched_to JSONB,  -- {"S3": true, "S4": true, "workers": ["SMS", "Mobile"]}
    direct_topics_used JSONB,  -- {"sys2.direct.logistics": true, "sys2.direct.personnel": true}
    
    -- Reconciliation
    s5_approval VARCHAR(20),  -- "approved", "rejected", "override", NULL
    s5_approval_timestamp TIMESTAMP,
    synced_to_s5 BOOLEAN DEFAULT false,
    
    INDEX idx_timestamp,
    INDEX idx_alert_id,
    INDEX idx_system_mode,
    INDEX idx_synced_to_s5
);
```

---

## Operational Flows (Simplified)

### Flow 1: Normal Mode → Degraded (S5 at 50% health for 30s)

```
T+0s: Heartbeat_Monitor detects S5 health dropping (8/10 → 5/10)
T+0s: Target mode = DEGRADED, but hold_timer starts
T+30s: hold_timer expires, Mode_Controller transitions to DEGRADED
T+31s: New alerts use abort_window=60s (half of normal 120s)
T+31s: If S5 doesn't respond in 60s, Rules_Evaluator proceeds autonomously
T+31s: Decision_Journal records all autonomous decisions
T+31s: Decisions published to sys2.direct.logistics AND sys2.direct.personnel
```

**What changed:**
- Alert abort window shortened (120s → 60s)
- Direct topics activated (S3 & S4 consume directly)
- Journal recording ON
- Everything else: same pipe-and-filter

### Flow 2: Degraded → Autonomous (S5 at 0% health for 30s)

```
T+0s: Heartbeat_Monitor detects S5 completely unreachable
T+0s: 5 consecutive missed beats (50s total)
T+50s: S5 timeout expires, target_mode = AUTONOMOUS
T+50s: hold_timer starts
T+80s: hold_timer expires, Mode_Controller transitions to AUTONOMOUS
T+81s: New alerts skip abort_window entirely, immediate autonomous decision
T+81s: Decision_Journal records with mode=AUTONOMOUS
T+81s: Dispatch to direct topics (S3, S4) + workers
```

**What changed:**
- Abort window = 0 (immediate decision)
- No S5 coordination attempt
- All decisions recorded in journal

### Flow 3: Autonomous → Normal (S5 recovers)

```
T+0s: Heartbeat_Monitor detects first successful beat from S5
T+0s: target_mode = NORMAL, hold_timer starts
T+30s: If S5 sustained success, Mode_Controller transitions to NORMAL
T+31s: Journal_Drainer starts async background job:
       - Query: SELECT * FROM decision_journal WHERE s5_available=false AND synced_to_s5=false
       - Send batch report to S5 (REST API)
       - Update: synced_to_s5=true
T+31s: New alerts revert to normal workflow (await S5 approval)
T+N: Journal drain completes (async, doesn't block normal operation)
```

**What changed:**
- Abort window reverts to 120s
- Direct topics dormant again (S5 becomes hub)
- Journal draining happens in background (doesn't block)

---

## Comparison: Full vs Simplified

| Aspect | Full Design | Simplified | Tradeoff |
|---|---|---|---|
| **Modes** | 4 (Normal/Degraded/Autonomous/Reconciling) | 3 (Normal/Degraded/Autonomous) | Reconciling is background job, not explicit state |
| **Health monitor** | Sliding window 10 beats | Same | None |
| **Hysteresis** | 30s hold | Same | None |
| **Direct topics** | 2 topics (logistics, personnel) | Same | None |
| **Decision journal** | Full reconciliation workflow | Append-only log + async drain | Simpler, same outcome |
| **Priority queue** | Weighted (70/20/10) | 2-tier FIFO (CRITICAL/STANDARD) | Slightly less granular, but still prevents saturation |
| **Preemption** | P0 preempts P2 | None | Loss: P0 can't interrupt, but CRITICAL prioritized anyway |
| **New components** | 4 (Monitor, Journal, Drainer, Controller) | 4 (same) | None |
| **New DB tables** | 1 (decision_journal) | Same | None |
| **Complexity** | Medium | Medium | Simplified scheduler logic |

**Net impact**: Simplified version is ~15% less code, same architectural soundness.

---

## Cross-System Connectors (Final)

```
// S1 → S2: Sensor events (unchanged)
connector event_notification S1_data_acquisition_edge.publisher -> S2_early_warning_notification.Broker_In {
    protocol = AMQP
    style = Pub/Sub
    timeout_ms = 500
    encrypted = true
}

// S2 → S5: Health check (new)
connector data_stream S2_early_warning_notification.Heartbeat_Monitor -> S5_central_command_core {
    protocol = REST
    style = RequestResponse
    timeout_ms = 500
    encrypted = true
}

// S2 → S5: Approval request (normal mode only)
connector data_stream S2_early_warning_notification.Rules_Evaluator -> S5_central_command_core {
    protocol = REST
    style = RequestResponse
    timeout_ms = 120000  // Abort window
    encrypted = true
}

// S2 → S4: Normal mode (S5 orchestrates)
connector event_notification S5_central_command_core -> S4_personnel_orchestration.BrokerIn {
    protocol = AMQP
    style = MessageQueue
    encrypted = true
}

// S2 → S4: Degraded/Autonomous mode (direct)
connector event_notification S2_early_warning_notification.Broker_Out -> S4_personnel_orchestration.BrokerIn {
    topic = "sys2.direct.personnel"
    protocol = AMQP
    style = Pub/Sub
    encrypted = true
    // Dormant in NORMAL mode
}

// S2 → S3: Degraded/Autonomous mode (direct)
connector event_notification S2_early_warning_notification.Broker_Out -> S3_supply_resource_logistics {
    topic = "sys2.direct.logistics"
    protocol = AMQP
    style = Pub/Sub
    encrypted = true
    // Dormant in NORMAL mode
}

// S2 → S5: Reconciliation report (async, Autonomous→Normal transition)
connector data_stream S2_early_warning_notification.Journal_Drainer -> S5_central_command_core {
    protocol = REST
    style = RequestResponse
    timeout_ms = 5000
    encrypted = true
    // Batch report of autonomous decisions
}
```

---

## Why This Simplified Design Works

1. **Operationally Sound**
   - Clear state machine: no ambiguous edge cases
   - Health score prevents flapping (30s hysteresis)
   - Modes map directly to scenario scenarios (Normal/50%/0%)

2. **Minimal New Code**
   - 4 components (2 new, 2 modified)
   - 1 new database table (decision_journal)
   - 2 Kafka topics (dormant routing, no new infrastructure)

3. **Preserves Existing Architecture**
   - Pipe-and-filter chain unchanged
   - AMQP broker unchanged
   - Workers unchanged

4. **Solves Real Problems**
   - Prevents "S2 goes to sleep" (autonomous mode)
   - Handles "S5 at 50%" (degraded mode with shortened windows)
   - Enables reconciliation (decision journal)
   - Prevents S2↔S5 conflicts (dormant topics activate only when needed)

5. **Testable**
   - Health monitor: unit test scoring logic
   - Mode transitions: state machine tests (3 states, 3 transitions)
   - Journal: DB tests for append/drain
   - E2E: simulate each mode, verify behavior

---

## Next Steps

1. **Validate health thresholds with S5 team**: Is 80%/50%/0% the right breakdown?
2. **Define decision_journal message format**: What exactly gets synced back to S5?
3. **Coordinate with S3 & S4**: Do they understand sys2.direct.* topics? Can they handle concurrent messages from S5 + S2?
4. **Set heartbeat interval**: 10s is a guess; might be 5s or 30s depending on S5's SLA
5. **Model the mode_controller**: Where does it live? (Separate component or part of Rules_Evaluator?)
