# SentinelAI — Demo Guide

Everything below is drawn from a real, verified pipeline run — the same 2,500-entity / 251,884-event dataset referenced throughout this project's documentation. No entity ID, risk score, MITRE mapping, or narrative text on this page is invented; every example is a real record pulled directly from `frontend/public/data/alerts.json` at the time this document was written.

## Table of Contents

- [Example Datasets](#example-datasets)
- [Screenshot Checklist](#screenshot-checklist)
- [Example Analyst Scenarios](#example-analyst-scenarios)
- [Example Attack Scenarios (One Per Type)](#example-attack-scenarios-one-per-type)
- [Demo Walkthrough](#demo-walkthrough)

---

## Example Datasets

No synthetic "demo-only" dataset exists separately from the real pipeline output — using the same data the platform actually produces is the point. The dataset referenced throughout this project's documentation and used to generate every fixture the dashboard renders:

| Artifact | Location | Scale |
|---|---|---|
| Synthetic entities | `ai-engine/data/generated/<run_id>/entities.csv` | 2,500 entities (users, service accounts, edge/IoT devices) |
| Raw + injected events | `ai-engine/data/attacks/<run_id>/events_injected.csv` | 251,884 events, 7 attack types injected |
| Engineered features | `ai-engine/data/features/<run_id>/engineered_events.parquet` | 251,884 rows × 33 behavioural features |
| Detection results | `ai-engine/data/detections/<run_id>/detection_results.csv` | 4,545 flagged (247,339 Normal / 3,596 Suspicious / 949 Anomalous) |
| Classification results | `ai-engine/data/classifications/<run_id>/classification_report.csv` | 4,545 classified, 1,291 with ground truth for evaluation |
| Dashboard fixtures | `frontend/public/data/*.json` | 320 alerts (45 per attack type, capped), sampled from the 4,545 |

To generate a fresh copy of this dataset from scratch, follow [ai-engine/README.md's "Running the Complete Pipeline"](../ai-engine/README.md#running-the-complete-pipeline) — every command is real and independently runnable.

## Screenshot Checklist

A precise list of what to capture for a submission gallery, each verified against the live running dashboard (`http://localhost:5173`) rather than assumed:

| # | Page/State | URL | What should be visible |
|---|---|---|---|
| 1 | Executive Overview | `/` | 7 metric cards (Total Events 251,884; Anomalies 4,545; Critical Alerts 281; Detection Accuracy 98.57%; Average Risk 33.4; False Positive Rate 71.6%; Detection Latency ~0.5ms), "Highest-Risk Open Alerts" list, System Health panel |
| 2 | Live Alert Queue | `/alerts` | Full 320-alert table with search/filter/sort controls, pagination ("Showing 1-25 of 320 alerts") |
| 3 | Alert Details Panel | Click any alert row on `/alerts` | Sheet panel with tabs — evidence, feature contributions, recommended actions |
| 4 | Explainability tab | Within the Alert Details Panel | Feature-attribution percentages and the analyst-facing narrative |
| 5 | Behaviour Timeline tab | Within the Alert Details Panel | The entity's recent event history leading up to the flagged event |
| 6 | MITRE ATT&CK tab | Within the Alert Details Panel | Tactic/technique mapping for the alert's classified attack type |
| 7 | Entities | `/entities` | Entities aggregated from alerts, ranked by peak risk score |
| 8 | Analytics | `/analytics` | 6 charts: attack distribution, severity distribution, risk distribution, hourly activity, top resources, geo distribution |
| 9 | System Health | `/system-health` | Live backend/database status plus batch engine statuses (Detection, Classification, Explainability, Streaming) |
| 10 | Settings | `/settings` | Deferred-configuration placeholder (intentional — not a bug, see `FolderStructure.md`) |

## Example Analyst Scenarios

Two real, complete triage walkthroughs an analyst could follow using the actual dashboard, built from real alert records.

### Scenario 1 — Escalate a Critical brute-force alert

1. Open `/alerts`, sort by Risk descending. The top row is `USR-001431` (HR), risk **61.4**, attack type **Brute Force**, confidence **80%**, severity **Critical**.
2. Click the row to open the Alert Details Panel. The evidence summary reads: *"This event scored an anomaly of 0.90 on a 0-1 scale and a risk score of 61.4 out of 100, resulting in an 'anomalous' verdict at 'critical' severity."*
3. Check the Explainability tab — the top contributing factor is the **device** dimension (18.6%): *"Device 'b0ba09c1a097e389b354b3deae078480' does not appear in this entity's behaviour profile at all."*
4. Check the MITRE tab — mapped to **Credential Access / T1110 Brute Force**.
5. The recommended action is flagged **immediate priority**: *"Escalate to SOC immediately — Severity is High or Critical, exceeding the threshold for individual analyst handling alone."*
6. Analyst decision: escalate per the recommendation, and independently verify the unfamiliar device against the entity's known-device inventory before granting continued access.

### Scenario 2 — Triage a medium-severity device-spoofing alert

1. Filter `/alerts` by attack type = Device Spoofing. The highest-risk example is `USR-000992` (HR), risk **42.8**, confidence **71.1%**, severity **Medium**.
2. Evidence summary: anomaly score 0.46, verdict **suspicious** (not yet anomalous) — a lower-urgency case than Scenario 1.
3. Top contributing factor: **device** dimension at **34.1%** — the largest single-dimension share seen across the sampled alert set — *"Device '84f0ed2ffafafb4d2c93a79665a6a1c4' does not appear in this entity's behaviour profile at all. (First appearance of this fingerprint in the entity's event history up to this point.)"*
4. MITRE mapping: **Defense Evasion / T1036 Masquerading**.
5. Recommended action: *"Isolate the endpoint presenting the mismatched device identity — a device fingerprint inconsistent with the entity's known devices may itself be compromised or spoofed."*
6. Analyst decision: given `suspicious` (not `anomalous`) verdict and medium severity, this is a same-shift review item rather than an immediate page — isolate the endpoint and confirm with the user before escalating further.

## Example Attack Scenarios (One Per Type)

The highest-risk real example of each of the 7 known attack types plus `unknown`, exactly as they appear in the dataset:

| Attack Type | Example Entity | Risk | Confidence | MITRE | Top Driving Factor |
|---|---|---|---|---|---|
| Brute Force | USR-001431 (HR) | 61.4 | 80% | Credential Access / T1110 | Unfamiliar device (18.6%) |
| Impossible Travel | USR-000836 (Engineering) | 56.6 | 56.3% | Initial Access / T1078 | Login at hour 23 vs. entity avg 12.2±2.3h (20.9%) |
| Credential Stuffing | USR-001431 (HR) | 56.4 | 57.9% | Credential Access / T1110.004 | Unfamiliar device, first-seen fingerprint (18.6%) |
| Insider Drift | USR-001431 (HR) | 56.4 | 73.9% | Privilege Escalation / T1078 | Unfamiliar device (18.6%) |
| Low-and-Slow Exfiltration | USR-001746 (Finance) | 47.5 | 56.6% | Exfiltration / T1030 | Unfamiliar device (20.8%) |
| Device Spoofing | USR-000992 (HR) | 42.8 | 71.1% | Defense Evasion / T1036 | Unfamiliar device, first-seen (34.1%) |
| Lateral Movement | USR-000215 (IT) | 32.8 | 36.6% | Lateral Movement / T1021 | First access to sensitive "VPN Gateway" resource (34.7%) |
| Unknown | USR-000401 (Engineering) | 25.5 | 5.7% | — (no match above threshold) | Elevated access to "CI/CD Pipeline" (41.9%) — flagged, but no known signature scored high enough for automated classification |

Note the confidence gradient: attack types with sharp, singular tells (Brute Force, Device Spoofing) score high confidence; types requiring a broader pattern match (Lateral Movement, Unknown) score lower — a genuine, unforced property of the real classifier's output, not curated for this table.

## Demo Walkthrough

A ~5-minute live walkthrough script:

1. **Health check** (30s) — `curl http://localhost:8000/api/v1/health` → real `200 OK`, then point out the same status reflected live in the dashboard's System Health panel, polled every 30 seconds.
2. **Executive Overview** (60s) — land on `/`, narrate the 7 real headline metrics, click into "Highest-Risk Open Alerts" to show it's backed by the same data as the full queue.
3. **Alert triage** (90s) — navigate to `/alerts`, demonstrate search/filter/sort across the real 320-alert set, open one alert's detail panel, walk through its Explainability/Timeline/MITRE tabs (see Scenario 1 above for exact real content).
4. **Explain the "why"** (60s) — emphasize that every number in the panel — risk score, feature contribution percentages, MITRE mapping — was computed by a real, independently-runnable pipeline stage, not looked up from a canned response.
5. **Analytics** (45s) — `/analytics`, point out the attack/severity/risk distributions are the real aggregate shape of the 251,884-event dataset.
6. **Honesty checkpoint** (30s) — explicitly state what's real vs. not: real detection/classification/explainability pipeline, static (not live-API) dashboard data by design, no trained ML model, no production deployment. This project's documentation makes the same disclosure everywhere else — the demo should match it exactly.
