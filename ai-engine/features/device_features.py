from __future__ import annotations

from features.entity_history import EntityHistoryTracker


def extract_device_features(
    device_fingerprint: str,
    device_os: str | None,
    device_mac: str | None,
    tracker: EntityHistoryTracker,
) -> dict[str, object]:
    return {
        "device_familiarity_score": round(tracker.device_familiarity_score(device_fingerprint), 4),
        "fingerprint_mismatch": tracker.is_device_novel(device_fingerprint),
        "os_novelty": tracker.is_os_novel(device_os),
        "mac_novelty": tracker.is_mac_novel(device_mac),
    }