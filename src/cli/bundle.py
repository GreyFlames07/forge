"""
Bundle formatter — renders a walker output dict as YAML, JSON, or markdown.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any

import yaml


# Human-readable headers for each bundle section.
_SECTION_HEADERS: dict[str, str] = {
    "target":                     "Target",
    "l0_registry_slice":          "L0 — Registry (sliced)",
    "l1_conventions":             "L1 — Conventions",
    "l2_module":                  "L2 — Owner Module",
    "l2_entry_points":            "L2 — Invoking Entry Points",
    "policies_applied":           "L2 — Policies Applied",
    "policies":                   "L2 — Policies",
    "shared_module_interfaces":   "L2 — Whitelisted Module Interfaces",
    "l3_atom":                    "L3 — Target Atom",
    "l3_artifact":                "L3 — Target Artifact",
    "owned_atoms":                "L3 — Owned Atoms",
    "owned_artifacts":            "L3 — Owned Artifacts",
    "called_atom_signatures":     "L3 — Called Atom Signatures",
    "producer_atom_signature":    "L3 — Producer Atom Signature",
    "source_artifacts":           "L3 — Upstream Source Artifacts",
    "consumer_signatures":        "L3 — Consumer Signatures",
    "training_artifact":          "L3 — Training Artifact",
    "handler_atoms":              "L3 — Handler Atoms",
    "step_atom_signatures":       "L3 — Step Atom Signatures",
    "l4_journey":                 "L4 — Target Journey",
    "l4_orchestration":           "L4 — Target Orchestration",
    "invoked_orchestrations":     "L4 — Invoked Orchestrations",
    "l4_callers":                 "L4 — Callers (atoms consumed here)",
    "l5_operations":              "L5 — Operations",
}


# Ensure PyYAML emits OrderedDicts in insertion order.
def _represent_ordered_dict(dumper, data):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())


yaml.add_representer(OrderedDict, _represent_ordered_dict)


def render(bundle: OrderedDict[str, Any], fmt: str = "yaml") -> str:
    if fmt == "json":
        return json.dumps(bundle, indent=2, default=_json_default)
    if fmt == "markdown":
        return _render_markdown(bundle)
    return _render_yaml(bundle)


def _render_yaml(bundle: OrderedDict[str, Any]) -> str:
    parts: list[str] = []
    target = bundle.get("target") or {}
    parts.append("# " + "=" * 66)
    parts.append(f"# FORGE CONTEXT BUNDLE")
    parts.append(f"# target: {target.get('id', '<unknown>')}")
    parts.append(f"# kind:   {target.get('kind', '<unknown>')}")
    if target.get("atom_kind"):
        parts.append(f"# atom_kind: {target['atom_kind']}")
    parts.append("# " + "=" * 66)
    parts.append("")

    for key, value in bundle.items():
        if key == "target":
            continue
        if value is None or (isinstance(value, (dict, list)) and not value):
            continue
        header = _SECTION_HEADERS.get(key, key)
        parts.append("# " + "-" * 66)
        parts.append(f"# {header}")
        parts.append("# " + "-" * 66)
        parts.append(yaml.dump({key: value}, sort_keys=False, allow_unicode=True,
                               default_flow_style=False, width=100).rstrip())
        parts.append("")

    return "\n".join(parts) + "\n"


def _render_markdown(bundle: OrderedDict[str, Any]) -> str:
    target = bundle.get("target") or {}
    parts: list[str] = [
        f"# Forge context: `{target.get('id', '<unknown>')}`",
        "",
        f"- **kind**: `{target.get('kind', '<unknown>')}`",
    ]
    if target.get("atom_kind"):
        parts.append(f"- **atom_kind**: `{target['atom_kind']}`")
    parts.append("")

    for key, value in bundle.items():
        if key == "target":
            continue
        if value is None or (isinstance(value, (dict, list)) and not value):
            continue
        header = _SECTION_HEADERS.get(key, key)
        parts.append(f"## {header}")
        parts.append("")
        parts.append("```yaml")
        parts.append(yaml.dump({key: value}, sort_keys=False, allow_unicode=True,
                               default_flow_style=False, width=100).rstrip())
        parts.append("```")
        parts.append("")
    return "\n".join(parts)


def _json_default(o: Any) -> Any:
    if isinstance(o, OrderedDict):
        return dict(o)
    raise TypeError(f"Unserializable: {type(o)}")
