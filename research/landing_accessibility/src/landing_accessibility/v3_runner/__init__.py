"""v3 수집 파이프라인 런너 — 동결 계약 적재 계층.

정본은 ``research/landing_accessibility/control/v3/FINAL_MAIN50_MANIFEST.json`` (A 동결,
v3.0.2), 대조군은 ``SSOTV3/`` 의 registry CSV/JSON 이다. 상세는 :mod:`.registry` 참조.
"""

from __future__ import annotations

from .contracts import (
    FIXTURE_INPUT_MODES,
    TASK_ROLE_PRIMARY,
    TASK_ROLE_SECONDARY_REPEATED,
    TASK_ROLES,
    TaskContract,
)
from .registry import (
    CONTRACT_HASH_EXCLUDED_FIELDS,
    CONTRACT_HASH_PAYLOAD_FIELDS,
    CONTROL_UNCOVERED_FIELDS,
    DEFAULT_MANIFEST_PATH,
    MANIFEST_RELPATH,
    PRIMARY_SAMPLE_FILTER,
    FamilyDenominatorChain,
    RegistryConflictError,
    RegistryError,
    RegistryIntegrityError,
    RegistryLookupError,
    RegistryParseError,
    RegistrySourceMissingError,
    ReplacementLog,
    ReplacementReserveEntry,
    TaskRegistry,
    canonical_contract_payload,
    canonical_json,
    compute_manifest_body_sha256,
    compute_manifest_file_sha256,
    load_task_registry,
    recompute_task_contract_hash,
    resolve_manifest_path,
    resolve_ssot_dir,
)

__all__ = [
    "CONTRACT_HASH_EXCLUDED_FIELDS",
    "CONTRACT_HASH_PAYLOAD_FIELDS",
    "CONTROL_UNCOVERED_FIELDS",
    "DEFAULT_MANIFEST_PATH",
    "FIXTURE_INPUT_MODES",
    "MANIFEST_RELPATH",
    "PRIMARY_SAMPLE_FILTER",
    "TASK_ROLES",
    "TASK_ROLE_PRIMARY",
    "TASK_ROLE_SECONDARY_REPEATED",
    "FamilyDenominatorChain",
    "RegistryConflictError",
    "RegistryError",
    "RegistryIntegrityError",
    "RegistryLookupError",
    "RegistryParseError",
    "RegistrySourceMissingError",
    "ReplacementLog",
    "ReplacementReserveEntry",
    "TaskContract",
    "TaskRegistry",
    "canonical_contract_payload",
    "canonical_json",
    "compute_manifest_body_sha256",
    "compute_manifest_file_sha256",
    "load_task_registry",
    "recompute_task_contract_hash",
    "resolve_manifest_path",
    "resolve_ssot_dir",
]
