"""
Element context bundle walker for the Forge spec system.

walk(idx, element_id) returns an ordered dict of section → content plus a
list of unresolved references. The bundle formatter renders these sections
in insertion order.

Bundle sections:
  element          — full element data (with inline properties + operations)
  module           — parent module
  domain           — parent domain
  system           — parent system
  contracts        — contracts referenced by element operations
  types            — all types referenced by properties + operations (transitive)
  errors           — all errors raised by operations
  interactions     — interactions where element operations are caller or callee
  policies_applied — cascaded from conception → system → domain → module → element
  datastores       — datastores whose schemas reference this element
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from cli.index import Entry, Index

# Built-in scalar base IDs — not worth re-emitting in the bundle.
_BUILTIN_PREFIXES = ("system.types.", "system.errors.")


def walk(idx: Index, entity_id: str) -> tuple[OrderedDict[str, Any], list[str]]:
    """Build a context bundle for entity_id. Returns (bundle, unresolved_ids)."""
    entry = idx.get(entity_id)
    if entry is None:
        raise KeyError(f"Unknown id: {entity_id}")
    if entry.kind != "element":
        raise ValueError(
            f"{entity_id} (kind={entry.kind}) is not bundleable; "
            "only elements can be bundled via `forge context`."
        )

    unresolved: list[str] = []
    bundle = _expand_element(idx, entry, unresolved)
    return bundle, unresolved


# ---------------------------------------------------------------------------
# Element expander
# ---------------------------------------------------------------------------

def _expand_element(
    idx: Index, element: Entry, unresolved: list[str]
) -> OrderedDict[str, Any]:
    data = element.data or {}

    # --- Ancestor IDs derived from the element's dot-path ID ---
    parts = element.id.split(".")
    # ID shape: <conception>.<system>.<domain>.<module>.<element>
    # parts:      0           1        2        3        4
    module_id = ".".join(parts[:4]) if len(parts) >= 4 else None
    domain_id = ".".join(parts[:3]) if len(parts) >= 3 else None
    system_id = ".".join(parts[:2]) if len(parts) >= 2 else None
    conception_id = parts[0] if parts else None

    module = idx.get(module_id) if module_id else None
    domain = idx.get(domain_id) if domain_id else None
    system = idx.get(system_id) if system_id else None
    conception = idx.get(conception_id) if conception_id else None

    if module is None and module_id:
        unresolved.append(module_id)
    if domain is None and domain_id:
        unresolved.append(domain_id)

    # --- Inline properties and operations from element data ---
    properties: list[dict] = data.get("properties") or []
    operations: list[dict] = data.get("operations") or []

    # --- Collect referenced IDs ---
    type_ids: set[str] = set()
    error_ids: set[str] = set()
    contract_ids: set[str] = set()
    operation_ids: set[str] = set()

    for prop in properties:
        if isinstance(prop, dict):
            dt = prop.get("data_type")
            if isinstance(dt, str):
                type_ids.add(dt)

    for op in operations:
        if not isinstance(op, dict):
            continue
        op_id = op.get("id")
        if op_id:
            operation_ids.add(op_id)
        for tid in op.get("inputs") or []:
            if isinstance(tid, str):
                type_ids.add(tid)
        for tid in op.get("outputs") or []:
            if isinstance(tid, str):
                type_ids.add(tid)
        for eid in op.get("raises") or []:
            if isinstance(eid, str):
                error_ids.add(eid)
        cid = op.get("contract")
        if isinstance(cid, str):
            contract_ids.add(cid)

    # Pull types from referenced contracts.
    contracts: OrderedDict[str, Any] = OrderedDict()
    for cid in sorted(contract_ids):
        ce = idx.get(cid)
        if ce:
            contracts[cid] = ce.data
            for tid in ce.data.get("inputs") or []:
                if isinstance(tid, str):
                    type_ids.add(tid)
            for tid in ce.data.get("outputs") or []:
                if isinstance(tid, str):
                    type_ids.add(tid)
            for eid in ce.data.get("errors") or []:
                if isinstance(eid, str):
                    error_ids.add(eid)
        else:
            unresolved.append(cid)

    # --- Transitive type resolution ---
    types = _resolve_types_transitive(idx, type_ids, unresolved)

    # --- Errors ---
    errors: OrderedDict[str, Any] = OrderedDict()
    for eid in sorted(error_ids):
        ee = idx.get(eid)
        if ee:
            errors[eid] = ee.data
        else:
            unresolved.append(eid)

    # --- Interactions involving this element's operations ---
    interactions = _find_interactions(idx, operation_ids)

    # --- Policy cascade: conception → system → domain → module → element ---
    policies_applied = _cascade_policies(idx, [conception, system, domain, module, element], unresolved)

    # --- Datastores that reference this element ---
    datastores = _find_datastores(idx, element.id)

    # --- Assemble bundle ---
    bundle: OrderedDict[str, Any] = OrderedDict()
    bundle["target"] = {
        "id": element.id,
        "kind": "element",
        "element_kind": data.get("kind"),
    }
    bundle["element"] = data
    bundle["module"] = module.data if module else None
    bundle["domain"] = domain.data if domain else None
    bundle["system"] = system.data if system else None
    if contracts:
        bundle["contracts"] = contracts
    if types:
        bundle["types"] = types
    if errors:
        bundle["errors"] = errors
    if interactions:
        bundle["interactions"] = interactions
    if policies_applied:
        bundle["policies_applied"] = policies_applied
    if datastores:
        bundle["datastores"] = datastores

    return bundle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_types_transitive(
    idx: Index, seed_ids: set[str], unresolved: list[str]
) -> OrderedDict[str, Any]:
    """Resolve type IDs transitively. Composite types may reference other types."""
    resolved: OrderedDict[str, Any] = OrderedDict()
    frontier = set(seed_ids)
    seen: set[str] = set()

    while frontier:
        tid = frontier.pop()
        if tid in seen:
            continue
        seen.add(tid)

        # Skip built-ins (they are defined in framework.yaml, always available).
        if any(tid.startswith(p) for p in _BUILTIN_PREFIXES):
            te = idx.get(tid)
            if te:
                resolved[tid] = te.data
            continue

        te = idx.get(tid)
        if te is None:
            unresolved.append(tid)
            continue
        resolved[tid] = te.data

        # Composite types reference other types in their properties.
        for prop in te.data.get("properties") or []:
            if not isinstance(prop, dict):
                continue
            dt = prop.get("data_type")
            if isinstance(dt, str) and dt not in seen:
                frontier.add(dt)

    return resolved


def _find_interactions(
    idx: Index, operation_ids: set[str]
) -> OrderedDict[str, Any]:
    """Return interactions where any of the given operations are caller or callee."""
    result: OrderedDict[str, Any] = OrderedDict()
    if not operation_ids:
        return result
    for ie in idx.by_kind("interaction"):
        caller = ie.data.get("caller") if isinstance(ie.data, dict) else None
        callee = ie.data.get("callee") if isinstance(ie.data, dict) else None
        if caller in operation_ids or callee in operation_ids:
            result[ie.id] = ie.data
    return result


def _cascade_policies(
    idx: Index,
    ancestors: list[Entry | None],
    unresolved: list[str],
) -> OrderedDict[str, Any]:
    """Collect policies from each ancestor in order (conception to element).

    Policies are additive; lower nodes supplement, not override.
    """
    seen: set[str] = set()
    result: OrderedDict[str, Any] = OrderedDict()

    for node in ancestors:
        if node is None:
            continue
        data = node.data if isinstance(node.data, dict) else {}
        for pid in data.get("policies") or []:
            if not isinstance(pid, str) or pid in seen:
                continue
            seen.add(pid)
            pe = idx.get(pid)
            if pe:
                result[pid] = pe.data
            else:
                unresolved.append(pid)

    return result


def _find_datastores(idx: Index, element_id: str) -> OrderedDict[str, Any]:
    """Return datastores whose schemas reference this element."""
    result: OrderedDict[str, Any] = OrderedDict()
    for ds in idx.by_kind("datastore"):
        if not isinstance(ds.data, dict):
            continue
        for schema in ds.data.get("schemas") or []:
            if not isinstance(schema, dict):
                continue
            if schema.get("type") == element_id:
                result[ds.id] = ds.data
                break
    return result
