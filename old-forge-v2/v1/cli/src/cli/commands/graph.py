"""`forge graph` — generate a dependency graph from the spec directory."""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

from cli import common

NAME = "graph"
HELP = "Generate a dependency graph of the spec as an HTML or Mermaid diagram."
DESCRIPTION = (
    "Builds a dependency graph from contracts, interactions, element "
    "relationships, and datastore consumers. Produces a self-contained "
    "HTML file with an embedded Mermaid diagram (default) or raw Mermaid "
    "syntax (--format mermaid). Use --scope <node-id> to limit the graph "
    "to the subgraph reachable from that node."
)

_MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"

# Dot-path depths for structural kinds.
# conception.system.domain.module.element = 5 parts
# conception.system.domain.module          = 4 parts
_ELEMENT_DEPTH = 5
_MODULE_DEPTH  = 4

# Kinds rendered as standalone nodes (not subgraph containers).
# Contracts are shown purely as labelled edges between modules, not as nodes.
_PERIPHERAL_KINDS = frozenset({"datastore"})


# ===========================================================================
# Argparse
# ===========================================================================

def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help=HELP, description=DESCRIPTION)
    common.add_spec_dir_arg(p)
    p.add_argument(
        "--output", "-o", default="./forge-graph.html",
        help="Output path for the HTML file. Default: ./forge-graph.html",
    )
    p.add_argument(
        "--format", choices=["html", "mermaid"], default="html",
        help="Output format: 'html' (default) or 'mermaid' (raw syntax to stdout).",
    )
    p.add_argument(
        "--scope", default=None, metavar="NODE_ID",
        help="Limit graph to the subgraph reachable from this node id.",
    )
    p.add_argument(
        "--show-deployments", action="store_true",
        help=(
            "Group modules inside their deployment environment instead of their "
            "domain. Shows which environment each module is deployed to."
        ),
    )
    p.add_argument(
        "--no-open", action="store_true",
        help="Do not auto-open the HTML file after writing.",
    )
    p.set_defaults(handler=run)


# ===========================================================================
# Entry point
# ===========================================================================

def run(args: argparse.Namespace) -> int:
    idx, rc = common.load_index(args.spec_dir)
    if rc != 0:
        return rc

    edges = _collect_edges(idx)

    if args.scope:
        if idx.get(args.scope) is None:
            print(f"error: unknown node id: {args.scope}", file=sys.stderr)
            common.suggest_similar(idx, args.scope)
            return 1
        edges = _filter_to_scope(edges, args.scope)

    mermaid_text = _render_mermaid(idx, edges, show_deployments=args.show_deployments)

    if args.format == "mermaid":
        print(mermaid_text)
        return 0

    html = _render_html(
        mermaid_text,
        scope_label=args.scope,
        conception=idx.conception_name,
        show_deployments=args.show_deployments,
    )
    out_path = Path(args.output).expanduser().resolve()
    try:
        out_path.write_text(html, encoding="utf-8")
    except OSError as exc:
        print(f"error: could not write {out_path}: {exc}", file=sys.stderr)
        return 1

    print(f"graph: wrote {out_path}")
    if not args.no_open:
        _open_file(out_path)
    return 0


# ===========================================================================
# Edge data structure
# ===========================================================================

class Edge:
    __slots__ = ("src", "dst", "label", "kind")

    def __init__(self, src: str, dst: str, label: str = "", kind: str = "dep") -> None:
        self.src = src
        self.dst = dst
        self.label = label
        # kind: "contract" | "interaction" | "relationship" | "datastore"
        self.kind = kind

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.src, self.dst, self.label) == (other.src, other.dst, other.label)

    def __hash__(self) -> int:
        return hash((self.src, self.dst, self.label))


# ===========================================================================
# Edge collection
# ===========================================================================

