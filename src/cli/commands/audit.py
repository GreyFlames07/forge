from __future__ import annotations

from argparse import ArgumentParser, Namespace
import base64
from html import escape
from pathlib import Path
import json
import platform
import subprocess

from cli.commands.base import add_project_dir_arg
from cli.common import find_project_root
from cli.schema import ForgeSchema, load_schema


def register_audit(subparsers) -> None:
    parser = subparsers.add_parser("audit", help="Generate a self-contained Forge audit dashboard HTML file")
    add_project_dir_arg(parser)
    parser.add_argument("--output", "-o", default="./forge-audit.html", help="Output HTML path")
    parser.add_argument("--no-open", action="store_true", help="Do not automatically open the generated audit artifact")
    parser.set_defaults(func=run)


def run(args: Namespace) -> int:
    root = find_project_root(Path(args.project_dir).resolve() if args.project_dir else None)
    schema = load_schema(root)
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_audit_html(schema), encoding="utf-8")
    if not args.no_open:
        _open_file(output)
    print(f"Forge audit written to {output}")
    return 0


def _open_file(path: Path) -> None:
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", str(path)], check=False)
    elif system == "Windows":
        subprocess.run(["cmd", "/c", "start", "", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def _template_text(filename: str) -> str:
    templates_root = Path(__file__).resolve().parents[1] / "assets"
    return (templates_root / filename).read_text(encoding="utf-8")


def _asset_data_url(filename: str, mime_type: str = "image/svg+xml") -> str:
    assets_root = Path(__file__).resolve().parents[1] / "assets"
    encoded = base64.b64encode((assets_root / filename).read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def render_audit_html(schema: ForgeSchema) -> str:
    sections: list[dict[str, str]] = [
        {"id": "overview", "group": "Overview", "label": "Overview"},
        {"id": "system-overview", "group": "System", "label": "System"},
        {"id": "runtime-overview", "group": "Runtime", "label": "Runtime Overview"},
        {"id": "data-overview", "group": "Data", "label": "Data Overview"},
        {"id": "verticals-overview", "group": "Verticals", "label": "Verticals"},
        {"id": "deployment-overview", "group": "Deployment", "label": "Deployment"},
    ]
    dynamic_sections: list[str] = []

    for flow in schema.high_level_flows:
        section_id = f"high-level-flow-{flow['id']}"
        sections.append({"id": section_id, "group": "Flows", "label": f"HL Flow: {flow['id']}"})
        dynamic_sections.append(
            _section(
                section_id,
                "Flows",
                f"High-Level Flow: {flow['id']}",
                "Business flow and decision structure.",
                _render_high_level_flow(flow),
                schema.system.get("id", "forge"),
            )
        )

    for flow in schema.runtime_flows:
        section_id = f"runtime-flow-{flow['id']}"
        sections.append({"id": section_id, "group": "Flows", "label": f"Runtime Flow: {flow['id']}"})
        dynamic_sections.append(
            _section(
                section_id,
                "Flows",
                f"Runtime Flow: {flow['id']}",
                "Container-level flow of data through the system.",
                _render_runtime_flow(flow),
                schema.system.get("id", "forge"),
            )
        )

    for container in schema.containers:
        section_id = f"container-{container['id']}"
        sections.append({"id": section_id, "group": "Runtime", "label": f"Container: {container['id']}"})
        dynamic_sections.append(
            _section(
                section_id,
                "Runtime",
                f"Container: {container['id']}",
                "Internal component structure and component-level flows.",
                _render_container_section(container),
                schema.system.get("id", "forge"),
            )
        )

    item_buttons = "".join(
        _item_button(section["label"], section["id"], section["group"])
        for section in sections
        if section["id"] not in {
            "overview",
            "system-overview",
            "runtime-overview",
            "data-overview",
            "verticals-overview",
            "deployment-overview",
        }
    )

    data_payload = json.dumps(_interaction_payload(schema))
    template = _template_text("audit_template.html")
    replacements = {
        "__DYNAMIC_ITEM_BUTTONS_HTML__": item_buttons,
        "__SYSTEM_ID__": escape(str(schema.system.get("id", "forge"))),
        "__AUDIT_DATA__": data_payload,
        "__OVERVIEW_BODY__": _render_overview_section(schema),
        "__SYSTEM_BODY__": _render_system_section(schema),
        "__RUNTIME_BODY__": _render_runtime_section(schema),
        "__DATA_BODY__": _render_data_section(schema),
        "__VERTICALS_BODY__": _render_verticals_section(schema),
        "__DEPLOYMENT_BODY__": _render_deployment_section(schema),
        "__DYNAMIC_SECTIONS_HTML__": "".join(dynamic_sections),
        "./forge_white_small.drawio.svg": _asset_data_url("forge_white_small.drawio.svg"),
        "./forge_full_logo.drawio.svg": _asset_data_url("forge_full_logo.drawio.svg"),
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template


def _interaction_payload(schema: ForgeSchema) -> dict[str, object]:
    return {
        "system_id": schema.system.get("id"),
        "verticals": [item.get("id") for item in schema.verticals],
        "runtime_flows": [item.get("id") for item in schema.runtime_flows],
        "containers": [item.get("id") for item in schema.containers],
        "graph_targets": _graph_targets(schema),
    }


def _item_button(label: str, target: str, group: str) -> str:
    return f'<button class="toolbar-btn" data-target="{escape(target)}" data-group="{escape(group)}">{escape(label)}</button>'


def _section(section_id: str, group: str, title: str, description: str, body: str, system_id: str) -> str:
    return f'<section class="section" id="{escape(section_id)}" data-group="{escape(group)}">{body}</section>'


def _render_overview_section(schema: ForgeSchema) -> str:
    cards = f"""
    <div class="grid">
      <div class="card"><h3>System</h3><p>{escape(str(schema.system.get('id', '')))}</p></div>
      <div class="card"><h3>High-Level Flows</h3><p>{len(schema.high_level_flows)}</p></div>
      <div class="card"><h3>Runtime Containers</h3><p>{len(schema.runtime.get('containers', []))}</p></div>
      <div class="card"><h3>Verticals</h3><p>{len(schema.verticals)}</p></div>
    </div>
    """
    quick_links = """
    <div class="grid">
      <div class="card"><h3>Jump To System</h3><p>Open the system boundary and external dependency view.</p><div class="pill-list"><span class="pill" data-target="system-overview">Open System</span></div></div>
      <div class="card"><h3>Jump To Runtime</h3><p>Inspect the container graph and runtime boundaries.</p><div class="pill-list"><span class="pill" data-target="runtime-overview">Open Runtime</span></div></div>
      <div class="card"><h3>Jump To Data</h3><p>Review promoted data shapes and persistent storage.</p><div class="pill-list"><span class="pill" data-target="data-overview">Open Data</span></div></div>
      <div class="card"><h3>Jump To Deployment</h3><p>Review environment and node placement.</p><div class="pill-list"><span class="pill" data-target="deployment-overview">Open Deployment</span></div></div>
    </div>
    """
    return cards + quick_links


def _render_system_section(schema: ForgeSchema) -> str:
    actors = schema.system.get("actors", [])
    dependencies = schema.system.get("external_dependencies", [])
    cards = f"""
    <div class="grid">
      <div class="card"><h3>Purpose</h3><p>{escape(str(schema.system.get('purpose', '')))}</p></div>
      <div class="card"><h3>Boundary</h3><p>{escape(str(schema.system.get('boundary', '')))}</p></div>
      <div class="card"><h3>Security</h3><p>{escape(str(schema.system.get('security', '')))}</p></div>
    </div>
    """
    diagram = _render_system_graph(schema.system.get("id", "system"), actors, dependencies)
    return cards + _diagram_card("System Context", "Actors, system boundary, and external dependencies", diagram)


def _render_runtime_section(schema: ForgeSchema) -> str:
    containers = schema.runtime.get("containers", [])
    relationships = schema.runtime.get("relationships", [])
    deepened_container_ids = {str(item["id"]) for item in schema.containers}
    cards = '<div class="grid">' + "".join(
        f'<div class="card"><h3>{escape(item["id"])}</h3><p>{escape(item.get("description", ""))}</p>'
        + (
            f'<div class="pill-list"><span class="pill" data-target="container-{escape(item["id"])}">Open Container</span></div>'
            if str(item["id"]) in deepened_container_ids
            else ""
        )
        + '</div>'
        for item in containers
    ) + "</div>"
    diagram = _render_runtime_graph(containers, relationships, deepened_container_ids)
    return cards + _diagram_card("Runtime Topology", "Container graph and boundary-crossing relationships", diagram)


def _render_verticals_section(schema: ForgeSchema) -> str:
    return '<div class="grid">' + "".join(
        f'<div class="card"><h3>{escape(vertical["id"])}</h3><p>{escape(vertical.get("description", ""))}</p>'
        f'<div class="pill-list">'
        + "".join(
            f'<span class="pill" data-target="high-level-flow-{escape(flow_id)}">{escape(flow_id)}</span>'
            for flow_id in vertical.get("high_level_flows", [])
        )
        + "</div></div>"
        for vertical in schema.verticals
    ) + "</div>"


def _render_data_section(schema: ForgeSchema) -> str:
    early_state_cards = "".join(
        f'<div class="card"><h3>{escape(item["id"])}</h3><p>{escape(item.get("description", ""))}</p>'
        f'<div class="footer-note">Category: {escape(str(item.get("category", "")))}</div></div>'
        for item in schema.early_state
    )
    data_shape_cards = "".join(
        f'<div class="card"><h3>{escape(item["id"])}</h3><p>{escape(item.get("description", ""))}</p>'
        f'<div class="footer-note">Kind: {escape(str(item.get("kind", "")))}</div></div>'
        for item in schema.data_shapes
    )
    persistent_shape_cards = "".join(
        f'<div class="card"><h3>{escape(item["id"])}</h3><p>{escape(item.get("description", ""))}</p>'
        f'<div class="footer-note">Store: {escape(str(item.get("data_store_container", "")))}</div></div>'
        for item in schema.persistent_shapes
    )
    return (
        '<div class="grid">' + early_state_cards + "</div>"
        + '<div class="grid">' + data_shape_cards + "</div>"
        + '<div class="grid">' + persistent_shape_cards + "</div>"
    )


def _render_deployment_section(schema: ForgeSchema) -> str:
    environments = schema.deployment.get("environments", [])
    blocks = []
    for environment in environments:
        node_cards = "".join(
            f'<div class="card"><h3>{escape(node["id"])}</h3><p>{escape(node.get("description", ""))}</p>'
            f'<div class="footer-note">Kind: {escape(str(node.get("kind", "")))}<br />'
            f'Trust Boundary: {escape(str(node.get("trust_boundary", "")))}</div></div>'
            for node in environment.get("nodes", [])
        )
        blocks.append(
            f'<div class="card"><h3>{escape(environment["id"])}</h3><p>{escape(environment.get("description", ""))}</p></div>'
            + '<div class="grid">' + node_cards + '</div>'
        )
    return "".join(blocks)


def _render_high_level_flow(flow: dict[str, object]) -> str:
    return _flow_panel(flow, "Business/system flow", include_container=False)


def _render_runtime_flow(flow: dict[str, object]) -> str:
    return _flow_panel(flow, "Container-level runtime flow", include_container=True)


def _render_container_section(container: dict[str, object]) -> str:
    components = container.get("components", [])
    cards = '<div class="grid">' + "".join(
        f'<div class="card"><h3>{escape(component["id"])}</h3><p>{escape(component.get("description", ""))}</p></div>'
        for component in components
    ) + "</div>"
    diagram = _render_container_graph(container)
    flow_panels = "".join(
        _flow_panel(flow, f"Component Flow: {flow.get('id')}", include_component=True, target_prefix="component")
        for flow in container.get("component_flows", [])
    )
    return cards + _diagram_card("Container Components", "Internal component structure and flow handoffs", diagram) + flow_panels


def _flow_panel(flow: dict[str, object], subtitle: str, include_container: bool = False, include_component: bool = False, target_prefix: str = "container") -> str:
    steps_html = []
    for step in flow.get("steps", []):
        branches = step.get("branches", [])
        branch_html = ""
        if branches:
            branch_html = "<ul class='branch-list'>" + "".join(
                f"<li><strong>{escape(branch.get('condition', 'Condition'))}</strong><br />"
                f"{escape(str(branch.get('outgoing', '')))}</li>"
                for branch in branches
            ) + "</ul>"
        subject = ""
        if include_container and step.get("container"):
            subject = f"<div class='pill-list'><span class='pill' data-target='container-{escape(step['container'])}'>Container: {escape(step['container'])}</span></div>"
        if include_component and step.get("component"):
            subject = f"<div class='pill-list'><span class='pill'>{escape(step['component'])}</span></div>"
        steps_html.append(
            f"<div class='flow-step'><h4>Step {step.get('id')}</h4>{subject}<p>{escape(str(step.get('description', '')))}</p>"
            f"<div class='footer-note'>Outgoing: {escape(str(step.get('outgoing', '')))}</div>{branch_html}</div>"
        )
    outcomes = flow.get("outcomes", [])
    outcome_block = ""
    if outcomes:
        outcome_block = "<div class='card'><h3>Outcomes</h3><p>" + "<br />".join(escape(str(item)) for item in outcomes) + "</p></div>"
    return f"""
      <div class="card">
        <h3>{escape(str(flow.get('id', subtitle)))}</h3>
        <p>{escape(subtitle)}. {escape(str(flow.get('description', '')))}</p>
        <div class="footer-note">Trigger: {escape(str(flow.get('trigger', '')))}</div>
        <div class="flow-steps">{''.join(steps_html)}</div>
      </div>
      {outcome_block}
    """


def _diagram_card(title: str, subtitle: str, inner: str) -> str:
    return f"""
    <div class="card diagram-card">
      <div class="diagram-header">
        <div>
          <h3>{escape(title)}</h3>
          <p>{escape(subtitle)}</p>
        </div>
        <div class="diagram-controls" aria-label="{escape(title)} controls">
          <button class="diagram-control-btn" data-diagram-zoom="out" type="button" aria-label="Zoom out">-</button>
          <button class="diagram-control-btn" data-diagram-zoom="reset" type="button" aria-label="Reset zoom">100%</button>
          <button class="diagram-control-btn" data-diagram-zoom="in" type="button" aria-label="Zoom in">+</button>
        </div>
      </div>
      <div class="diagram-wrap">{inner}</div>
    </div>
    """


def _render_system_graph(system_id: str, actors: list[dict], dependencies: list[dict]) -> str:
    system_node = _elk_node(system_id, "system", "system", target="runtime-overview", partition=1, width=260, height=76)
    graph = _elk_graph([system_node], [])
    graph["children"].extend(
        _elk_node(actor["id"], actor.get("kind", "actor"), "actor", partition=0, width=160, height=68)
        for actor in actors
    )
    graph["children"].extend(
        _elk_node(dep["id"], dep.get("kind", "external"), "dependency", partition=2, width=160, height=68)
        for dep in dependencies
    )
    for actor in actors:
        graph["edges"].append(_elk_edge(actor["id"], system_id, "interacts", style="dashed"))
    for dep in dependencies:
        graph["edges"].append(_elk_edge(system_id, dep["id"], "depends on"))
    return _elk_block(graph)


def _render_runtime_graph(containers: list[dict], relationships: list[dict], deepened_container_ids: set[str]) -> str:
    nodes = [
        _elk_node(
            container["id"],
            str(container.get("kind", "container")),
            _runtime_visual_kind(str(container.get("kind", "container"))),
            target=(f'container-{container["id"]}' if str(container["id"]) in deepened_container_ids else None),
            partition=_runtime_partition(str(container.get("kind", "container"))),
            width=220 if str(container.get("kind", "")) != "database" else 200,
            height=78,
        )
        for container in containers
    ]
    edges = [
        _elk_edge(str(relation.get("from", "")), str(relation.get("to", "")), str(relation.get("description", "")))
        for relation in relationships
    ]
    return _elk_block(_elk_graph(nodes, edges))


def _render_container_graph(container: dict[str, object]) -> str:
    components = container.get("components", [])
    flow_steps: list[dict[str, object]] = []
    for flow in container.get("component_flows", []):
        flow_steps.extend(flow.get("steps", []))

    order_map: dict[str, int] = {}
    for index, step in enumerate(flow_steps):
        component_id = step.get("component")
        if component_id and component_id not in order_map:
            order_map[str(component_id)] = index

    nodes = [
        _elk_node(
            component["id"],
            "component",
            "component",
            partition=order_map.get(str(component["id"]), len(order_map)),
            width=220,
            height=72,
        )
        for component in components
    ]
    seen_edges: set[tuple[str, str]] = set()
    edges: list[dict[str, object]] = []
    for flow in container.get("component_flows", []):
        steps = flow.get("steps", [])
        for step in steps:
            if step.get("next") is None:
                continue
            next_step = next((candidate for candidate in steps if candidate.get("id") == step.get("next")), None)
            if not next_step or not step.get("component") or not next_step.get("component"):
                continue
            key = (str(step["component"]), str(next_step["component"]))
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append(_elk_edge(key[0], key[1], "flows to"))
    return _elk_block(_elk_graph(nodes, edges))


def _graph_targets(schema: ForgeSchema) -> dict[str, str]:
    targets: dict[str, str] = {}
    system_id = schema.system.get("id")
    if system_id:
        targets[_elk_id(str(system_id))] = "runtime-overview"
    for container in schema.containers:
        targets[_elk_id(str(container["id"]))] = f'container-{container["id"]}'
    return targets


def _elk_id(value: str) -> str:
    safe = []
    for char in value:
        safe.append(char if char.isalnum() else "_")
    collapsed = "".join(safe).strip("_")
    return collapsed or "node"


def _elk_node(
    node_id: str,
    subtitle: str,
    kind: str,
    *,
    target: str | None = None,
    partition: int = 0,
    width: float = 180,
    height: float = 72,
) -> dict[str, object]:
    return {
        "id": _elk_id(node_id),
        "width": width,
        "height": height,
        "layoutOptions": {
            "elk.partitioning.partition": str(partition),
        },
        "forge": {
            "label": str(node_id),
            "subtitle": str(subtitle),
            "kind": kind,
            "target": target,
        },
    }


def _elk_edge(source: str, target: str, label: str, *, style: str = "solid") -> dict[str, object]:
    return {
        "id": f'{_elk_id(source)}__{_elk_id(target)}__{len(label)}',
        "sources": [_elk_id(source)],
        "targets": [_elk_id(target)],
        "forge": {
            "label": label,
            "style": style,
        },
    }


def _elk_graph(nodes: list[dict[str, object]], edges: list[dict[str, object]]) -> dict[str, object]:
    return {
        "id": "root",
        "layoutOptions": {
            "elk.algorithm": "layered",
            "elk.direction": "RIGHT",
            "elk.partitioning.activate": "true",
            "elk.spacing.nodeNode": "56",
            "elk.layered.spacing.nodeNodeBetweenLayers": "120",
            "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
            "elk.layered.nodePlacement.bk.fixedAlignment": "BALANCED",
            "elk.edgeRouting": "ORTHOGONAL",
            "elk.layered.unnecessaryBendpoints": "true",
        },
        "children": nodes,
        "edges": edges,
    }


def _elk_block(graph: dict[str, object]) -> str:
    return f'<div class="elk-graph" data-graph="{escape(json.dumps(graph), quote=True)}"></div>'


def _runtime_partition(kind: str) -> int:
    if kind.startswith("client_side") or kind == "mobile_app":
        return 0
    if kind in {"database", "blob_or_content_store", "file_system"}:
        return 2
    if kind == "external_container":
        return 3
    return 1


def _runtime_visual_kind(kind: str) -> str:
    if kind == "database":
        return "database"
    if kind == "external_container":
        return "external"
    return "container"
