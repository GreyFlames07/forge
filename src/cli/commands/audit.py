from __future__ import annotations

import base64
import errno
import hashlib
import json
import platform
import subprocess
from argparse import Namespace
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cli.commands.base import add_project_dir_arg
from cli.common import find_project_root
from cli.crawler import ForgeCrawlError, ForgeCrawlResult, crawl_project, dump_crawl_error
from cli.schema import ForgeSchema, load_schema

DEFAULT_AUDIT_PORT = 49891


def register_audit(subparsers) -> None:
    parser = subparsers.add_parser("audit", help="Launch a live Forge audit dashboard webserver")
    add_project_dir_arg(parser)
    parser.add_argument("--output", "-o", default="./forge-audit.html", help="Output HTML path")
    parser.add_argument(
        "--artifact",
        action="store_true",
        help="Write the static audit HTML artifact instead of launching the live webserver",
    )
    parser.add_argument("--no-open", action="store_true", help="Do not automatically open the browser or generated audit artifact")
    parser.add_argument("--headless", action="store_true", help="Alias for --no-open")
    parser.add_argument("--port", type=int, default=DEFAULT_AUDIT_PORT, help="Live audit server port")
    parser.set_defaults(func=run)


def run(args: Namespace) -> int:
    requested_root = Path(args.project_dir).resolve() if args.project_dir else None
    suppress_open = bool(args.no_open or args.headless)
    if args.artifact:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(_render_audit_for_path(requested_root), encoding="utf-8")
        if not suppress_open:
            _open_file(output)
        print(f"Forge audit written to {output}")
        return 0

    root = _audit_root(requested_root)
    _serve_audit(root, open_browser=not suppress_open, port=args.port)
    return 0


def _audit_root(requested_root: Path | None) -> Path:
    try:
        return crawl_project(requested_root or Path.cwd()).root
    except FileNotFoundError:
        return find_project_root(requested_root)


def _render_audit_for_path(root: Path | None) -> str:
    try:
        return render_v4_audit_html(crawl_project(root or Path.cwd()))
    except FileNotFoundError:
        return render_audit_html(load_schema(find_project_root(root)))
    except ForgeCrawlError as exc:
        return f"<html><body><h1>Forge audit error</h1><pre>{escape(dump_crawl_error(exc, 'json', root))}</pre></body></html>"


def _serve_audit(root: Path, *, open_browser: bool, port: int = DEFAULT_AUDIT_PORT) -> None:
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), _audit_handler(root))
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            print(f"Forge audit live server already running at http://127.0.0.1:{port}")
            return
        raise
    host, port = server.server_address
    url = f"http://{host}:{port}"
    if open_browser:
        _open_file(url)
    print(f"Forge audit live server running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nForge audit server stopped.")
    finally:
        server.server_close()


def _audit_handler(root: Path) -> type[BaseHTTPRequestHandler]:
    class AuditHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/__forge_audit_version":
                html = _render_audit_for_path(root)
                payload = json.dumps({"version": hashlib.sha256(html.encode("utf-8")).hexdigest()}).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            if self.path not in {"/", "/index.html"}:
                self.send_error(HTTPStatus.NOT_FOUND, "Not found")
                return
            try:
                html = _render_audit_for_path(root)
            except Exception as exc:  # pragma: no cover - exercised via direct helper test
                body = f"<html><body><h1>Forge audit error</h1><pre>{escape(str(exc))}</pre></body></html>"
                payload = body.encode("utf-8")
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            else:
                payload = html.encode("utf-8")
                self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            del format, args

    return AuditHandler


def render_live_audit_html(root: Path) -> str:
    """Render the live audit dashboard from the current on-disk schema."""
    return _render_audit_for_path(root)


