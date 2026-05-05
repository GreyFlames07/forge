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

# Minimum dot-path depth for node kinds we render as graph nodes.
# Elements: conception.system.domain.module.element = 5 parts
# Modules:  conception.system.domain.module          = 4 parts
# Types, errors, etc. are NOT rendered as nodes.
_ELEMENT_DEPTH = 5
_MODULE_DEPTH  = 4


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

    mermaid_text = _render_mermaid(idx, edges)

    if args.format == "mermaid":
        print(mermaid_text)
        return 0

    html = _render_html(mermaid_text, scope_label=args.scope,
                        conception=idx.conception_name)
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

        # --- Contracts: producer module → consumer modules ---
        if entry.kind == "contract":
            producer = data.get("producer")
            consumers = data.get("consumers") or []
            label = data.get("name") or entry_id.split(".")[-1]
            if producer and isinstance(producer, str):
                for consumer in (consumers if isinstance(consumers, list) else []):
                    if isinstance(consumer, str) and consumer:
                        edges.add(Edge(producer, consumer, label, "contract"))

        # --- Interactions: caller op → callee op (simplified to parent elements) ---
        elif entry.kind == "interaction":
            caller = data.get("caller")
            callee = data.get("callee")
            label = data.get("name") or entry_id.split(".")[-1]
            if caller and callee:
                # Simplify operation IDs to their parent element IDs
                src = _parent_element(str(caller), idx)
                dst = _parent_element(str(callee), idx)
                if src and dst and src != dst:
                    edges.add(Edge(src, dst, label, "interaction"))

        # --- Element relationships ---
        elif entry.kind == "element":
            for rel in (data.get("relationships") or []):
                if not isinstance(rel, dict):
                    continue
                target = rel.get("target")
                label = rel.get("type") or ""
                if isinstance(target, str) and target:
                    edges.add(Edge(entry_id, target, label, "relationship"))

        # --- Datastores: consumer modules → datastore ---
        elif entry.kind == "datastore":
            label = data.get("name") or entry_id.split(".")[-1]
            for consumer in (data.get("consumers") or []):
                if isinstance(consumer, str) and consumer:
                    edges.add(Edge(consumer, entry_id, label, "datastore"))

    return list(edges)


def _parent_element(node_id: str, idx: Any) -> str | None:
    """Given an operation/property ID, return the parent element ID.

    Falls back gracefully: if the node itself is an element, return it.
    If the node isn't in the index at all, try truncating to element depth.
    """
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
        # Strip last segment to get the parent element
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
# Mermaid rendering
# ===========================================================================

def _safe_id(node_id: str) -> str:
    return node_id.replace(".", "_").replace("-", "_").replace(" ", "_")


def _node_shape(node_id: str, idx: Any) -> tuple[str, str]:
    """Return (open_bracket, close_bracket) for Mermaid node shape."""
    entry = idx.get(node_id)
    if entry is None:
        return ("[", "]")
    shapes = {
        "element":   ("[", "]"),
        "module":    ("([", "])"),
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
    return f"{name}<br/><small>{kind}</small>"


def _domain_of(node_id: str, idx: Any) -> str | None:
    """Return the domain ID for grouping, or None."""
    parts = node_id.split(".")
    # conception.system.domain = 3 parts
    if len(parts) >= 3:
        candidate = ".".join(parts[:3])
        e = idx.get(candidate)
        if e and e.kind == "domain":
            return candidate
    return None


def _render_mermaid(idx: Any, edges: list[Edge]) -> str:
    # Collect all node IDs referenced by edges
    all_nodes: set[str] = set()
    for e in edges:
        all_nodes.add(e.src)
        all_nodes.add(e.dst)

    # Group nodes by domain for subgraphs
    domain_nodes: dict[str, list[str]] = {}
    ungrouped: list[str] = []
    for node in sorted(all_nodes):
        domain = _domain_of(node, idx)
        if domain:
            domain_nodes.setdefault(domain, []).append(node)
        else:
            ungrouped.append(node)

    lines: list[str] = ["graph LR"]

    # Emit domain subgraphs
    for domain_id in sorted(domain_nodes):
        entry = idx.get(domain_id)
        domain_label = (
            (entry.data.get("name") if entry and isinstance(entry.data, dict) else None)
            or domain_id.split(".")[-1]
        )
        lines.append(f'    subgraph {_safe_id(domain_id)}["{domain_label}"]')
        for node in sorted(set(domain_nodes[domain_id])):
            o, c = _node_shape(node, idx)
            label = _node_label(node, idx)
            lines.append(f'        {_safe_id(node)}{o}"{label}"{c}')
        lines.append("    end")

    # Ungrouped nodes (datastores, contracts, etc. outside any domain)
    for node in sorted(set(ungrouped)):
        o, c = _node_shape(node, idx)
        label = _node_label(node, idx)
        lines.append(f'    {_safe_id(node)}{o}"{label}"{c}')

    lines.append("")

    # Emit edges — dashed for interactions, solid for everything else
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

    return "\n".join(lines) + "\n"


# ===========================================================================
# HTML rendering
# ===========================================================================

def _render_html(mermaid_text: str, scope_label: str | None, conception: str) -> str:
    title = f"Forge Graph — {conception}"
    if scope_label:
        title += f" ({scope_label})"

    indented = textwrap.indent(mermaid_text, "            ")

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
            padding: 2rem;
            gap: 1.5rem;
        }}
        h1 {{
            font-size: 1.3rem;
            font-weight: 600;
            color: #94a3b8;
            letter-spacing: 0.02em;
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
        .legend {{
            font-size: 0.78rem;
            color: #475569;
            display: flex;
            gap: 2rem;
        }}
        .legend span::before {{ margin-right: 0.4em; }}
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
        <span>[ ] element</span>
        <span>([ ]) module</span>
        <span>[( )] datastore</span>
        <span>{{ }} contract</span>
        <span>solid arrow: contract / datastore / relationship</span>
        <span>dashed arrow: interaction</span>
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
