"""
Spec directory loader and flat id index for Forge v2.

Walks the spec/ directory, derives a full dot-path ID for every node from
its file path, and builds a flat dict for O(1) lookup.

ID resolution rules (applied to the path relative to spec/):
  1. Strip role-filename suffixes: system.yaml → parent dir, domain.yaml →
     parent dir, module.yaml → parent dir.
  2. For flat multi-doc files (implementation/): ID comes from each doc's own
     `id` field.
  3. Everything else: drop .yaml extension, join path parts with `.`.
  4. Prepend the conception name from conception.yaml.

Built-in scalars and errors from framework.yaml are indexed under the fixed
prefixes `system.types.*` and `system.errors.*`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# Registry directory names that hang directly off a system directory.
_REGISTRY_DIRS = frozenset({
    "types", "errors", "policies", "contracts",
    "integrations", "interactions", "flows", "constants",
})

# Maps registry dir name → node kind.
_REGISTRY_KIND: dict[str, str] = {
    "types": "type",
    "errors": "error",
    "policies": "policy",
    "contracts": "contract",
    "integrations": "integration",
    "interactions": "interaction",
    "flows": "flow",
    "constants": "constant",
}

# Maps implementation flat-file name → node kind (multi-doc).
_IMPL_KIND: dict[str, str] = {
    "datastores.yaml": "datastore",
    "tests.yaml": "test",
    "environments.yaml": "environment",
    "deployments.yaml": "deployment",
}

# Singleton role filenames — their directory IS the node.
_ROLE_FILES = frozenset({"system.yaml", "domain.yaml", "module.yaml"})


@dataclass
class Entry:
    id: str
    kind: str
    data: Any
    file: Path | None = None


@dataclass
class Index:
    spec_dir: Path
    conception_name: str = ""
    entries: dict[str, Entry] = field(default_factory=dict)
    framework: dict[str, Any] = field(default_factory=dict)

    def get(self, entity_id: str) -> Entry | None:
        return self.entries.get(entity_id)

    def by_kind(self, kind: str) -> list[Entry]:
        return [e for e in self.entries.values() if e.kind == kind]


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def resolve_spec_dir(explicit: str | None = None) -> Path:
    """Resolve spec dir from explicit arg, env var, or auto-discover.

    Auto-discovery walks up from cwd looking for spec/conception.yaml.
    """
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("FORGE_SPEC_DIR")
    if env:
        return Path(env).expanduser().resolve()

    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "spec" / "conception.yaml").is_file():
            return candidate / "spec"
        # Also accept if spec_dir itself is passed (conception.yaml at root).
        if (candidate / "conception.yaml").is_file():
            return candidate
    raise FileNotFoundError(
        "Cannot locate spec dir. Pass --spec-dir, set $FORGE_SPEC_DIR, "
        "or run `forge init` to bootstrap a new project.\n"
        "Expected: spec/conception.yaml relative to project root."
    )


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load(spec_dir: Path) -> Index:
    spec_dir = Path(spec_dir).resolve()
    if not spec_dir.is_dir():
        raise FileNotFoundError(f"Spec dir not found: {spec_dir}")

    idx = Index(spec_dir=spec_dir)

    # Load framework.yaml first (not a node — stored separately).
    framework_path = spec_dir / "framework.yaml"
    if framework_path.is_file():
        idx.framework = _load_yaml(framework_path) or {}
        _index_framework_builtins(idx)

    # Load conception.yaml to get the conception name.
    conception_path = spec_dir / "conception.yaml"
    if conception_path.is_file():
        data = _load_yaml(conception_path) or {}
        conception_id = data.get("id") or ""
        idx.conception_name = conception_id
        if conception_id:
            idx.entries[conception_id] = Entry(
                id=conception_id, kind="conception", data=data, file=conception_path
            )

    if not idx.conception_name:
        raise FileNotFoundError(
            f"conception.yaml not found or missing 'id' field at {spec_dir}"
        )

    # Walk all YAML files under spec_dir.
    for yaml_file in sorted(spec_dir.rglob("*.yaml")):
        rel = yaml_file.relative_to(spec_dir)
        parts = rel.parts  # e.g. ('shortener', 'types', 'ShortCode.yaml')

        # Skip already-handled top-level singletons.
        if len(parts) == 1:
            continue

        _index_file(idx, yaml_file, parts)

    return idx


def _index_file(idx: Index, yaml_file: Path, parts: tuple[str, ...]) -> None:
    fn = parts[-1]
    parent = parts[-2] if len(parts) >= 2 else ""

    # --- Structural singletons: system.yaml, domain.yaml, module.yaml ---
    if fn in _ROLE_FILES:
        kind = fn.replace(".yaml", "")  # "system", "domain", "module"
        node_id = _derive_id(idx.conception_name, parts[:-1])
        data = _load_yaml(yaml_file) or {}
        idx.entries[node_id] = Entry(id=node_id, kind=kind, data=data, file=yaml_file)
        return

    # --- Registry files: types/, errors/, policies/, etc. ---
    if parent in _REGISTRY_DIRS:
        kind = _REGISTRY_KIND[parent]
        node_id = _derive_id(idx.conception_name, (*parts[:-1], fn[:-5]))  # strip .yaml
        data = _load_yaml(yaml_file) or {}
        idx.entries[node_id] = Entry(id=node_id, kind=kind, data=data, file=yaml_file)
        return

    # --- Implementation flat multi-doc files ---
    if parent == "implementation" and fn in _IMPL_KIND:
        kind = _IMPL_KIND[fn]
        _index_multidoc(idx, yaml_file, kind)
        return

    # --- Element files: depth >= 4 (system/domain/module/element.yaml) ---
    if len(parts) >= 4:
        node_id = _derive_id(idx.conception_name, (*parts[:-1], fn[:-5]))
        data = _load_yaml(yaml_file) or {}
        idx.entries[node_id] = Entry(id=node_id, kind="element", data=data, file=yaml_file)
        # Index inline properties and operations so interactions can resolve caller/callee.
        _index_inline_subnodes(idx, data, yaml_file)
        return


def _index_inline_subnodes(idx: Index, element_data: Any, yaml_file: Path) -> None:
    """Index inline properties and operations from an element file.

    These are not independently bundleable but need index entries so that
    interaction caller/callee references can be validated.
    """
    if not isinstance(element_data, dict):
        return
    for section, kind in (("properties", "property"), ("operations", "operation")):
        for subnode in element_data.get(section) or []:
            if not isinstance(subnode, dict):
                continue
            sid = subnode.get("id")
            if sid:
                idx.entries[sid] = Entry(id=sid, kind=kind, data=subnode, file=yaml_file)


def _index_multidoc(idx: Index, yaml_file: Path, kind: str) -> None:
    """Index each YAML document in a flat multi-doc file by its own `id` field."""
    try:
        raw = yaml_file.read_text(encoding="utf-8")
    except OSError:
        return
    for doc in yaml.safe_load_all(raw):
        if not isinstance(doc, dict):
            continue
        node_id = doc.get("id")
        if not node_id:
            continue
        idx.entries[node_id] = Entry(id=node_id, kind=kind, data=doc, file=yaml_file)


def _index_framework_builtins(idx: Index) -> None:
    """Index built-in scalars and errors from framework.yaml."""
    fw = idx.framework
    for scalar in fw.get("scalars") or []:
        if not isinstance(scalar, dict):
            continue
        sid = scalar.get("id")
        if sid:
            idx.entries[sid] = Entry(id=sid, kind="type", data=scalar)
    for error in fw.get("errors") or []:
        if not isinstance(error, dict):
            continue
        eid = error.get("id")
        if eid:
            idx.entries[eid] = Entry(id=eid, kind="error", data=error)


# ---------------------------------------------------------------------------
# ID derivation
# ---------------------------------------------------------------------------

def _derive_id(conception_name: str, parts: tuple[str, ...]) -> str:
    """Join path parts with '.' and prepend the conception name."""
    return conception_name + "." + ".".join(parts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Classify for context bundling
# ---------------------------------------------------------------------------

_BUNDLEABLE = frozenset({"element"})


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
