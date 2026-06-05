from __future__ import annotations

import fnmatch
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from cli.yaml_io import dump_yaml, read_yaml

V4_ROOT_FILES = ("system.yaml", "containers.yaml", "entities.yaml")
DEFAULT_DECISIONS: dict[str, Any] = {"schema": "forge.decisions", "decisions": []}
ANNOTATION_KINDS = {"component", "type", "persistence", "operation"}


DEFAULT_CRAWLER_CONFIG: dict[str, Any] = {
    "schema": "forge.crawler",
    "crawler": {
        "ignore_dirs": [
            ".git",
            ".hg",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            "__pycache__",
            "node_modules",
            "dist",
            "build",
        ],
        "ignore_patterns": [
            "**/*.generated.*",
            "**/vendor/**",
        ],
        "comment_profiles": {
            "hash": {
                "extensions": [".py", ".rb", ".sh", ".yaml", ".yml"],
                "prefixes": ["#"],
            },
            "slash": {
                "extensions": [
                    ".ts",
                    ".tsx",
                    ".js",
                    ".jsx",
                    ".go",
                    ".rs",
                    ".java",
                    ".kt",
                    ".cs",
                    ".swift",
                    ".php",
                ],
                "prefixes": ["//"],
            },
            "sql": {
                "extensions": [".sql"],
                "prefixes": ["--"],
            },
        },
    },
}


@dataclass(frozen=True)
class ForgeCrawlError(Exception):
    """Clean structured crawler failure."""

    code: str
    message: str
    source: Path | None = None
    line: int | None = None
    annotation: str | None = None

    def to_dict(self, root: Path | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.source is not None:
            payload["error"]["source"] = _relative_path(self.source, root) if root is not None else str(self.source)
        if self.line is not None:
            payload["error"]["line"] = self.line
        if self.annotation is not None:
            payload["error"]["annotation"] = self.annotation
        return payload


@dataclass(frozen=True)
class CommentProfile:
    """Line-comment parser configuration for a set of file extensions."""

    name: str
    extensions: tuple[str, ...]
    prefixes: tuple[str, ...]


@dataclass(frozen=True)
class CrawlerConfig:
    """User-editable crawler configuration loaded from forge/crawler.yaml."""

    ignore_dirs: tuple[str, ...]
    ignore_patterns: tuple[str, ...]
    profiles: tuple[CommentProfile, ...]

    @property
    def prefixes_by_extension(self) -> dict[str, tuple[str, ...]]:
        prefixes: dict[str, list[str]] = defaultdict(list)
        for profile in self.profiles:
            for extension in profile.extensions:
                normalized = _normalize_extension(extension)
                prefixes[normalized].extend(profile.prefixes)
        return {extension: tuple(dict.fromkeys(values)) for extension, values in prefixes.items()}

    @property
    def configured_extensions(self) -> set[str]:
        return set(self.prefixes_by_extension)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ignore_dirs": list(self.ignore_dirs),
            "ignore_patterns": list(self.ignore_patterns),
            "comment_profiles": {
                profile.name: {
                    "extensions": list(profile.extensions),
                    "prefixes": list(profile.prefixes),
                }
                for profile in self.profiles
            },
        }