def _collect_edges(idx: Any) -> list[Edge]:
    edges: set[Edge] = set()

    for entry_id, entry in idx.entries.items():
        if not isinstance(entry.data, dict):
            continue
        data = entry.data

        # Contracts: producer module → consumer modules
        if entry.kind == "contract":
            producer = data.get("producer")
            consumers = data.get("consumers") or []
            label = data.get("name") or entry_id.split(".")[-1]
            if producer and isinstance(producer, str):
                for consumer in (consumers if isinstance(consumers, list) else []):
                    if isinstance(consumer, str) and consumer:
                        edges.add(Edge(producer, consumer, label, "contract"))

        # Interactions: caller op → callee op (resolved to parent elements)
        elif entry.kind == "interaction":
            caller = data.get("caller")
            callee = data.get("callee")
            label = data.get("name") or entry_id.split(".")[-1]
            if caller and callee:
                src = _parent_element(str(caller), idx)
                dst = _parent_element(str(callee), idx)
                if src and dst and src != dst:
                    edges.add(Edge(src, dst, label, "interaction"))

        # Element relationships
        elif entry.kind == "element":
            for rel in (data.get("relationships") or []):
                if not isinstance(rel, dict):
                    continue
                target = rel.get("target")
                label = rel.get("type") or ""
                if isinstance(target, str) and target:
                    edges.add(Edge(entry_id, target, label, "relationship"))

        # Datastores: consumer modules → datastore node
        elif entry.kind == "datastore":
            label = data.get("name") or entry_id.split(".")[-1]
            for consumer in (data.get("consumers") or []):
                if isinstance(consumer, str) and consumer:
                    edges.add(Edge(consumer, entry_id, label, "datastore"))

    return list(edges)


def _parent_element(node_id: str, idx: Any) -> str | None:
    """Given an operation/property ID, return the parent element ID."""
    entry = idx.get(node_id)
    if entry is None:
        parts = node_id.split(".")
        if len(parts) >= _ELEMENT_DEPTH:
            candidate = ".".join(parts[:_ELEMENT_DEPTH])
            if idx.get(candidate) is not None:
                return candidate
        return None
    if entry.kind == "element":
        return node_id
    if entry.kind in ("operation", "property"):
        parts = node_id.split(".")
        if len(parts) > _ELEMENT_DEPTH:
            return ".".join(parts[:_ELEMENT_DEPTH])
    return None


# ===========================================================================
# Scope filtering
# ===========================================================================

def _filter_to_scope(edges: list[Edge], scope_id: str) -> list[Edge]:
    fwd: dict[str, set[str]] = {}
    bwd: dict[str, set[str]] = {}
    for e in edges:
        fwd.setdefault(e.src, set()).add(e.dst)
        bwd.setdefault(e.dst, set()).add(e.src)

    reachable: set[str] = {scope_id}
    frontier = {scope_id}
    while frontier:
        nxt: set[str] = set()
        for node in frontier:
            for nb in (fwd.get(node) or set()) | (bwd.get(node) or set()):
                if nb not in reachable:
                    reachable.add(nb)
                    nxt.add(nb)
        frontier = nxt

    return [e for e in edges if e.src in reachable or e.dst in reachable]


# ===========================================================================
# Mermaid rendering — helpers
# ===========================================================================

def _safe_id(node_id: str) -> str:
    return node_id.replace(".", "_").replace("-", "_").replace(" ", "_")


def _node_shape(node_id: str, idx: Any) -> tuple[str, str]:
    entry = idx.get(node_id)
    if entry is None:
        return ("[", "]")
    shapes = {
        "element":   ("[", "]"),
        "datastore": ("[(", ")]"),
        "contract":  ("{", "}"),
    }
    return shapes.get(entry.kind, ("[", "]"))


def _node_label(node_id: str, idx: Any) -> str:
    entry = idx.get(node_id)
    if entry is None:
        return node_id.split(".")[-1]
    data = entry.data if isinstance(entry.data, dict) else {}
    name = data.get("name") or node_id.split(".")[-1]
    kind = entry.kind or ""
    if kind == "datastore":
        engine = data.get("engine") or data.get("kind") or ""
        subtitle = f"{engine} · {kind}" if engine else kind
    else:
        subtitle = kind
    return f"{name}<br/><small>{subtitle}</small>"


def _domain_of(node_id: str, idx: Any) -> str | None:
    """Return the domain ID (3-part dot-path) for a module/element, or None."""
    parts = node_id.split(".")
    if len(parts) >= 3:
        candidate = ".".join(parts[:3])
        e = idx.get(candidate)
        if e and e.kind == "domain":
            return candidate
    return None


def _build_module_elements(idx: Any) -> dict[str, list[str]]:
    """Map module_id → sorted list of element_ids that belong to it."""
    result: dict[str, list[str]] = {}
    for entry in idx.entries.values():
        if entry.kind != "element":
            continue
        parts = entry.id.split(".")
        if len(parts) == _ELEMENT_DEPTH:
            module_id = ".".join(parts[:_MODULE_DEPTH])
            result.setdefault(module_id, []).append(entry.id)
    return {k: sorted(v) for k, v in result.items()}


