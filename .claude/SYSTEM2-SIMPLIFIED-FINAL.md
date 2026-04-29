# System 2: Simplified Final Design

## What System 2 Actually Does

System 2 has **one core responsibility**: Generate and publish alerts based on sensor data.

**Nothing more. Nothing less.**

### System 2's Actual Scope (ONLY)

✅ **Ingest** sensor events from S1 (AMQP broker subscription)  
✅ **Evaluate** threats using rules engine (pipe-and-filter)  
✅ **Publish** alerts to event broker (AMQP, fire and forget)  
✅ **Log** everything in decision journal (audit trail)  
✅ **Check** S5 health & request approval in normal mode (REST)  
✅ **Reconcile** autonomous decisions when S5 recovers (async batch)  

### What System 2 Does NOT Do

❌ ~~Tell S3 what to do~~ (S3 is autonomous)  
❌ ~~Tell S4 what to do~~ (S4 is unaffected)  
❌ ~~Orchestrate cross-system actions~~ (S5's responsibility)  
❌ ~~Send commands to S3/S4~~ (Publish alerts only, that's it)  

---

## Operational Modes (Simplified)

### NORMAL (S5 ≥ 80% healthy)
```
S1 → S2 [Evaluate] → Broker [Publish] 
                  ↓
                S5 [Decides what S3/S4 do]
                  ↓
            S3/S4 [Execute S5's orders]
```
- S2 waits for S5 approval (120s abort window)
- S5 is the hub, S5 tells S3/S4 what to do
- S2 is just the alert generator

### DEGRADED (S5 50-79% healthy for 30s)
```
S1 → S2 [Evaluate] → Broker [Publish]
                  ↓
    [Try S5 for approval - 60s timeout]
                  ↓
    Timeout? → Continue autonomous
                  ↓
    Publish to Broker with mode=DEGRADED
                  ↓
    S3/S4 read alerts, make own decisions
    (S5 is available but slow; S5 can still override)
```
- S2 attempts S5 approval but with shorter timeout (60s)
- If S5 doesn't respond, S2 proceeds
- S2 logs decision: "mode=DEGRADED, proceeded autonomously"
- **S3/S4 independently subscribe to S2's alerts and act**

### AUTONOMOUS (S5 0% healthy for 30s)
```
S1 → S2 [Evaluate] → Broker [Publish]
                  ↓
    Skip S5, immediate decision
                  ↓
    Publish to Broker with mode=AUTONOMOUS
                  ↓
    Log: decision_journal entry
                  ↓
    S3/S4 read alerts, make own decisions
    (No S5 coordination at all)
```
- S2 makes all decisions immediately (0s abort window)
- **S3/S4 independently subscribe to S2's alerts and act**
- S2 logs everything: "Here's what I decided while S5 was down"

---

## Data Flow: The Truth

**In all modes, S2 does the exact same thing:**

1. Read sensor events from S1
2. Evaluate with rules engine
3. **Publish alert to event broker**
4. Done.

**The difference is:**
- Who approves it first (S5 in Normal, nobody in Autonomous)
- Whether it's recorded in journal (yes in Autonomous)
- How long to wait for approval (120s → 60s → 0s)

**S2 never sends anything to S3 or S4 directly.**

S3 and S4 are responsible for:
- Subscribing to S2's alert stream
- Reading alerts
- Making their own decisions based on those alerts
- Acting autonomously when S5 is unavailable

---

## Architecture: Stripped Down to Essentials

### Components S2 Actually Needs

**Tier 1: Communication** (5 components)
- `Broker_In`: Subscribe to S1 sensor events (AMQP)
- `Broker_Out`: Publish alerts to event broker (AMQP)
- `API_Gateway`: REST interface for S5 approval requests
- `Heartbeat_Monitor`: Health check S5 (10s interval)
- Workers (4): Dispatch to population (SMS, Mobile, Radio, Official)

**Tier 2: Logic** (8 components)
- `Event_Normalizer`: Standardize sensor format
- `Spatio_Temporal_Correlator`: Aggregate related events
- `Rules_Evaluator`: Mode-aware decision logic
- `Decision_Maker`: Final alert classification
- `Alert_Manager`: Deduplication & prioritization
- `Dispatcher`: Route to workers by region
- `Mode_Controller`: State machine (Normal/Degraded/Autonomous)
- `Journal_Drainer`: Async reconciliation (when S5 recovers)

**Tier 3: Data** (4 components)
- `Alert_History_DB`: Permanent audit trail
- `Rules_Repository`: Rule definitions
- `Decision_Journal`: Autonomous decisions log
- `Cache_Distribuido`: Rules cache (Redis)

**Total: 17 components** (vs. 26 before simplification)

---

## Cross-System Connectors (Actual Reality)

```
┌─────────────────────────────────────────────────────────────────┐
│                    System 2 Simplified Model                    │
└─────────────────────────────────────────────────────────────────┘

Inbound:
  S1 → S2.Broker_In (sensor events, AMQP)
  S5 → S2.Rules_Evaluator (approval request timeout, REST)

Outbound:
  S2.Heartbeat_Monitor → S5 (health check, REST 10s interval)
  S2.Rules_Evaluator → S5 (approval request, REST, abort window)
  S2.Alert_Manager → S5 (alert summary, REST)
  S2.Journal_Drainer → S5 (reconciliation batch, REST, async)
  S2.Broker_Out → [Event Broker] (alerts, AMQP)
  S2.Dispatcher → Workers (SMS, Mobile, Radio, Official)

What's NOT there:
  S2 ↛ S3 (S2 does NOT command S3)
  S2 ↛ S4 (S2 does NOT command S4)

Note:
  S3 and S4 independently subscribe to S2's alerts
  when S5 is unavailable. That's their responsibility.
```

---

## Scenario Mapping

### Normal Mode (Healthy SoS)
```
Flood detected
  ↓
S1: publishes "hydrological_alert" to Broker
  ↓
S2: evaluates, publishes "CRITICAL_FLOOD" to Broker
  ↓
S2: calls S5 approval API: "please approve my alert"
  ↓
S5: "Approved. S3: deploy trucks. S4: deploy firefighters."
  ↓
S3: executes supply orders (independent decision)
S4: executes personnel orders (independent decision)
Workers: send SMS/mobile/radio/official alerts
```

### Degraded Mode (S5 at 50% capacity)
```
Flood detected + earthquake
  ↓
S1: publishes both events to Broker
  ↓
S2: evaluates both, publishes to Broker
  ↓
S2: calls S5 approval API (60s timeout)
  ↓
S5: OVERLOADED, doesn't respond in time
  ↓
S2: proceeds autonomously (60s expired)
S2: logs: "mode=DEGRADED, no approval, proceeded anyway"
  ↓
S3 reads S2's alerts: "Flood in zone X, Earthquake in zone Y"
S3 thinks: "Both are critical, deploying trucks to both zones"
S3: makes own decision, executes
  ↓
S4 reads S2's alerts: same
S4: makes own decision, executes
  ↓
Workers: send alerts to population
```

### Autonomous Mode (S5 Complete Failure)
```
Multi-disaster (flood + fire + earthquake simultaneously)
  ↓
S1: publishes 200 events in 5 seconds
  ↓
S2: evaluates all, publishes all to Broker
  ↓
S2: Mode_Controller says "AUTONOMOUS" (S5 down 30s+)
  ↓
S2: SKIP S5 approval (abort window = 0)
S2: publish immediately
S2: log each decision: "mode=AUTONOMOUS, decided solo"
  ↓
S3 reads alert stream: priority-weighted decisions
S3: "200 alerts, need to deploy smartly. Using local rules..."
S3: autonomous decisions based on rules + S2 alerts
  ↓
S4 reads alert stream: same
S4: "I need to deploy rescue, medical, firefighting..."
S4: autonomous decisions based on rules + S2 alerts
  ↓
Workers: blast SMS to 500K people, push notifications to official channels
```

### Recovery (S5 Comes Back)
```
S5: ONLINE (health = 100%)
  ↓
Mode_Controller: AUTONOMOUS → DEGRADED (30s hold)
  ↓
Mode_Controller: DEGRADED → NORMAL (30s hold)
  ↓
S2 is back to normal: waiting for S5 approval
  ↓
Journal_Drainer (async background job):
  - Query: "SELECT * FROM decision_journal 
           WHERE mode IN ('DEGRADED', 'AUTONOMOUS') 
           AND synced=false"
  ↓
  - Result: "Here are 200 decisions I made while you were down"
  ↓
  - Send to S5: REST POST /reconciliation
  ↓
  - S5 reviews: "X% were correct. Y% need adjustment."
  ↓
  - Update journal: synced=true
  ↓
Complete audit trail created
```

---

## What Changed from Over-Engineered Version

| Aspect | Before | After | Reason |
|--------|--------|-------|--------|
| S2→S3 connector | Present | Removed | S3 subscribes independently |
| S2→S4 connector | Present | Removed | S4 is unaffected |
| Assumption | S2 coordinates S3/S4 | S2 only publishes | Scenario doesn't support it |
| Components | 26 | 17 | Removed coordination logic |
| Direct topics | sys2.direct.* | None | Not needed; broker is enough |
| S2 responsibility | "coordinate actions" | "publish alerts" | Proper scope |

---

## Implementation Checklist

- [x] Remove S2→S3 direct connectors
- [x] Remove S2→S4 direct connectors
- [x] Keep S2↔S5 health/approval connections
- [x] Keep S2→Workers (population notifications)
- [x] Keep decision journal + reconciliation
- [x] Model validates ✅
- [ ] Confirm with S3 team: "You'll subscribe to S2's alerts independently, right?"
- [ ] Confirm with S4 team: "You're unaffected by S5 downtime, right?"
- [ ] Confirm with S5 team: "When degraded, you might timeout; S2 will proceed"

---

## Summary

**System 2 is a alert generator, not a coordinator.**

It:
- Generates alerts from sensor data
- Publishes them to the broker
- Logs autonomous decisions when S5 is unavailable
- Reconciles with S5 when it recovers

It doesn't:
- Tell S3 or S4 what to do
- Orchestrate the SoS
- Make operational decisions for other systems

**Each system (S3, S4) is responsible for subscribing to alerts and making its own autonomous decisions when S5 is unavailable.**

This is **looser coupling, cleaner architecture, and more operationally sound**.

---

## Files Updated

- `team-2b/model.arch` — Simplified to 17 components (no direct S3/S4 coordination)
- `cross-connectors/model.arch` — Removed S2→S3, S2→S4 connectors
- `build.arch` — Regenerated, validates successfully

**Status**: ✅ Model built and validated  
**Branch**: `system-2-modeling`
