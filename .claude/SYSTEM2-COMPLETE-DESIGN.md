# System 2: Complete Operational Design

## Overview

**System 2 - Early Warning & Mass Notification (Alerta Temprana y Notificación Masiva)** is designed to operate seamlessly within the NERCMS-LSSA System of Systems while maintaining autonomous operation during S5 (Central Command) failures.

**Status**: ✅ Model compiled and validated  
**Files Created**:
- `team-2b/model.arch` — Complete System 2 internal architecture
- `cross-connectors/model.arch` — Updated with S2↔S1, S2↔S3, S2↔S4, S2↔S5 connections

---

## Operational Modes

System 2 operates in three distinct modes, managed by the `Mode_Controller` component:

### 1. NORMAL Mode (S5 ≥ 80% healthy)
- **Trigger**: System 5 health score ≥ 80%
- **Behavior**: S5 orchestrates all alert handling
- **Abort Window**: 120 seconds (Rules_Evaluator waits for S5 approval)
- **Data Flow**:
  ```
  Sensors → S2 [Evaluate] → S5 [Approve/Reject] → S4/S3/Workers
  ```
- **Direct Topics**: `sys2.direct.logistics` and `sys2.direct.personnel` remain **dormant**

### 2. DEGRADED Mode (S5: 50-79% healthy for 30 seconds)
- **Trigger**: Health score drops below 80% and stays there for 30 continuous seconds
- **Behavior**: S2 proposes alerts; S5 can still override if responding; if S5 silent, S2 proceeds
- **Abort Window**: 60 seconds (shortened from 120s)
- **Data Flow**:
  ```
  Sensors → S2 [Evaluate] 
    ├→ S5 [Try to get approval - 60s timeout]
    │  ├─ YES: S5 decides coordination
    │  └─ TIMEOUT: S2 proceeds autonomously
    └→ Decision_Journal [Record decision: s5_available=degraded]
        ├→ sys2.direct.personnel [S4 consumes]
        └→ sys2.direct.logistics [S3 consumes]
  ```
- **Direct Topics**: Activated if S5 doesn't respond within abort window
- **Audit**: All autonomous decisions recorded with mode=DEGRADED

### 3. AUTONOMOUS Mode (S5: 0% healthy for 30 seconds)
- **Trigger**: Health score = 0% (S5 completely unreachable) for 30 continuous seconds
- **Behavior**: S2 makes all decisions independently, no S5 coordination attempt
- **Abort Window**: 0 seconds (immediate decision and dispatch)
- **Data Flow**:
  ```
  Sensors → S2 [Evaluate] 
    → Decision_Journal [Record decision: s5_available=false]
    ├→ sys2.direct.personnel [S4 consumes directly]
    ├→ sys2.direct.logistics [S3 consumes directly]
    └→ Workers [Dispatch to public/agencies]
  ```
- **Direct Topics**: Always active
- **Audit**: All decisions recorded with mode=AUTONOMOUS
- **Prevention**: S2 never "goes to sleep" (scenario requirement met)