def _build_env_modules(idx: Any) -> dict[str, list[str]]:
    """Map environment_id → sorted list of module_ids deployed there."""
    result: dict[str, list[str]] = {}
    for entry in idx.entries.values():
        if entry.kind != "deployment" or not isinstance(entry.data, dict):
            continue
        module = entry.data.get("module")
        env = entry.data.get("environment")
        if module and env:
            result.setdefault(str(env), []).append(str(module))
    return {k: sorted(set(v)) for k, v in result.items()}


def _emit_module_subgraph(
    lines: list[str],
    idx: Any,
    module_id: str,
    module_elements: dict[str, list[str]],
    depth: int,
) -> None:
    """Emit a module as a Mermaid subgraph containing its element nodes."""
    pad = "    " * depth
    entry = idx.get(module_id)
    name = (
        (entry.data.get("name") if entry and isinstance(entry.data, dict) else None)
        or module_id.split(".")[-1]
    )
    lines.append(f'{pad}subgraph {_safe_id(module_id)}["{name}"]')
    for elem_id in module_elements.get(module_id, []):
        o, c = _node_shape(elem_id, idx)
        label = _node_label(elem_id, idx)
        lines.append(f'{pad}    {_safe_id(elem_id)}{o}"{label}"{c}')
    lines.append(f'{pad}end')


def _emit_peripheral_nodes(lines: list[str], idx: Any) -> None:
    """Emit datastore and contract nodes (standalone, not inside any subgraph)."""
    for entry in sorted(idx.entries.values(), key=lambda e: e.id):
        if entry.kind not in _PERIPHERAL_KINDS:
            continue
        o, c = _node_shape(entry.id, idx)
        label = _node_label(entry.id, idx)
        lines.append(f'    {_safe_id(entry.id)}{o}"{label}"{c}')


def _emit_domain_groups(
    lines: list[str], idx: Any, module_elements: dict[str, list[str]]
) -> None:
    """Emit domain subgraphs → module subgraphs → element nodes."""
    all_modules = sorted(e.id for e in idx.entries.values() if e.kind == "module")

    domain_modules: dict[str, list[str]] = {}
    ungrouped_modules: list[str] = []
    for m in all_modules:
        d = _domain_of(m, idx)
        if d:
            domain_modules.setdefault(d, []).append(m)
        else:
            ungrouped_modules.append(m)

    for domain_id in sorted(domain_modules):
        entry = idx.get(domain_id)
        label = (
            (entry.data.get("name") if entry and isinstance(entry.data, dict) else None)
            or domain_id.split(".")[-1]
        )
        lines.append(f'    subgraph {_safe_id(domain_id)}["{label}"]')
        for module_id in sorted(domain_modules[domain_id]):
            _emit_module_subgraph(lines, idx, module_id, module_elements, depth=2)
        lines.append("    end")

    for module_id in sorted(ungrouped_modules):
        _emit_module_subgraph(lines, idx, module_id, module_elements, depth=1)

    _emit_peripheral_nodes(lines, idx)


def _emit_env_groups(
    lines: list[str], idx: Any, module_elements: dict[str, list[str]]
) -> None:
    """Emit environment subgraphs → module subgraphs → element nodes."""
    env_modules = _build_env_modules(idx)
    deployed: set[str] = {m for ms in env_modules.values() for m in ms}
    all_modules = sorted(e.id for e in idx.entries.values() if e.kind == "module")

    for env_id in sorted(env_modules):
        entry = idx.get(env_id)
        data = entry.data if entry and isinstance(entry.data, dict) else {}
        name = data.get("name") or env_id.split(".")[-1]
        kind_label = data.get("kind") or "environment"
        lines.append(f'    subgraph {_safe_id(env_id)}["{name} ({kind_label})"]')
        for module_id in env_modules[env_id]:
            _emit_module_subgraph(lines, idx, module_id, module_elements, depth=2)
        lines.append("    end")

    for module_id in sorted(m for m in all_modules if m not in deployed):
        _emit_module_subgraph(lines, idx, module_id, module_elements, depth=1)

    _emit_peripheral_nodes(lines, idx)


# ===========================================================================
# Mermaid rendering — styles
# ===========================================================================

