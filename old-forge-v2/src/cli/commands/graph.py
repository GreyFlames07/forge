from __future__ import annotations

from argparse import Namespace
import json
import platform
import subprocess
from pathlib import Path

from cli.commands.base import add_forge_dir_arg
from cli.common import find_forge_root
from cli.schema import load_schema

_MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"
_SVG_PAN_ZOOM_CDN = "https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"
_CYTOSCAPE_CDN = "https://cdn.jsdelivr.net/npm/cytoscape@3.30.4/dist/cytoscape.min.js"


def register_graph(subparsers) -> None:
    parser = subparsers.add_parser("graph", help="Render a Forge graph as HTML or raw Mermaid")
    add_forge_dir_arg(parser)
    parser.add_argument("--vertical", help="Filter to a vertical id")
    parser.add_argument("--runtime", action="store_true", help="Default the graph to runtime-focused relationships")
    parser.add_argument("--contracts", action="store_true", help="Default the graph to contract-focused relationships")
    parser.add_argument("--bootstrap", action="store_true", help="Default the graph to bootstrap-only relationships")
    parser.add_argument("--output", "-o", default="./forge-graph.html", help="Output HTML path. Default: ./forge-graph.html")
    parser.add_argument("--format", choices=["html", "mermaid"], default="html", help="Output format: html or raw mermaid")
    parser.add_argument("--no-open", action="store_true", help="Do not auto-open the generated HTML file")
    parser.set_defaults(func=run)


def _safe_id(value: str) -> str:
    return value.replace(".", "_").replace("-", "_").replace(" ", "_").replace("/", "_")


def _node_label(item: dict) -> str:
    name = item.get("name") or item.get("id") or item.get("kind", "unknown")
    kind = item.get("kind", "")
    return f"{name}<br/><small>{kind}</small>"


def _kind_style(kind: str) -> str:
    mapping = {
        "unit": "fill:#14213d,stroke:#60a5fa,color:#dbeafe",
        "operation": "fill:#102a23,stroke:#34d399,color:#d1fae5",
        "surface": "fill:#2a1a3a,stroke:#c084fc,color:#f3e8ff",
        "type": "fill:#312e18,stroke:#f59e0b,color:#fef3c7",
        "store": "fill:#0a1f14,stroke:#10b981,color:#d1fae5",
        "flow": "fill:#2b1d14,stroke:#fb923c,color:#ffedd5",
        "verification": "fill:#1f2937,stroke:#94a3b8,color:#e5e7eb",
    }
    return mapping.get(kind, "fill:#1f2937,stroke:#94a3b8,color:#e5e7eb")


def _all_nodes(schema) -> dict[str, dict]:
    nodes: dict[str, dict] = {}
    for item in schema.collections["units"]:
        env_chip = " | ".join(schema.system.get("promotion_stages", []))
        label = f"{item.get('name', item['id'])}<br/><small>{item.get('kind', 'unit')}</small>"
        if env_chip:
            label += f"<br/><small>[{env_chip}]</small>"
        nodes[item["id"]] = {"id": item["id"], "label": label, "kind": "unit", "unit_kind": item.get("kind", "unit")}
    for item in schema.collections["operations"]:
        nodes[item["id"]] = {
            "id": item["id"],
            "label": _node_label({"kind": "operation", **item}),
            "kind": "operation",
            "unit": item.get("unit"),
            "vertical": item.get("vertical"),
        }
    for item in schema.collections["surfaces"]:
        nodes[item["id"]] = {
            "id": item["id"],
            "label": _node_label({"kind": "surface", **item}),
            "kind": "surface",
            "unit": item.get("unit"),
            "transport": item.get("transport"),
            "vertical": item.get("vertical"),
        }
    for item in schema.collections["types"]:
        nodes[item["id"]] = {"id": item["id"], "label": _node_label({"kind": "type", **item}), "kind": "type"}
    for item in schema.collections["stores"]:
        nodes[item["id"]] = {"id": item["id"], "label": _node_label({"kind": "store", **item}), "kind": "store"}
    for item in schema.collections["flows"]:
        nodes[item["id"]] = {"id": item["id"], "label": _node_label({"kind": "flow", **item}), "kind": "flow"}
    for group, items in schema.verification.items():
        for item in items:
            item_id = f"verification.{group}.{item['id']}"
            nodes[item_id] = {
                "id": item_id,
                "label": f"{item.get('id', item_id)}<br/><small>verification:{group}</small>",
                "kind": "verification",
                "verification_group": group,
            }
    return nodes


def _add_edge(edges: list[dict], src: str | None, dst: str | None, label: str, family: str) -> None:
    if src and dst:
        edges.append({"src": src, "dst": dst, "label": label, "family": family})


def _all_edges(schema) -> list[dict]:
    edges: list[dict] = []
    for item in schema.collections["units"]:
        unit_id = item["id"]
        for ref in item.get("depends_on", {}).get("units", []):
            _add_edge(edges, unit_id, ref, "depends on", "runtime")
        for ref in item.get("depends_on", {}).get("stores", []):
            _add_edge(edges, unit_id, ref, "uses", "runtime")
    for item in schema.collections["operations"]:
        op_id = item["id"]
        _add_edge(edges, item.get("unit"), op_id, "implements", "runtime")
        for ref in item.get("inputs", []):
            _add_edge(edges, op_id, ref, "input", "contract")
        for ref in item.get("outputs", []):
            _add_edge(edges, op_id, ref, "output", "contract")
        for ref in item.get("referenced_types", []):
            _add_edge(edges, op_id, ref, "ref", "contract")
        for ref in item.get("errors", []):
            _add_edge(edges, op_id, ref, "error", "contract")
        for ref in item.get("reads", {}).get("types", []):
            _add_edge(edges, op_id, ref, "reads", "contract")
        for ref in item.get("writes", {}).get("types", []):
            _add_edge(edges, op_id, ref, "writes", "contract")
        for ref in item.get("reads", {}).get("stores", []):
            _add_edge(edges, op_id, ref, "reads", "runtime")
        for ref in item.get("writes", {}).get("stores", []):
            _add_edge(edges, op_id, ref, "writes", "runtime")
        for ref in item.get("emits", []):
            _add_edge(edges, op_id, ref, "emits", "contract")
        for ref in item.get("consumes", []):
            _add_edge(edges, ref, op_id, "consumed by", "contract")
    for item in schema.collections["surfaces"]:
        surface_id = item["id"]
        _add_edge(edges, item.get("unit"), surface_id, "exposes", "runtime")
        _add_edge(edges, surface_id, item.get("operation"), "calls", "runtime")
    for item in schema.collections["types"]:
        type_id = item["id"]
        persistence = item.get("persistence", {})
        _add_edge(edges, type_id, persistence.get("store"), "store", "persistence")
        _add_edge(edges, type_id, persistence.get("metadata_store"), "metadata", "persistence")
        _add_edge(edges, type_id, persistence.get("payload_store"), "payload", "persistence")
    for item in schema.collections["flows"]:
        flow_id = item["id"]
        for step in item.get("path", []):
            _add_edge(edges, flow_id, step.get("ref"), step.get("kind", "step"), "flow")
    for item in schema.verification["startup"]:
        _add_edge(edges, f"verification.startup.{item['id']}", item.get("unit"), "checks", "verification")
    for item in schema.verification["surfaces"]:
        _add_edge(edges, f"verification.surfaces.{item['id']}", item.get("surface"), "checks", "verification")
    for item in schema.verification["flows"]:
        _add_edge(edges, f"verification.flows.{item['id']}", item.get("flow"), "checks", "verification")
    deduped: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()
    for edge in edges:
        key = (edge["src"], edge["dst"], edge["label"], edge["family"])
        if key not in seen:
            seen.add(key)
            deduped.append(edge)
    return deduped


