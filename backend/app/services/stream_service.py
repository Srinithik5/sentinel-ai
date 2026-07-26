from __future__ import annotations

import asyncio
import datetime
import random

entities = [
    "user_dev_04",
    "user_admin_ksmith",
    "svc_auth_01",
    "svc_billing_api",
    "user_analyst_09",
    "entity_corp_99",
]

attack_scenarios = [
    {
        "attack_type": "Privilege Escalation",
        "resource": "/etc/shadow",
        "action": "EXEC_SUDO_ROOT",
        "severity": "critical",
        "risk_score_min": 0.88,
        "risk_score_max": 0.99,
    },
    {
        "attack_type": "Data Exfiltration",
        "resource": "/db/finance/salaries.sql",
        "action": "BULK_EXPORT_CSV",
        "severity": "high",
        "risk_score_min": 0.78,
        "risk_score_max": 0.92,
    },
    {
        "attack_type": "Credential Dumping",
        "resource": "/api/v1/admin/tokens",
        "action": "AUTH_TOKEN_HARVEST",
        "severity": "critical",
        "risk_score_min": 0.85,
        "risk_score_max": 0.98,
    },
    {
        "attack_type": "Lateral Movement",
        "resource": "s3://secure-vault/keys.pem",
        "action": "SSH_KEY_READ",
        "severity": "high",
        "risk_score_min": 0.75,
        "risk_score_max": 0.89,
    },
]

normal_actions = [
    ("/api/v1/users/profile", "GET_USER_PROFILE", "low", 0.02, 0.15),
    ("/api/v1/dashboard/metrics", "FETCH_METRICS", "low", 0.01, 0.10),
    ("/auth/session/refresh", "TOKEN_REFRESH", "low", 0.03, 0.18),
    ("/db/query/search", "EXECUTE_SEARCH", "medium", 0.15, 0.35),
    ("/api/v1/reports/daily", "DOWNLOAD_REPORT", "low", 0.05, 0.22),
]


def generate_event(force_anomaly: bool = False) -> dict:
    """Generate a single stream event telemetry object."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    entity_id = random.choice(entities)
    event_id = f"evt_{random.randint(100000, 999999)}"

    is_anomaly = force_anomaly or (random.random() < 0.15)

    if is_anomaly:
        scenario = random.choice(attack_scenarios)
        risk_score = round(random.uniform(scenario["risk_score_min"], scenario["risk_score_max"]), 3)
        return {
            "eventId": event_id,
            "timestamp": now,
            "entityId": entity_id,
            "action": scenario["action"],
            "resource": scenario["resource"],
            "riskScore": risk_score,
            "severity": scenario["severity"],
            "isAnomaly": True,
            "attackType": scenario["attack_type"],
            "details": {
                "ip": f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
                "userAgent": "Mozilla/5.0 (Sentinel-Simulated-Agent)",
                "responseTimeMs": random.randint(300, 2500),
                "statusCode": random.choice([401, 403, 500]),
            },
        }

    resource, action, severity, r_min, r_max = random.choice(normal_actions)
    risk_score = round(random.uniform(r_min, r_max), 3)
    return {
        "eventId": event_id,
        "timestamp": now,
        "entityId": entity_id,
        "action": action,
        "resource": resource,
        "riskScore": risk_score,
        "severity": severity,
        "isAnomaly": False,
        "attackType": None,
        "details": {
            "ip": f"10.0.{random.randint(1, 20)}.{random.randint(1, 255)}",
            "userAgent": "Mozilla/5.0 (Standard-Internal-Client)",
            "responseTimeMs": random.randint(12, 120),
            "statusCode": 200,
        },
    }
