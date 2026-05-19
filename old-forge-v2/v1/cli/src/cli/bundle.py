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
    "target":           "Target",
    "element":          "Element",
    "module":           "Module",
    "domain":           "Domain",
    "system":           "System",
    "contracts":        "Contracts",
    "types":            "Types",
    "errors":           "Errors",
    "interactions":     "Interactions",
    "policies_applied": "Policies Applied",
    "datastores":       "Datastores",
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
    parts.append("# FORGE CONTEXT BUNDLE")
    parts.append(f"# target: {target.get('id', '<unknown>')}")
    parts.append(f"# kind:   {target.get('kind', '<unknown>')}")
    if target.get("element_kind"):
        parts.append(f"# element_kind: {target['element_kind']}")
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
    if target.get("element_kind"):
        parts.append(f"- **element_kind**: `{target['element_kind']}`")
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
