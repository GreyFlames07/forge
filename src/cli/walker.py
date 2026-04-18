"""
Per-kind dependency walkers.

Each walker returns an ordered dict of section-name -> content, which
the bundle formatter renders in source order. Sections with None values
are omitted.

Walker outputs:
  - atom:     L0 slice, L1, L2 module, policies applied, types, atom
              spec, called signatures, L4 callers, L5
  - module:   L1, module spec, owned atoms (full), owned artifacts,
              applied policies, shared module interfaces, L0 slice, L5
  - journey:  L1, journey spec, entry point, handler atoms (full),
              invoked orchestrations (full), L0 slice, L5
  - flow:     L1, flow spec, trigger payload type, sequence atoms
              (signatures), compensation atoms (signatures), L0 slice, L5
  - artifact: L1, artifact spec, owner module, producer atom
              (signature), source artifacts (shallow), consumers
              (signatures), L0 schema type
"""

from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any

from cli.index import Entry, Index

# Side-effect markers that indicate a step mutates state (for saga
# compensation implication heuristic).
_MUTATING_MARKERS = {"WRITES_DB", "WRITES_FS", "WRITES_CACHE", "EMITS_EVENT", "CALLS_EXTERNAL"}

# Primitive types from L0.4 — not extracted from L0, filtered out.
_PRIMITIVES = {"string", "integer", "number", "boolean", "bigint", "bytes", "timestamp", "uuid"}

# Regex to pull id-shaped tokens out of free-form logic/invariant strings.
_ID_TOKEN = re.compile(
    r"const\.([A-Z][A-Z0-9_]+)"
    r"|external\.([a-z][a-z0-9_]*)\."
    r"|(atm\.[a-z]{3}\.[a-z_]+)"
    r"|((?<![A-Za-z0-9_.])[A-Z]{3}\.[A-Z]{3}\.\d{3})"
    r"|(reg\.[a-z]+\.[A-Z][a-zA-Z]+)"
)


# ======================================================================
# Public dispatch
# ======================================================================

def walk(idx: Index, entity_id: str) -> tuple[OrderedDict[str, Any], list[str]]:
    """Build a context bundle for entity_id. Returns (bundle, unresolved_ids)."""
    entry = idx.get(entity_id)
    if entry is None:
        raise KeyError(f"Unknown id: {entity_id}")

    unresolved: list[str] = []
    dispatch = {
        "atom":     expand_atom,
        "module":   expand_module,
        "journey":  expand_journey,
        "flow":     expand_flow,
        "artifact": expand_artifact,
    }
    fn = dispatch.get(entry.kind)
    if fn is None:
        raise ValueError(f"{entity_id} (kind={entry.kind}) is not bundleable")

    bundle = fn(idx, entry, unresolved)
    return bundle, unresolved


# ======================================================================
# Atom walker
# ======================================================================