@dataclass(frozen=True)
class ForgeAnnotation:
    """Code-owned Forge annotation extracted from a source file."""

    kind: str
    payload: dict[str, Any]
    source: Path
    line: int
    container: str | None = None
    component: str | None = None

    @property
    def id(self) -> str | None:
        annotation_id = self.payload.get("id")
        if isinstance(annotation_id, str):
            return annotation_id
        if self.kind == "persistence":
            entity_id = self.payload.get("entity")
            return entity_id if isinstance(entity_id, str) else None
        return None

    def to_dict(self, root: Path) -> dict[str, Any]:
        return {
            "id": self.id,
            "container": self.container,
            "component": self.component,
            "source": _relative_path(self.source, root),
            "line": self.line,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class ForgeCrawlResult:
    """Merged V4 crawl result from central Forge files and code annotations."""

    root: Path
    workspace_root: Path
    system: dict[str, Any]
    containers: dict[str, Any]
    entities: dict[str, Any]
    decisions: dict[str, Any]
    config: CrawlerConfig
    annotations: list[ForgeAnnotation] = field(default_factory=list)
    skipped_file_types: dict[str, int] = field(default_factory=dict)
    forge_docs: list[Path] = field(default_factory=list)

    def annotations_by_kind(self, kind: str) -> list[ForgeAnnotation]:
        return [annotation for annotation in self.annotations if annotation.kind == kind]

    @property
    def components(self) -> list[ForgeAnnotation]:
        return self.annotations_by_kind("component")

    @property
    def data_shapes(self) -> list[ForgeAnnotation]:
        return self.annotations_by_kind("type")

    @property
    def persistence(self) -> list[ForgeAnnotation]:
        return self.annotations_by_kind("persistence")

    @property
    def operations(self) -> list[ForgeAnnotation]:
        return self.annotations_by_kind("operation")

    def to_dict(self) -> dict[str, Any]:
        extracted_containers = _extracted_containers(self)
        return _json_safe({
            "schema": "forge.extracted_model",
            "root": str(self.root),
            "workspace_root": str(self.workspace_root),
            "system": self.system.get("system", self.system),
            "containers": extracted_containers,
            "container_flows": _collection(self.containers, "container_flows"),
            "entities": _collection(self.entities, "entities"),
            "decisions": _collection(self.decisions, "decisions"),
            "persistence": [annotation.to_dict(self.workspace_root) for annotation in self.persistence],
            "warnings": _warnings(self),
            "findings": _validation_findings(self),
            "forge_docs": [
                {"source": _relative_path(path, self.root), "title": _markdown_title(path)}
                for path in self.forge_docs
            ],
            "summary": {
                "containers": len(extracted_containers),
                "container_flows": len(_collection(self.containers, "container_flows")),
                "entities": len(_collection(self.entities, "entities")),
                "decisions": len(_collection(self.decisions, "decisions")),
                "components": len(self.components),
                "data_shapes": len(self.data_shapes),
                "persistence": len(self.persistence),
                "operations": len(self.operations),
                "warnings": len(_warnings(self)["skipped_file_types"]),
                "duplicate_findings": len(_validation_findings(self)["duplicates"]),
                "validation_findings": _validation_finding_count(_validation_findings(self)),
                "forge_docs": len(self.forge_docs),
            },
        })


def is_v4_forge_root(path: Path) -> bool:
    """Return whether a directory contains the V4 central Forge schema files."""
    return path.is_dir() and all((path / filename).exists() for filename in V4_ROOT_FILES)


def find_v4_project_root(start: Path | None = None) -> Path:
    """Find a V4 Forge root from a repository, nested path, or direct forge directory."""
    current = (start or Path.cwd()).resolve()
    if is_v4_forge_root(current):
        return current
    embedded = current / "forge"
    if is_v4_forge_root(embedded):
        return embedded
    for candidate in current.parents:
        if is_v4_forge_root(candidate):
            return candidate
        embedded = candidate / "forge"
        if is_v4_forge_root(embedded):
            return embedded
    raise FileNotFoundError(
        "Could not find a Forge V4 project root. Run inside a workspace containing "
        "`system.yaml`, `containers.yaml`, and `entities.yaml`, run from a repository with `forge/`, "
        "or pass `--project-dir`."
    )


def crawl_project(root: Path) -> ForgeCrawlResult:
    """Crawl V4 central schema files and embedded code annotations."""
    forge_root = find_v4_project_root(root)
    workspace_root = forge_root.parent
    system = read_yaml(forge_root / "system.yaml")
    containers = read_yaml(forge_root / "containers.yaml")
    entities = read_yaml(forge_root / "entities.yaml")
    decisions = read_yaml(forge_root / "decisions.yaml") if (forge_root / "decisions.yaml").exists() else DEFAULT_DECISIONS
    config = load_crawler_config(forge_root)
    container_source_roots = _container_source_roots(workspace_root, containers)
    annotations: list[ForgeAnnotation] = []
    skipped_file_types: Counter[str] = Counter()
    for source_root in _scan_roots(container_source_roots.values()):
        if source_root.exists():
            root_annotations, root_skipped = _crawl_source_root(source_root, workspace_root, container_source_roots, config)
            annotations.extend(root_annotations)
            skipped_file_types.update(root_skipped)
    return ForgeCrawlResult(
        root=forge_root,
        workspace_root=workspace_root,
        system=system,
        containers=containers,
        entities=entities,
        decisions=decisions,
        config=config,
        annotations=sorted(annotations, key=lambda item: (str(item.source), item.line)),
        skipped_file_types=dict(sorted(skipped_file_types.items())),
        forge_docs=_forge_markdown_docs(forge_root),
    )


def load_crawler_config(forge_root: Path) -> CrawlerConfig:
    """Load optional forge/crawler.yaml, falling back to built-in defaults."""
    config_path = forge_root / "crawler.yaml"
    raw_config = _deep_merge(DEFAULT_CRAWLER_CONFIG, read_yaml(config_path)) if config_path.exists() else DEFAULT_CRAWLER_CONFIG
    crawler = raw_config.get("crawler", {})
    if not isinstance(crawler, dict):
        raise ForgeCrawlError("invalid_crawler_config", "`crawler` must be a mapping.", source=config_path)
    profiles_raw = crawler.get("comment_profiles", {})
    if not isinstance(profiles_raw, dict):
        raise ForgeCrawlError("invalid_crawler_config", "`crawler.comment_profiles` must be a mapping.", source=config_path)
    profiles: list[CommentProfile] = []
    for name, profile_raw in profiles_raw.items():
        if not isinstance(profile_raw, dict):
            raise ForgeCrawlError("invalid_crawler_config", f"Comment profile `{name}` must be a mapping.", source=config_path)
        profiles.append(
            CommentProfile(
                name=str(name),
                extensions=tuple(_normalize_extension(item) for item in _string_list(profile_raw.get("extensions", []))),
                prefixes=tuple(_string_list(profile_raw.get("prefixes", []))),
            )
        )
    if not profiles:
        raise ForgeCrawlError("invalid_crawler_config", "`crawler.comment_profiles` must define at least one profile.", source=config_path)
    for profile in profiles:
        if not profile.extensions:
            raise ForgeCrawlError("invalid_crawler_config", f"Comment profile `{profile.name}` must define extensions.", source=config_path)
        if not profile.prefixes:
            raise ForgeCrawlError("invalid_crawler_config", f"Comment profile `{profile.name}` must define prefixes.", source=config_path)
    return CrawlerConfig(
        ignore_dirs=tuple(_string_list(crawler.get("ignore_dirs", []))),
        ignore_patterns=tuple(_string_list(crawler.get("ignore_patterns", []))),
        profiles=tuple(profiles),
    )


def dump_crawl_result(result: ForgeCrawlResult, format_: str) -> str:
    """Render a crawl result as JSON-compatible YAML or a compact Markdown summary."""
    payload = result.to_dict()
    if format_ == "yaml":
        return dump_yaml(payload)
    if format_ == "md":
        summary = payload["summary"]
        lines = [
            f"# Forge Crawl: {payload['system'].get('id', result.root.name)}",
            "",
            f"- containers: `{summary['containers']}`",
            f"- container flows: `{summary['container_flows']}`",
            f"- entities: `{summary['entities']}`",
            f"- decisions: `{summary['decisions']}`",
            f"- components: `{summary['components']}`",
            f"- data shapes: `{summary['data_shapes']}`",
            f"- persistence annotations: `{summary['persistence']}`",
            f"- operations: `{summary['operations']}`",
            f"- warnings: `{summary['warnings']}`",
            f"- duplicate findings: `{summary['duplicate_findings']}`",
            f"- validation findings: `{summary['validation_findings']}`",
        ]
        skipped = payload["warnings"]["skipped_file_types"]
        if skipped:
            lines.extend(["", "## Skipped File Types"])
            lines.extend(f"- `{item['extension']}`: {item['count']} files" for item in skipped)
        return "\n".join(lines)
    raise ValueError(f"Unsupported crawl output format: {format_}")


def dump_crawl_error(error: ForgeCrawlError, format_: str, root: Path | None = None) -> str:
    """Render a crawler error without tracebacks or extra CLI noise."""
    payload = error.to_dict(root)
    if format_ == "json":
        import json

        return json.dumps(payload, indent=2)
    if format_ == "yaml":
        return dump_yaml(payload).rstrip()
    return payload["error"]["message"]


def _crawl_source_root(
    source_root: Path,
    workspace_root: Path,
    container_source_roots: dict[str, Path],
    config: CrawlerConfig,
) -> tuple[list[ForgeAnnotation], Counter[str]]:
    annotations: list[ForgeAnnotation] = []
    skipped_file_types: Counter[str] = Counter()
    for source in _iter_source_files(source_root, workspace_root, config):
        prefixes = config.prefixes_by_extension.get(_normalize_extension(source.suffix))
        if not prefixes:
            skipped_file_types[_normalize_extension(source.suffix)] += 1
            continue
        annotations.extend(_extract_annotations(source, workspace_root, container_source_roots, prefixes))
    return annotations, skipped_file_types


def _iter_source_files(source_root: Path, workspace_root: Path, config: CrawlerConfig) -> list[Path]:
    files: list[Path] = []
    for path in source_root.rglob("*"):
        if _ignored(path, workspace_root, config):
            continue
        if path.is_file():
            files.append(path)
    return sorted(files)


def _extract_annotations(
    source: Path,
    workspace_root: Path,
    container_source_roots: dict[str, Path],
    prefixes: tuple[str, ...],
) -> list[ForgeAnnotation]:
    lines = source.read_text(encoding="utf-8").splitlines()
    annotations: list[ForgeAnnotation] = []
    current_component: str | None = None
    index = 0
    while index < len(lines):
        marker = _annotation_marker(lines[index], prefixes)
        if marker is None:
            index += 1
            continue
        kind, prefix = marker
        start_line = index + 1
        index += 1
        payload_lines: list[str] = []
        while index < len(lines):
            comment = _comment_payload(lines[index], prefix)
            if comment is None:
                break
            payload_lines.append(comment)
            index += 1
        if kind not in ANNOTATION_KINDS:
            continue
        payload = _parse_annotation_payload(source, start_line, kind, payload_lines)
        if kind == "operation":
            payload = _normalize_operation_payload(payload)
        container = _annotation_container(payload, source, workspace_root, container_source_roots)
        component = _annotation_component(kind, payload, current_component)
        annotation = ForgeAnnotation(
            kind=kind,
            payload=payload,
            source=source.resolve(),
            line=start_line,
            container=container,
            component=component,
        )
        annotations.append(annotation)
        if kind == "component":
            current_component = annotation.id
    return annotations


def _annotation_marker(line: str, prefixes: tuple[str, ...]) -> tuple[str, str] | None:
    stripped = line.lstrip()
    for prefix in prefixes:
        marker_prefix = f"{prefix} @forge:"
        compact_marker_prefix = f"{prefix}@forge:"
        if stripped.startswith(marker_prefix):
            return stripped[len(marker_prefix) :].strip(), prefix
        if stripped.startswith(compact_marker_prefix):
            return stripped[len(compact_marker_prefix) :].strip(), prefix
    return None


def _comment_payload(line: str, prefix: str) -> str | None:
    stripped = line.lstrip()
    if not stripped.startswith(prefix):
        return None
    payload = stripped[len(prefix) :]
    if payload.startswith(" "):
        return payload[1:]
    return payload


def _parse_annotation_payload(source: Path, line: int, kind: str, payload_lines: list[str]) -> dict[str, Any]:
    payload_text = "\n".join(_normalize_schema_shorthand(line_text) for line_text in payload_lines).strip()
    if not payload_text:
        return {}
    try:
        loaded = yaml.safe_load(payload_text)
    except yaml.YAMLError as exc:
        raise ForgeCrawlError(
            "malformed_annotation",
            "Forge annotation must parse as prefix-commented YAML.",
            source=source,
            line=line,
            annotation=f"@forge:{kind}",
        ) from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ForgeCrawlError(
            "malformed_annotation",
            "Forge annotation must parse to a YAML mapping.",
            source=source,
            line=line,
            annotation=f"@forge:{kind}",
        )
    return loaded


def _normalize_operation_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize compact operation flow refs like `register_user:1`."""
    normalized = dict(payload)
    if isinstance(normalized.get("container_flow"), str):
        _normalize_operation_entry(normalized)
    participates_in = normalized.get("participates_in")
    if isinstance(participates_in, list):
        normalized["participates_in"] = [
            _normalize_operation_entry(dict(item))
            if isinstance(item, dict)
            else item
            for item in participates_in
        ]
    return normalized


def _normalize_operation_entry(entry: dict[str, Any]) -> dict[str, Any]:
    container_flow = entry.get("container_flow")
    if isinstance(container_flow, str):
        flow_id, step = _split_flow_step_ref(container_flow)
        entry["container_flow"] = flow_id
        if step is not None and entry.get("step") is None:
            entry["step"] = step
    local_flow = entry.get("local_flow")
    if isinstance(local_flow, str):
        local_flow_id, local_step = _split_flow_step_ref(local_flow)
        entry["local_flow"] = local_flow_id
        if local_step is not None and entry.get("local_step") is None:
            entry["local_step"] = local_step
    return entry


def _split_flow_step_ref(value: str) -> tuple[str, int | None]:
    flow_id, separator, raw_step = value.rpartition(":")
    if not separator or not flow_id or not raw_step.isdigit():
        return value, None
    return flow_id, int(raw_step)


def _normalize_schema_shorthand(line: str) -> str:
    return re.sub(r":\s*(\[[a-zA-Z_]+\[[^\]]+\]\])\s*$", r": '\1'", line)


def _annotation_container(
    payload: dict[str, Any],
    source: Path,
    workspace_root: Path,
    container_source_roots: dict[str, Path],
) -> str | None:
    explicit = payload.get("container")
    if isinstance(explicit, str):
        return explicit
    resolved_source = source.resolve()
    matching: list[tuple[int, str]] = []
    for container_id, source_root in container_source_roots.items():
        try:
            resolved_source.relative_to(source_root)
        except ValueError:
            continue
        matching.append((len(source_root.relative_to(workspace_root).parts), container_id))
    if not matching:
        return None
    return max(matching)[1]


def _annotation_component(kind: str, payload: dict[str, Any], current_component: str | None) -> str | None:
    explicit = payload.get("component")
    if isinstance(explicit, str):
        return explicit
    if kind == "component":
        annotation_id = payload.get("id")
        return annotation_id if isinstance(annotation_id, str) else None
    return current_component


def _container_source_roots(workspace_root: Path, containers: dict[str, Any]) -> dict[str, Path]:
    source_roots: dict[str, Path] = {}
    for container in _collection(containers, "containers"):
        container_id = container.get("id")
        source_root = container.get("source_root")
        if isinstance(container_id, str) and isinstance(source_root, str) and source_root:
            source_roots[container_id] = (workspace_root / source_root).resolve()
    return source_roots


def _scan_roots(source_roots: Any) -> list[Path]:
    resolved = sorted({Path(root).resolve() for root in source_roots})
    scan_roots: list[Path] = []
    for root in resolved:
        if any(_is_relative_to(root, existing) for existing in scan_roots):
            continue
        scan_roots.append(root)
    return scan_roots


def _extracted_containers(result: ForgeCrawlResult) -> list[dict[str, Any]]:
    containers: list[dict[str, Any]] = []
    for container in _collection(result.containers, "containers"):
        container_id = container.get("id")
        if not isinstance(container_id, str):
            continue
        containers.append(
            {
                **container,
                "components": [
                    annotation.to_dict(result.workspace_root)
                    for annotation in result.components
                    if annotation.container == container_id
                ],
                "data_shapes": [
                    annotation.to_dict(result.workspace_root)
                    for annotation in result.data_shapes
                    if annotation.container == container_id
                ],
                "operations": [
                    annotation.to_dict(result.workspace_root)
                    for annotation in result.operations
                    if annotation.container == container_id
                ],
            }
        )
    return containers


def _warnings(result: ForgeCrawlResult) -> dict[str, Any]:
    return {
        "skipped_file_types": [
            {
                "extension": extension,
                "count": count,
                "reason": "No crawler comment profile configured for this file extension.",
            }
            for extension, count in sorted(result.skipped_file_types.items())
        ]
    }


def _duplicate_findings(result: ForgeCrawlResult) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[ForgeAnnotation]] = defaultdict(list)
    for annotation in result.annotations:
        if annotation.id:
            grouped[(annotation.kind, annotation.id)].append(annotation)
    findings: list[dict[str, Any]] = []
    for (kind, annotation_id), duplicate_annotations in sorted(grouped.items()):
        if len(duplicate_annotations) < 2:
            continue
        findings.append(
            {
                "kind": kind,
                "id": annotation_id,
                "sources": [
                    {
                        "source": _relative_path(annotation.source, result.workspace_root),
                        "line": annotation.line,
                        "container": annotation.container,
                    }
                    for annotation in duplicate_annotations
                ],
            }
        )
    return findings


def _validation_findings(result: ForgeCrawlResult) -> dict[str, Any]:
    return {
        "duplicates": _duplicate_findings(result),
        "missing_required_fields": _missing_required_field_findings(result),
        "unresolved_references": _unresolved_reference_findings(result),
        "invalid_flow_steps": _invalid_flow_step_findings(result),
        "config": _config_findings(result.config),
    }


def _validation_finding_count(findings: dict[str, Any]) -> int:
    return sum(len(value) for value in findings.values() if isinstance(value, list))


def _missing_required_field_findings(result: ForgeCrawlResult) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    required_by_kind = {
        "component": ["id", "role", "description"],
        "type": ["id", "type_kind", "shape"],
        "operation": ["id", "input", "logic"],
        "persistence": ["entity", "storage_model", "physical_store", "security"],
    }
    for annotation in result.annotations:
        for field_name in required_by_kind.get(annotation.kind, []):
            if annotation.payload.get(field_name) in (None, "", []):
                findings.append(_annotation_finding(annotation, result, f"`{field_name}` is required."))
        if annotation.kind == "component" and annotation.payload.get("role") == "interface" and not annotation.payload.get("interface"):
            findings.append(_annotation_finding(annotation, result, "`interface` is required when role is `interface`."))
        if annotation.kind == "operation" and not _operation_entries(annotation):
            findings.append(
                _annotation_finding(
                    annotation,
                    result,
                    "`container_flow` and `local_flow` with `flow_id:step` values are required, either directly or through `participates_in`.",
                )
            )
    for label, items, required_fields in (
        ("container", _collection(result.containers, "containers"), ["id", "kind", "technology", "description"]),
        ("container_flow", _collection(result.containers, "container_flows"), ["id", "business_action", "description", "steps"]),
        ("entity", _collection(result.entities, "entities"), ["id", "category", "description", "canonical_type", "logical_owner"]),
    ):
        for item in items:
            for field_name in required_fields:
                if item.get(field_name) in (None, "", []):
                    findings.append({"kind": label, "id": item.get("id"), "message": f"`{field_name}` is required."})
            if label == "container_flow":
                for step in _collection(item, "steps"):
                    if step.get("container") in (None, ""):
                        findings.append({"kind": label, "id": item.get("id"), "message": "`step.container` is required."})
                    if step.get("from") or step.get("to"):
                        findings.append({"kind": label, "id": item.get("id"), "message": "Container-flow steps use `container`, not `from`/`to`."})
    return findings


def _unresolved_reference_findings(result: ForgeCrawlResult) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    system = result.system.get("system", result.system)
    actors = _ids(system.get("actors", []))
    business_actions = _ids(system.get("business_actions", []))
    containers = _ids(_collection(result.containers, "containers"))
    entities = _ids(_collection(result.entities, "entities"))
    container_flows = _ids(_collection(result.containers, "container_flows"))
    components = {annotation.id for annotation in result.components if annotation.id}
    data_shapes = {annotation.id for annotation in result.data_shapes if annotation.id}

    for action in system.get("business_actions", []):
        if isinstance(action, dict) and action.get("actor") and action["actor"] not in actors:
            findings.append(_reference_finding("business_action", action.get("id"), "actor", action["actor"], "actor"))

    for flow in _collection(result.containers, "container_flows"):
        if flow.get("business_action") and flow["business_action"] not in business_actions:
            findings.append(_reference_finding("container_flow", flow.get("id"), "business_action", flow["business_action"], "business_action"))
        trigger = flow.get("trigger", {})
        if isinstance(trigger, dict):
            if trigger.get("actor") and trigger["actor"] not in actors:
                findings.append(_reference_finding("container_flow", flow.get("id"), "trigger.actor", trigger["actor"], "actor"))
            if trigger.get("container") and trigger["container"] not in containers:
                findings.append(_reference_finding("container_flow", flow.get("id"), "trigger.container", trigger["container"], "container"))
        for step in _collection(flow, "steps"):
            if step.get("container") and step["container"] not in containers:
                findings.append(_reference_finding("container_flow", flow.get("id"), "step.container", step["container"], "container"))
            for ref in sorted(_extract_refs(step)):
                if ref not in data_shapes:
                    findings.append(_reference_finding("container_flow", flow.get("id"), "step.ref", ref, "data_shape"))

    for entity in _collection(result.entities, "entities"):
        entity_id = entity.get("id")
        for field_name in ("canonical_type", "logical_owner", "persisted_in"):
            entity_ref = entity.get(field_name)
            if not isinstance(entity_ref, dict):
                continue
            if entity_ref.get("container") and entity_ref["container"] not in containers:
                findings.append(_reference_finding("entity", entity_id, f"{field_name}.container", entity_ref["container"], "container"))
            if entity_ref.get("component") and entity_ref["component"] not in components:
                findings.append(_reference_finding("entity", entity_id, f"{field_name}.component", entity_ref["component"], "component"))
            if field_name == "canonical_type" and entity_ref.get("ref") and entity_ref["ref"] not in data_shapes:
                findings.append(_reference_finding("entity", entity_id, f"{field_name}.ref", entity_ref["ref"], "data_shape"))

    for annotation in result.components:
        if annotation.container and annotation.container not in containers:
            findings.append(_reference_finding("component", annotation.id, "container", annotation.container, "container", annotation, result))
        if annotation.payload.get("parent_component") and annotation.payload["parent_component"] not in components:
            findings.append(
                _reference_finding(
                    "component",
                    annotation.id,
                    "parent_component",
                    annotation.payload["parent_component"],
                    "component",
                    annotation,
                    result,
                )
            )
        for shape in annotation.payload.get("data_shapes", []) if isinstance(annotation.payload.get("data_shapes"), list) else []:
            if shape not in data_shapes:
                findings.append(_reference_finding("component", annotation.id, "data_shapes", shape, "data_shape", annotation, result))
        interface = annotation.payload.get("interface", {})
        if isinstance(interface, dict):
            for flow_id in interface.get("container_flows", []) if isinstance(interface.get("container_flows"), list) else []:
                if flow_id not in container_flows:
                    findings.append(_reference_finding("component", annotation.id, "interface.container_flows", flow_id, "container_flow", annotation, result))
            if interface.get("actor") and interface["actor"] not in actors:
                findings.append(_reference_finding("component", annotation.id, "interface.actor", interface["actor"], "actor", annotation, result))

    for annotation in result.data_shapes:
        if annotation.container and annotation.container not in containers:
            findings.append(_reference_finding("type", annotation.id, "container", annotation.container, "container", annotation, result))
        if annotation.payload.get("entity") and annotation.payload["entity"] not in entities:
            findings.append(_reference_finding("type", annotation.id, "entity", annotation.payload["entity"], "entity", annotation, result))
        for ref in sorted(_extract_refs(annotation.payload.get("shape", {}))):
            if ref not in data_shapes:
                findings.append(_reference_finding("type", annotation.id, "shape.ref", ref, "data_shape", annotation, result))

    for annotation in result.operations:
        if annotation.container and annotation.container not in containers:
            findings.append(_reference_finding("operation", annotation.id, "container", annotation.container, "container", annotation, result))
        for entry in _operation_entries(annotation):
            if entry.get("container_flow") and entry["container_flow"] not in container_flows:
                findings.append(_reference_finding("operation", annotation.id, "container_flow", entry["container_flow"], "container_flow", annotation, result))
        for field_name in ("input", "output"):
            for ref in sorted(_extract_refs(annotation.payload.get(field_name))):
                if ref not in data_shapes:
                    findings.append(_reference_finding("operation", annotation.id, field_name, ref, "data_shape", annotation, result))
        for field_name in ("returns", "passes"):
            for ref in sorted(_extract_refs(annotation.payload.get(field_name))):
                if ref not in data_shapes:
                    findings.append(_reference_finding("operation", annotation.id, field_name, ref, "data_shape", annotation, result))
        for entry in _operation_entries(annotation):
            for field_name in ("input", "output", "passes"):
                for ref in sorted(_extract_refs(entry.get(field_name))):
                    if ref not in data_shapes:
                        findings.append(_reference_finding("operation", annotation.id, field_name, ref, "data_shape", annotation, result))

    for annotation in result.persistence:
        if annotation.payload.get("entity") and annotation.payload["entity"] not in entities:
            findings.append(_reference_finding("persistence", annotation.id, "entity", annotation.payload["entity"], "entity", annotation, result))
        if annotation.payload.get("physical_store") and annotation.payload["physical_store"] not in containers:
            findings.append(
                _reference_finding(
                    "persistence",
                    annotation.id,
                    "physical_store",
                    annotation.payload["physical_store"],
                    "container",
                    annotation,
                    result,
                )
            )
    return findings


def _invalid_flow_step_findings(result: ForgeCrawlResult) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for flow in _collection(result.containers, "container_flows"):
        steps = _collection(flow, "steps")
        step_ids = {step.get("id") for step in steps}
        previous_step: dict[str, Any] | None = None
        for step in steps:
            findings.extend(_step_findings("container_flow", flow.get("id"), step, step_ids))
            if (
                previous_step
                and previous_step.get("id") != step.get("id")
                and previous_step.get("container")
                and previous_step.get("container") == step.get("container")
            ):
                findings.append(
                    {
                        "kind": "container_flow",
                        "id": flow.get("id"),
                        "step": step.get("id"),
                        "message": "Adjacent runtime steps in the same container should be merged into one step.",
                    }
                )
            previous_step = step
    operations_by_flow: dict[tuple[str | None, str | None, str | None], list[ForgeAnnotation]] = defaultdict(list)
    for operation in result.operations:
        for entry in _operation_entries(operation):
            operations_by_flow[(operation.container, entry.get("container_flow"), entry.get("local_flow"))].append(operation)
    for (_container, container_flow, local_flow), operations in operations_by_flow.items():
        entries = [
            (operation, entry)
            for operation in operations
            for entry in _operation_entries(operation)
            if entry.get("container_flow") == container_flow and entry.get("local_flow") == local_flow
        ]
        step_ids = {entry.get("local_step") for _operation, entry in entries}
        for operation, entry in entries:
            local_step = dict(entry)
            local_step["id"] = entry.get("local_step")
            for finding in _step_findings("operation", operation.id, local_step, step_ids):
                finding.update({"container_flow": container_flow, "local_flow": local_flow})
                findings.append(finding)
    return findings


def _step_findings(kind: str, owner_id: Any, step: dict[str, Any], step_ids: set[Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    step_id = step.get("id", step.get("step"))
    if "next" in step and "branches" in step:
        findings.append({"kind": kind, "id": owner_id, "step": step_id, "message": "Step must not define both `next` and `branches`."})
    if step.get("next") is not None and step["next"] not in step_ids:
        findings.append({"kind": kind, "id": owner_id, "step": step_id, "field": "next", "reference": step["next"], "message": "Step target does not exist."})
    branches = step.get("branches", [])
    if isinstance(branches, list):
        for branch in branches:
            if isinstance(branch, dict) and branch.get("next") is not None and branch["next"] not in step_ids:
                findings.append(
                    {
                        "kind": kind,
                        "id": owner_id,
                        "step": step_id,
                        "field": "branches.next",
                        "reference": branch["next"],
                        "message": "Branch target does not exist.",
                    }
                )
    return findings


def _operation_entries(annotation: ForgeAnnotation) -> list[dict[str, Any]]:
    if (
        annotation.payload.get("container_flow")
        and annotation.payload.get("local_flow")
        and annotation.payload.get("step") is not None
        and annotation.payload.get("local_step") is not None
    ):
        return [annotation.payload]
    participates_in = annotation.payload.get("participates_in", [])
    if not isinstance(participates_in, list):
        return []
    return [
        item
        for item in participates_in
        if isinstance(item, dict)
        and item.get("container_flow")
        and item.get("local_flow")
        and item.get("step") is not None
        and item.get("local_step") is not None
    ]


def _config_findings(config: CrawlerConfig) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    extension_profiles: dict[str, list[str]] = defaultdict(list)
    for profile in config.profiles:
        for extension in profile.extensions:
            extension_profiles[extension].append(profile.name)
    for extension, profiles in sorted(extension_profiles.items()):
        if len(profiles) > 1:
            findings.append({"extension": extension, "profiles": profiles, "message": "Extension is mapped by multiple comment profiles."})
    return findings


def _annotation_finding(annotation: ForgeAnnotation, result: ForgeCrawlResult, message: str) -> dict[str, Any]:
    return {
        "kind": annotation.kind,
        "id": annotation.id,
        "source": _relative_path(annotation.source, result.workspace_root),
        "line": annotation.line,
        "message": message,
    }


def _reference_finding(
    kind: str,
    owner_id: Any,
    field_name: str,
    reference: Any,
    expected_kind: str,
    annotation: ForgeAnnotation | None = None,
    result: ForgeCrawlResult | None = None,
) -> dict[str, Any]:
    finding = {
        "kind": kind,
        "id": owner_id,
        "field": field_name,
        "reference": reference,
        "expected_kind": expected_kind,
        "message": f"`{reference}` does not resolve to a known {expected_kind}.",
    }
    if annotation is not None and result is not None:
        finding["source"] = _relative_path(annotation.source, result.workspace_root)
        finding["line"] = annotation.line
    return finding


def _ids(items: Any) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {item["id"] for item in items if isinstance(item, dict) and isinstance(item.get("id"), str)}


def _extract_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, str):
        refs.update(re.findall(r"ref\[([a-zA-Z0-9_]+)\]", value))
        return refs
    if isinstance(value, list):
        for item in value:
            refs.update(_extract_refs(item))
        return refs
    if isinstance(value, dict):
        for item in value.values():
            refs.update(_extract_refs(item))
    return refs


def _forge_markdown_docs(forge_root: Path) -> list[Path]:
    return sorted(path for path in forge_root.glob("*.md") if path.is_file())


def _markdown_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return path.stem


def _ignored(path: Path, workspace_root: Path, config: CrawlerConfig) -> bool:
    if any(part in config.ignore_dirs for part in path.parts):
        return True
    relative = _relative_path(path, workspace_root)
    return any(fnmatch.fnmatch(relative, pattern) for pattern in config.ignore_patterns)


def _collection(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _json_safe(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_json_safe(item) for item in value)
    return value


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _normalize_extension(extension: str) -> str:
    if not extension:
        return ""
    return extension if extension.startswith(".") else f".{extension}"


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _relative_path(path: Path, root: Path | None) -> str:
    if root is None:
        return str(path)
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