# Colour palette (works over Mermaid dark theme).
_C_OUTER   = "fill:#0d1829,stroke:#1e3a5e,color:#64748b"   # domain / environment
_C_MODULE  = "fill:#1a2d4a,stroke:#2563eb,color:#93c5fd"   # module subgraph
_C_ELEMENT = "fill:#0f2235,stroke:#4a9ef8,color:#bfdbfe"   # element node
_C_STORE   = "fill:#0a1f14,stroke:#059669,color:#6ee7b7"   # datastore node


def _emit_styles(lines: list[str], idx: Any, show_deployments: bool) -> None:
    lines.append("")
    lines.append(f"    classDef elementNode {_C_ELEMENT}")
    lines.append(f"    classDef datastoreNode {_C_STORE}")

    elem_ids = sorted(
        _safe_id(e.id)
        for e in idx.entries.values()
        if e.kind == "element" and len(e.id.split(".")) == _ELEMENT_DEPTH
    )
    if elem_ids:
        lines.append(f"    class {','.join(elem_ids)} elementNode")

    ds_ids = sorted(_safe_id(e.id) for e in idx.entries.values() if e.kind == "datastore")
    if ds_ids:
        lines.append(f"    class {','.join(ds_ids)} datastoreNode")

    outer_kind = "environment" if show_deployments else "domain"
    for e in sorted(idx.entries.values(), key=lambda x: x.id):
        if e.kind == outer_kind:
            lines.append(f"    style {_safe_id(e.id)} {_C_OUTER}")
    for e in sorted(idx.entries.values(), key=lambda x: x.id):
        if e.kind == "module":
            lines.append(f"    style {_safe_id(e.id)} {_C_MODULE}")


# ===========================================================================
# Mermaid rendering — main
# ===========================================================================

def _render_mermaid(idx: Any, edges: list[Edge], show_deployments: bool = False) -> str:
    module_elements = _build_module_elements(idx)

    lines: list[str] = ["graph LR"]

    if show_deployments:
        _emit_env_groups(lines, idx, module_elements)
    else:
        _emit_domain_groups(lines, idx, module_elements)

    lines.append("")

    seen: set[tuple[str, str, str]] = set()
    for e in edges:
        src = _safe_id(e.src)
        dst = _safe_id(e.dst)
        safe_label = (e.label or "").replace('"', "'").replace("\n", " ")
        key = (src, dst, safe_label)
        if key in seen:
            continue
        seen.add(key)

        if e.kind == "interaction":
            arrow = f'-. "{safe_label}" .->' if safe_label else "-.->"
        elif safe_label:
            arrow = f'-->|"{safe_label}"|'
        else:
            arrow = "-->"

        lines.append(f"    {src} {arrow} {dst}")

    _emit_styles(lines, idx, show_deployments)

    return "\n".join(lines) + "\n"


# ===========================================================================
# HTML rendering
# ===========================================================================