def expand_atom(idx: Index, atom: Entry, unresolved: list[str]) -> OrderedDict[str, Any]:
    spec = atom.data.get("spec") or {}
    owner_id = atom.data.get("owner_module")
    owner = idx.get(owner_id) if owner_id else None

    type_ids = _collect_type_ids(spec)
    error_codes = _collect_error_codes(spec)
    constants = _collect_constants_from_text(_logic_text(spec))
    markers = set(spec.get("side_effects") or [])
    external_schemas = _collect_external_schemas(_logic_text(spec))
    called_atom_ids = _collect_called_atoms(spec)

    # MODEL atom pulls in its training data artifact.
    training_artifact = None
    if atom.data.get("kind") == "MODEL":
        ts = (spec.get("training_contract") or {}).get("data_source")
        if ts:
            training_artifact = _resolve(idx, ts, "artifact", unresolved)
        fb = (spec.get("fallback") or {}).get("invoke")
        if fb:
            called_atom_ids.add(fb)

    # L1 propagation wrap_unexpected code is universally relevant.
    unexpected_code = (idx.l1.get("failure", {}).get("propagation", {}) or {}).get("unexpected_code")
    if unexpected_code:
        error_codes.add(unexpected_code)

    # Applicable policies: those listed on owner module whose applies_when
    # predicate matches this atom.
    policies_applied = _filter_policies_for_atom(idx, atom, owner)

    # L4 callers.
    callers = _find_atom_callers(idx, atom.id)

    # Called atom signatures.
    called_sigs = OrderedDict()
    for aid in sorted(called_atom_ids):
        called_sigs[aid] = _atom_signature(idx, aid, unresolved)

    l0_slice = _build_l0_slice(
        idx,
        type_ids=type_ids,
        error_codes=error_codes,
        constant_ids=constants,
        markers=markers,
        external_schemas=external_schemas,
    )

    bundle: OrderedDict[str, Any] = OrderedDict()
    bundle["target"] = {"id": atom.id, "kind": "atom", "atom_kind": atom.data.get("kind")}
    bundle["l0_registry_slice"] = l0_slice
    bundle["l1_conventions"] = idx.l1
    if owner:
        bundle["l2_module"] = owner.data
    else:
        bundle["l2_module"] = None
        unresolved.append(owner_id or "<missing owner_module>")
    bundle["policies_applied"] = policies_applied
    bundle["l3_atom"] = atom.data
    bundle["called_atom_signatures"] = called_sigs
    if training_artifact is not None:
        bundle["training_artifact"] = training_artifact
    bundle["l4_callers"] = callers
    bundle["l5_operations"] = idx.l5
    return bundle


# ======================================================================
# Module walker
# ======================================================================

def expand_module(idx: Index, module: Entry, unresolved: list[str]) -> OrderedDict[str, Any]:
    owned_atoms = module.data.get("owned_atoms") or []
    owned_artifacts = module.data.get("owned_artifacts") or []
    dep_modules = (module.data.get("dependency_whitelist") or {}).get("modules") or []
    policy_ids = module.data.get("policies") or []

    # Full expansion of each owned atom.
    atoms_full: OrderedDict[str, Any] = OrderedDict()
    aggregated_type_ids: set[str] = set()
    aggregated_errors: set[str] = set()
    aggregated_constants: set[str] = set()
    aggregated_markers: set[str] = set()
    aggregated_externals: set[str] = set()

    for aid in owned_atoms:
        entry = idx.get(aid)
        if entry is None:
            unresolved.append(aid)
            atoms_full[aid] = {"status": "UNRESOLVED"}
            continue
        atoms_full[aid] = entry.data
        spec = entry.data.get("spec") or {}
        aggregated_type_ids |= _collect_type_ids(spec)
        aggregated_errors |= _collect_error_codes(spec)
        aggregated_constants |= _collect_constants_from_text(_logic_text(spec))
        aggregated_markers |= set(spec.get("side_effects") or [])
        aggregated_externals |= _collect_external_schemas(_logic_text(spec))

    # Include datastores' entity types.
    for datastore in (module.data.get("persistence_schema") or {}).get("datastores") or []:
        if datastore.get("type"):
            aggregated_type_ids.add(datastore["type"])

    artifacts_full = OrderedDict()
    for art_id in owned_artifacts:
        entry = idx.get(art_id)
        artifacts_full[art_id] = entry.data if entry else {"status": "UNRESOLVED"}
        if entry is None:
            unresolved.append(art_id)

    # Shared module interfaces (signatures only).
    shared_deps = OrderedDict()
    for mid in dep_modules:
        entry = idx.get(mid)
        if entry:
            shared_deps[mid] = {
                "id": entry.data.get("id"),
                "description": entry.data.get("description"),
                "interface": entry.data.get("interface"),
            }
        else:
            shared_deps[mid] = {"status": "UNRESOLVED"}
            unresolved.append(mid)

    policies = OrderedDict()
    for pid in policy_ids:
        entry = idx.get(pid)
        policies[pid] = entry.data if entry else {"status": "UNRESOLVED"}
        if entry is None:
            unresolved.append(pid)

    l0_slice = _build_l0_slice(
        idx,
        type_ids=aggregated_type_ids,
        error_codes=aggregated_errors,
        constant_ids=aggregated_constants,
        markers=aggregated_markers,
        external_schemas=aggregated_externals,
    )

    bundle: OrderedDict[str, Any] = OrderedDict()
    bundle["target"] = {"id": module.id, "kind": "module"}
    bundle["l0_registry_slice"] = l0_slice
    bundle["l1_conventions"] = idx.l1
    bundle["l2_module"] = module.data
    bundle["policies"] = policies
    bundle["shared_module_interfaces"] = shared_deps
    bundle["owned_atoms"] = atoms_full
    bundle["owned_artifacts"] = artifacts_full
    bundle["l5_operations"] = idx.l5
    return bundle