def render_v4_audit_html(result: ForgeCrawlResult) -> str:
    """Render the V4 audit dashboard using the shared audit web structure."""
    model = result.to_dict()
    system = model["system"]
    sections: list[dict[str, str]] = [
        {"id": "system-overview", "group": "System", "label": "System"},
        {"id": "runtime-overview", "group": "Runtime", "label": "Runtime Overview"},
        {"id": "data-overview", "group": "Data", "label": "Entities & Data"},
        {"id": "verticals-overview", "group": "Verticals", "label": "Findings"},
    ]
    dynamic_sections: list[str] = []
    for flow in model["container_flows"]:
        section_id = f"flow-{flow['id']}"
        sections.append({"id": section_id, "group": "Flows", "label": str(flow["id"])})
        dynamic_sections.append(
            _section(
                section_id,
                "Flows",
                f"Flow: {flow['id']}",
                "Container-level flow across runtime boundaries.",
                _render_v4_flow_section(flow, model),
                str(system.get("id", "forge")),
                with_header=False,
            )
        )
    for container in model["containers"]:
        section_id = f"container-{container['id']}"
        sections.append({"id": section_id, "group": "Runtime", "label": f"Container: {container['id']}"})
        dynamic_sections.append(
            _section(
                section_id,
                "Runtime",
                f"Container: {container['id']}",
                "Source-root components, data shapes, and extracted operations.",
                _render_v4_container_section(container),
                str(system.get("id", "forge")),
                with_header=False,
            )
        )
    for entity in model["entities"]:
        section_id = f"entity-{entity['id']}"
        sections.append({"id": section_id, "group": "Data", "label": str(entity["id"])})
        dynamic_sections.append(
            _section(
                section_id,
                "Data",
                f"Entity: {entity['id']}",
                "Business state, canonical shape, ownership, and persistence.",
                _render_v4_entity_section(entity, model),
                str(system.get("id", "forge")),
                with_header=False,
            )
        )
    for doc in result.forge_docs:
        section_id = f"doc-{_elk_id(doc.stem)}"
        sections.append({"id": section_id, "group": "System", "label": doc.name})
        dynamic_sections.append(
            _section(
                section_id,
                "System",
                f"Doc: {doc.name}",
                "Markdown document from the Forge folder.",
                _render_v4_doc_section(doc),
                str(system.get("id", "forge")),
                with_header=False,
            )
        )

    template = _template_text("audit_template.html")
    replacements = {
        "__DYNAMIC_ITEM_BUTTONS_HTML__": "".join(
            _item_button(section["label"], section["id"], section["group"])
            for section in _toolbar_sections(sections)
        ),
        "__SYSTEM_ID__": escape(str(system.get("id", "forge"))),
        "__AUDIT_DATA__": json.dumps(
            {
                "system_id": system.get("id"),
                "verticals": [],
                "runtime_flows": [flow.get("id") for flow in model["container_flows"]],
                "containers": [container.get("id") for container in model["containers"]],
                "graph_targets": _v4_graph_targets(model),
            }
        ),
        "__OVERVIEW_BODY__": _render_v4_overview_section(model),
        "__SYSTEM_BODY__": _render_v4_system_section(model),
        "__RUNTIME_BODY__": _render_v4_runtime_section(model),
        "__DATA_BODY__": _render_v4_data_section(model),
        "__VERTICALS_BODY__": _render_v4_findings_overview(model),
        "__DEPLOYMENT_BODY__": "",
        "__DYNAMIC_SECTIONS_HTML__": "".join(dynamic_sections),
        "./forge_white_small.drawio.svg": _asset_data_url("forge_white_small.drawio.svg"),
        "./forge_full_logo.drawio.svg": _asset_data_url("forge_full_logo.drawio.svg"),
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template


def _v4_audit_section(title: str, body: str) -> str:
    return f"<section><h2>{escape(title)}</h2>{body}</section>"


def _render_v4_overview_section(model: dict[str, object]) -> str:
    system = model["system"]
    summary = model["summary"]
    cards = [
        ("System", str(system.get("id", "forge")), "system-overview"),
        ("Containers", str(summary.get("containers", 0)), "runtime-overview"),
        ("Flows", str(summary.get("container_flows", 0)), "flow-" + str(model["container_flows"][0]["id"]) if model["container_flows"] else "runtime-overview"),
        ("Findings", str(summary.get("validation_findings", 0)), "verticals-overview"),
    ]
    summary_html = "".join(
        '<div class="card card-defined" role="button" tabindex="0" '
        f'data-target="{escape(target)}"><h3>{escape(title)}</h3><p>{escape(value)}</p></div>'
        for title, value, target in cards
    )
    return (
        _section_header(
            "overview",
            f"{system.get('id', 'forge')} / Overview",
            "Forge V4 Audit",
            "C1/C2 central schema plus extracted C3 implementation annotations.",
        )
        + f'<div class="grid grid-4">{summary_html}</div>'
    )


def _render_v4_system_section(model: dict[str, object]) -> str:
    system = model["system"]
    cards = f"""
    <div class="grid grid-1 system-summary-grid">
      <div class="card"><h3>Purpose</h3><p>{escape(str(system.get('purpose', '')))}</p></div>
      <div class="card"><h3>Boundary</h3><p>{escape(str(system.get('boundary', '')))}</p></div>
      <div class="card"><h3>Security</h3><p>{escape(str(system.get('security', '')))}</p></div>
    </div>
    """
    actions = "".join(
        f'<div class="card"><h3>{escape(str(action.get("id", "")))}</h3>'
        f'<p>{escape(str(action.get("intent", "")))}</p>'
        f'<div class="pill-list"><span class="kind-chip chip-shape">{escape(str(action.get("actor", "")))}</span></div></div>'
        for action in system.get("business_actions", [])
        if isinstance(action, dict)
    )
    diagram = _render_system_graph(
        str(system.get("id", "system")),
        [item for item in system.get("actors", []) if isinstance(item, dict)],
        [item for item in system.get("external_dependencies", []) if isinstance(item, dict)],
    )
    return cards + _diagram_card("System Context", "Actors, boundary, and external dependencies", diagram) + '<div class="vertical-cards">' + actions + "</div>"


def _render_v4_runtime_section(model: dict[str, object]) -> str:
    containers = model["containers"]
    relationships = _v4_relationships(model)
    deepened = {str(container.get("id")) for container in containers}
    cards = '<div class="vertical-cards">' + "".join(_v4_container_card(container) for container in containers) + "</div>"
    diagram = _render_runtime_graph(containers, relationships, deepened)
    return (
        _diagram_card("Runtime Topology", "Unique directed connections between runtime containers", diagram)
        + _render_v4_runtime_controls(model)
        + cards
    )


def _render_v4_data_section(model: dict[str, object]) -> str:
    rows = []
    persistence_by_entity = {
        str(item.get("payload", {}).get("entity")): item.get("payload", {})
        for item in model["persistence"]
        if isinstance(item, dict) and isinstance(item.get("payload"), dict)
    }
    for entity in model["entities"]:
        target = f"entity-{entity['id']}"
        chips = _v4_data_overview_chips(entity, persistence_by_entity.get(str(entity.get("id"))))
        rows.append(
            f'<button class="record-row" type="button" data-target="{escape(target)}">'
            f'<div class="record-main"><h3>{escape(str(entity.get("id", "")))}</h3>'
            f'<p>{escape(str(entity.get("description", "")))}</p></div>'
            f'<div class="record-side"><div class="pill-list">{chips}</div></div>'
            "</button>"
        )
    return '<div class="record-list">' + "".join(rows) + "</div>"


def _v4_data_overview_chips(entity: dict[str, object], persistence: dict[str, object] | None) -> str:
    chip_specs = [("chip-persistent", str(entity.get("category", "")))]
    if persistence:
        chip_specs.extend(
            [
                ("chip-storage", str(persistence.get("storage_model", ""))),
                ("chip-deploy", str(persistence.get("physical_store", ""))),
                ("chip-table", str(persistence.get("table", ""))),
            ]
        )
        lifecycle = persistence.get("lifecycle")
        if isinstance(lifecycle, dict):
            states = lifecycle.get("states")
            if isinstance(states, list) and states:
                chip_specs.append(("chip-lifecycle", f"{len(states)} states"))
    return "".join(
        f'<span class="kind-chip {css_class}">{escape(label)}</span>'
        for css_class, label in chip_specs
        if label
    )


def _render_v4_findings_overview(model: dict[str, object]) -> str:
    return (
        _section_header(
            "verticals-overview",
            f"{model['system'].get('id', 'forge')} / Validation",
            "Validation Findings",
            "Crawler and schema findings from the extracted model.",
        )
        + _v4_findings_html(model["findings"])
    )


def _render_v4_runtime_controls(model: dict[str, object]) -> str:
    environments: set[str] = set()
    for container in model["containers"]:
        for deployment in container.get("deployment", []):
            if isinstance(deployment, dict):
                environments.add(str(deployment.get("environment", "unknown")))
    if not environments:
        return ""
    options = "".join(
        f'<option value="{escape(environment)}">{escape(environment)}</option>'
        for environment in sorted(environments)
    )
    return (
        '<div class="runtime-controls" data-environment-config>'
        '<div><h3>Runtime Containers</h3><p>Deployment fields update by environment.</p></div>'
        f'<select class="environment-select" data-environment-select aria-label="Deployment environment">{options}</select>'
        '</div>'
    )


def _render_v4_flow_section(flow: dict[str, object], model: dict[str, object]) -> str:
    operations = [
        operation
        for container in model["containers"]
        for operation in container.get("operations", [])
        if _v4_operation_in_flow_payload(operation, str(flow.get("id", "")))
    ]
    return _v4_flow_card(flow, operations)


def _render_v4_container_section(container: dict[str, object]) -> str:
    diagram = _diagram_card(
        "Extracted Components",
        "Components discovered from source-root annotations.",
        _render_v4_component_graph(container),
        css_class="diagram-card-compact",
    )
    components = _component_rows(container.get("components", []))
    shapes = _data_shape_rows(container.get("data_shapes", []))
    operations = _operation_rows(container.get("operations", []))
    return (
        '<div class="container-stack">'
        + diagram
        + f'<div class="card component-table-card"><h4>Components</h4>{components or "<p>No components extracted.</p>"}</div>'
        + f'<div class="card data-shape-table-card"><h4>Data Shapes</h4>{shapes or "<p>No data shapes extracted.</p>"}</div>'
        + f'<div class="card operation-table-card"><h4>Operations</h4>{operations or "<p>No operations extracted.</p>"}</div>'
        + "</div>"
    )


def _render_v4_entity_section(entity: dict[str, object], model: dict[str, object]) -> str:
    shapes = [
        shape
        for container in model["containers"]
        for shape in container.get("data_shapes", [])
        if shape.get("payload", {}).get("entity") == entity.get("id")
    ]
    persistence = [item for item in model["persistence"] if item.get("payload", {}).get("entity") == entity.get("id")]
    return (
        '<div class="entity-detail-stack">'
        + _v4_entity_summary_card(entity)
        + _v4_entity_lifecycle_card(entity)
        + _v4_entity_data_shapes_card(shapes)
        + _v4_entity_persistence_card(persistence)
        + "</div>"
    )


def _render_v4_doc_section(path: Path) -> str:
    return f'<div class="card"><div class="schema-viewer"><pre>{escape(path.read_text(encoding="utf-8"))}</pre></div></div>'


def _component_rows(components: object) -> str:
    if not isinstance(components, list):
        return ""
    rows = []
    for component in components:
        if not isinstance(component, dict):
            continue
        payload = component.get("payload", component)
        if not isinstance(payload, dict):
            payload = {}
        component_id = str(component.get("id") or payload.get("id") or "")
        source = f"{component.get('source', '')}:{component.get('line', '')}".strip(":")
        role = str(payload.get("role", component.get("role", "")))
        description = str(payload.get("description", component.get("description", "")))
        responsibilities = payload.get("responsibilities", component.get("responsibilities", []))
        responsibility_items = "".join(
            f"<li>{escape(str(item))}</li>"
            for item in responsibilities
            if str(item).strip()
        ) if isinstance(responsibilities, list) else ""
        source_html = f'<span class="component-source">{escape(source)}</span>' if source else ""
        role_html = f'<span class="kind-chip chip-storage">{escape(role)}</span>' if role else ""
        responsibility_html = (
            '<div class="component-responsibilities">'
            '<span class="component-row-label">Responsibilities</span>'
            f"<ul>{responsibility_items}</ul>"
            "</div>"
            if responsibility_items
            else ""
        )
        rows.append(
            '<details class="component-table-row component-expandable-row">'
            '<summary class="component-row-head">'
            '<div>'
            f'<h5>{escape(component_id)}</h5>'
            f"{source_html}"
            '</div>'
            f"{role_html}"
            '<span class="entity-shape-chevron" aria-hidden="true"></span>'
            '</summary>'
            '<div class="component-row-body">'
            f'<p>{escape(description)}</p>'
            f"{responsibility_html}"
            '</div>'
            '</details>'
        )
    return f'<div class="component-table">{"".join(rows)}</div>' if rows else ""


def _data_shape_rows(shapes: object) -> str:
    if not isinstance(shapes, list):
        return ""
    rows = []
    for shape in shapes:
        if not isinstance(shape, dict):
            continue
        payload = shape.get("payload", shape)
        if not isinstance(payload, dict):
            payload = {}
        shape_id = str(shape.get("id") or payload.get("id") or "")
        source = f"{shape.get('source', '')}:{shape.get('line', '')}".strip(":")
        kind = str(payload.get("type_kind", payload.get("kind", "")))
        source_html = f'<span class="component-source">{escape(source)}</span>' if source else ""
        kind_html = f'<span class="kind-chip chip-shape">{escape(kind)}</span>' if kind else ""
        rows.append(
            '<div class="component-table-row data-shape-row">'
            '<div class="component-row-head">'
            '<div>'
            f'<h5>{escape(shape_id)}</h5>'
            f"{source_html}"
            '</div>'
            f"{kind_html}"
            '</div>'
            '</div>'
        )
    return f'<div class="component-table data-shape-table">{"".join(rows)}</div>' if rows else ""


def _operation_rows(operations: object) -> str:
    if not isinstance(operations, list):
        return ""
    rows = []
    for operation in operations:
        if not isinstance(operation, dict):
            continue
        payload = operation.get("payload", operation)
        if not isinstance(payload, dict):
            payload = {}
        operation_id = str(operation.get("id") or payload.get("id") or "")
        source = f"{operation.get('source', '')}:{operation.get('line', '')}".strip(":")
        chip_label = str(payload.get("component") or payload.get("local_flow") or payload.get("container_flow") or "operation")
        io_rows = [
            ("Input", payload.get("input", "")),
            ("Returns", payload.get("returns", "")),
        ]
        io_html = "".join(
            f"<tr><th>{escape(label)}</th><td>{escape(str(value))}</td></tr>"
            for label, value in io_rows
            if str(value).strip()
        )
        logic = payload.get("logic", [])
        logic_items = "".join(f"<li>{escape(str(item))}</li>" for item in logic if str(item).strip()) if isinstance(logic, list) else ""
        participates = payload.get("participates_in", [])
        participate_rows = "".join(
            "<tr>"
            f"<td>{escape(str(item.get('container_flow', '')))}</td>"
            f"<td>{escape(str(item.get('local_flow', '')))}</td>"
            f"<td>{escape(str(item.get('step', '')))}</td>"
            f"<td>{escape(str(item.get('passes', '')))}</td>"
            "</tr>"
            for item in participates
            if isinstance(item, dict)
        )
        source_html = f'<span class="component-source">{escape(source)}</span>' if source else ""
        body = (
            '<div class="operation-row-body">'
            + (
                '<div class="metadata-table-wrap operation-io-table"><table class="metadata-table">'
                f"{io_html}"
                "</table></div>"
                if io_html
                else ""
            )
            + (
                '<div class="component-responsibilities">'
                '<span class="component-row-label">Logic</span>'
                f"<ul>{logic_items}</ul>"
                "</div>"
                if logic_items
                else ""
            )
            + (
                '<details class="payload-expandable operation-participation-details">'
                f"<summary>Participation ({len([item for item in participates if isinstance(item, dict)])})</summary>"
                '<div class="metadata-table-wrap"><table class="metadata-table operation-participation-table">'
                "<tr><th>Flow</th><th>Local Flow</th><th>Step</th><th>Passes</th></tr>"
                f"{participate_rows}"
                "</table></div>"
                "</details>"
                if participate_rows
                else ""
            )
            + "</div>"
        )
        rows.append(
            '<details class="component-table-row component-expandable-row operation-row">'
            '<summary class="component-row-head">'
            '<div>'
            f"<h5>{escape(operation_id)}</h5>"
            f"{source_html}"
            "</div>"
            f'<span class="kind-chip chip-deploy">{escape(chip_label)}</span>'
            '<span class="entity-shape-chevron" aria-hidden="true"></span>'
            "</summary>"
            f"{body}"
            "</details>"
        )
    return f'<div class="component-table operation-table">{"".join(rows)}</div>' if rows else ""


def _v4_entity_summary_card(entity: dict[str, object]) -> str:
    refs = [
        ("Category", entity.get("category", "")),
        ("Canonical Type", _v4_ref_text(entity.get("canonical_type"))),
        ("Logical Owner", _v4_ref_text(entity.get("logical_owner"))),
        ("Persisted In", _v4_ref_text(entity.get("persisted_in"))),
    ]
    summary_html = "".join(
        '<div class="metadata-summary-item">'
        f'<span class="metadata-summary-label">{escape(label)}</span>'
        f'<span class="metadata-summary-value">{escape(str(value))}</span>'
        '</div>'
        for label, value in refs
        if str(value).strip()
    )
    security = str(entity.get("security", "")).strip()
    security_row = (
        '<div class="metadata-table-wrap"><table class="metadata-table">'
        f'<tr><th>Security</th><td>{escape(security)}</td></tr>'
        '</table></div>'
        if security
        else ""
    )
    return (
        '<div class="card entity-summary-card">'
        '<div class="card-header">'
        f'<h3>{escape(str(entity.get("id", "")))}</h3>'
        f'<div class="pill-list"><span class="kind-chip chip-persistent">{escape(str(entity.get("category", "")))}</span></div>'
        '</div>'
        f'<p>{escape(str(entity.get("description", "")))}</p>'
        f'<div class="metadata-summary metadata-summary-compact">{summary_html}</div>'
        f'{security_row}'
        f'{_v4_raw_details("Raw Entity Payload", entity)}'
        '</div>'
    )


def _v4_entity_lifecycle_card(entity: dict[str, object]) -> str:
    lifecycle = entity.get("lifecycle")
    if not isinstance(lifecycle, dict):
        return ""
    states = lifecycle.get("states", [])
    transitions = lifecycle.get("transitions", [])
    if not states and not transitions:
        return ""
    state_chips = "".join(f'<span class="kind-chip chip-lifecycle">{escape(str(state))}</span>' for state in states)
    diagram_rows = "".join(
        '<div class="entity-state-transition">'
        f'<span class="entity-state-node">{escape(str(item.get("from", "")))}</span>'
        '<span class="entity-state-arrow" aria-hidden="true">&rarr;</span>'
        f'<span class="entity-state-node">{escape(str(item.get("to", "")))}</span>'
        '</div>'
        for item in transitions
        if isinstance(item, dict)
    )
    state_diagram = (
        f'<div class="entity-state-diagram">{diagram_rows}</div>'
        if diagram_rows
        else f'<div class="entity-state-diagram entity-state-diagram-flat">{state_chips}</div>'
    )
    transition_rows = "".join(
        "<tr>"
        f"<td>{escape(str(item.get('from', '')))}</td>"
        f"<td>{escape(str(item.get('to', '')))}</td>"
        f"<td>{escape(str(item.get('condition', '')))}</td>"
        "</tr>"
        for item in transitions
        if isinstance(item, dict)
    )
    transition_table = (
        '<details class="payload-expandable lifecycle-transition-details">'
        f'<summary>Transitions ({len([item for item in transitions if isinstance(item, dict)])})</summary>'
        '<div class="metadata-table-wrap"><table class="metadata-table lifecycle-transition-table">'
        '<colgroup><col class="lifecycle-col-state"><col class="lifecycle-col-state"><col class="lifecycle-col-condition"></colgroup>'
        '<tr><th>From</th><th>To</th><th>Condition</th></tr>'
        f'{transition_rows}'
        '</table></div>'
        '</details>'
        if transition_rows
        else ""
    )
    return (
        '<div class="card entity-lifecycle-card">'
        '<h4>Lifecycle</h4>'
        f'{state_diagram}'
        f'{transition_table}'
        '</div>'
    )


def _v4_entity_data_shapes_card(shapes: list[dict[str, object]]) -> str:
    rows = []
    for shape in shapes:
        payload = shape.get("payload", {})
        if not isinstance(payload, dict):
            continue
        shape_payload = payload.get("shape", {})
        raw_payload = escape(json.dumps(shape_payload, indent=2))
        rows.append(
            '<details class="entity-shape-row">'
            '<summary>'
            f'<span class="entity-shape-name">{escape(str(shape.get("id", "")))}</span>'
            f'<span class="kind-chip chip-shape">{escape(str(payload.get("type_kind", "")))}</span>'
            '<span class="entity-shape-chevron" aria-hidden="true"></span>'
            '</summary>'
            f'<div class="schema-viewer"><pre>{raw_payload}</pre></div>'
            '</details>'
        )
    row_list = (
        f'<div class="entity-shape-list">{"".join(rows)}</div>'
        if rows
        else "<p>No related data shapes.</p>"
    )
    return f'<div class="card entity-shapes-card"><h4>Related Data Shapes</h4>{row_list}</div>'


def _v4_entity_persistence_card(persistence: list[dict[str, object]]) -> str:
    if not persistence:
        return '<div class="card entity-persistence-card"><h4>Persistence</h4><p>No persistence annotation.</p></div>'
    blocks = []
    for item in persistence:
        payload = item.get("payload", {})
        if not isinstance(payload, dict):
            continue
        summary = [
            ("Storage Model", payload.get("storage_model", "")),
            ("Physical Store", payload.get("physical_store", "")),
            ("Table", payload.get("table", "")),
            ("Migrations", payload.get("migrations_path", "")),
        ]
        summary_html = "".join(
            '<div class="metadata-summary-item">'
            f'<span class="metadata-summary-label">{escape(label)}</span>'
            f'<span class="metadata-summary-value">{escape(str(value))}</span>'
            '</div>'
            for label, value in summary
            if str(value).strip()
        )
        patterns = payload.get("access_patterns", [])
        pattern_list = "".join(f"<li>{escape(str(pattern))}</li>" for pattern in patterns) if isinstance(patterns, list) else ""
        rows = [
            ("Access Patterns", f"<ul>{pattern_list}</ul>" if pattern_list else ""),
            ("Security", escape(str(payload.get("security", "")))),
        ]
        table_rows = "".join(
            f"<tr><th>{escape(label)}</th><td>{value}</td></tr>"
            for label, value in rows
            if str(value).strip()
        )
        blocks.append(
            '<div class="entity-persistence-block">'
            f'<div class="metadata-summary metadata-summary-compact">{summary_html}</div>'
            '<div class="metadata-table-wrap"><table class="metadata-table">'
            f'{table_rows}'
            '</table></div>'
            f'{_v4_raw_details("Raw Persistence Payload", payload)}'
            '</div>'
        )
    return f'<div class="card entity-persistence-card"><h4>Persistence</h4>{"".join(blocks)}</div>'


def _v4_ref_text(value: object) -> str:
    if not isinstance(value, dict):
        return str(value or "")
    return " / ".join(str(value.get(key, "")) for key in ("container", "component", "ref") if value.get(key))


def _v4_raw_details(label: str, payload: object) -> str:
    return (
        '<details class="payload-expandable">'
        f'<summary>{escape(label)}</summary>'
        f'<div class="schema-viewer"><pre>{escape(json.dumps(payload, indent=2))}</pre></div>'
        '</details>'
    )


def _v4_relationships(model: dict[str, object]) -> list[dict[str, object]]:
    seen: set[tuple[str, str]] = set()
    relationships: list[dict[str, object]] = []
    for flow in model["container_flows"]:
        for step in flow.get("steps", []):
            if not isinstance(step, dict) or not step.get("from") or not step.get("to"):
                continue
            key = (str(step["from"]), str(step["to"]))
            if key in seen:
                continue
            seen.add(key)
            relationships.append(
                {
                    "from": step["from"],
                    "to": step["to"],
                    "description": "",
                }
            )
    return relationships


def _render_v4_component_graph(container: dict[str, object]) -> str:
    components = [item for item in container.get("components", []) if isinstance(item, dict)]
    lines = [
        "flowchart LR",
        "  classDef forgeNode fill:#ffffff,stroke:#d1d9e0,stroke-width:1.5px,color:#1f2328;",
    ]
    node_ids = []
    for component in components:
        node_id = _elk_id(str(component.get("id", "")))
        node_ids.append(node_id)
        label = _mermaid_label(str(component.get("id", "")))
        lines.append(f'  {node_id}["{label}"]')
        lines.append(f"  class {node_id} forgeNode;")
    for left, right in zip(node_ids, node_ids[1:]):
        lines.append(f"  {left} ~~~ {right}")
    return _mermaid_block("\n".join(lines))


def _v4_graph_targets(model: dict[str, object]) -> dict[str, str]:
    targets = {}
    system_id = model["system"].get("id")
    if system_id:
        targets[_elk_id(str(system_id))] = "runtime-overview"
    for container in model["containers"]:
        targets[_elk_id(str(container.get("id", "")))] = f'container-{container.get("id", "")}'
    return targets


def _v4_operation_in_flow_payload(operation: dict[str, object], flow_id: str) -> bool:
    payload = operation.get("payload", {})
    if not isinstance(payload, dict):
        return False
    if payload.get("container_flow") == flow_id:
        return True
    return any(
        item.get("container_flow") == flow_id
        for item in payload.get("participates_in", [])
        if isinstance(item, dict)
    )


def _v4_mapping_table(payload: dict[str, object]) -> str:
    excluded = {"actors", "business_actions", "external_dependencies"}
    rows = "".join(
        f"<tr><th>{escape(str(key))}</th><td>{escape(str(value))}</td></tr>"
        for key, value in payload.items()
        if key not in excluded
    )
    return f"<table>{rows}</table>"


def _v4_container_card(container: dict[str, object]) -> str:
    chips = "".join(
        f'<span class="kind-chip">{escape(str(item))}</span>'
        for item in [container.get("kind"), container.get("technology"), container.get("source_root")]
        if item
    )
    components = "".join(
        f'<li>{escape(str(component.get("id", "")))}</li>'
        for component in container.get("components", [])
        if isinstance(component, dict)
    )
    component_count = len(container.get("components", []))
    deployment_panels = _v4_container_deployment_panels(container)
    return (
        '<div class="card runtime-container-card">'
        '<div class="runtime-container-header">'
        f'<h3>{escape(str(container.get("id", "")))}</h3>'
        f'<div class="runtime-container-meta">{chips}</div>'
        '</div>'
        f'<p class="runtime-container-description">{escape(str(container.get("description", "")))}</p>'
        '<details class="runtime-component-dropdown">'
        f'<summary>Components ({component_count})</summary>'
        f'<ul>{components or "<li>No components extracted.</li>"}</ul>'
        '</details>'
        f'{deployment_panels}'
        '</div>'
    )


def _v4_container_deployment_panels(container: dict[str, object]) -> str:
    deployments = [
        deployment
        for deployment in container.get("deployment", [])
        if isinstance(deployment, dict)
    ]
    panels = []
    for index, deployment in enumerate(deployments):
        environment = str(deployment.get("environment", "unknown"))
        hidden = "" if index == 0 else " hidden"
        platform = escape(str(deployment.get("platform", "")))
        node = escape(str(deployment.get("node", "")))
        endpoint = escape(str(deployment.get("endpoint", "")))
        panels.append(
            f'<div class="runtime-deployment-panel"{hidden} data-environment-panel="{escape(environment)}">'
            '<div class="runtime-deployment-copy">'
            '<div class="runtime-deployment-label">Deployment</div>'
            f'<p>{escape(str(deployment.get("notes", "")))}</p>'
            '</div>'
            '<div class="runtime-deployment-fields">'
            f'<div><span>Platform</span><strong>{platform}</strong></div>'
            f'<div><span>Node</span><strong>{node}</strong></div>'
            f'<div class="runtime-deployment-endpoint"><span>Endpoint</span><strong>{endpoint}</strong></div>'
            '</div>'
            '</div>'
        )
    return "".join(panels)


def _v4_flow_card(flow: dict[str, object], operations: list[dict[str, object]] | None = None) -> str:
    flow_id = str(flow.get("id", ""))
    flow_operations = operations or []
    steps = "".join(
        _v4_flow_step_row(step, flow_id, flow_operations)
        for step in flow.get("steps", [])
        if isinstance(step, dict)
    )
    diagram = _diagram_card(
        f"Flow Diagram: {flow.get('id', '')}",
        "Numbered edges correspond to the flow steps below.",
        _render_v4_flow_graph(flow),
    )
    return (
        '<div class="card">'
        f'<h3>{escape(str(flow.get("id", "")))}</h3>'
        f'<p>{escape(str(flow.get("description", "")))}</p>'
        f"{diagram}"
        '<div class="flow-step-list">'
        f"{steps or '<p>No flow steps extracted.</p>'}"
        "</div>"
        "</div>"
    )


def _v4_flow_step_row(step: dict[str, object], flow_id: str, operations: list[dict[str, object]]) -> str:
    logic = step.get("logic", [])
    if isinstance(logic, list):
        logic_items = "".join(f"<li>{escape(str(item))}</li>" for item in logic if str(item).strip())
    else:
        logic_items = f"<li>{escape(str(logic))}</li>" if str(logic).strip() else ""
    step_id = str(step.get("id", ""))
    input_value = str(step.get("input", ""))
    output_value = _v4_step_output(step)
    operation_groups = _v4_step_operation_groups(operations, flow_id, step_id)
    operation_group_html = "".join(
        '<details class="flow-local-group">'
        '<summary>'
        '<span>'
        f'<strong>{escape(group["container"])}</strong>'
        f'<em>{escape(group["local_flow"])}</em>'
        '</span>'
        f'<span>{len(group["operations"])} operations</span>'
        '</summary>'
        '<div class="flow-operation-list">'
        + "".join(_v4_flow_operation_row(operation) for operation in group["operations"])
        + '</div>'
        '</details>'
        for group in operation_groups
    )
    return (
        '<details class="flow-step-row">'
        '<summary class="flow-step-summary">'
        f'<span class="flow-step-index">{escape(step_id)}</span>'
        '<span class="flow-step-visible">'
        f'<strong>{escape(str(step.get("from", "")))} → {escape(str(step.get("to", "")))}</strong>'
        '</span>'
        '<span class="entity-shape-chevron" aria-hidden="true"></span>'
        '</summary>'
        '<div class="flow-step-content">'
        '<ul class="flow-step-io">'
        f'<li><span>Input</span><strong>{escape(input_value)}</strong></li>'
        f'<li><span>Output</span><strong>{escape(output_value)}</strong></li>'
        '</ul>'
        + (
            '<div class="flow-step-logic">'
            '<span>Logic</span>'
            f'<ul>{logic_items}</ul>'
            '</div>'
            if logic_items
            else ""
        )
        + (
            '<div class="flow-step-local">'
            '<span class="component-row-label">Local flows and operations</span>'
            f'{operation_group_html}'
            '</div>'
            if operation_group_html
            else ""
        )
        + '</div>'
        '</details>'
    )


def _v4_step_operation_groups(
    operations: list[dict[str, object]],
    flow_id: str,
    step_id: str,
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for operation in operations:
        payload = operation.get("payload", {})
        if not isinstance(payload, dict):
            continue
        entries: list[dict[str, object]] = []
        if payload.get("container_flow") == flow_id and str(payload.get("step", "")) == step_id:
            entries.append(payload)
        entries.extend(
            item
            for item in payload.get("participates_in", [])
            if (
                isinstance(item, dict)
                and item.get("container_flow") == flow_id
                and str(item.get("step", "")) == step_id
            )
        )
        for entry in entries:
            local_flow = str(entry.get("local_flow") or payload.get("local_flow") or "local_flow")
            container = _v4_operation_container_label(operation, payload, local_flow)
            grouped.setdefault((container, local_flow), []).append(operation)
    return [
        {"container": container, "local_flow": local_flow, "operations": group_operations}
        for (container, local_flow), group_operations in sorted(grouped.items())
    ]


def _v4_operation_container_label(operation: dict[str, object], payload: dict[str, object], local_flow: str) -> str:
    explicit = operation.get("container") or payload.get("container")
    if explicit:
        return str(explicit)
    if local_flow.endswith("_frontend"):
        return "frontend_ui"
    if local_flow.endswith("_backend"):
        return "backend_api"
    return "container"


def _v4_flow_operation_row(operation: dict[str, object]) -> str:
    payload = operation.get("payload", {})
    if not isinstance(payload, dict):
        payload = {}
    source = f"{operation.get('source', '')}:{operation.get('line', '')}"
    io_items = "".join(
        f"<li><span>{escape(label)}</span><strong>{escape(str(value))}</strong></li>"
        for label, value in (("Input", payload.get("input")), ("Returns", payload.get("returns")))
        if value
    )
    logic = payload.get("logic", [])
    logic_items = ""
    if isinstance(logic, list):
        logic_items = "".join(f"<li>{escape(str(item))}</li>" for item in logic if str(item).strip())
    elif str(logic).strip():
        logic_items = f"<li>{escape(str(logic))}</li>"
    return (
        '<details class="flow-operation-row">'
        '<summary>'
        '<span>'
        f'<strong>{escape(str(operation.get("id", "")))}</strong>'
        f'<em>{escape(source)}</em>'
        '</span>'
        '<span></span>'
        '<span class="entity-shape-chevron" aria-hidden="true"></span>'
        '</summary>'
        + (f'<ul class="flow-step-io flow-operation-io">{io_items}</ul>' if io_items else "")
        + (
            '<div class="flow-step-logic">'
            '<span>Logic</span>'
            f'<ul>{logic_items}</ul>'
            '</div>'
            if logic_items
            else ""
        )
        + '</details>'
    )


def _render_v4_flow_graph(flow: dict[str, object]) -> str:
    container_ids: list[str] = []
    edge_numbers_by_pair: dict[tuple[str, str], list[str]] = {}
    for step in flow.get("steps", []):
        if not isinstance(step, dict):
            continue
        source = step.get("from")
        target = step.get("to")
        if not source or not target:
            continue
        for container_id in (str(source), str(target)):
            if container_id not in container_ids:
                container_ids.append(container_id)
        edge_numbers_by_pair.setdefault((str(source), str(target)), []).append(str(step.get("id", "")))
    edges = [
        _elk_edge(
            source,
            target,
            ", ".join(number for number in numbers if number),
            show_label=True,
            label_wrap=8,
        )
        for (source, target), numbers in edge_numbers_by_pair.items()
    ]
    nodes = [
        _elk_node(container_id, "container", _runtime_visual_kind(container_id), partition=index, width=220, height=78)
        for index, container_id in enumerate(container_ids)
    ]
    return _elk_block(_elk_graph(nodes, edges))


def _render_v4_local_flow_graph(operations: list[dict[str, object]], flow_id: str) -> str:
    grouped: dict[str, list[dict[str, object]]] = {}
    for operation in operations:
        payload = operation.get("payload", {})
        if not isinstance(payload, dict):
            continue
        entries = []
        if payload.get("container_flow") == flow_id:
            entries.append(payload)
        entries.extend(
            item
            for item in payload.get("participates_in", [])
            if isinstance(item, dict) and item.get("container_flow") == flow_id
        )
        for entry in entries:
            local_flow = str(entry.get("local_flow", "local_flow"))
            grouped.setdefault(local_flow, []).append(operation)

    blocks: list[str] = []
    for local_flow, local_operations in sorted(grouped.items()):
        nodes = [
            _elk_node(
                str(operation.get("id", "")),
                str(operation.get("component", "") or operation.get("container", "") or "operation"),
                "component",
                partition=index,
                width=240,
                height=74,
            )
            for index, operation in enumerate(local_operations)
        ]
        edges = []
        sorted_operations = sorted(local_operations, key=lambda item: _v4_operation_step(item, flow_id, local_flow))
        for index, operation in enumerate(sorted_operations[:-1]):
            next_operation = sorted_operations[index + 1]
            step_number = _v4_operation_step(operation, flow_id, local_flow)
            edges.append(
                _elk_edge(
                    str(operation.get("id", "")),
                    str(next_operation.get("id", "")),
                    str(step_number),
                    show_label=True,
                    label_wrap=8,
                )
            )
        blocks.append(
            _diagram_card(
                f"Local Flow: {local_flow}",
                "Numbered operation edges correspond to extracted operation steps.",
                _elk_block(_elk_graph(nodes, edges)),
            )
        )
    return "".join(blocks)


def _v4_operation_step(operation: dict[str, object], flow_id: str, local_flow: str) -> int:
    payload = operation.get("payload", {})
    if not isinstance(payload, dict):
        return 0
    if payload.get("container_flow") == flow_id and payload.get("local_flow") == local_flow:
        return int(payload.get("step", 0) or 0)
    for item in payload.get("participates_in", []):
        if isinstance(item, dict) and item.get("container_flow") == flow_id and item.get("local_flow") == local_flow:
            return int(item.get("step", 0) or 0)
    return 0


def _v4_step_output(step: dict[str, object]) -> str:
    if step.get("output"):
        return str(step["output"])
    branches = step.get("branches", [])
    if not isinstance(branches, list):
        return ""
    return "; ".join(
        f"{branch.get('condition', 'branch')}: {branch.get('output', '')}"
        for branch in branches
        if isinstance(branch, dict)
    )


def _v4_step_logic(step: dict[str, object]) -> str:
    logic = step.get("logic", [])
    if not isinstance(logic, list):
        return escape(str(logic))
    return "<br />".join(escape(str(item)) for item in logic)


def _v4_entity_card(entity: dict[str, object]) -> str:
    return (
        '<div class="card">'
        f'<h3>{escape(str(entity.get("id", "")))}</h3>'
        f'<p>{escape(str(entity.get("description", "")))}</p>'
        f"<pre>{escape(json.dumps(entity, indent=2))}</pre>"
        "</div>"
    )


def _v4_annotation_card(annotation: dict[str, object]) -> str:
    source = f"{annotation.get('source', '')}:{annotation.get('line', '')}"
    return (
        '<div class="card">'
        f'<h3>{escape(str(annotation.get("id", "")))}</h3>'
        f'<p class="muted">{escape(source)}</p>'
        f"<pre>{escape(json.dumps(annotation.get('payload', {}), indent=2))}</pre>"
        "</div>"
    )


def _v4_findings_html(findings: dict[str, object]) -> str:
    blocks = []
    for group, items in findings.items():
        if not isinstance(items, list) or not items:
            continue
        body = "".join(f"<pre>{escape(json.dumps(item, indent=2))}</pre>" for item in items)
        blocks.append(f'<div class="card"><h3>{escape(str(group))}</h3>{body}</div>')
    return "".join(blocks) or '<div class="card"><p>No validation findings.</p></div>'


def _v4_docs_html(result: ForgeCrawlResult) -> str:
    cards = []
    for path in result.forge_docs:
        cards.append(f'<div class="card"><h3>{escape(path.name)}</h3><pre>{escape(path.read_text(encoding="utf-8"))}</pre></div>')
    return "".join(cards) or '<div class="card"><p>No Forge markdown docs found.</p></div>'


def _open_file(path: str | Path) -> None:
    target = str(path)
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", target], check=False)
    elif system == "Windows":
        subprocess.run(["cmd", "/c", "start", "", target], check=False)
    else:
        subprocess.run(["xdg-open", target], check=False)


def _template_text(filename: str) -> str:
    templates_root = Path(__file__).resolve().parents[1] / "assets"
    return (templates_root / filename).read_text(encoding="utf-8")


def _asset_data_url(filename: str, mime_type: str = "image/svg+xml") -> str:
    assets_root = Path(__file__).resolve().parents[1] / "assets"
    asset_bytes = (assets_root / filename).read_bytes()
    if mime_type == "image/svg+xml":
        svg_text = asset_bytes.decode("utf-8")
        svg_text = svg_text.replace("color-scheme: light dark;", "")
        svg_text = svg_text.replace(
            "fill: light-dark(#ffffff, var(--ge-dark-color, #121212));",
            "fill: #ffffff;",
        )
        svg_text = svg_text.replace(
            "stroke: light-dark(rgb(0, 0, 0), rgb(255, 255, 255));",
            "stroke: rgb(0, 0, 0);",
        )
        asset_bytes = svg_text.encode("utf-8")
    encoded = base64.b64encode(asset_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def render_audit_html(schema: ForgeSchema) -> str:
    data_entries = _build_data_entries(schema)
    sections: list[dict[str, str]] = [
        {"id": "system-overview", "group": "System", "label": "System"},
        {"id": "runtime-overview", "group": "Runtime", "label": "Runtime Overview"},
        {"id": "data-overview", "group": "Data", "label": "Data Overview"},
        {"id": "verticals-overview", "group": "Verticals", "label": "Verticals"},
    ]
    dynamic_sections: list[str] = []

    related_runtime_ids: set[str] = set()
    for flow in schema.high_level_flows:
        section_id = f"flow-{flow['id']}"
        sections.append({"id": section_id, "group": "Flows", "label": str(flow["id"])})
        runtime_flows = _runtime_flows_for_high_level(schema, flow)
        related_runtime_ids.update(str(item.get("id", "")) for item in runtime_flows)
        dynamic_sections.append(
            _section(
                section_id,
                "Flows",
                f"Flow: {flow['id']}",
                "High-level flow with nested runtime and component realization.",
                _render_flow_section(schema, flow, runtime_flows),
                schema.system.get("id", "forge"),
            )
        )

    for flow in schema.runtime_flows:
        if str(flow.get("id", "")) in related_runtime_ids:
            continue
        section_id = f"flow-runtime-{flow['id']}"
        sections.append({"id": section_id, "group": "Flows", "label": str(flow["id"])})
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

    for entry in data_entries:
        section_id = f"data-item-{entry['id']}"
        sections.append({"id": section_id, "group": "Data", "label": str(entry["id"])})
        dynamic_sections.append(
            _section(
                section_id,
                "Data",
                str(entry["id"]),
                "Data entry",
                _data_entry_section(entry),
                schema.system.get("id", "forge"),
            )
        )

    item_buttons = "".join(
        _item_button(section["label"], section["id"], section["group"])
        for section in _toolbar_sections(sections)
    )

    data_payload = json.dumps(_interaction_payload(schema))
    template = _template_text("audit_template.html")
    replacements = {
        "__DYNAMIC_ITEM_BUTTONS_HTML__": item_buttons,
        "__SYSTEM_ID__": escape(str(schema.system.get("id", "forge"))),
        "__AUDIT_DATA__": data_payload,
        "__OVERVIEW_BODY__": _render_overview_section(schema, data_entries),
        "__SYSTEM_BODY__": _render_system_section(schema),
        "__RUNTIME_BODY__": _render_runtime_section(schema),
        "__DATA_BODY__": _render_data_section(data_entries),
        "__VERTICALS_BODY__": _render_verticals_section(schema),
        "__DEPLOYMENT_BODY__": "",
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


def _render_overview_section(schema: ForgeSchema, data_entries: list[dict[str, object]]) -> str:
    summary_cards = [
        ("System", str(schema.system.get("id", "forge")), None),
        ("High-Level Flows", str(len(schema.high_level_flows)), "flow"),
        ("Runtime Containers", str(len(schema.runtime.get("containers", []))), "runtime"),
        ("Verticals", str(len(schema.verticals)), "vertical"),
    ]
    summary_html = "".join(
        '<div class="card">'
        f"<h3>{escape(title)}</h3>"
        f"<p>{escape(value)}</p>"
        "</div>"
        for title, value, _kind in summary_cards
    )
    jump_cards = [
        ("Jump To System", "Open the system boundary and external dependency view.", "Open System", "system-overview"),
        ("Jump To Runtime", "Inspect the container graph and runtime boundaries.", "Open Runtime", "runtime-overview"),
        ("Jump To Data", "Review promoted data shapes and persistent storage.", "Open Data", "data-overview"),
    ]
    jump_html = "".join(
        '<div class="card">'
        f"<h3>{escape(title)}</h3>"
        f"<p>{escape(description)}</p>"
        f'<button class="pill action-pill" type="button" data-target="{escape(target)}">{escape(label)}</button>'
        "</div>"
        for title, description, label, target in jump_cards
    )
    return (
        _section_header(
            "overview",
            f"{schema.system.get('id', 'forge')} / Overview",
            "Overview",
            "System-wide audit summary and quick links into the architecture.",
        )
        + f'<div class="grid grid-4">{summary_html}</div>'
        + f'<div class="grid grid-4">{jump_html}</div>'
    )


def _item_button(label: str, target: str, group: str) -> str:
    return f'<button class="toolbar-btn" data-target="{escape(target)}" data-group="{escape(group)}">{escape(label)}</button>'


def _toolbar_sections(sections: list[dict[str, str]]) -> list[dict[str, str]]:
    hidden_ids = {
        "overview",
        "system-overview",
        "runtime-overview",
        "data-overview",
        "verticals-overview",
        "deployment-overview",
    }
    indexed = list(enumerate(section for section in sections if section["id"] not in hidden_ids))
    chosen: dict[tuple[str, str], tuple[int, int, dict[str, str]]] = {}

    for position, section in indexed:
        key = (section["group"], section["label"])
        priority = _toolbar_section_priority(section)
        existing = chosen.get(key)
        if existing is None:
            chosen[key] = (position, priority, section)
            continue
        existing_position, existing_priority, existing_section = existing
        if priority > existing_priority:
            chosen[key] = (existing_position, priority, section)
        else:
            chosen[key] = (existing_position, existing_priority, existing_section)

    return [entry[2] for entry in sorted(chosen.values(), key=lambda value: value[0])]


def _toolbar_section_priority(section: dict[str, str]) -> int:
    section_id = section["id"]
    if section["group"] != "Data":
        return 0
    if section_id.startswith("data-item-"):
        return 1
    return 0


def _section(
    section_id: str,
    group: str,
    title: str,
    description: str,
    body: str,
    system_id: str,
    *,
    with_header: bool = True,
) -> str:
    breadcrumb = f"{system_id} / {title}"
    header = _section_header(section_id, breadcrumb, title, description) if with_header else ""
    return (
        f'<section class="section" id="{escape(section_id)}" data-group="{escape(group)}">'
        f"{header}"
        f"{body}"
        "</section>"
    )


def _section_header(section_id: str, breadcrumb: str, title: str, description: str) -> str:
    del section_id
    return (
        '<div class="section-header">'
        f'<p class="section-eyebrow">{escape(breadcrumb)}</p>'
        f'<h2 class="section-title">{escape(title)}</h2>'
        f'<p class="section-description">{escape(description)}</p>'
        "</div>"
    )


def _render_system_section(schema: ForgeSchema) -> str:
    actors = schema.system.get("actors", [])
    dependencies = schema.system.get("external_dependencies", [])
    cards = f"""
    <div class="grid grid-1">
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
    card_html: list[str] = []
    for item in containers:
        container_id = str(item["id"])
        classes = "card card-defined" if container_id in deepened_container_ids else "card card-muted"
        attrs = f' class="{classes}"'
        if container_id in deepened_container_ids:
            attrs += f' data-target="container-{escape(container_id)}" role="button" tabindex="0"'
        card_html.append(
            f'<div{attrs}>'
            f'<div class="card-header"><h3>{escape(container_id)}</h3></div>'
            f'<p>{escape(item.get("description", ""))}</p>'
            '</div>'
        )
    cards = '<div class="vertical-cards">' + "".join(card_html) + "</div>"
    diagram = _render_runtime_graph(containers, relationships, deepened_container_ids)
    deployment = _render_deployment_section(schema)
    return _diagram_card("Runtime Topology", "Container graph and boundary-crossing relationships", diagram) + deployment + cards


def _render_verticals_section(schema: ForgeSchema) -> str:
    card_html: list[str] = []
    for vertical in schema.verticals:
        flow_ids = [str(flow_id) for flow_id in vertical.get("high_level_flows", [])]
        attrs = ' class="card card-defined"'
        if flow_ids:
            attrs += f' data-target="flow-{escape(flow_ids[0])}" role="button" tabindex="0"'
        card_html.append(
            f'<div{attrs}><h3>{escape(vertical["id"])}</h3><p>{escape(vertical.get("description", ""))}</p></div>'
        )
    return '<div class="vertical-cards">' + "".join(card_html) + "</div>"


def _render_data_section(entries: list[dict[str, object]]) -> str:
    rows = [_data_record_row(entry) for entry in entries]
    return f'<div class="record-list">{"".join(rows)}</div>'


def _data_record_row(entry: dict[str, object]) -> str:
    target = f"data-item-{entry['id']}"
    chips = "".join(_data_entry_summary_chips(entry))
    meta = _data_entry_summary_meta(entry)
    return (
        f'<button class="record-row" type="button" data-target="{escape(target)}">'
        f'<div class="record-main"><h3>{escape(str(entry.get("id", "")))}</h3><p>{escape(str(entry.get("description", "")))}</p></div>'
        f'<div class="record-side"><div class="pill-list">{chips}</div>{meta}</div>'
        f'</button>'
    )


def _data_entry_section(entry: dict[str, object]) -> str:
    sections: list[str] = []
    if entry.get("early_state"):
        sections.append(_early_state_card(entry["early_state"]))
    if entry.get("data_shape"):
        shape = entry["data_shape"]
        shape_chips = [f'<span class="kind-chip chip-shape">{escape(str(shape.get("kind", "data_shape")))}</span>']
        if entry.get("persistent_shape"):
            shape_chips.append(
                f'<span class="kind-chip chip-persistent">{escape(str(entry["persistent_shape"].get("storage_model", "persistent_shape")))}</span>'
            )
        sections.append(
            _data_entry_card(
                "Data Shape",
                str(shape.get("description", "")),
                shape_chips,
                json.dumps(_data_body(shape), indent=2),
            )
        )
    if entry.get("persistent_shape"):
        persistent = entry["persistent_shape"]
        sections.append(
            _persistent_shape_card(persistent)
        )
    sections_html = f'<div class="data-entry-stack">{"".join(sections)}</div>' if sections else ""
    return (
        '<div class="card">'
        '<div class="card-header">'
        f'<h3>{escape(str(entry.get("id", "")))}</h3>'
        f'<div class="pill-list">{"".join(_data_entry_summary_chips(entry))}</div>'
        '</div>'
        f'<p>{escape(str(entry.get("description", "")))}</p>'
        f'{sections_html}'
        '</div>'
    )


def _data_body(item: dict[str, object]) -> object:
    if "shape" in item:
        return item.get("shape", {})
    if "states" in item:
        return {"states": item.get("states", [])}
    return item


def _persistent_shape_card(persistent: dict[str, object]) -> str:
    summary_items = [
        ("Logical Owner", persistent.get("logical_owner_container", "")),
        ("Data Store", persistent.get("data_store_container", "")),
        ("Storage Model", persistent.get("storage_model", "")),
    ]
    metadata_rows = [
        ("Persistence Behaviour", persistent.get("persistence_behavior", "")),
        ("Lifecycle Notes", persistent.get("lifecycle_status_notes", "")),
        ("Security", persistent.get("security", "")),
    ]
    summary_html = "".join(
        '<div class="metadata-summary-item">'
        f'<span class="metadata-summary-label">{escape(label)}</span>'
        f'<span class="metadata-summary-value">{escape(str(value))}</span>'
        '</div>'
        for label, value in summary_items
        if str(value).strip()
    )
    table_rows = "".join(
        f"<tr><th>{escape(label)}</th><td>{escape(str(value))}</td></tr>"
        for label, value in metadata_rows
        if str(value).strip()
    )
    state_machine = persistent.get("state_machine", {}) or {}
    machine_block = ""
    if state_machine.get("states"):
        machine_block = _diagram_card(
            "State Machine",
            "Persistent lifecycle states and transition conditions.",
            _render_state_machine_graph(state_machine),
        )
    return (
        '<div class="card persistent-shape-card">'
        '<h4>Persistent Shape</h4>'
        f'<p>{escape(str(persistent.get("description", "")))}</p>'
        f'<div class="metadata-summary">{summary_html}</div>'
        '<div class="metadata-table-wrap">'
        '<table class="metadata-table">'
        f"{table_rows}"
        '</table>'
        '</div>'
        f'{machine_block}'
        '</div>'
    )


def _early_state_card(early_state: dict[str, object]) -> str:
    description_parts = [
        str(early_state.get("description", "")).strip(),
        str(early_state.get("why_it_matters", "")).strip(),
    ]
    description = " ".join(part for part in description_parts if part)
    return (
        '<div class="card early-state-card">'
        '<h4>Early State</h4>'
        f'<p>{escape(description)}</p>'
        '</div>'
    )


def _data_entry_card(title: str, description: str, chips: list[str], body: str) -> str:
    return (
        '<div class="card" style="margin-top:16px;">'
        f'<h4>{escape(title)}</h4>'
        f'<p>{escape(description)}</p>'
        f'<div class="schema-viewer"><pre>{escape(body)}</pre></div>'
        '</div>'
    )


def _render_state_machine_graph(state_machine: dict[str, object]) -> str:
    states = [str(item) for item in state_machine.get("states", [])]
    transitions = state_machine.get("transitions", []) or []
    partitions = _state_machine_partitions(states, transitions)
    nodes = [
        _elk_node(state, "state", "state-node", partition=partitions.get(state, index), width=190, height=64)
        for index, state in enumerate(states)
    ]
    source_counts: dict[str, int] = {}
    source_indices: dict[str, int] = {}
    for item in transitions:
        source = str(item.get("from", ""))
        source_counts[source] = source_counts.get(source, 0) + 1
    edges = []
    for item in transitions:
        source = str(item.get("from", ""))
        target = str(item.get("to", ""))
        if not source or not target:
            continue
        index = source_indices.get(source, 0)
        source_indices[source] = index + 1
        edges.append(
            _elk_edge(
                source,
                target,
                str(item.get("condition", "")),
                show_label=True,
                label_lane=_state_machine_label_lane(index, source_counts.get(source, 1)),
                label_wrap=28,
            )
        )
    return _elk_block(_elk_graph(nodes, edges))


def _state_machine_partitions(states: list[str], transitions: list[object]) -> dict[str, int]:
    incoming = {state: 0 for state in states}
    outgoing: dict[str, list[str]] = {state: [] for state in states}
    for transition in transitions:
        if not isinstance(transition, dict):
            continue
        source = str(transition.get("from", ""))
        target = str(transition.get("to", ""))
        if source in outgoing and target in incoming:
            outgoing[source].append(target)
            incoming[target] += 1

    roots = [state for state in states if incoming.get(state, 0) == 0] or states[:1]
    partitions = {state: 0 for state in roots}
    queue = list(roots)
    while queue:
        state = queue.pop(0)
        next_partition = partitions[state] + 1
        for target in outgoing.get(state, []):
            # Cyclic state machines are valid. Keep the first discovered layer
            # so layout terminates instead of increasing forever on back-edges.
            if target not in partitions:
                partitions[target] = next_partition
                queue.append(target)
    for state in states:
        partitions.setdefault(state, 0)
    return partitions


def _state_machine_label_lane(index: int, total: int) -> int:
    if total <= 1:
        return -1
    pattern = [-1, 1, -2, 2]
    return pattern[index] if index < len(pattern) else index - (total // 2)


def _data_entry_summary_chips(entry: dict[str, object]) -> list[str]:
    chips: list[str] = []
    if entry.get("early_state"):
        chips.append(
            f'<span class="kind-chip chip-early">{escape(str(entry["early_state"].get("category", "early_state")))}</span>'
        )
    if entry.get("data_shape"):
        chips.append(
            f'<span class="kind-chip chip-shape">{escape(str(entry["data_shape"].get("kind", "data_shape")))}</span>'
        )
    if entry.get("persistent_shape"):
        chips.append(
            f'<span class="kind-chip chip-persistent">{escape(str(entry["persistent_shape"].get("storage_model", "persistent_shape")))}</span>'
        )
    return chips


def _data_entry_summary_meta(entry: dict[str, object]) -> str:
    parts: list[str] = []
    if entry.get("early_state"):
        parts.append("early state")
    if entry.get("data_shape"):
        parts.append("data shape")
    if entry.get("persistent_shape"):
        parts.append("persistent shape")
    return f'<div class="record-meta">{escape(" · ".join(parts))}</div>'


def _build_data_entries(schema: ForgeSchema) -> list[dict[str, object]]:
    entries: dict[str, dict[str, object]] = {}

    persistent_by_shape_id = {
        str(item.get("data_shape", "")): item
        for item in schema.persistent_shapes
        if item.get("data_shape")
    }

    for item in schema.early_state:
        entry_id = str(item["id"])
        entries.setdefault(entry_id, {"id": entry_id, "early_state": None, "data_shape": None, "persistent_shape": None})
        entries[entry_id]["early_state"] = item

    for item in schema.persistent_shapes:
        entry_id = str(item["id"])
        entries.setdefault(entry_id, {"id": entry_id, "early_state": None, "data_shape": None, "persistent_shape": None})
        entries[entry_id]["persistent_shape"] = item
        data_shape_id = str(item.get("data_shape", ""))
        if data_shape_id:
            data_shape = schema.index("data_shapes").get(data_shape_id)
            if data_shape is not None:
                entries[entry_id]["data_shape"] = data_shape

    for item in schema.data_shapes:
        data_shape_id = str(item["id"])
        if data_shape_id in persistent_by_shape_id:
            continue
        entry_id = data_shape_id
        entries.setdefault(entry_id, {"id": entry_id, "early_state": None, "data_shape": None, "persistent_shape": None})
        entries[entry_id]["data_shape"] = item

    results: list[dict[str, object]] = []
    for entry_id in sorted(entries):
        entry = entries[entry_id]
        description = ""
        if entry.get("early_state"):
            description = str(entry["early_state"].get("description", ""))
        elif entry.get("persistent_shape"):
            description = str(entry["persistent_shape"].get("description", ""))
        elif entry.get("data_shape"):
            description = str(entry["data_shape"].get("description", ""))
        entry["description"] = description
        results.append(entry)
    return results


def _render_deployment_section(schema: ForgeSchema) -> str:
    environments = schema.deployment.get("environments", [])
    blocks = []
    for environment in environments:
        diagram = _render_deployment_graph(environment, schema)
        node_cards = "".join(
            f'<div class="card deployment-node-card">'
            '<div class="card-header">'
            f'<h3>{escape(node["id"])}</h3>'
            f'<div class="pill-list"><span class="kind-chip chip-deploy">{escape(str(node.get("kind", "")))}</span>'
            f'<span class="kind-chip chip-boundary">{escape(str(node.get("trust_boundary", "")))}</span></div>'
            '</div>'
            f'<p>{escape(node.get("description", ""))}</p>'
            f'<div class="footer-note">{escape(str(node.get("technology", "")))}'
            + (
                f'<br />Containers: {escape(", ".join(str(item) for item in node.get("containers", [])))}'
                if node.get("containers")
                else ""
            )
            + '</div></div>'
            for node in environment.get("nodes", [])
        )
        blocks.append(
            '<div class="deployment-stack">'
            f'<div class="card"><h3>{escape(environment["id"])}</h3><p>{escape(environment.get("description", ""))}</p></div>'
            + _diagram_card(f'Deployment Diagram: {environment["id"]}', "Environment nodes, trust boundaries, and dependencies", diagram)
            + '<div class="vertical-cards">' + node_cards + '</div>'
            + '</div>'
        )
    return "".join(blocks)


def _render_high_level_flow(flow: dict[str, object]) -> str:
    return _flow_panel(flow, "Business/system flow", include_container=False)


def _render_runtime_flow(flow: dict[str, object]) -> str:
    return _flow_panel(flow, "Container-level runtime flow", include_container=True)


def _render_flow_section(schema: ForgeSchema, flow: dict[str, object], runtime_flows: list[dict[str, object]]) -> str:
    blocks = [
        _flow_panel(flow, "Business/system flow", include_container=False),
    ]
    for runtime_flow in runtime_flows:
        component_blocks = _runtime_component_flow_blocks(schema, runtime_flow)
        component_html = ""
        if component_blocks:
            component_html = (
                '<div class="card" style="margin-top:16px;">'
                '<h4>Low-Level Flows</h4>'
                f"{''.join(component_blocks)}"
                '</div>'
            )
        blocks.append(
            '<details class="flow-expandable runtime-flow-expandable" style="margin-top:16px;">'
            f'<summary>Runtime Flow: {escape(str(runtime_flow.get("id", "")))}</summary>'
            '<div class="flow-expandable-body">'
            f'<div class="pill-list"><span class="pill" data-target="runtime-overview">Runtime Overview</span></div>'
            f'{_flow_panel(runtime_flow, "Container-level runtime flow", include_container=True)}'
            f'{component_html}'
            '</div>'
            '</details>'
        )
    return "".join(blocks)


def _runtime_flows_for_high_level(schema: ForgeSchema, high_level_flow: dict[str, object]) -> list[dict[str, object]]:
    flow_id = str(high_level_flow.get("id", ""))
    matched = [
        item for item in schema.runtime_flows
        if str(item.get("high_level_flow", "")) == flow_id
    ]
    if matched:
        return matched
    return [
        item for item in schema.runtime_flows
        if str(item.get("id", "")).startswith(f"{flow_id}_")
    ]


def _runtime_component_flow_blocks(schema: ForgeSchema, runtime_flow: dict[str, object]) -> list[str]:
    runtime_id = str(runtime_flow.get("id", ""))
    blocks: list[str] = []
    for container in schema.containers:
        for component_flow in container.get("component_flows", []):
            if str(component_flow.get("runtime_flow", "")) != runtime_id:
                continue
            blocks.append(
                '<details class="flow-expandable">'
                f'<summary>{escape(str(container.get("id", "")))} · {escape(str(component_flow.get("id", "")))}</summary>'
                '<div class="flow-expandable-body">'
                f'{_flow_panel(component_flow, "Component-level internal flow", include_component=True)}'
                '</div>'
                '</details>'
            )
    return blocks


def _render_container_section(container: dict[str, object]) -> str:
    components = container.get("components", [])
    cards = (
        '<div class="card component-table-card"><h4>Components</h4>'
        f'{_component_rows(components) or "<p>No components extracted.</p>"}'
        '</div>'
    )
    diagram = _render_container_graph(container)
    flow_panels = "".join(
        _flow_panel(flow, f"Component Flow: {flow.get('id')}", include_component=True, target_prefix="component")
        for flow in container.get("component_flows", [])
    )
    return (
        '<div class="container-stack">'
        + _diagram_card("Container Components", "Internal component structure and flow handoffs", diagram)
        + cards
        + flow_panels
        + "</div>"
    )


def _render_deployment_graph(environment: dict[str, object], schema: ForgeSchema) -> str:
    deepened_container_ids = {str(item["id"]) for item in schema.containers}
    nodes = []
    for node in environment.get("nodes", []):
        kind = str(node.get("kind", ""))
        width, height = _deployment_node_dimensions(kind)
        target = None
        for container_id in node.get("containers", []) or []:
            if str(container_id) in deepened_container_ids:
                target = f"container-{container_id}"
                break
        nodes.append(
            _elk_node(
                str(node["id"]),
                str(node.get("technology") or node.get("kind") or "node"),
                _deployment_visual_kind(kind),
                target=target,
                partition=_deployment_partition(str(node.get("trust_boundary", "")), kind),
                width=width,
                height=height,
                icon=_deployment_icon(kind),
            )
        )
    edges = []
    for node in environment.get("nodes", []):
        for dep in node.get("depends_on", []) or []:
            edges.append(
                _elk_edge(
                    str(node["id"]),
                    str(dep),
                    "depends on",
                    show_label=False,
                )
            )
    return _elk_block(_elk_graph(nodes, edges))


def _flow_panel(
    flow: dict[str, object],
    subtitle: str,
    include_container: bool = False,
    include_component: bool = False,
    target_prefix: str = "container",
) -> str:
    steps_html = []
    for step in flow.get("steps", []):
        branches = step.get("branches", [])
        branch_html = ""
        if branches:
            branch_html = _branch_list(branches, expand_outgoing=not include_component)
        subject = ""
        if include_container and step.get("container"):
            subject = (
                f"<p class='flow-step-meta' data-target='container-{escape(step['container'])}'>"
                f"Container: {escape(step['container'])}</p>"
            )
        if include_component and step.get("component"):
            subject = f"<p class='flow-step-meta'>Component: {escape(step['component'])}</p>"
        description = _flow_description(step.get("description", ""))
        outgoing = str(step.get("outgoing", "")).strip()
        outgoing_html = _outgoing_html(outgoing, expand=not include_component)
        steps_html.append(
            f"<div class='flow-step'><h4>Step {step.get('id')}</h4>{subject}{description}"
            f"{outgoing_html}{branch_html}</div>"
        )
    outcomes = flow.get("outcomes", [])
    outcome_block = ""
    if outcomes:
        outcome_block = (
            "<div class='flow-outcomes'><h4>Outcomes</h4><p>"
            + "<br />".join(escape(str(item)) for item in outcomes)
            + "</p></div>"
        )
    return f"""
      <div class="card">
        <h3>{escape(str(flow.get('id', subtitle)))}</h3>
        <p>{escape(subtitle)}. {escape(str(flow.get('description', '')))}</p>
        <p class="flow-trigger">Trigger: {escape(str(flow.get('trigger', '')))}</p>
        <div class="flow-steps">{''.join(steps_html)}</div>
        {outcome_block}
      </div>
    """


def _flow_description(value: object) -> str:
    if isinstance(value, list):
        items = "".join(f"<li>{escape(str(item))}</li>" for item in value)
        return f"<ul class='branch-list'>{items}</ul>"
    return f"<p>{escape(str(value))}</p>"


def _branch_list(branches: object, *, expand_outgoing: bool = True) -> str:
    branch_items = []
    for branch in branches:
        if not isinstance(branch, dict):
            continue
        outgoing = str(branch.get("outgoing", "")).strip()
        outgoing_html = _outgoing_html(outgoing, expand=expand_outgoing)
        branch_items.append(
            f"<li><strong>{escape(str(branch.get('condition', 'Condition')))}</strong>"
            f"{outgoing_html}</li>"
        )
    return "<ul class='branch-list'>" + "".join(branch_items) + "</ul>"


def _outgoing_html(value: str, *, expand: bool = True) -> str:
    if not value:
        return ""
    if not expand and _is_shape_like_text(value):
        return (
            "<div class='footer-note'>Outgoing</div>"
            f'<div class="schema-viewer"><pre>{escape(_format_shape_like_text(value))}</pre></div>'
        )
    if _is_shape_like_text(value):
        return _payload_details("Outgoing Payload", value)
    return f"<div class='footer-note'>Outgoing: {escape(value)}</div>"


def _payload_details(label: str, value: str) -> str:
    formatted = _format_shape_like_text(value)
    return (
        '<details class="payload-expandable">'
        f"<summary>{escape(label)}</summary>"
        f'<div class="schema-viewer"><pre>{escape(formatted)}</pre></div>'
        "</details>"
    )


def _format_shape_like_text(value: str) -> str:
    text = value.strip()
    if not _is_shape_like_text(text):
        return text

    lines: list[str] = []
    current = ""
    indent = 0
    for char in text:
        if char in "{[":
            prefix = current.strip()
            line = f"{prefix} {char}" if prefix else char
            lines.append(("  " * indent) + line)
            current = ""
            indent += 1
            continue
        if char in "}]":
            if current.strip():
                lines.append(("  " * indent) + current.strip())
                current = ""
            indent = max(indent - 1, 0)
            lines.append(("  " * indent) + char)
            continue
        if char == ",":
            if current.strip():
                lines.append(("  " * indent) + current.strip() + ",")
                current = ""
            elif lines:
                lines[-1] += ","
            continue
        current += char

    if current.strip():
        lines.append(("  " * indent) + current.strip())
    return "\n".join(lines)


def _is_shape_like_text(value: str) -> bool:
    return value.strip().startswith(("{", "["))


def _diagram_card(title: str, subtitle: str, inner: str, *, css_class: str = "") -> str:
    classes = "card diagram-card" + (f" {css_class}" if css_class else "")
    return f"""
    <div class="{escape(classes)}">
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
        graph["edges"].append(_elk_edge(actor["id"], system_id, "", style="dashed", show_label=False))
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
    source_counts: dict[str, int] = {}
    source_indices: dict[str, int] = {}
    for relation in relationships:
        src = str(relation.get("from", ""))
        source_counts[src] = source_counts.get(src, 0) + 1
    edges = []
    for relation in relationships:
        src = str(relation.get("from", ""))
        index = source_indices.get(src, 0)
        source_indices[src] = index + 1
        edges.append(
            _elk_edge(
                src,
                str(relation.get("to", "")),
                str(relation.get("description", "")),
                show_label=True,
                label_lane=_label_lane(index, source_counts.get(src, 1)),
                label_wrap=16,
            )
        )
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
            edges.append(_elk_edge(key[0], key[1], "flows to", show_label=False))
            next_order = order_map.get(key[1])
            current_order = order_map.get(key[0])
            if next_order is None and current_order is not None:
                order_map[key[1]] = current_order + 1
        for step in steps:
            branches = step.get("branches", [])
            if not step.get("component") or not branches:
                continue
            for branch in branches:
                branch_next = branch.get("next")
                if branch_next is None:
                    continue
                next_step = next((candidate for candidate in steps if candidate.get("id") == branch_next), None)
                if not next_step or not next_step.get("component"):
                    continue
                key = (str(step["component"]), str(next_step["component"]))
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                edges.append(_elk_edge(key[0], key[1], "flows to", show_label=False, style="dashed"))
                next_order = order_map.get(key[1])
                current_order = order_map.get(key[0])
                if next_order is None and current_order is not None:
                    order_map[key[1]] = current_order + 1
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
    icon: str | None = None,
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
            "icon": icon or "",
        },
    }


def _elk_edge(
    source: str,
    target: str,
    label: str,
    *,
    style: str = "solid",
    show_label: bool = True,
    label_lane: int = 0,
    label_wrap: int = 18,
) -> dict[str, object]:
    display_label = _edge_label(label)
    return {
        "id": f'{_elk_id(source)}__{_elk_id(target)}__{len(display_label)}',
        "sources": [_elk_id(source)],
        "targets": [_elk_id(target)],
        "forge": {
            "label": display_label,
            "style": style,
            "showLabel": show_label,
            "labelLane": label_lane,
            "labelWrap": label_wrap,
        },
    }


def _edge_label(label: str, max_words: int = 5) -> str:
    words = str(label).split()
    if len(words) <= max_words:
        return str(label).strip()
    return " ".join(words[:max_words])


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
    return _mermaid_block(_mermaid_from_elk_graph(graph))


def _mermaid_block(source: str) -> str:
    return (
        '<div class="mermaid-graph diagram-surface" data-mermaid-rendered="false">'
        f'<pre class="mermaid">{escape(source)}</pre>'
        "</div>"
    )


def _mermaid_from_elk_graph(graph: dict[str, object]) -> str:
    lines = [
        "flowchart LR",
        "  classDef forgeNode fill:#ffffff,stroke:#d1d9e0,stroke-width:1.5px,color:#1f2328;",
        "  classDef forgeExternal fill:#fff7ed,stroke:#fdba74,stroke-width:1.5px,color:#1f2328;",
        "  classDef forgeDatabase fill:#f6f8fa,stroke:#94a3b8,stroke-width:1.5px,color:#1f2328;",
    ]
    for node in graph.get("children", []):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id", "node"))
        forge = node.get("forge", {})
        if not isinstance(forge, dict):
            forge = {}
        label = str(forge.get("label") or node_id)
        kind = str(forge.get("kind") or "")
        shape_open, shape_close = _mermaid_node_shape(kind)
        lines.append(f'  {node_id}{shape_open}"{_mermaid_label(label)}"{shape_close}')
        lines.append(f"  class {node_id} {_mermaid_class(kind)};")
        target = str(forge.get("target") or "")
        if target:
            lines.append(f'  click {node_id} "#{_mermaid_label(target)}"')
    for edge in graph.get("edges", []):
        if not isinstance(edge, dict):
            continue
        sources = edge.get("sources", [])
        targets = edge.get("targets", [])
        if not sources or not targets:
            continue
        forge = edge.get("forge", {})
        if not isinstance(forge, dict):
            forge = {}
        source = str(sources[0])
        target = str(targets[0])
        label = str(forge.get("label") or "").strip() if forge.get("showLabel", True) is not False else ""
        dashed = str(forge.get("style", "")) == "dashed"
        lines.append(_mermaid_edge_line(source, target, label, dashed=dashed))
    return "\n".join(lines)


def _mermaid_node_shape(kind: str) -> tuple[str, str]:
    if kind in {"actor", "dependency", "external", "deploy-external"}:
        return "((", "))"
    if kind in {"database", "deploy-database"}:
        return "[(", ")]"
    return "[", "]"


def _mermaid_class(kind: str) -> str:
    if kind in {"database", "deploy-database"}:
        return "forgeDatabase"
    if kind in {"dependency", "external", "deploy-external", "system"}:
        return "forgeExternal"
    return "forgeNode"


def _mermaid_edge_line(source: str, target: str, label: str, *, dashed: bool = False) -> str:
    if not label:
        arrow = "-.->" if dashed else "-->"
        return f"  {source} {arrow} {target}"
    if dashed:
        return f'  {source} -->|"{_mermaid_label(label)}"| {target}'
    return f'  {source} -->|"{_mermaid_label(label)}"| {target}'


def _mermaid_label(value: str) -> str:
    return " ".join(str(value).replace('"', "'").split())


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


def _label_lane(index: int, total: int) -> int:
    if total <= 1:
        return -3
    pattern = [-3, 3, -6, 6, -9, 9, -12, 12]
    return pattern[index] if index < len(pattern) else ((index // 2) + 2) * (3 if index % 2 else -3)


def _deployment_partition(trust_boundary: str, kind: str) -> int:
    if trust_boundary == "public_client_environment" or kind == "browser":
        return 0
    if trust_boundary == "public_edge_network" or kind == "cdn":
        return 1
    if trust_boundary == "private_application_network":
        return 2
    if trust_boundary == "private_data_tier":
        return 3
    if trust_boundary == "third_party_boundary":
        return 4
    return 2


def _deployment_visual_kind(kind: str) -> str:
    mapping = {
        "browser": "deploy-browser",
        "cdn": "deploy-edge",
        "kubernetes_service": "deploy-service",
        "managed_database": "deploy-database",
        "external_api": "deploy-external",
    }
    return mapping.get(kind, "deploy-service")


def _deployment_icon(kind: str) -> str:
    mapping = {
        "browser": "◫",
        "cdn": "⬡",
        "kubernetes_service": "◼",
        "managed_database": "◉",
        "external_api": "◎",
    }
    return mapping.get(kind, "◼")


def _deployment_node_dimensions(kind: str) -> tuple[float, float]:
    if kind == "managed_database":
        return 250, 110
    if kind == "external_api":
        return 250, 100
    if kind == "kubernetes_service":
        return 240, 98
    if kind == "cdn":
        return 220, 92
    if kind == "browser":
        return 220, 92
    return 220, 92