def _vertical_scope(schema, vertical_id: str, edges: list[dict]) -> tuple[dict[str, dict], list[dict]]:
    nodes = _all_nodes(schema)
    allowed: set[str] = set()
    for collection in ("operations", "surfaces", "types", "flows"):
        for item in schema.collections[collection]:
            if item.get("vertical") == vertical_id:
                allowed.add(item["id"])
                if item.get("unit"):
                    allowed.add(item["unit"])
    for item in schema.collections["operations"]:
        if item.get("vertical") == vertical_id:
            allowed.update(item.get("reads", {}).get("stores", []))
            allowed.update(item.get("writes", {}).get("stores", []))
    expanded = set(allowed)
    for edge in edges:
        if edge["src"] in allowed or edge["dst"] in allowed:
            expanded.add(edge["src"])
            expanded.add(edge["dst"])
    filtered_edges = [edge for edge in edges if edge["src"] in expanded and edge["dst"] in expanded]
    filtered_nodes = {node_id: node for node_id, node in nodes.items() if node_id in expanded}
    return filtered_nodes, filtered_edges


def _preset_families(args: Namespace) -> list[str]:
    if args.bootstrap:
        return ["runtime", "contract", "persistence", "verification"]
    if args.runtime:
        return ["runtime", "verification"]
    if args.contracts:
        return ["contract", "persistence"]
    return ["runtime", "contract", "persistence", "verification", "flow"]


def _bootstrap_related_ids(schema) -> set[str]:
    related: set[str] = set()
    related.update(schema.bootstrap.get("required_units", []))
    related.update(schema.bootstrap.get("required_surfaces", []))
    related.update(schema.bootstrap.get("required_stores", []))
    required_surfaces = set(schema.bootstrap.get("required_surfaces", []))
    required_units = set(schema.bootstrap.get("required_units", []))
    required_ops = {
        item.get("operation")
        for item in schema.collections["surfaces"]
        if item.get("id") in required_surfaces and item.get("operation")
    }
    related.update(required_ops)
    for item in schema.collections["operations"]:
        if item.get("id") in required_ops:
            if item.get("vertical"):
                related.add(item["vertical"])
            related.update(item.get("inputs", []))
            related.update(item.get("outputs", []))
            related.update(item.get("referenced_types", []))
    for item in schema.collections["flows"]:
        step_refs = {step.get("ref") for step in item.get("path", []) if step.get("ref")}
        if step_refs & (required_surfaces | required_ops):
            related.add(item["id"])
    for item in schema.verification["startup"]:
        if item.get("unit") in required_units:
            related.add(f"verification.startup.{item['id']}")
    for item in schema.verification["surfaces"]:
        if item.get("surface") in required_surfaces:
            related.add(f"verification.surfaces.{item['id']}")
    for item in schema.verification["flows"]:
        if item.get("flow") in related:
            related.add(f"verification.flows.{item['id']}")
    return related


