"""`forge graph` — generate a dependency graph from the spec directory."""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import tempfile
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
    "to the subgraph rooted at that node."
)

_MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"


# ===========================================================================
# Argparse registration
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
        "--scope",
        default=None,
        metavar="NODE_ID",
        help=(
            "Limit the graph to the subgraph reachable from this node id. "
            "The node itself and all nodes it depends on (or that depend on it) "
            "are included."
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

    # Build the full edge set
    edges: list[Edge] = _collect_edges(idx)

    # Scope filtering
    if args.scope:
        if idx.get(args.scope) is None:
            print(f"error: unknown node id: {args.scope}", file=sys.stderr)
            common.suggest_similar(idx, args.scope)
            return 1
        edges = _filter_to_scope(edges, args.scope)

    # Group nodes into subgraphs by module
    subgraphs = _build_subgraphs(idx, edges)

    mermaid_text = _render_mermaid(subgraphs, edges)

    if args.format == "mermaid":
        print(mermaid_text)
        return 0

    # HTML output
    html = _render_html(mermaid_text, scope_label=args.scope)
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
# Graph data structures
# ===========================================================================

class Edge:
    __slots__ = ("src", "dst", "label", "kind")

    def __init__(self, src: str, dst: str, label: str = "", kind: str = "dep") -> None:
        self.src = src
        self.dst = dst
        self.label = label
        self.kind = kind  # "contract" | "interaction" | "relationship" | "datastore"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Edge):
            return NotImplemented
        return (self.src, self.dst, self.label, self.kind) == (other.src, other.dst, other.label, other.kind)

    def __hash__(self) -> int:
        return hash((self.src, self.dst, self.label, self.kind))


# ===========================================================================
# Edge collection
# ===========================================================================

def _collect_edges(idx: Any) -> list[Edge]:
    edges: set[Edge] = set()

    for entry_id, entry in idx.entries.items():
        if not isinstance(entry.data, dict):
            continue
        data = entry.data

        # Contract relationships: producer module -> consumer modules
        if entry.kind == "contract":
            producer = data.get("producer")
            consumers = data.get("consumers") or []
            contract_name = data.get("name") or entry_id
            if producer:
                for consumer in (consumers if isinstance(consumers, list) else [consumers]):
                    if consumer:
                        edges.add(Edge(
                            src=str(producer),
                            dst=str(consumer),
                            label=str(contract_name),
                            kind="contract",
                        ))

        # Interaction relationships: caller operation -> callee operation
        elif entry.kind == "interaction":
            caller = data.get("caller") or data.get("caller_operation")
            callee = data.get("callee") or data.get("callee_operation")
            interaction_name = data.get("name") or entry_id
            if caller and callee:
                edges.add(Edge(
                    src=str(caller),
                    dst=str(callee),
                    label=str(interaction_name),
                    kind="interaction",
                ))

        # Element relationships: from the 'relationships' field
        elif entry.kind == "element":
            for rel in (data.get("relationships") or []):
                if not isinstance(rel, dict):
                    continue
                target = rel.get("target") or rel.get("to") or rel.get("id")
                rel_label = rel.get("type") or rel.get("label") or ""
                if target:
                    edges.add(Edge(
                        src=entry_id,
                        dst=str(target),
                        label=str(rel_label),
                        kind="relationship",
                    ))

        # Datastore consumers: module -> datastore
        elif entry.kind == "datastore":
            consumers = data.get("consumers") or data.get("consumer_modules") or []
            ds_name = data.get("name") or entry_id
            if isinstance(consumers, list):
                for consumer in consumers:
                    if consumer:
                        edges.add(Edge(
                            src=str(consumer),
                            dst=entry_id,
                            label=str(ds_name),
                            kind="datastore",
                        ))
            # Also check for a single 'owner' or 'owner_module'
            owner = data.get("owner") or data.get("owner_module")
            if owner:
                edges.add(Edge(
                    src=str(owner),
                    dst=entry_id,
                    label="owns",
                    kind="datastore",
                ))

        # Generic: walk 'operations' for any cross-module calls
        operations = data.get("operations") or []
        if isinstance(operations, list):
            for op in operations:
                if not isinstance(op, dict):
                    continue
                op_id = op.get("id") or ""
                for call in (op.get("calls") or op.get("invokes") or []):
                    if isinstance(call, str) and "." in call:
                        edges.add(Edge(
                            src=op_id or entry_id,
                            dst=call,
                            label="calls",
                            kind="interaction",
                        ))

    return list(edges)


# ===========================================================================
# Scope filtering
# ===========================================================================

def _filter_to_scope(edges: list[Edge], scope_id: str) -> list[Edge]:
    """Keep only edges connected (directly or transitively) to scope_id."""
    # Build adjacency sets in both directions
    fwd: dict[str, set[str]] = {}
    bwd: dict[str, set[str]] = {}
    edge_map: dict[tuple[str, str], list[Edge]] = {}

    for e in edges:
        fwd.setdefault(e.src, set()).add(e.dst)
        bwd.setdefault(e.dst, set()).add(e.src)
        edge_map.setdefault((e.src, e.dst), []).append(e)

    # BFS from scope_id in both directions
    reachable: set[str] = {scope_id}
    frontier = {scope_id}
    while frontier:
        next_frontier: set[str] = set()
        for node in frontier:
            for neighbour in (fwd.get(node) or set()):
                if neighbour not in reachable:
                    reachable.add(neighbour)
                    next_frontier.add(neighbour)
            for neighbour in (bwd.get(node) or set()):
                if neighbour not in reachable:
                    reachable.add(neighbour)
                    next_frontier.add(neighbour)
        frontier = next_frontier

    return [e for e in edges if e.src in reachable or e.dst in reachable]


# ===========================================================================
# Subgraph grouping
# ===========================================================================

def _module_of(node_id: str, idx: Any) -> str | None:
    """Return the owning module id for a node, or None."""
    entry = idx.get(node_id)
    if entry is None:
        return None
    if entry.kind == "module":
        return node_id
    data = entry.data if isinstance(entry.data, dict) else {}
    owner = data.get("owner_module") or data.get("module")
    if owner:
        return str(owner)
    # Derive from dot-path: the module is everything up to the third segment
    parts = node_id.split(".")
    if len(parts) >= 3:
        return ".".join(parts[:3])
    if len(parts) >= 2:
        return ".".join(parts[:2])
    return None


def _build_subgraphs(idx: Any, edges: list[Edge]) -> dict[str, list[str]]:
    """Map module id -> list of node ids that belong to it."""
    all_nodes: set[str] = set()
    for e in edges:
        all_nodes.add(e.src)
        all_nodes.add(e.dst)

    subgraphs: dict[str, list[str]] = {}
    ungrouped: list[str] = []

    for node in sorted(all_nodes):
        module = _module_of(node, idx)
        if module:
            subgraphs.setdefault(module, []).append(node)
        else:
            ungrouped.append(node)

    if ungrouped:
        subgraphs["__ungrouped__"] = ungrouped

    return subgraphs


# ===========================================================================
# Mermaid rendering
# ===========================================================================

_KIND_ARROW: dict[str, str] = {
    "contract": "-->|{label}|",
    "interaction": "-. {label} .->",
    "relationship": "-->|{label}|",
    "datastore": "-->|{label}|",
}


def _safe_id(node_id: str) -> str:
    """Convert a dot-path id into a Mermaid-safe identifier."""
    return node_id.replace(".", "_").replace("-", "_").replace(" ", "_")


def _node_label(node_id: str, idx: Any) -> str:
    """Return a short human-readable label for a node."""
    entry = idx.get(node_id)
    if entry is None:
        return node_id
    data = entry.data if isinstance(entry.data, dict) else {}
    name = data.get("name") or ""
    kind = entry.kind or ""
    if name:
        return f"{name}\\n({kind})"
    return f"{node_id}\\n({kind})"


def _render_mermaid(subgraphs: dict[str, list[str]], edges: list[Edge]) -> str:
    lines: list[str] = ["graph LR"]

    # Emit subgraphs
    for module_id, nodes in sorted(subgraphs.items()):
        if module_id == "__ungrouped__":
            label = "ungrouped"
        else:
            label = module_id
        lines.append(f'    subgraph {_safe_id(module_id)}["{label}"]')
        for node in sorted(set(nodes)):
            safe = _safe_id(node)
            # Use a simple box — no index lookup needed here, done in label func
            lines.append(f"        {safe}")
        lines.append("    end")

    lines.append("")

    # Emit edges
    seen_edges: set[tuple[str, str, str]] = set()
    for e in edges:
        src = _safe_id(e.src)
        dst = _safe_id(e.dst)
        label = e.label or ""
        key = (src, dst, label)
        if key in seen_edges:
            continue
        seen_edges.add(key)

        safe_label = label.replace('"', "'")
        if safe_label:
            lines.append(f'    {src} -->|"{safe_label}"| {dst}')
        else:
            lines.append(f"    {src} --> {dst}")

    return "\n".join(lines) + "\n"


# ===========================================================================
# HTML rendering
# ===========================================================================

def _render_html(mermaid_text: str, scope_label: str | None = None) -> str:
    title = "Forge Spec Graph"
    if scope_label:
        title += f" — {scope_label}"

    # Indent mermaid source for embedding in a <pre> block
    indented = textwrap.indent(mermaid_text, "            ")

    html = f"""\
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
            padding: 2rem;
        }}
        h1 {{
            font-size: 1.4rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            letter-spacing: 0.02em;
            color: #94a3b8;
        }}
        .diagram-container {{
            background: #1e2433;
            border-radius: 12px;
            padding: 2rem;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
            width: 100%;
            max-width: 1400px;
            overflow-x: auto;
        }}
        .mermaid {{
            display: flex;
            justify-content: center;
        }}
        .legend {{
            margin-top: 1.5rem;
            font-size: 0.8rem;
            color: #64748b;
            text-align: center;
        }}
        .legend span {{
            margin: 0 0.75rem;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="diagram-container">
        <div class="mermaid">
{indented}
        </div>
    </div>
    <div class="legend">
        <span>Solid arrows: contracts / relationships / datastores</span>
        <span>Dashed arrows: interactions / calls</span>
    </div>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'dark',
            flowchart: {{
                curve: 'basis',
                padding: 20,
                nodeSpacing: 50,
                rankSpacing: 70,
            }},
            securityLevel: 'loose',
        }});
    </script>
</body>
</html>
"""
    return html


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
        pass  # silently ignore if the open command is unavailable