# ======================================================================
# Journey walker
# ======================================================================

def expand_journey(idx: Index, journey: Entry, unresolved: list[str]) -> OrderedDict[str, Any]:
    handlers = journey.data.get("handlers") or {}
    transitions = journey.data.get("transitions") or []

    handler_atoms: OrderedDict[str, Any] = OrderedDict()
    invoked_flows: OrderedDict[str, Any] = OrderedDict()
    aggregated_type_ids: set[str] = set()
    aggregated_errors: set[str] = set()
    aggregated_constants: set[str] = set()
    aggregated_markers: set[str] = set()
    aggregated_externals: set[str] = set()

    for state, handler in handlers.items():
        aid = handler.get("atom") if isinstance(handler, dict) else None
        if aid:
            entry = idx.get(aid)
            if entry:
                handler_atoms[aid] = entry.data
                spec = entry.data.get("spec") or {}
                aggregated_type_ids |= _collect_type_ids(spec)
                aggregated_errors |= _collect_error_codes(spec)
                aggregated_constants |= _collect_constants_from_text(_logic_text(spec))
                aggregated_markers |= set(spec.get("side_effects") or [])
                aggregated_externals |= _collect_external_schemas(_logic_text(spec))
            else:
                handler_atoms[aid] = {"status": "UNRESOLVED"}
                unresolved.append(aid)

    for t in transitions:
        inv = t.get("invoke") if isinstance(t, dict) else None
        if not inv:
            continue
        entry = idx.get(inv)
        if entry is None:
            unresolved.append(inv)
            continue
        if entry.kind == "flow":
            invoked_flows[inv] = entry.data
        elif entry.kind == "atom" and inv not in handler_atoms:
            handler_atoms[inv] = entry.data

    # L2 entry points that invoke this journey.
    entry_points = []
    for mod in idx.by_kind("module"):
        for ep in (mod.data.get("interface") or {}).get("entry_points") or []:
            if ep.get("invokes") == journey.id:
                entry_points.append({"owner_module": mod.id, **ep})

    l0_slice = _build_l0_slice(
        idx,
        type_ids=aggregated_type_ids,
        error_codes=aggregated_errors,
        constant_ids=aggregated_constants,
        markers=aggregated_markers,
        external_schemas=aggregated_externals,
    )

    bundle: OrderedDict[str, Any] = OrderedDict()
    bundle["target"] = {"id": journey.id, "kind": "journey"}
    bundle["l0_registry_slice"] = l0_slice
    bundle["l1_conventions"] = idx.l1
    bundle["l2_entry_points"] = entry_points
    bundle["l4_journey"] = journey.data
    bundle["handler_atoms"] = handler_atoms
    bundle["invoked_orchestrations"] = invoked_flows
    bundle["l5_operations"] = idx.l5
    return bundle


# ======================================================================
# Flow walker
# ======================================================================

