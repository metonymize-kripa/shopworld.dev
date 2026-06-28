"""Content-addressing for frozen artifacts.

Every artifact that participates in a battery run -- scenarios, paraphrase
banks, rubrics, judge caches -- is content-addressed with BLAKE2b. The address
is a stable function of the artifact's *canonical* serialisation, so two
artifacts with identical content always share an address regardless of dict
ordering or whitespace.

A battery run is identified by a manifest that hashes every input artifact plus
the engine version, giving one root hash that pins the entire run.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


def canonical_json(obj: Any) -> str:
    """Canonical JSON: sorted keys, no insignificant whitespace, UTF-8.

    This is the single serialisation used for hashing so that semantically
    identical objects always hash identically.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def content_hash(obj: Any) -> str:
    """Return the hex BLAKE2b-128 content address of a JSON-able object."""
    payload = canonical_json(obj).encode("utf-8")
    return hashlib.blake2b(payload, digest_size=16).hexdigest()


def content_hash_bytes(data: bytes) -> str:
    return hashlib.blake2b(data, digest_size=16).hexdigest()


@dataclass(frozen=True)
class Manifest:
    """Pins an entire battery run by hashing all of its inputs."""

    engine_version: str
    battery_version: str
    artifact_hashes: dict[str, str]

    def root_hash(self) -> str:
        return content_hash(
            {
                "engine_version": self.engine_version,
                "battery_version": self.battery_version,
                "artifacts": self.artifact_hashes,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "battery_version": self.battery_version,
            "artifact_hashes": dict(sorted(self.artifact_hashes.items())),
            "root_hash": self.root_hash(),
        }
