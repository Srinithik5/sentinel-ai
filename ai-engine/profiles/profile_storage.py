from __future__ import annotations

import json
from pathlib import Path

from profiles.profile_manager import BehaviourProfile


class ProfileStorage:
    """File-based persistence for BehaviourProfiles. Each entity gets one
    JSON file holding its full version history, so `load_latest` always
    returns the most recent version while the complete evolution of a
    baseline remains auditable via `load_history`.
    """

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, entity_id: str) -> Path:
        safe_name = entity_id.replace("/", "_")
        return self.storage_dir / f"{safe_name}.json"

    def load_latest(self, entity_id: str) -> BehaviourProfile | None:
        path = self._path_for(entity_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        versions = payload.get("versions", [])
        if not versions:
            return None
        return BehaviourProfile.from_dict(versions[-1])

    def load_history(self, entity_id: str) -> list[BehaviourProfile]:
        path = self._path_for(entity_id)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return [BehaviourProfile.from_dict(version) for version in payload.get("versions", [])]

    def save(self, profile: BehaviourProfile) -> None:
        """Appends `profile` as a new version for its entity, preserving
        every prior version already on disk. This is both "save" (first
        version) and "update" (subsequent versions) — the distinction is
        just whether a file already exists.
        """
        path = self._path_for(profile.entity_id)
        existing_versions: list[dict[str, object]] = []
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                existing_versions = json.load(handle).get("versions", [])

        existing_versions.append(profile.to_dict())
        payload = {"entity_id": profile.entity_id, "versions": existing_versions}

        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def list_entity_ids(self) -> list[str]:
        return sorted(path.stem for path in self.storage_dir.glob("*.json"))