def expand_flow(idx: Index, flow: Entry, unresolved: list[str]) -> OrderedDict[str, Any]:
    sequence = flow.data.get("sequence") or []

    step_sigs: OrderedDict[str, Any] = OrderedDict()
    aggregated_type_ids: set[str] = set()
    aggregated_errors: set[str] = set()
    aggregated_markers: set[str] = set()

    trigger = flow.data.get("trigger") or {}
    if trigger.get("payload_type"):
        aggregated_type_ids.add(trigger["payload_type"])

    for step in sequence:
        inv = step.get("invoke")
        comp = step.get("compensation")
        for aid in filter(None, [inv, comp]):
            if aid in step_sigs:
                continue
            step_sigs[aid] = _atom_signature(idx, aid, unresolved)
            entry = idx.get(aid)
            if entry and entry.kind == "atom":
                spec = entry.data.get("spec") or {}
                aggregated_type_ids |= _collect_type_ids(spec)
                aggregated_errors |= _collect_error_codes(spec)
                aggregated_markers |= set(spec.get("side_effects") or [])

    # L2 entry points that invoke this flow.
    entry_points = []
    for mod in idx.by_kind("module"):
        for ep in (mod.data.get("interface") or {}).get("entry_points") or []:
            if ep.get("invokes") == flow.id:
                entry_points.append({"owner_module": mod.id, **ep})

    l0_slice = _build_l0_slice(
        idx,
        type_ids=aggregated_type_ids,
        error_codes=aggregated_errors,
        constant_ids=set(),
        markers=aggregated_markers,
        external_schemas=set(),
    )

    bundle: OrderedDict[str, Any] = OrderedDict()
    bundle["target"] = {"id": flow.id, "kind": "flow"}
    bundle["l0_registry_slice"] = l0_slice
    bundle["l1_conventions"] = idx.l1
    bundle["l2_entry_points"] = entry_points
    bundle["l4_orchestration"] = flow.data
    bundle["step_atom_signatures"] = step_sigs
    bundle["l5_operations"] = idx.l5
    return bundle


# ======================================================================
# Artifact walker
# ======================================================================

def expand_artifact(idx: Index, artifact: Entry, unresolved: list[str]) -> OrderedDict[str, Any]:
    owner_id = artifact.data.get("owner_module")
    owner = idx.get(owner_id) if owner_id else None

    schema = artifact.data.get("schema")
    type_ids: set[str] = set()
    if isinstance(schema, str) and schema not in _PRIMITIVES:
        type_ids.add(schema)
    elif isinstance(schema, dict):
        type_ids |= _scan_types_in_fields(schema)

    prod = (artifact.data.get("provenance") or {}).get("produced_by")
    producer_sig = None
    if prod and prod not in ("external", "manual"):
        producer_sig = _atom_signature(idx, prod, unresolved)

    source_artifacts = OrderedDict()
    for sid in (artifact.data.get("provenance") or {}).get("source_artifacts") or []:
        entry = idx.get(sid)
        if entry:
            source_artifacts[sid] = {
                "description": entry.data.get("description"),
                "format": entry.data.get("format"),
                "schema": entry.data.get("schema"),
            }
        else:
            source_artifacts[sid] = {"status": "UNRESOLVED"}
            unresolved.append(sid)

    consumers = OrderedDict()
    for cid in artifact.data.get("consumers") or []:
        consumers[cid] = _atom_signature(idx, cid, unresolved)

    l0_slice = _build_l0_slice(
        idx,
        type_ids=type_ids,
        error_codes=set(),
        constant_ids=set(),
        markers=set(),
        external_schemas=set(),
    )

    bundle: OrderedDict[str, Any] = OrderedDict()
    bundle["target"] = {"id": artifact.id, "kind": "artifact"}
    bundle["l0_registry_slice"] = l0_slice
    bundle["l1_conventions"] = idx.l1
    bundle["l2_module"] = owner.data if owner else None
    if owner is None and owner_id:
        unresolved.append(owner_id)
    bundle["l3_artifact"] = artifact.data
    bundle["producer_atom_signature"] = producer_sig
    bundle["source_artifacts"] = source_artifacts
    bundle["consumer_signatures"] = consumers
    return bundle


# ======================================================================
# Shared helpers
# ======================================================================