def _layout_payload(schema, nodes: dict[str, dict]) -> dict:
    bootstrap_related = _bootstrap_related_ids(schema)
    bootstrap_verticals = {
        item.get("vertical")
        for item in schema.collections["surfaces"]
        if item.get("id") in schema.bootstrap.get("required_surfaces", []) and item.get("vertical")
    }
    bootstrap_verticals.update(
        item.get("vertical")
        for item in schema.collections["operations"]
        if item.get("id") in bootstrap_related and item.get("vertical")
    )
    layers = {
        "units": [item["id"] for item in schema.collections["units"] if item["id"] in nodes],
        "surfaces": [item["id"] for item in schema.collections["surfaces"] if item["id"] in nodes],
        "operations": [item["id"] for item in schema.collections["operations"] if item["id"] in nodes],
        "types": [item["id"] for item in schema.collections["types"] if item["id"] in nodes],
        "stores": [item["id"] for item in schema.collections["stores"] if item["id"] in nodes],
        "flows": [item["id"] for item in schema.collections["flows"] if item["id"] in nodes],
        "verification": [node_id for node_id, node in nodes.items() if node["kind"] == "verification"],
    }
    bootstrap_slice = {
        "id": "bootstrap",
        "label": "Bootstrap",
        "members": {
            "units": [item["id"] for item in schema.collections["units"] if item["id"] in bootstrap_related and item["id"] in nodes],
            "surfaces": [item["id"] for item in schema.collections["surfaces"] if item["id"] in bootstrap_related and item["id"] in nodes],
            "operations": [item["id"] for item in schema.collections["operations"] if item["id"] in bootstrap_related and item["id"] in nodes],
            "types": [item["id"] for item in schema.collections["types"] if item["id"] in bootstrap_related and item["id"] in nodes],
            "stores": [item["id"] for item in schema.collections["stores"] if item["id"] in bootstrap_related and item["id"] in nodes],
            "flows": [item["id"] for item in schema.collections["flows"] if item["id"] in bootstrap_related and item["id"] in nodes],
        },
        "bootstrap_related": True,
    }
    claimed_by_band = {band: set(member_ids) for band, member_ids in bootstrap_slice["members"].items()}
    additional_slices = []
    for vertical in schema.collections["verticals"]:
        if vertical["id"] in bootstrap_verticals:
            continue
        raw_members = {
            "units": sorted(
                {
                    item.get("unit")
                    for item in schema.collections["surfaces"] + schema.collections["operations"]
                    if item.get("vertical") == vertical["id"] and item.get("unit") in nodes
                }
            ),
            "surfaces": [item["id"] for item in schema.collections["surfaces"] if item.get("vertical") == vertical["id"] and item["id"] in nodes],
            "operations": [item["id"] for item in schema.collections["operations"] if item.get("vertical") == vertical["id"] and item["id"] in nodes],
            "types": [item["id"] for item in schema.collections["types"] if item.get("vertical") == vertical["id"] and item["id"] in nodes],
            "stores": sorted(
                {
                    store_id
                    for item in schema.collections["operations"]
                    if item.get("vertical") == vertical["id"]
                    for store_id in item.get("reads", {}).get("stores", []) + item.get("writes", {}).get("stores", [])
                    if store_id and store_id in nodes
                }
                | {
                    store_id
                    for type_item in schema.collections["types"]
                    if type_item.get("vertical") == vertical["id"]
                    for store_id in [
                        type_item.get("persistence", {}).get("store"),
                        type_item.get("persistence", {}).get("metadata_store"),
                        type_item.get("persistence", {}).get("payload_store"),
                    ]
                    if store_id and store_id in nodes
                }
            ),
            "flows": [item["id"] for item in schema.collections["flows"] if item.get("vertical") == vertical["id"] and item["id"] in nodes],
        }
        members = {
            band: [member_id for member_id in member_ids if member_id not in claimed_by_band.setdefault(band, set())]
            for band, member_ids in raw_members.items()
        }
        if any(members.values()):
            for band, member_ids in members.items():
                claimed_by_band[band].update(member_ids)
            additional_slices.append(
                {
                    "id": vertical["id"],
                    "label": vertical.get("name", vertical["id"]),
                    "members": members,
                    "bootstrap_related": False,
                }
            )
    assigned_members = set()
    for member_list in bootstrap_slice["members"].values():
        assigned_members.update(member_list)
    for slice_item in additional_slices:
        for member_list in slice_item["members"].values():
            assigned_members.update(member_list)
    overflow_members = {
        "units": [item["id"] for item in schema.collections["units"] if item["id"] in nodes and item["id"] not in assigned_members],
        "surfaces": [item["id"] for item in schema.collections["surfaces"] if item["id"] in nodes and item["id"] not in assigned_members],
        "operations": [item["id"] for item in schema.collections["operations"] if item["id"] in nodes and item["id"] not in assigned_members],
        "types": [item["id"] for item in schema.collections["types"] if item["id"] in nodes and item["id"] not in assigned_members],
        "stores": [item["id"] for item in schema.collections["stores"] if item["id"] in nodes and item["id"] not in assigned_members],
        "flows": [item["id"] for item in schema.collections["flows"] if item["id"] in nodes and item["id"] not in assigned_members],
    }
    if any(overflow_members.values()):
        additional_slices.append(
            {
                "id": "shared",
                "label": "Shared",
                "members": overflow_members,
                "bootstrap_related": False,
            }
        )
    return {
        "layers": layers,
        "bootstrapSlice": bootstrap_slice,
        "additionalSlices": additional_slices,
        "deploymentLabel": " -> ".join(schema.system.get("promotion_stages", [])) or "deployments",
        "bootstrapRelated": sorted(bootstrap_related & set(nodes)),
    }


def _mermaid_from_projection(
    nodes: dict[str, dict],
    edges: list[dict],
    layout: dict,
    selected_node_kinds: list[str],
    selected_families: list[str],
) -> str:
    included_nodes = {node_id: node for node_id, node in nodes.items() if node["kind"] in selected_node_kinds}
    lines: list[str] = ["graph TB"]
    slice_heads: list[str] = []
    hidden_links: list[str] = []

    def emit_band(container: str, label: str, node_ids: list[str]) -> str | None:
        visible = [node_id for node_id in node_ids if node_id in included_nodes]
        if not visible:
            return None
        anchor_id = f"{container}_anchor"
        lines.append(f'        subgraph {container}["{label}"]')
        lines.append(f'            {anchor_id}[" "]')
        if len(visible) <= 4:
            lines.append("            direction LR")
            for node_id in visible:
                lines.append(f'            {_safe_id(node_id)}["{included_nodes[node_id]["label"]}"]')
        else:
            lines.append("            direction TB")
            for index in range(0, len(visible), 4):
                row = visible[index:index + 4]
                lines.append(f'            subgraph {container}_row_{index // 4}[" "]')
                lines.append("                direction LR")
                for node_id in row:
                    lines.append(f'                {_safe_id(node_id)}["{included_nodes[node_id]["label"]}"]')
                lines.append("            end")
        lines.append("        end")
        hidden_links.append(f"    {anchor_id} --> {_safe_id(visible[0])}")
        return anchor_id

    def emit_slice(slice_id: str, label: str, members: dict[str, list[str]], bootstrap_related: bool) -> None:
        nonlocal slice_heads
        visible_members = {
            key: [node_id for node_id in values if node_id in included_nodes]
            for key, values in members.items()
        }
        if not any(visible_members.values()):
            return
        container = f"slice_{_safe_id(slice_id)}"
        lines.append(f'        subgraph {container}["{label}"]')
        lines.append("            direction TB")
        band_anchors: list[str] = []
        units_anchor = emit_band(f"{container}_units", "Units", visible_members["units"])
        if units_anchor:
            band_anchors.append(units_anchor)
        if "flow" in selected_node_kinds:
            flows_anchor = emit_band(f"{container}_flows", "Flows", visible_members["flows"])
            if flows_anchor:
                band_anchors.append(flows_anchor)
        surfaces_anchor = emit_band(f"{container}_surfaces", "Surfaces", visible_members["surfaces"])
        if surfaces_anchor:
            band_anchors.append(surfaces_anchor)
        operations_anchor = emit_band(f"{container}_operations", "Operations", visible_members["operations"])
        if operations_anchor:
            band_anchors.append(operations_anchor)
        types_anchor = emit_band(f"{container}_types", "Types", visible_members["types"])
        if types_anchor:
            band_anchors.append(types_anchor)
        stores_anchor = emit_band(f"{container}_stores", "Stores", visible_members["stores"])
        if stores_anchor:
            band_anchors.append(stores_anchor)
        lines.append("        end")
        for upper, lower in zip(band_anchors, band_anchors[1:]):
            hidden_links.append(f"    {upper} --> {lower}")
        first_member = next(
            (
                node_id
                for key in ("units", "flows", "surfaces", "operations", "types", "stores")
                for node_id in visible_members[key]
            ),
            None,
        )
        if first_member:
            slice_heads.append(_safe_id(first_member))
        if bootstrap_related:
            lines.append(f"        style {container} fill:#2b1111,stroke:#ef4444,color:#fee2e2,stroke-width:2px")
        else:
            lines.append(f"        style {container} fill:#111827,stroke:#334155,color:#e2e8f0")

    bootstrap_slice = layout["bootstrapSlice"]
    lines.append('    subgraph slice_row["Slices"]')
    lines.append("        direction LR")
    emit_slice(bootstrap_slice["id"], bootstrap_slice["label"], bootstrap_slice["members"], True)
    for slice_item in layout["additionalSlices"]:
        emit_slice(slice_item["id"], slice_item["label"], slice_item["members"], False)
    lines.append('        slice_layout_anchor[" "]')
    lines.append("    end")
    lines.append("    style slice_layout_anchor fill:transparent,stroke:transparent,color:transparent")

    verification_nodes = [node_id for node_id in layout["layers"]["verification"] if node_id in included_nodes]
    if verification_nodes:
        lines.append('    subgraph verification_band["Verification"]')
        lines.append("        direction LR")
        lines.append('        verification_layout_anchor[" "]')
        for node_id in verification_nodes:
            lines.append(f'        {_safe_id(node_id)}["{included_nodes[node_id]["label"]}"]')
        lines.append("    end")
        lines.append("    style verification_band fill:#0f172a,stroke:#64748b,color:#e2e8f0")
        lines.append("    style verification_layout_anchor fill:transparent,stroke:transparent,color:transparent")
        hidden_links.append("    slice_layout_anchor --> verification_layout_anchor")

    if len(slice_heads) > 1:
        for left, right in zip(slice_heads, slice_heads[1:]):
            hidden_links.append(f"    {left} ~~~ {right}")
    lines.append("")
    lines.extend(hidden_links)
    lines.append("")
    for edge in edges:
        if edge["family"] not in selected_families:
            continue
        if edge["src"] not in included_nodes or edge["dst"] not in included_nodes:
            continue
        arrow = f'-->|"{edge["label"]}"|' if edge["label"] else "-->"
        lines.append(f"    {_safe_id(edge['src'])} {arrow} {_safe_id(edge['dst'])}")
    lines.append("")
    if hidden_links:
        for index in range(len(hidden_links)):
            lines.append(f"    linkStyle {index} stroke:transparent,fill:none")
        lines.append("")
    for kind in sorted({node["kind"] for node in included_nodes.values()}):
        lines.append(f"    classDef {kind}Node {_kind_style(kind)}")
        members = sorted(_safe_id(node_id) for node_id, node in included_nodes.items() if node["kind"] == kind)
        if members:
            lines.append(f"    class {','.join(members)} {kind}Node")
    hidden_nodes = sorted({segment.split()[0] for segment in hidden_links if "_anchor" in segment})
    if hidden_nodes:
        lines.append("    classDef hiddenAnchor fill:transparent,stroke:transparent,color:transparent")
        lines.append(f"    class {','.join(hidden_nodes)} hiddenAnchor")
    return "\n".join(lines) + "\n"