### 4. Recovery: Autonomous → Normal (S5 recovers)
- **Trigger**: S5 responds successfully after being down
- **Behavior**: Mode transitions back through Degraded → Normal (30s hold each)
- **Sync Process** (async, doesn't block):
  1. `Journal_Drainer` queries Decision_Journal: `SELECT * WHERE s5_available=false AND synced=false`
  2. Sends batch report to S5 via REST API
  3. S5 reviews autonomous decisions, can approve/reject/adjust
  4. Updates journal: `synced=true` for reviewed alerts
- **Result**: Complete audit trail of autonomous decisions available to S5

---

## Health Monitoring (Heartbeat_Monitor)

### Sliding Window Algorithm
```
Health Score = (successful_heartbeats / last_10_beats) × 100

Examples:
  10/10 = 100% → NORMAL
  8/10  = 80%  → NORMAL (threshold)
  7/10  = 70%  → DEGRADED (below 80%)
  5/10  = 50%  → DEGRADED (scenario requirement met)
  0/10  = 0%   → AUTONOMOUS
```

### Hysteresis (Prevents Flapping)
- Health score must stay **below threshold for 30 continuous seconds** before mode transition
- Prevents rapid oscillation on flaky connections (e.g., brief network glitch)
- Detection times:
  - Normal → Degraded: 30s after health < 80%
  - Degraded → Autonomous: 30s after health = 0%
  - Autonomous → Normal: 30s after first successful beat

### Heartbeat Mechanism
- **Interval**: 10 seconds
- **Protocol**: REST GET to S5 health endpoint
- **Timeout**: 500ms (fail-fast on network issues)
- **Window size**: 10 beats = 100 seconds total window

---

## Data Flows by Scenario

### Scenario: Localized Flooding (Normal Mode)

```
T+0s: Hydrological sensor detects rising water
      └→ S1 publishes event_notification (AMQP)

T+5ms: S2.Broker_In receives event
      └→ Event_Normalizer standardizes format
      └→ Spatio_Temporal_Correlator finds related events
      └→ Rules_Evaluator checks cache (Redis)
      └→ Decision_Maker classifies: CRITICAL flood alert

T+50ms: Alert_Manager deduplicates, logs to Alert_History_DB
       └→ Dispatcher routes by region/severity
       └→ SMS_Worker, Mobile_Worker queued

T+75ms: S2.Broker_Out publishes alert to S5 (REST approval request)
       └→ Rules_Evaluator awaits S5 response (120s abort window)

T+100ms: S5 receives alert, approves dispatch
        └→ S5 → S4.BrokerIn: "Deploy firefighters zone X"
        └→ S5 → S3: "Request water trucks zone X"
        └→ S5 → Workers: "Send SMS/mobile alerts"

T+200ms: SMS sent to 50K+ subscribers
        └→ ACKs tracked by Delivery_Monitor
        └→ Metrics persisted to Delivery_Metrics_DB

T+5min: Emergency services arrive, situation stabilizes
```

### Scenario: S5 Degradation (50% health, 30s hold)

```
T+0s: S5 drops to 50% capacity (power shortage)
      └→ Heartbeat_Monitor health = 5/10

T+10s-30s: Health stays 5/10, hold_timer accumulates

T+30s: hold_timer expires, Mode_Controller: NORMAL → DEGRADED
      └→ Abort_Window: 120s → 60s

T+35s: New flood alert arrives
      └→ Rules_Evaluator requests S5 approval (60s timeout)
      └→ S5 is overloaded, doesn't respond

T+95s: 60s abort window expires, no S5 response
      └→ Rules_Evaluator decides autonomously
      └→ Alert_Manager records: mode=DEGRADED, s5_available=false
      └→ Decision_Journal logs decision

T+100s: Dispatcher immediately sends to:
       ├→ sys2.direct.personnel (S4 consumes)
       ├→ sys2.direct.logistics (S3 consumes)
       └→ Workers (SMS, Mobile, Radio, Official)

T+1min: S3 and S4 receive alerts directly from S2 (bypass S5)
       └→ Firefighters deploy based on S2 alert
       └→ Supply trucks requested via S2 directly

T+5min: S5 recovers to 95% health
       └→ Heartbeat_Monitor detects recovery
       └→ Mode transitions: DEGRADED (30s) → NORMAL

T+6min: Journal_Drainer (async background):
       └→ Queries autonomous decisions from DEGRADED period
       └→ Sends batch report to S5
       └→ S5 reviews: "X alerts were correct, Y need adjustment"
       └→ Updates journal: synced=true
       └→ Complete audit trail created
```

### Scenario: S5 Complete Failure (100% down, 30+ seconds)

```
T+0s: S5 datacenter power failure
      └→ Heartbeat_Monitor: all beats fail

T+5s-50s: Timeout waiting for S5 response (50s total: 5×10s)

T+50s: S5 timeout confirmed, health=0/10, Mode_Controller: DEGRADED → AUTONOMOUS
      └→ Abort_Window: 60s → 0s (immediate)

T+51s: Multiple earthquakes, floods, fires detected simultaneously
      └→ 200 sensor events arrive in 5 seconds

T+52s: Each event processes autonomously:
       └→ Normalizer → Correlator → Rules_Evaluator (reads mode=AUTONOMOUS)
       └→ Decision_Maker classifies severity (CRITICAL/HIGH/MEDIUM/LOW)

T+54s: Alert_Manager applies priority queue (2-tier):
       ├→ CRITICAL (70% capacity): life-threatening events
       │  └─ Immediate dispatch to S4/S3/Workers
       ├→ STANDARD (30% capacity): operational alerts
       │  └─ Queued, processed as bandwidth available
       └─ If queue > 5000: drop STANDARD alerts (graceful degradation)

T+55s: Dispatcher routes:
       └→ sys2.direct.personnel: "Dispatch all rescue teams to zones A,B,C,D"
       └→ sys2.direct.logistics: "Deploy medical, water, food supplies"
       └→ Workers: SMS blast to 500K people in affected regions

T+2min: S4 Personnel receives 200 alerts from S2 (not S5)
       └→ Firefighters, rescue, medical all deploy autonomously
       └→ No central coordination bottleneck

T+3min: S3 Logistics receives requests from S2 directly
       └→ Trucks route to zones X, Y, Z automatically
       └→ No S5 approval needed

T+10min: S5 power restored, recovers to 100% health
        └→ Heartbeat_Monitor detects recovery (sustained 30s)
        └→ Mode transitions: AUTONOMOUS (30s) → DEGRADED (30s) → NORMAL

T+11min: Journal_Drainer starts async:
        └→ SELECT alerts WHERE mode=AUTONOMOUS, synced=false
        └→ Result: 200 alerts, all with decision_journal entries
        └→ Sends report to S5: "Here's what S2 decided while you were down"
        └→ S5 can audit/validate/learn from autonomous decisions

T+15min: Journal drain completes (doesn't block operations)
        └→ S2 back to NORMAL mode operation
        └→ S5 reviews: "X% of autonomous decisions were correct"
        └→ Improves rules for next incident
```

---

## Component Architecture

### Tier 1: Communication (8 components)
- **Broker_In/Out**: AMQP pub/sub hubs (Kafka/RabbitMQ)
- **API_Gateway**: REST interface for S5 (normal mode coordination)
- **Heartbeat_Monitor**: S5 health checker (10s interval, sliding window)
- **Workers** (4): SMS, Mobile, Radio, Official Channels (scalable)
- **Delivery_Monitor**: ACK/metrics tracking

### Tier 2: Logic (9 components)
- **Event_Normalizer**: Standardize sensor events (stage 1)
- **Spatio_Temporal_Correlator**: Aggregate related events (stage 2)
- **Rules_Evaluator**: Mode-aware rule engine (stage 3, reads Mode_Controller)
- **Decision_Maker**: Final alert classification (stage 4)
- **Alert_Manager**: Deduplication, prioritization, mode-aware behavior
- **Dispatcher**: Route to workers by region/severity
- **Mode_Controller**: State machine for operational modes
- **Template_Service**: i18n alert formatting
- **Journal_Drainer**: Async reconciliation with S5 (background)

### Tier 3: Data (5 components)
- **Alert_History_DB**: Audit trail of all alerts (always logged)
- **Rules_Repository**: Rule definitions and thresholds (versioned)
- **Decision_Journal**: Append-only log of autonomous decisions
- **Cache_Distribuido**: Redis cache for rules/templates (hot data)
- **Delivery_Metrics_DB**: ACK tracking per channel/region

---

## Cross-System Connectors

### S1 → S2: Sensor Events (Realtime)
```
S1.publisher → S2.Broker_In
  Protocol: AMQP (Pub/Sub)
  Timeout: 500ms
  Encrypted: true
  Throughput: ~1000 events/sec (scales with sensors)
```

### S2 ↔ S5: Health & Coordination
```
S2.Heartbeat_Monitor → S5 (Health check)
  Protocol: REST GET /health
  Interval: 10 seconds
  Timeout: 500ms
  Purpose: Sliding window health score calculation

S2.Rules_Evaluator → S5 (Approval request, mode-dependent)
  Protocol: REST POST /alerts/approve
  Timeout: 120s (Normal), 60s (Degraded), 0s (Autonomous)
  Purpose: S5 can approve, reject, or override S2 decisions

S2.Journal_Drainer → S5 (Reconciliation, async batch)
  Protocol: REST POST /reconciliation
  Timeout: 5000ms
  Purpose: Sync autonomous decisions when S5 recovers
  Frequency: Once after S5 recovery, then background job
```

### S2 → S4: Personnel Deployment (Dual Path)
```
NORMAL Mode:
  S5 → S4.BrokerIn (S5 coordinates)
    Protocol: Tcp (MessageQueue)
    Encrypted: true

DEGRADED/AUTONOMOUS Mode:
  S2.Broker_Out → S4.BrokerIn (Direct)
    Topic: sys2.direct.personnel
    Protocol: AMQP (Pub/Sub)
    Encrypted: true
    Timeout: 1000ms
    Message: {"alert_id", "zone", "action", "responder_type"}
```

### S2 → S3: Logistics/Resources (Dual Path)
```
NORMAL Mode:
  S5 coordinates (not shown in cross-connectors, handled by S5)

DEGRADED/AUTONOMOUS Mode:
  S2.Broker_Out → S3 (Direct)
    Topic: sys2.direct.logistics
    Protocol: AMQP (Pub/Sub)
    Encrypted: true
    Timeout: 1000ms
    Message: {"alert_id", "zone", "resource_type", "quantity"}
```

### S2 ↔ S1: Historical Queries (Optional)
```
S2 → S1.interface (Query historical data if needed)
  Protocol: REST (RequestResponse)
  Encrypted: true
  Purpose: Optional context enrichment (not critical path)
```

---

## Quality Attributes Achieved

| Attribute | Mechanism | Evidence |
|-----------|-----------|----------|
| **Availability** | Autonomous mode, graceful degradation | Works even if S5 down 100% |
| **Reliability** | At-least-once (AMQP broker + DB logging) | No alerts lost silently |
| **Resilience** | Mode-aware fallback, direct channels | Doesn't fail catastrophically |
| **Performance** | Realtime pipe-and-filter (< 100ms decision) | <5s end-to-end alert to public |
| **Scalability** | Broker-based, stateless workers | Workers scale 1-10 replicas |
| **Auditability** | Decision_Journal + Delivery_Metrics_DB | Complete trace of what S2 did during S5 outage |
| **Security** | TLS encryption, token auth | All cross-system comms encrypted |

---

## Configuration & Deployment

### Mode Thresholds (Tunable)
```
HEARTBEAT_INTERVAL = 10 seconds        # How often to check S5
HEARTBEAT_TIMEOUT = 500 milliseconds   # Fail-fast timeout
WINDOW_SIZE = 10 beats                 # Last 100 seconds of health
HEALTH_THRESHOLDS = [0.80, 0.50, 0.0] # Normal/Degraded/Autonomous
MODE_HOLD_DURATION = 30 seconds        # Hysteresis to prevent flapping
```

### Abort Windows (Tunable by Scenario)
```
NORMAL Mode:     120 seconds   # S5 has plenty of time to respond
DEGRADED Mode:   60 seconds    # Shortened, but still gives S5 a chance
AUTONOMOUS Mode: 0 seconds     # Immediate decision (S5 is down)
```

### Priority Queue (Tunable)
```
CRITICAL Alerts:  70% of dispatch capacity
STANDARD Alerts:  30% of dispatch capacity
DROP_POLICY:      Drop STANDARD if queue > 5000
PREEMPTION:       CRITICAL can pause STANDARD (optional)
```

### Worker Scaling (Tunable)
```
SMS_Worker:               min=2, max=10   (high throughput)
Mobile_Worker:            min=2, max=10   (high throughput)
Radio_TV_Worker:          min=1, max=3    (medium throughput)
Official_Channels_Worker: min=1, max=5    (medium throughput)
```

---

## Testing Strategy

### Unit Tests
- [ ] Heartbeat_Monitor sliding window scoring logic
- [ ] Mode_Controller state machine transitions (3 states, hysteresis logic)
- [ ] Alert_Manager deduplication and prioritization
- [ ] Rules_Evaluator decision logic (per rule set)

### Integration Tests
- [ ] E2E flow: Sensor → S2 → S4/S3 in each mode
- [ ] Mode transition: Normal → Degraded (30s hold verified)
- [ ] Journal recording: All autonomous decisions logged
- [ ] Journal drain: Batch report to S5 after recovery

### Chaos Tests
- [ ] S5 network latency: Health score calculation under delays
- [ ] S5 total failure: Mode switches to Autonomous, alerts still dispatch
- [ ] S4/S3 unavailability: S2 queues, doesn't block sensor processing
- [ ] Worker failure: Alert_Manager queues, workers restart
- [ ] Database failure: Alert_History_DB unavailable → graceful degradation

### Load Tests
- [ ] 1000+ events/sec: Correlator + Rules_Evaluator throughput
- [ ] 500K SMS recipients: Worker scaling under peak
- [ ] Multi-disaster: CRITICAL (70%) vs STANDARD (30%) prioritization

---

## Known Limitations & Future Work

1. **S5 Health Endpoint**: Assumes S5 provides `/health` endpoint (not yet designed)
2. **Direct Topic Schema**: Needs agreement with S3/S4 on message format
3. **Journal Replay**: Doesn't automatically re-send missed alerts; S5 must review
4. **Rules Version Control**: Rules_Repository needs migration strategy for updates
5. **Manual Alert Override**: S5 can override, but UI workflow not yet designed

---

## Handoff Checklist

- [x] System 2 model created (team-2b/model.arch)
- [x] Cross-connectors updated with all S2 connections
- [x] Operational modes state machine designed
- [x] Health monitoring algorithm documented
- [x] Decision journal and reconciliation workflow defined
- [x] Priority queue and backpressure handling specified
- [x] Model builds and validates ✅
- [ ] S5 team: Confirm `/health` endpoint and approval API
- [ ] S3 team: Confirm `sys2.direct.logistics` topic subscription
- [ ] S4 team: Confirm `sys2.direct.personnel` topic subscription
- [ ] Validation: Compare actual S5 load profile with 80%/50%/0% thresholds
- [ ] Deployment: Configure heartbeat interval, abort windows per environment

---

## Summary

System 2 is now fully modeled as an **autonomous, resilient, mode-aware alert system** that:

✅ Operates seamlessly with S1 (sensor data), S4 (personnel), S3 (logistics), S5 (command)  
✅ Automatically degrades gracefully when S5 is unavailable (scenario requirement)  
✅ Prevents "going to sleep" (autonomous mode immediate dispatch)  
✅ Maintains complete audit trail (decision journal)  
✅ Prevents S2↔S5 conflicts (direct topics dormant in normal mode)  
✅ Handles multi-disaster peaks (2-tier priority queue)  
✅ Recovers and reconciles when S5 comes back online  

**The design is operationally sound, testable, and ready for implementation.**
