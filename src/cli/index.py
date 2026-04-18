"""
Spec directory loader and flat id index.

Loads every YAML under a spec directory (L0 singleton, L1 singleton,
L2 modules + policies, L3 atoms + artifacts, L4 flows + journeys,
L5 singleton) and produces a flat dict keyed by id for O(1) lookup.

L0 sub-sections (errors, types, constants, external_schemas) are
exploded into individually-keyed entries so callers can ask for a
single error code or type id without knowing the registry's shape.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Entry:
    id: str
    kind: str           # atom|module|journey|flow|artifact|policy|type|error|constant|external_schema|marker
    data: Any
    file: Path | None = None


@dataclass
class Index:
    spec_dir: Path
    entries: dict[str, Entry] = field(default_factory=dict)
    l0: dict[str, Any] = field(default_factory=dict)   # raw L0 registry
    l1: dict[str, Any] = field(default_factory=dict)   # raw L1 conventions
    l5: dict[str, Any] = field(default_factory=dict)   # raw L5 operations

    def get(self, entity_id: str) -> Entry | None:
        return self.entries.get(entity_id)

    def by_kind(self, kind: str) -> list[Entry]:
        return [e for e in self.entries.values() if e.kind == kind]

    def naming_regex(self, key: str) -> re.Pattern[str] | None:
        pat = self.l0.get("naming_ledger", {}).get(key)
        return re.compile(pat) if pat else None


# ---------- discovery ----------

def resolve_spec_dir(explicit: str | None = None) -> Path:
    """Resolve spec dir from explicit arg, env var, or auto-discover."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("FORGE_SPEC_DIR")
    if env:
        return Path(env).expanduser().resolve()

    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "L0_registry.yaml").is_file():
            return candidate
        if (candidate / ".forge" / "L0_registry.yaml").is_file():
            return candidate / ".forge"
        # Back-compat for projects initialized before the .forge convention:
        if (candidate / "forge" / "docs" / "L0_registry.yaml").is_file():
            return candidate / "forge" / "docs"
        # Also check for a .forge/ with just the structure (L-layer dirs / templates)
        # even if L0_registry.yaml hasn't been written yet (e.g., fresh init, not yet run discover).
        if (candidate / ".forge").is_dir() and (candidate / ".forge" / "L2_modules").is_dir():
            return candidate / ".forge"
    raise FileNotFoundError(
        "Cannot locate spec dir. Pass --spec-dir, set FORGE_SPEC_DIR, "
        "or run `forge init` to bootstrap a new project."
    )


# ---------- loader ----------

def load(spec_dir: Path) -> Index:
    spec_dir = Path(spec_dir).resolve()
    if not spec_dir.is_dir():
        raise FileNotFoundError(f"Spec dir not found: {spec_dir}")

    idx = Index(spec_dir=spec_dir)

    _load_singleton(idx, spec_dir / "L0_registry.yaml", slot="l0")
    _load_singleton(idx, spec_dir / "L1_conventions.yaml", slot="l1")
    _load_singleton(idx, spec_dir / "L5_operations.yaml", slot="l5")

    _explode_l0(idx)

    _load_dir(idx, spec_dir / "L2_modules", kind="module", top_key="module")
    _load_dir(idx, spec_dir / "L2_policies", kind="policy", top_key="policy")
    _load_dir(idx, spec_dir / "L3_atoms", kind="atom", top_key="atom")
    _load_dir(idx, spec_dir / "L3_artifacts", kind="artifact", top_key="artifact")
    _load_dir(idx, spec_dir / "L4_flows", kind="flow", top_key="orchestration")
    _load_dir(idx, spec_dir / "L4_journeys", kind="journey", top_key="journey")

    return idx


def _load_singleton(idx: Index, path: Path, slot: str) -> None:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    setattr(idx, slot, data)


def _load_dir(idx: Index, directory: Path, kind: str, top_key: str) -> None:
    if not directory.is_dir():
        return
    for path in sorted(directory.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        body = doc.get(top_key) or {}
        entity_id = body.get("id")
        if not entity_id:
            continue
        idx.entries[entity_id] = Entry(id=entity_id, kind=kind, data=body, file=path)


def _explode_l0(idx: Index) -> None:
    """Index individual errors/types/constants/external_schemas/markers by id."""
    l0 = idx.l0
    for code, body in (l0.get("errors") or {}).items():
        idx.entries[code] = Entry(id=code, kind="error", data=body)
    for tid, body in (l0.get("types") or {}).items():
        idx.entries[tid] = Entry(id=tid, kind="type", data=body)
    for cid, body in (l0.get("constants") or {}).items():
        idx.entries[cid] = Entry(id=cid, kind="constant", data=body)
    for sid, body in (l0.get("external_schemas") or {}).items():
        idx.entries[sid] = Entry(id=sid, kind="external_schema", data=body)
    for marker, desc in (l0.get("side_effect_markers") or {}).items():
        idx.entries[marker] = Entry(id=marker, kind="marker", data={"description": desc})


# ---------- id dispatch ----------

_BUNDLEABLE = {"atom", "module", "journey", "flow", "artifact"}


def classify(idx: Index, entity_id: str) -> str:
    """Return the kind for an id, raising if unknown or not bundleable."""
    entry = idx.get(entity_id)
    if entry is None:
        raise KeyError(f"Unknown id: {entity_id}")
    if entry.kind not in _BUNDLEABLE:
        raise ValueError(
            f"{entity_id} is a {entry.kind}; only {sorted(_BUNDLEABLE)} "
            "can be bundled via `forge context`."
        )
    return entry.kind