def _render_html(title: str, graph_payload: dict, default_node_kinds: list[str], default_families: list[str]) -> str:
    payload_json = json.dumps(graph_payload)
    default_kinds_json = json.dumps(default_node_kinds)
    default_families_json = json.dumps(default_families)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <script src="{_CYTOSCAPE_CDN}"></script>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; }}
    .page {{ display: grid; grid-template-columns: 320px 1fr; min-height: 100vh; }}
    .sidebar {{ border-right: 1px solid #233046; background: #131a26; padding: 1.1rem 1.1rem 1.5rem; position: sticky; top: 0; height: 100vh; overflow: auto; }}
    .content {{ padding: 1rem 1rem 1.25rem; }}
    h1 {{ margin: 0 0 0.45rem; font-size: 1.1rem; color: #dbeafe; }}
    .subtitle {{ color: #94a3b8; font-size: 0.86rem; line-height: 1.45; margin-bottom: 1rem; }}
    .section {{ margin-bottom: 1rem; padding-top: 0.2rem; }}
    .section h2 {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; margin: 0 0 0.65rem; }}
    .option {{ display: flex; align-items: center; gap: 0.55rem; margin: 0.35rem 0; color: #cbd5e1; font-size: 0.9rem; }}
    .controls {{ display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.45rem; }}
    button {{ background: #1d4ed8; color: white; border: 0; border-radius: 8px; padding: 0.45rem 0.65rem; cursor: pointer; font-size: 0.82rem; }}
    button.secondary {{ background: #243041; color: #dbeafe; }}
    .meta {{ display: flex; gap: 0.9rem; flex-wrap: wrap; margin: 0 0 0.8rem; color: #94a3b8; font-size: 0.82rem; }}
    .diagram-toolbar {{ display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; margin-bottom: 0.6rem; }}
    .diagram {{ background: #182131; border: 1px solid #233046; border-radius: 14px; padding: 0.6rem; height: calc(100vh - 8rem); overflow: hidden; }}
    #graph-root {{ width: 100%; height: 100%; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #111827; border-radius: 10px; padding: 0.75rem; color: #cbd5e1; font-size: 0.75rem; margin-top: 0.75rem; max-height: 22rem; overflow: auto; }}
    @media (max-width: 980px) {{
      .page {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid #233046; }}
      .diagram {{ height: 70vh; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <aside class="sidebar">
      <h1>{title}</h1>
      <div class="subtitle">Local slice graph: bootstrap is the leftmost red slice, additional slices sit to the right, and verification stays at the bottom. The main view is behavior-first, while the runtime view groups surfaces, operations, and stores into blue runtime containers.</div>
      <div class="section">
        <h2>Presets</h2>
        <div class="controls">
          <button type="button" data-preset="all">All</button>
          <button type="button" data-preset="runtime" class="secondary">Runtime</button>
          <button type="button" data-preset="contracts" class="secondary">Contracts</button>
          <button type="button" data-preset="bootstrap" class="secondary">Bootstrap</button>
        </div>
      </div>
      <div class="section">
        <h2>Node Kinds</h2>
        <div id="node-kind-options"></div>
      </div>
      <div class="section">
        <h2>Relationship Families</h2>
        <div id="family-options"></div>
      </div>
      <div class="section">
        <h2>Source</h2>
        <button type="button" id="toggle-source" class="secondary">Show Graph Data</button>
      </div>
    </aside>
    <main class="content">
      <div class="meta">
        <div id="node-count"></div>
        <div id="edge-count"></div>
      </div>
      <div class="diagram-toolbar">
        <div class="controls">
          <button type="button" id="zoom-in">Zoom In</button>
          <button type="button" id="zoom-out" class="secondary">Zoom Out</button>
          <button type="button" id="zoom-reset" class="secondary">Reset</button>
        </div>
      </div>
      <div class="diagram">
        <div id="graph-root"></div>
      </div>
      <pre id="graph-source" hidden></pre>
    </main>
  </div>
  <script>
    const GRAPH = {payload_json};
    const DEFAULT_NODE_KINDS = {default_kinds_json};
    const DEFAULT_FAMILIES = {default_families_json};
    const NODE_KIND_ORDER = ["surface", "flow", "operation", "type", "store", "verification"];
    const FAMILY_ORDER = ["runtime", "contract", "persistence", "flow", "verification"];
    const MAIN_BAND_ORDER = ["surfaces", "flows", "operations", "types", "stores"];
    const MAIN_BAND_BY_KIND = {{ surface: "surfaces", flow: "flows", operation: "operations", type: "types", store: "stores" }};
    const RUNTIME_BAND_ORDER = ["surfaces", "operations", "stores"];
    let cy = null;
    let activePreset = "all";

    const nodeKindContainer = document.getElementById("node-kind-options");
    const familyContainer = document.getElementById("family-options");
    const sourceEl = document.getElementById("graph-source");
    const graphRoot = document.getElementById("graph-root");
    const nodeCountEl = document.getElementById("node-count");
    const edgeCountEl = document.getElementById("edge-count");

    function option(label, value, checked, name) {{
      const wrapper = document.createElement("label");
      wrapper.className = "option";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = value;
      input.dataset.group = name;
      input.checked = checked;
      wrapper.appendChild(input);
      const text = document.createElement("span");
      text.textContent = label;
      wrapper.appendChild(text);
      return wrapper;
    }}

    function buildOptions() {{
      for (const kind of NODE_KIND_ORDER) {{
        if (GRAPH.nodeKinds.includes(kind)) nodeKindContainer.appendChild(option(kind, kind, DEFAULT_NODE_KINDS.includes(kind), "node-kind"));
      }}
      for (const family of FAMILY_ORDER) {{
        if (GRAPH.edgeFamilies.includes(family)) familyContainer.appendChild(option(family, family, DEFAULT_FAMILIES.includes(family), "family"));
      }}
    }}

    function selectedValues(group) {{
      return [...document.querySelectorAll(`input[data-group="${{group}}"]`)].filter((el) => el.checked).map((el) => el.value);
    }}

    function parseStyle(styleString) {{
      const out = {{}};
      for (const part of styleString.split(",")) {{
        const [key, value] = part.split(":").map((item) => item && item.trim());
        if (key && value) out[key] = value;
      }}
      return out;
    }}

    function styleForKind(kind) {{
      return parseStyle(GRAPH.kindStyles[kind] || "fill:#1f2937,stroke:#94a3b8,color:#e5e7eb");
    }}

    function normalizeLabel(label) {{
      return String(label || "")
        .replace(/<br\\s*\\/?>/gi, "\\n")
        .replace(/<\\/?.*?small>/gi, "")
        .replace(/<[^>]+>/g, "")
        .replace(/\\n{3,}/g, "\\n\\n")
        .trim();
    }}

    function sliceDescriptors() {{
      return [GRAPH.layout.bootstrapSlice, ...GRAPH.layout.additionalSlices];
    }}

    function visibleMembersForSlice(slice, selectedKinds, bandOrder) {{
      const members = {{}};
      for (const band of bandOrder) {{
        members[band] = (slice.members[band] || []).filter((id) => {{
          const node = GRAPH.nodeById[id];
          return node && selectedKinds.includes(node.kind);
        }});
      }}
      return members;
    }}

    function decorateNodeLabel(node, mode) {{
      return normalizeLabel(node.label);
    }}

    function shortUnitLabel(unitId) {{
      const unit = GRAPH.nodeById[unitId];
      if (!unit) return unitId;
      return normalizeLabel(unit.label).split("\\n")[0] || unitId;
    }}

    function visibleBehaviorNodeForUnit(unitId, nodeIds) {{
      for (const kind of ["surface", "operation"]) {{
        const match = GRAPH.nodes.find((node) => node.kind === kind && node.unit === unitId && nodeIds.has(node.id));
        if (match) return match.id;
      }}
      return null;
    }}

    function computeSliceLayout(slices, selectedKinds, bandOrder) {{
      const nodeWidth = 198;
      const nodeHeight = 86;
      const nodeGapX = 34;
      const nodeGapY = 34;
      const bandPaddingX = 24;
      const bandPaddingTop = 30;
      const bandPaddingBottom = 20;
      const bandGap = 58;
      const sliceGap = 56;
      const slicePadding = 18;
      const gridLimit = 4;
      const positions = {{}};
      const sliceBoxes = {{}};
      let currentX = 40;
      let maxSliceBottom = 0;

      for (const slice of slices) {{
        const members = visibleMembersForSlice(slice, selectedKinds, bandOrder);
        const visibleBands = bandOrder.filter((band) => members[band].length);
        if (!visibleBands.length) continue;
        let maxBandWidth = 240;
        const bandLayouts = [];
        for (const band of visibleBands) {{
          const count = members[band].length;
          const cols = Math.min(gridLimit, Math.max(1, count));
          const rows = Math.ceil(count / gridLimit) || 1;
          const bandWidth = bandPaddingX * 2 + cols * nodeWidth + Math.max(0, cols - 1) * nodeGapX;
          const bandHeight = bandPaddingTop + rows * nodeHeight + Math.max(0, rows - 1) * nodeGapY + bandPaddingBottom;
          maxBandWidth = Math.max(maxBandWidth, bandWidth);
          bandLayouts.push({{ band, width: bandWidth, height: bandHeight }});
        }}
        const sliceWidth = maxBandWidth + slicePadding * 2;
        let localY = 60;
        for (const bandLayout of bandLayouts) {{
          const bandLeft = currentX + (sliceWidth - bandLayout.width) / 2;
          const bandTop = localY;
          positions[`band:${{slice.id}}:${{bandLayout.band}}`] = {{ x: bandLeft + bandLayout.width / 2, y: bandTop + bandLayout.height / 2 }};
          members[bandLayout.band].forEach((id, index) => {{
            const col = index % gridLimit;
            const row = Math.floor(index / gridLimit);
            positions[id] = {{
              x: bandLeft + bandPaddingX + nodeWidth / 2 + col * (nodeWidth + nodeGapX),
              y: bandTop + bandPaddingTop + nodeHeight / 2 + row * (nodeHeight + nodeGapY),
            }};
          }});
          localY += bandLayout.height + bandGap;
        }}
        const sliceHeight = Math.max(220, localY - bandGap + slicePadding);
        positions[`slice:${{slice.id}}`] = {{ x: currentX + sliceWidth / 2, y: sliceHeight / 2 }};
        sliceBoxes[slice.id] = {{ left: currentX, top: 0, width: sliceWidth, height: sliceHeight }};
        currentX += sliceWidth + sliceGap;
        maxSliceBottom = Math.max(maxSliceBottom, sliceHeight);
      }}

      const verificationNodes = GRAPH.layout.layers.verification.filter((id) => {{
        const node = GRAPH.nodeById[id];
        return node && selectedKinds.includes(node.kind);
      }});
      const verificationY = maxSliceBottom + 140;
      positions["verification::root"] = {{ x: Math.max(800, currentX) / 2, y: verificationY }};
      verificationNodes.forEach((id, index) => {{
        positions[id] = {{ x: 120 + index * (nodeWidth + nodeGapX), y: verificationY }};
      }});
      return {{ positions, verificationNodes, sliceBoxes }};
    }}

    function runtimeDescriptors(selectedKinds) {{
      const descriptors = [];
      const units = GRAPH.nodes.filter((node) => node.kind === "unit");
      for (const unit of units) {{
        const surfaces = GRAPH.nodes.filter((node) => node.kind === "surface" && node.unit === unit.id && selectedKinds.includes("surface")).map((node) => node.id);
        const operations = GRAPH.nodes.filter((node) => node.kind === "operation" && node.unit === unit.id && selectedKinds.includes("operation")).map((node) => node.id);
        const stores = GRAPH.edges
          .filter((edge) => edge.family === "runtime" && edge.src === unit.id && GRAPH.nodeById[edge.dst]?.kind === "store" && selectedKinds.includes("store"))
          .map((edge) => edge.dst);
        descriptors.push({{
          id: unit.id,
          label: shortUnitLabel(unit.id),
          bootstrap_related: (GRAPH.layout.bootstrapRelated || []).includes(unit.id),
          members: {{ surfaces, operations, stores }},
        }});
      }}
      return descriptors;
    }}

    function buildElements(selectedKinds, selectedFamilies) {{
      let includedNodes = GRAPH.nodes.filter((node) => selectedKinds.includes(node.kind));
      if (activePreset === "bootstrap") {{
        const allowed = new Set(GRAPH.layout.bootstrapRelated || []);
        includedNodes = includedNodes.filter((node) => allowed.has(node.id));
      }}
      if (activePreset !== "runtime") {{
        includedNodes = includedNodes.filter((node) => node.kind !== "unit");
      }} else {{
        includedNodes = includedNodes.filter((node) => node.kind !== "unit");
      }}
      const nodeIds = new Set(includedNodes.map((node) => node.id));
      const sliceMode = activePreset === "runtime" ? "runtime" : "main";
      const descriptors = activePreset === "runtime" ? runtimeDescriptors(selectedKinds) : sliceDescriptors();
      const bandOrder = activePreset === "runtime" ? RUNTIME_BAND_ORDER : MAIN_BAND_ORDER;
      const layout = computeSliceLayout(descriptors, selectedKinds, bandOrder);
      const runtimeSliceByUnit = Object.fromEntries(descriptors.map((slice) => [slice.id, `slice:${{slice.id}}`]));
      const runtimeAnchorByUnit = Object.fromEntries(descriptors.map((slice) => [slice.id, `anchor:${{slice.id}}`]));
      const runtimeDepLeftByUnit = Object.fromEntries(descriptors.map((slice) => [slice.id, `anchor:${{slice.id}}:dep-left`]));
      const runtimeDepRightByUnit = Object.fromEntries(descriptors.map((slice) => [slice.id, `anchor:${{slice.id}}:dep-right`]));
      const visibleContainerIds = new Set(Object.values(runtimeSliceByUnit));
      const visibleAnchorIds = new Set([...Object.values(runtimeAnchorByUnit), ...Object.values(runtimeDepLeftByUnit), ...Object.values(runtimeDepRightByUnit)]);
      const includedEdges = GRAPH.edges
        .filter((edge) => selectedFamilies.includes(edge.family))
        .map((edge) => {{
          let src = edge.src;
          let dst = edge.dst;
          if (activePreset === "runtime") {{
            const srcNode = GRAPH.nodeById[src];
            const dstNode = GRAPH.nodeById[dst];
            if (edge.family === "runtime" && ["exposes", "implements", "uses"].includes(edge.label)) return null;
            if (edge.family === "runtime" && edge.label === "depends on") {{
              if (srcNode?.kind === "unit" && runtimeDepLeftByUnit[src]) src = runtimeDepLeftByUnit[src];
              if (dstNode?.kind === "unit" && runtimeDepRightByUnit[dst]) dst = runtimeDepRightByUnit[dst];
            }} else {{
              if (srcNode?.kind === "unit" && runtimeSliceByUnit[src]) src = runtimeSliceByUnit[src];
              if (dstNode?.kind === "unit" && runtimeSliceByUnit[dst]) dst = runtimeSliceByUnit[dst];
            }}
            if (edge.family === "verification" && src.startsWith("verification.startup.") && dstNode?.kind === "unit" && runtimeAnchorByUnit[dst]) dst = runtimeAnchorByUnit[dst];
          }} else if (edge.family === "runtime" && edge.label === "depends on") {{
            return null;
          }} else if (edge.family === "verification" && src.startsWith("verification.startup.") && !nodeIds.has(dst)) {{
            const remapped = visibleBehaviorNodeForUnit(dst, nodeIds);
            if (remapped) dst = remapped;
          }}
          const srcVisible = nodeIds.has(src) || visibleContainerIds.has(src) || visibleAnchorIds.has(src);
          const dstVisible = nodeIds.has(dst) || visibleContainerIds.has(dst) || visibleAnchorIds.has(dst);
          if (!srcVisible || !dstVisible) return null;
          if (src === dst) return null;
          return {{ ...edge, src, dst }};
        }})
        .filter(Boolean);
      const elements = [];

      for (const slice of descriptors) {{
        const members = visibleMembersForSlice(slice, selectedKinds, bandOrder);
        if (!bandOrder.some((band) => members[band].length)) continue;
        let sliceClasses = "slice-parent";
        if (activePreset === "runtime") sliceClasses += " runtime-slice";
        else if (slice.bootstrap_related) sliceClasses += " bootstrap-slice";
        elements.push({{ data: {{ id: `slice:${{slice.id}}`, label: normalizeLabel(slice.label) }}, position: layout.positions[`slice:${{slice.id}}`], classes: sliceClasses }});
        if (activePreset === "runtime") {{
          const box = layout.sliceBoxes[slice.id];
          elements.push({{
            data: {{ id: `anchor:${{slice.id}}`, label: "" }},
            position: {{
              x: layout.positions[`slice:${{slice.id}}`].x,
              y: layout.positions[`slice:${{slice.id}}`].y - 132,
            }},
            classes: "runtime-anchor",
          }});
          elements.push({{
            data: {{ id: `anchor:${{slice.id}}:dep-left`, label: "" }},
            position: {{
              x: box.left - 18,
              y: layout.positions[`slice:${{slice.id}}`].y,
            }},
            classes: "runtime-anchor",
          }});
          elements.push({{
            data: {{ id: `anchor:${{slice.id}}:dep-right`, label: "" }},
            position: {{
              x: box.left + box.width + 18,
              y: layout.positions[`slice:${{slice.id}}`].y,
            }},
            classes: "runtime-anchor",
          }});
        }}
        for (const band of bandOrder) {{
          if (!members[band].length) continue;
          const bandLabels = activePreset === "runtime"
            ? {{ surfaces: "Exposes Surfaces", operations: "Implements Operations", stores: "Uses Stores" }}
            : {{ surfaces: "Surfaces", flows: "Flows", operations: "Operations", types: "Types", stores: "Stores" }};
          elements.push({{ data: {{ id: `band:${{slice.id}}:${{band}}`, parent: `slice:${{slice.id}}`, label: normalizeLabel(bandLabels[band] || (band.charAt(0).toUpperCase() + band.slice(1))) }}, position: layout.positions[`band:${{slice.id}}:${{band}}`], classes: "band-parent" }});
        }}
      }}

      if (layout.verificationNodes.length) {{
        elements.push({{ data: {{ id: "verification::root", label: "Verification" }}, position: layout.positions["verification::root"], classes: "verification-parent" }});
      }}

      for (const node of includedNodes) {{
        let parent = undefined;
        if (node.kind === "verification") {{
          parent = "verification::root";
        }} else {{
          for (const slice of descriptors) {{
            const band = (activePreset === "runtime" ? {{ surface: "surfaces", operation: "operations", store: "stores" }} : MAIN_BAND_BY_KIND)[node.kind];
            if (band && (slice.members[band] || []).includes(node.id)) {{
              parent = `band:${{slice.id}}:${{band}}`;
              break;
            }}
          }}
        }}
        elements.push({{ data: {{ id: node.id, label: decorateNodeLabel(node, sliceMode), parent }}, position: layout.positions[node.id], classes: `node-kind-${{node.kind}}` }});
      }}

      for (const edge of includedEdges) {{
        const sourcePos = layout.positions[edge.src];
        const targetPos = layout.positions[edge.dst];
        let directionClass = "edge-dir-down";
        if (sourcePos && targetPos) {{
          const dx = targetPos.x - sourcePos.x;
          const dy = targetPos.y - sourcePos.y;
          if (Math.abs(dx) > Math.abs(dy)) directionClass = dx >= 0 ? "edge-dir-right" : "edge-dir-left";
          else directionClass = dy >= 0 ? "edge-dir-down" : "edge-dir-up";
        }}
        const isRuntimeDependency = edge.family === "runtime" && edge.label === "depends on";
        elements.push({{
          data: {{ id: `edge:${{edge.src}}:${{edge.dst}}:${{edge.label}}:${{edge.family}}`, source: edge.src, target: edge.dst, label: edge.label }},
          classes: `edge-family-${{edge.family}}${{isRuntimeDependency ? " edge-runtime-dep" : ` ${{directionClass}}`}}`,
        }});
      }}

      sourceEl.textContent = JSON.stringify({{ selectedKinds, selectedFamilies, nodes: includedNodes.map((node) => node.id), edges: includedEdges }}, null, 2);
      nodeCountEl.textContent = `${{includedNodes.length}} nodes`;
      edgeCountEl.textContent = `${{includedEdges.length}} edges`;
      return elements;
    }}

    function ensureCy() {{
      if (cy) return cy;
      cy = cytoscape({{
        container: graphRoot,
        elements: [],
        style: [
          {{ selector: "node", style: {{ label: "data(label)", "text-wrap": "wrap", "text-max-width": 168, "font-size": 11, "line-height": 1.32, color: "#e5e7eb", "text-valign": "center", "text-halign": "center", shape: "round-rectangle", width: 198, height: 86, padding: "10px" }} }},
          {{ selector: ".slice-parent", style: {{ "background-color": "#111827", "background-opacity": 0.25, "border-color": "#334155", "border-width": 2, label: "data(label)", "text-valign": "top", "text-halign": "center", "text-margin-y": 2, "font-size": 14, "font-weight": 700, color: "#e2e8f0", shape: "round-rectangle", padding: "18px", "z-compound-depth": "bottom", "events": "no" }} }},
          {{ selector: ".bootstrap-slice", style: {{ "background-color": "#3b1212", "background-opacity": 0.65, "border-color": "#f87171" }} }},
          {{ selector: ".runtime-slice", style: {{ "background-color": "#14213d", "background-opacity": 0.45, "border-color": "#60a5fa" }} }},
          {{ selector: ".runtime-anchor", style: {{ width: 2, height: 2, "background-opacity": 0, "border-opacity": 0, label: "", "events": "no" }} }},
          {{ selector: ".band-parent", style: {{ "background-color": "#4b5563", "background-opacity": 0.72, "border-color": "#6b7280", "border-width": 1, label: "data(label)", "text-valign": "top", "text-halign": "center", "font-size": 11, color: "#f3f4f6", shape: "round-rectangle", padding: "10px", "z-compound-depth": "bottom", "events": "no" }} }},
          {{ selector: ".verification-parent", style: {{ "background-color": "#0f172a", "background-opacity": 0.35, "border-color": "#64748b", "border-width": 2, label: "data(label)", "text-valign": "top", "text-halign": "center", "font-size": 13, color: "#e2e8f0", shape: "round-rectangle", padding: "18px", "z-compound-depth": "bottom", "events": "no" }} }},
          {{ selector: "edge", style: {{ width: 1.8, "line-color": "#cbd5e1", "line-opacity": 1, "target-arrow-color": "#cbd5e1", "target-arrow-shape": "triangle", "target-arrow-fill": "filled", "arrow-scale": 1, "source-endpoint": "outside-to-node", "target-endpoint": "outside-to-node", "edge-distances": "node-position", "curve-style": "unbundled-bezier", "control-point-step-size": 52, label: "data(label)", "font-size": 10, color: "#e5e7eb", "text-background-color": "#4b5563", "text-background-opacity": 0.9, "text-background-padding": "2px", "text-rotation": "autorotate", "z-compound-depth": "top" }} }},
          {{ selector: ".edge-dir-down", style: {{ "control-point-weights": "0.35 0.7", "control-point-distances": "34 20" }} }},
          {{ selector: ".edge-dir-up", style: {{ "control-point-weights": "0.3 0.65", "control-point-distances": "-34 -20" }} }},
          {{ selector: ".edge-dir-right", style: {{ "control-point-weights": "0.25 0.7", "control-point-distances": "28 12" }} }},
          {{ selector: ".edge-dir-left", style: {{ "control-point-weights": "0.25 0.7", "control-point-distances": "-28 -12" }} }},
          {{ selector: ".edge-family-verification", style: {{ width: 1.6, "line-style": "dashed" }} }},
          {{ selector: ".edge-runtime-dep", style: {{ width: 2.2, "curve-style": "straight", "text-margin-y": -10, "text-background-color": "#334155", "text-background-opacity": 0.95 }} }},
        ],
        layout: {{ name: "preset", fit: false, padding: 30 }},
        userZoomingEnabled: true,
        userPanningEnabled: true,
        boxSelectionEnabled: false,
      }});
      for (const kind of NODE_KIND_ORDER) {{
        const style = styleForKind(kind);
        cy.style().selector(`.node-kind-${{kind}}`).style({{ "background-color": style.fill || "#1f2937", "border-color": style.stroke || "#94a3b8", "border-width": 2, color: style.color || "#e5e7eb" }}).update();
      }}
      return cy;
    }}

    function resetZoom() {{
      if (!cy) return;
      cy.fit(cy.elements(), 30);
      cy.center();
    }}

    function rerender() {{
      const selectedKinds = selectedValues("node-kind");
      const selectedFamilies = selectedValues("family");
      const instance = ensureCy();
      instance.elements().remove();
      instance.add(buildElements(selectedKinds, selectedFamilies));
      instance.layout({{ name: "preset", fit: false, padding: 30 }}).run();
      resetZoom();
    }}

    function setPreset(name) {{
      activePreset = name;
      const familyMap = {{
        all: FAMILY_ORDER.filter((family) => GRAPH.edgeFamilies.includes(family)),
        runtime: ["runtime", "verification"],
        contracts: ["contract", "persistence"],
        bootstrap: ["runtime", "contract", "persistence", "verification", "flow"]
      }};
      const nodeMap = {{
        all: NODE_KIND_ORDER.filter((kind) => GRAPH.nodeKinds.includes(kind)),
        runtime: ["surface", "operation", "store", "verification"],
        contracts: ["surface", "operation", "type", "store"],
        bootstrap: ["surface", "flow", "operation", "type", "store", "verification"]
      }};
      const families = new Set((familyMap[name] || familyMap.all).filter((family) => GRAPH.edgeFamilies.includes(family)));
      const kinds = new Set((nodeMap[name] || nodeMap.all).filter((kind) => GRAPH.nodeKinds.includes(kind)));
      for (const input of document.querySelectorAll('input[data-group="family"]')) input.checked = families.has(input.value);
      for (const input of document.querySelectorAll('input[data-group="node-kind"]')) input.checked = kinds.has(input.value);
      for (const button of document.querySelectorAll("button[data-preset]")) {{
        if (button.dataset.preset === name) button.classList.remove("secondary");
        else button.classList.add("secondary");
      }}
      rerender();
    }}

    buildOptions();
    document.addEventListener("change", (event) => {{
      if (event.target instanceof HTMLInputElement) rerender();
    }});
    for (const button of document.querySelectorAll("button[data-preset]")) {{
      button.addEventListener("click", () => setPreset(button.dataset.preset));
    }}
    document.getElementById("toggle-source").addEventListener("click", () => {{
      const hidden = sourceEl.hasAttribute("hidden");
      if (hidden) sourceEl.removeAttribute("hidden");
      else sourceEl.setAttribute("hidden", "");
    }});
    document.getElementById("zoom-in").addEventListener("click", () => cy && cy.zoom({{ level: cy.zoom() * 1.2, renderedPosition: {{ x: cy.width() / 2, y: cy.height() / 2 }} }}));
    document.getElementById("zoom-out").addEventListener("click", () => cy && cy.zoom({{ level: cy.zoom() / 1.2, renderedPosition: {{ x: cy.width() / 2, y: cy.height() / 2 }} }}));
    document.getElementById("zoom-reset").addEventListener("click", () => resetZoom());
    setPreset("all");
  </script>
</body>
</html>
"""


def _open_file(path: Path) -> None:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", str(path)], check=False)
        elif system == "Linux":
            subprocess.run(["xdg-open", str(path)], check=False)
        elif system == "Windows":
            subprocess.run(["start", str(path)], shell=True, check=False)
    except OSError:
        pass


def run(args: Namespace) -> int:
    forge_root = Path(args.forge_dir).resolve() if args.forge_dir else find_forge_root()
    schema = load_schema(forge_root)
    edges = _all_edges(schema)
    nodes = _all_nodes(schema)
    if args.vertical:
        nodes, edges = _vertical_scope(schema, args.vertical, edges)
    layout = _layout_payload(schema, nodes)
    if args.contracts:
        preferred_kinds = {"surface", "operation", "type", "store"}
    elif args.runtime or args.bootstrap:
        preferred_kinds = {"surface", "operation", "type", "store", "flow", "verification"}
    else:
        preferred_kinds = {"surface", "operation", "type", "store", "flow", "verification"}
    default_node_kinds = [kind for kind in ("surface", "flow", "operation", "type", "store", "verification") if kind in preferred_kinds and any(node["kind"] == kind for node in nodes.values())]
    default_families = _preset_families(args)
    if args.format == "mermaid":
        print(_mermaid_from_projection(nodes, edges, layout, default_node_kinds, default_families))
        return 0
    payload = {
        "nodes": sorted(nodes.values(), key=lambda item: (item["kind"], item["id"])),
        "edges": edges,
        "nodeById": {node_id: node for node_id, node in nodes.items()},
        "layout": layout,
        "nodeKinds": sorted({node["kind"] for node in nodes.values()}),
        "edgeFamilies": sorted({edge["family"] for edge in edges}),
        "kindStyles": {kind: _kind_style(kind) for kind in {node["kind"] for node in nodes.values()}},
    }
    title = f"Forge Graph - {schema.system.get('name', schema.system.get('id', 'system'))}"
    html = _render_html(title, payload, default_node_kinds, default_families)
    output = Path(args.output).expanduser().resolve()
    output.write_text(html, encoding="utf-8")
    print(f"graph: wrote {output}")
    if not args.no_open:
        _open_file(output)
    return 0