def _render_html(
    mermaid_text: str,
    scope_label: str | None,
    conception: str,
    show_deployments: bool = False,
) -> str:
    title = f"Forge Graph — {conception}"
    if scope_label:
        title += f" ({scope_label})"

    indented = textwrap.indent(mermaid_text, "            ")

    _key_styles = textwrap.dedent(f"""\
        classDef elementNode {_C_ELEMENT}
        classDef datastoreNode {_C_STORE}
        class eA,eB elementNode
        class ds datastoreNode
    """)

    if show_deployments:
        key_diagram = textwrap.dedent("""\
            graph LR
                subgraph envA["Production (production)"]
                    subgraph modA["ServiceA"]
                        eA["ElemA\\nelement"]
                    end
                    subgraph modB["ServiceB"]
                        eB["ElemB\\nelement"]
                    end
                end
                ds[("DataStore\\ndatastore")]
                modA -->|"contract"| modB
                eA -. "interaction" .-> eB
                modB -->|"store name"| ds
        """) + textwrap.indent(_key_styles, "        ") + textwrap.dedent(f"""\
                style envA {_C_OUTER}
                style modA {_C_MODULE}
                style modB {_C_MODULE}
        """)
        outer_label = "Environment (outer border)"
        outer_desc = (
            "A deployment target (production, staging, …). "
            "The outer border groups the modules deployed there."
        )
    else:
        key_diagram = textwrap.dedent("""\
            graph LR
                subgraph domain["Domain"]
                    subgraph modA["ServiceA"]
                        eA["ElemA\\nelement"]
                    end
                    subgraph modB["ServiceB"]
                        eB["ElemB\\nelement"]
                    end
                end
                ds[("DataStore\\ndatastore")]
                modA -->|"contract"| modB
                eA -. "interaction" .-> eB
                modB -->|"store name"| ds
        """) + textwrap.indent(_key_styles, "        ") + textwrap.dedent(f"""\
                style domain {_C_OUTER}
                style modA {_C_MODULE}
                style modB {_C_MODULE}
        """)
        outer_label = "Domain (outer border)"
        outer_desc = (
            "A bounded area of responsibility. "
            "Groups related modules and their elements within a system."
        )

    key_indented = textwrap.indent(key_diagram, "                ")

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <script src="{_MERMAID_CDN}"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0f1117;
            color: #e2e8f0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2rem 2rem 3rem;
            gap: 1.5rem;
        }}
        h1 {{
            font-size: 1.3rem;
            font-weight: 600;
            color: #94a3b8;
            letter-spacing: 0.02em;
        }}
        .subtitle {{
            font-size: 0.82rem;
            color: #475569;
            margin-top: -1rem;
            text-align: center;
            max-width: 680px;
            line-height: 1.5;
        }}
        .diagram-container {{
            background: #1e2433;
            border-radius: 12px;
            padding: 2rem;
            box-shadow: 0 4px 24px rgba(0,0,0,0.5);
            width: 100%;
            max-width: 1600px;
            overflow-x: auto;
        }}
        .mermaid {{ display: flex; justify-content: center; }}

        /* ── Key ─────────────────────────────────────────────────── */
        .key {{
            width: 100%;
            max-width: 1600px;
            background: #1a1f2e;
            border: 1px solid #2d3548;
            border-radius: 10px;
            padding: 2rem 2.5rem 2.25rem;
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 1.75rem 3.5rem;
            align-items: start;
        }}
        .key h3 {{
            grid-column: 1 / -1;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #64748b;
            margin-bottom: -0.5rem;
        }}
        .key-diagram {{ min-width: 640px; }}
        .key-descriptions {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
            padding-top: 0.5rem;
        }}
        .key-row {{
            display: flex;
            gap: 0.65rem;
            font-size: 0.85rem;
            line-height: 1.5;
        }}
        .key-row .bullet {{
            color: #475569;
            flex-shrink: 0;
            margin-top: 0.1rem;
        }}
        .key-row strong {{ color: #cbd5e1; font-weight: 600; }}
        .key-row span {{ color: #64748b; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="subtitle">
        Shows how the system's elements and modules depend on each other —
        which services call which, which datastores are shared, and how
        contracts bind producers to consumers.
    </p>

    <div class="diagram-container">
        <div class="mermaid">
{indented}
        </div>
    </div>

    <div class="key">
        <h3>Key</h3>

        <div class="key-diagram">
            <div class="mermaid">
{key_indented}
            </div>
        </div>

        <div class="key-descriptions">
            <div class="key-row">
                <span class="bullet">▸</span>
                <div><strong>{outer_label}</strong> <span>— {outer_desc}</span></div>
            </div>
            <div class="key-row">
                <span class="bullet">▸</span>
                <div><strong>Module (inner border)</strong> <span>— A deployable artifact (service, worker, function…) that packages one or more elements. Maps to a repo and a deployment unit.</span></div>
            </div>
            <div class="key-row">
                <span class="bullet">▸</span>
                <div><strong>Element</strong> <span>— The core implementation unit (aggregate, entity, value object, service, or projection). What developers actually build and own.</span></div>
            </div>
            <div class="key-row">
                <span class="bullet">▸</span>
                <div><strong>Datastore</strong> <span>— A database, cache, queue, or object store. The connecting arrow is labelled with the datastore name.</span></div>
            </div>
            <div class="key-row">
                <span class="bullet">▸</span>
                <div><strong>Solid arrow</strong> <span>— A contract reference (producer → consumer, labelled with the contract name) or a structural element relationship.</span></div>
            </div>
            <div class="key-row">
                <span class="bullet">▸</span>
                <div><strong>Dashed arrow</strong> <span>— An interaction: a direct runtime call from one element's operation to another's, as defined in the interactions registry.</span></div>
            </div>
        </div>
    </div>

    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: "dark",
            flowchart: {{ curve: "basis", padding: 20, nodeSpacing: 60, rankSpacing: 80 }},
            securityLevel: "loose",
        }});
    </script>
</body>
</html>
"""


# ===========================================================================
# Platform open
# ===========================================================================

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