def _atom_signature(idx: Index, atom_id: str, unresolved: list[str]) -> dict[str, Any]:
    entry = idx.get(atom_id)
    if entry is None or entry.kind != "atom":
        unresolved.append(atom_id)
        return {"status": "UNRESOLVED"}
    spec = entry.data.get("spec") or {}
    return {
        "kind": entry.data.get("kind"),
        "description": entry.data.get("description"),
        "input": spec.get("input"),
        "output": spec.get("output"),
        "side_effects": spec.get("side_effects"),
    }


def _resolve(idx: Index, entity_id: str, expected_kind: str, unresolved: list[str]) -> Any:
    entry = idx.get(entity_id)
    if entry is None or entry.kind != expected_kind:
        unresolved.append(entity_id)
        return {"status": "UNRESOLVED"}
    return entry.data


# ---------- collection primitives ----------

def _scan_types_in_fields(obj: Any, acc: set[str] | None = None) -> set[str]:
    """Recursively pull type_id strings out of inline field maps."""
    if acc is None:
        acc = set()
    if isinstance(obj, dict):
        t = obj.get("type")
        if isinstance(t, str) and t not in _PRIMITIVES:
            acc.add(t)
        for v in obj.values():
            _scan_types_in_fields(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _scan_types_in_fields(v, acc)
    return acc


def _collect_type_ids(spec: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    # PROCEDURAL: input + output.success as inline fields OR type id.
    inp = spec.get("input")
    if isinstance(inp, str) and inp not in _PRIMITIVES:
        out.add(inp)
    elif isinstance(inp, dict):
        out |= _scan_types_in_fields(inp)

    output = spec.get("output") or {}
    succ = output.get("success")
    if isinstance(succ, str) and succ not in _PRIMITIVES:
        out.add(succ)
    elif isinstance(succ, dict):
        out |= _scan_types_in_fields(succ)

    # COMPONENT: props, local_state, events_emitted.payload_type.
    for key in ("props", "local_state"):
        v = spec.get(key)
        if isinstance(v, dict):
            out |= _scan_types_in_fields(v)
    for evt in spec.get("events_emitted") or []:
        pt = evt.get("payload_type") if isinstance(evt, dict) else None
        if isinstance(pt, str) and pt not in _PRIMITIVES:
            out.add(pt)

    # MODEL: input_distribution, output_distribution.
    for key in ("input_distribution", "output_distribution"):
        v = spec.get(key)
        if isinstance(v, dict):
            out |= _scan_types_in_fields(v)

    # DECLARATIVE: desired_state may reference types.
    ds = spec.get("desired_state")
    if isinstance(ds, (dict, list)):
        out |= _scan_types_in_fields(ds)

    return out


def _collect_error_codes(spec: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for code in (spec.get("output") or {}).get("errors") or []:
        if isinstance(code, str):
            out.add(code)
    for fm in spec.get("failure_modes") or []:
        e = fm.get("error") if isinstance(fm, dict) else None
        if isinstance(e, str):
            out.add(e)
    # Error codes can also appear inside logic strings (RETURN PAY.VAL.001).
    for match in _ID_TOKEN.finditer(_logic_text(spec)):
        if match.group(4):
            out.add(match.group(4))
    return out


def _collect_called_atoms(spec: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for match in _ID_TOKEN.finditer(_logic_text(spec)):
        if match.group(3):
            out.add(match.group(3))
    for aid in spec.get("composes") or []:
        if isinstance(aid, str):
            out.add(aid)
    return out


def _collect_constants_from_text(text: str) -> set[str]:
    out: set[str] = set()
    for match in _ID_TOKEN.finditer(text):
        if match.group(1):
            out.add(match.group(1))
    return out


def _collect_external_schemas(text: str) -> set[str]:
    out: set[str] = set()
    for match in _ID_TOKEN.finditer(text):
        if match.group(2):
            out.add(match.group(2))
    return out


def _logic_text(spec: dict[str, Any]) -> str:
    """Stringify spec regions that may contain id tokens (logic, invariants)."""
    parts: list[str] = []
    for key in ("logic", "render_contract"):
        for line in spec.get(key) or []:
            parts.append(_stringify(line))
    invs = spec.get("invariants")
    if isinstance(invs, list):
        for line in invs:
            parts.append(_stringify(line))
    elif isinstance(invs, dict):
        for v in invs.values():
            for line in v or []:
                parts.append(_stringify(line))
    for fm in spec.get("failure_modes") or []:
        if isinstance(fm, dict):
            parts.append(_stringify(fm.get("trigger", "")))
    return "\n".join(parts)


def _stringify(x: Any) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return " ".join(f"{k}: {_stringify(v)}" for k, v in x.items())
    if isinstance(x, list):
        return " ".join(_stringify(v) for v in x)
    return str(x)


# ---------- L0 slice builder ----------

def _build_l0_slice(
    idx: Index,
    *,
    type_ids: set[str],
    error_codes: set[str],
    constant_ids: set[str],
    markers: set[str],
    external_schemas: set[str],
) -> OrderedDict[str, Any]:
    l0 = idx.l0
    # Transitive: referenced types may reference other types via fields.
    resolved_types: dict[str, Any] = {}
    frontier = set(type_ids)
    while frontier:
        tid = frontier.pop()
        if tid in resolved_types or tid in _PRIMITIVES:
            continue
        tdef = (l0.get("types") or {}).get(tid)
        if tdef is None:
            continue
        resolved_types[tid] = tdef
        # Pull any nested type refs out of this type's fields.
        frontier |= _scan_types_in_fields(tdef.get("fields") or {}) - resolved_types.keys()

    # Collect error categories referenced.
    referenced_categories: set[str] = set()
    resolved_errors: dict[str, Any] = {}
    for code in sorted(error_codes):
        err = (l0.get("errors") or {}).get(code)
        if err:
            resolved_errors[code] = err
            if err.get("category"):
                referenced_categories.add(err["category"])

    resolved_constants: dict[str, Any] = {}
    for cid in sorted(constant_ids):
        c = (l0.get("constants") or {}).get(cid)
        if c:
            resolved_constants[cid] = c

    resolved_markers: dict[str, str] = {}
    for m in sorted(markers):
        desc = (l0.get("side_effect_markers") or {}).get(m)
        if desc is not None:
            resolved_markers[m] = desc

    resolved_externals: dict[str, Any] = {}
    for sid in sorted(external_schemas):
        ext = (l0.get("external_schemas") or {}).get(sid)
        if ext:
            resolved_externals[sid] = ext

    resolved_categories: dict[str, str] = {}
    for cat in sorted(referenced_categories):
        desc = (l0.get("error_categories") or {}).get(cat)
        if desc is not None:
            resolved_categories[cat] = desc

    out: OrderedDict[str, Any] = OrderedDict()
    out["naming_ledger"] = l0.get("naming_ledger") or {}
    if resolved_categories:
        out["error_categories"] = resolved_categories
    if resolved_errors:
        out["errors"] = resolved_errors
    if resolved_types:
        out["types"] = resolved_types
    if resolved_constants:
        out["constants"] = resolved_constants
    if resolved_markers:
        out["side_effect_markers"] = resolved_markers
    if resolved_externals:
        out["external_schemas"] = resolved_externals
    return out


# ---------- policy predicate evaluator ----------

_POLICY_PATTERNS = re.compile(r'atom\.id\s+matches\s+"([^"]+)"')
_POLICY_SE = re.compile(r'atom\.side_effects\s+contains\s+([A-Z_]+)')


def _filter_policies_for_atom(
    idx: Index,
    atom: Entry,
    owner: Entry | None,
) -> OrderedDict[str, Any]:
    """Return applied policies keyed by policy id.

    Only evaluates policies listed on the owner module. Supports a narrow
    subset of predicate forms:
      - `atom.id matches "<pattern>"` with `*` as wildcard
      - `atom.side_effects contains <MARKER>`
      - conjunctions separated by ` and `
    """
    applied: OrderedDict[str, Any] = OrderedDict()
    if owner is None:
        return applied

    policy_ids = owner.data.get("policies") or []
    atom_id = atom.id
    markers = set((atom.data.get("spec") or {}).get("side_effects") or [])

    for pid in policy_ids:
        entry = idx.get(pid)
        if entry is None:
            continue
        predicate = entry.data.get("applies_when") or ""
        if _eval_predicate(predicate, atom_id, markers):
            applied[pid] = entry.data
    return applied


def _eval_predicate(predicate: str, atom_id: str, markers: set[str]) -> bool:
    if not predicate.strip():
        return True

    ok = True
    for clause in [c.strip() for c in predicate.split(" and ")]:
        m = _POLICY_PATTERNS.search(clause)
        if m:
            pattern = m.group(1).replace(".", r"\.").replace("*", ".*")
            if not re.fullmatch(pattern, atom_id):
                ok = False
            continue
        m = _POLICY_SE.search(clause)
        if m:
            if m.group(1) not in markers:
                ok = False
            continue
        # Unknown predicate form — conservative: skip application.
        ok = False
    return ok


# ---------- L4 caller scanner (for atoms) ----------

def _find_atom_callers(idx: Index, atom_id: str) -> OrderedDict[str, Any]:
    callers: OrderedDict[str, Any] = OrderedDict()

    # Orchestrations that invoke or compensate-with this atom.
    flows_ctx = []
    for flow in idx.by_kind("flow"):
        matches = []
        for step in flow.data.get("sequence") or []:
            role = None
            if step.get("invoke") == atom_id:
                role = "invoke"
            elif step.get("compensation") == atom_id:
                role = "compensation"
            if role:
                matches.append({
                    "role": role,
                    "step": step.get("step"),
                    "with": step.get("with"),
                    "on_error": step.get("on_error"),
                    "compensation": step.get("compensation"),
                })
        if matches:
            flows_ctx.append({
                "flow_id": flow.id,
                "transaction_boundary": flow.data.get("transaction_boundary"),
                "trigger": flow.data.get("trigger"),
                "matches": matches,
                "implications": _derive_flow_implications(flow.data, matches),
            })
    if flows_ctx:
        callers["orchestrations"] = flows_ctx

    # Journeys that use this atom as a handler or transition invoke.
    journeys_ctx = []
    for j in idx.by_kind("journey"):
        states_using = [s for s, h in (j.data.get("handlers") or {}).items()
                        if isinstance(h, dict) and h.get("atom") == atom_id]
        trans_using = [t for t in j.data.get("transitions") or []
                       if isinstance(t, dict) and t.get("invoke") == atom_id]
        if states_using or trans_using:
            journeys_ctx.append({
                "journey_id": j.id,
                "surface": j.data.get("surface"),
                "states": states_using,
                "transitions": trans_using,
            })
    if journeys_ctx:
        callers["journeys"] = journeys_ctx

    return callers


def _derive_flow_implications(flow: dict[str, Any], matches: list[dict[str, Any]]) -> list[str]:
    """Plain-English notes the implementing agent should honor."""
    out: list[str] = []
    tb = flow.get("transaction_boundary")
    for m in matches:
        if m["role"] == "invoke":
            oe = m.get("on_error") or {}
            for code, action in oe.items():
                action_str = str(action)
                if action_str.startswith("RETRY"):
                    out.append(
                        f"{code} → {action_str}: atom must be retry-safe "
                        f"(idempotency-key path required)."
                    )
                if "COMPENSATE" in action_str:
                    out.append(
                        f"{code} → {action_str}: atom's side effects must be "
                        f"reversible by its compensation, or not yet persisted "
                        f"when this error is returned."
                    )
            if tb == "saga" and m.get("compensation"):
                out.append(
                    f"Saga boundary with compensation={m['compensation']}: "
                    f"any mutations this atom makes must be reversible by that atom."
                )
        elif m["role"] == "compensation":
            out.append(
                f"Used as compensation for step '{m['step']}': must reverse the "
                f"effects of that step's invoke atom."
            )
    return out
