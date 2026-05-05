"""`forge validate` — lint the spec directory against structural rules."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from cli import common

NAME = "validate"
HELP = "Lint the spec directory for structural and referential errors."
DESCRIPTION = (
    "Validates the spec directory against the Forge v2 structural rules: "
    "presence of required files, ID consistency, referential integrity, "
    "directory layout constraints, required fields, and enum value correctness. "
    "Exits 0 if clean, 1 if any errors are found."
)

# ---------------------------------------------------------------------------
# Node kinds that live inside system-level registry directories
# ---------------------------------------------------------------------------
REGISTRY_DIR_NAMES: tuple[str, ...] = (
    "types", "errors", "policies", "contracts",
    "integrations", "interactions", "flows", "constants",
)

# Implementation flat-file names (the only files allowed inside implementation/)
IMPLEMENTATION_FILES: frozenset[str] = frozenset(
    {"datastores.yaml", "tests.yaml", "environments.yaml", "deployments.yaml"}
)

# Required fields for every node
REQUIRED_FIELDS: tuple[str, ...] = ("id", "type", "name", "status")

# Fields that look like cross-references (by suffix / exact name)
_REF_SUFFIXES: tuple[str, ...] = (
    "_id", "_ref", "_module", "_system", "_domain",
    "_operation", "_contract", "_integration", "_interaction",
    "_flow", "_datastore", "_type", "_error",
)
_REF_EXACT: frozenset[str] = frozenset(
    {"producer", "consumer", "caller", "callee", "owner"}
)


# ===========================================================================
# Argparse registration
# ===========================================================================

def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help=HELP, description=DESCRIPTION)
    common.add_spec_dir_arg(p)
    p.add_argument(
        "--warn-refs", action="store_true",
        help="Emit unresolvable cross-references as warnings instead of errors.",
    )
    p.set_defaults(handler=run)


# ===========================================================================
# Entry point
# ===========================================================================

def run(args: argparse.Namespace) -> int:
    idx, rc = common.load_index(args.spec_dir)
    if rc != 0:
        return rc

    spec_dir: Path = idx.spec_dir
    issues: list[str] = []   # "E file:path  message" or "W file:path  message"

    _check_conception(spec_dir, issues)
    _check_singleton_yaml_files(spec_dir, issues)
    _check_id_path_alignment(idx, issues)
    _check_duplicate_ids(spec_dir, idx, issues)
    _check_registry_and_impl_placement(spec_dir, issues)
    _check_element_files(spec_dir, issues)
    _check_required_fields(idx, issues)
    _check_enum_values(idx, issues)

    ref_tag = "W" if args.warn_refs else "E"
    _check_referential_integrity(idx, issues, ref_tag=ref_tag)

    if not issues:
        print("validate: OK — no issues found.")
        return 0

    errors = [i for i in issues if i.startswith("E ")]
    warnings = [i for i in issues if i.startswith("W ")]

    for line in issues:
        print(line)

    print()
    summary_parts = []
    if errors:
        summary_parts.append(f"{len(errors)} error(s)")
    if warnings:
        summary_parts.append(f"{len(warnings)} warning(s)")
    print(f"validate: {', '.join(summary_parts)}")

    return 1 if errors else 0


# ===========================================================================
# Rule implementations
# ===========================================================================

# --- Rule 1: conception.yaml must exist at spec root ----------------------

def _check_conception(spec_dir: Path, issues: list[str]) -> None:
    conception = spec_dir / "conception.yaml"
    if not conception.is_file():
        issues.append(f"E file:{conception}  conception.yaml is missing from spec root")


# --- Rule 2: system.yaml / domain.yaml / module.yaml are sole in their dir

def _check_singleton_yaml_files(spec_dir: Path, issues: list[str]) -> None:
    for singleton_name in ("system.yaml", "domain.yaml", "module.yaml"):
        for found in spec_dir.rglob(singleton_name):
            parent = found.parent
            siblings = list(parent.glob(singleton_name))
            # This should always be 1 (the file itself) — belt-and-suspenders.
            if len(siblings) > 1:
                issues.append(
                    f"E file:{found}  multiple '{singleton_name}' files in {parent}"
                )
            # Check that it is the *sole* .yaml file defining a structural node
            # — i.e. its directory doesn't also contain another system/domain/module yaml.
            for other_name in {"system.yaml", "domain.yaml", "module.yaml"} - {singleton_name}:
                if (parent / other_name).exists():
                    issues.append(
                        f"E file:{found}  directory {parent} contains both "
                        f"'{singleton_name}' and '{other_name}'"
                    )


# --- Rule 3: every node id field matches its path-derived ID ---------------

def _check_id_path_alignment(idx: Any, issues: list[str]) -> None:
    """Compare the 'id' field in each entry's data against the index key."""
    for entry_id, entry in idx.entries.items():
        if not isinstance(entry.data, dict):
            continue
        declared_id = entry.data.get("id")
        if declared_id is None:
            continue  # handled by required-fields rule
        if declared_id != entry_id:
            file_hint = f"file:{entry.file}  " if entry.file else ""
            issues.append(
                f"E {file_hint}id mismatch: declared '{declared_id}' "
                f"but index key is '{entry_id}'"
            )


# --- Rule 4: referential integrity -----------------------------------------

def _looks_like_ref_field(field_name: str) -> bool:
    """Heuristic: does this field name look like a cross-reference?"""
    if field_name in _REF_EXACT:
        return True
    for suffix in _REF_SUFFIXES:
        if field_name.endswith(suffix):
            return True
    return False


def _collect_string_refs(data: Any, refs: list[str]) -> None:
    """Walk data recursively, collecting strings from ref-looking fields."""
    if isinstance(data, dict):
        for k, v in data.items():
            if _looks_like_ref_field(k):
                if isinstance(v, str) and "." in v:
                    refs.append(v)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, str) and "." in item:
                            refs.append(item)
            _collect_string_refs(v, refs)
    elif isinstance(data, list):
        for item in data:
            _collect_string_refs(item, refs)


def _check_referential_integrity(idx: Any, issues: list[str], ref_tag: str) -> None:
    for entry_id, entry in idx.entries.items():
        if not isinstance(entry.data, dict):
            continue
        refs: list[str] = []
        _collect_string_refs(entry.data, refs)
        for ref in refs:
            if ref not in idx.entries:
                file_hint = f"file:{entry.file}  " if entry.file else ""
                issues.append(
                    f"{ref_tag} {file_hint}unresolved reference '{ref}' "
                    f"in entry '{entry_id}'"
                )


# --- Rule 5: no duplicate derived IDs across files -------------------------

def _check_duplicate_ids(spec_dir: Path, idx: Any, issues: list[str]) -> None:
    seen: dict[str, list[Path]] = defaultdict(list)
    for entry_id, entry in idx.entries.items():
        if entry.file:
            seen[entry_id].append(entry.file)
    for eid, files in seen.items():
        if len(files) > 1:
            file_list = ", ".join(str(f) for f in files)
            issues.append(
                f"E  duplicate derived id '{eid}' from files: {file_list}"
            )


# --- Rule 6: element files contain only inline properties and operations ---

def _check_element_files(spec_dir: Path, issues: list[str]) -> None:
    """
    Element files sit at module/<element>.yaml depth.
    They must only contain top-level keys 'properties' and/or 'operations'
    (plus id/name/type/status/description and similar metadata).
    No nested YAML documents (multi-doc separator ---) are allowed that
    define non-property/operation nodes.
    """
    # Structural node file names — these are not element files.
    structural = {"system.yaml", "domain.yaml", "module.yaml"}

    for yaml_file in spec_dir.rglob("*.yaml"):
        rel = yaml_file.relative_to(spec_dir)
        parts = rel.parts
        # Element files are at depth >= 3: <system>/<domain>/<module>/<element>.yaml
        # or inside registry dirs they're at <system>/types/TypeName.yaml etc.
        # We focus on files that are NOT structural singletons and NOT inside
        # known registry or implementation directories.
        if yaml_file.name in structural:
            continue
        if _is_under_registry_or_impl(yaml_file, spec_dir):
            continue
        if len(parts) < 4:
            continue  # too shallow to be an element

        # Read as multi-document stream and look for forbidden top-level keys.
        try:
            with yaml_file.open("r", encoding="utf-8") as f:
                raw = f.read()
        except OSError:
            continue

        docs = list(yaml.safe_load_all(raw))
        # If more than one document, extra docs must only be properties/operations.
        ELEMENT_ALLOWED_KINDS = {"property", "operation", None}
        for i, doc in enumerate(docs[1:], start=2):
            if not isinstance(doc, dict):
                continue
            doc_kind = doc.get("kind") or doc.get("type")
            if doc_kind not in ELEMENT_ALLOWED_KINDS:
                issues.append(
                    f"E file:{yaml_file}  document {i} has kind '{doc_kind}'; "
                    "element files may only contain property/operation sub-documents"
                )


def _is_under_registry_or_impl(path: Path, spec_dir: Path) -> bool:
    """Return True if path is inside a registry dir or implementation dir."""
    try:
        rel_parts = path.relative_to(spec_dir).parts
    except ValueError:
        return False
    for part in rel_parts[:-1]:  # exclude filename itself
        if part in REGISTRY_DIR_NAMES or part == "implementation":
            return True
    return False


# --- Rule 7 & 8: registry dirs and implementation/ placement ---------------

def _check_registry_and_impl_placement(spec_dir: Path, issues: list[str]) -> None:
    """
    Registry dirs (types/, errors/, etc.) and implementation/ must exist
    only directly under a system directory (identified by containing system.yaml).
    """
    system_dirs: set[Path] = {
        f.parent for f in spec_dir.rglob("system.yaml")
    }

    # Find all occurrences of registry dir names
    for dir_name in REGISTRY_DIR_NAMES:
        for found_dir in spec_dir.rglob(dir_name):
            if not found_dir.is_dir():
                continue
            parent = found_dir.parent
            if parent not in system_dirs:
                issues.append(
                    f"E file:{found_dir}  '{dir_name}/' must be directly under "
                    f"a system directory (one with system.yaml); found under {parent}"
                )

    # Check implementation/ placement and contents
    for impl_dir in spec_dir.rglob("implementation"):
        if not impl_dir.is_dir():
            continue
        parent = impl_dir.parent
        if parent not in system_dirs:
            issues.append(
                f"E file:{impl_dir}  'implementation/' must be directly under "
                f"a system directory; found under {parent}"
            )
        # Check that implementation/ contains only the four allowed flat files
        for child in impl_dir.iterdir():
            if child.name not in IMPLEMENTATION_FILES:
                issues.append(
                    f"E file:{child}  unexpected file in implementation/; "
                    f"only {sorted(IMPLEMENTATION_FILES)} are allowed"
                )


# --- Rule 9: enum values must match framework enum definitions --------------

def _check_enum_values(idx: Any, issues: list[str]) -> None:
    framework_enums: dict[str, dict] = {}
    if hasattr(idx, "framework") and isinstance(idx.framework, dict):
        framework_enums = idx.framework.get("enums") or {}

    if not framework_enums:
        return  # no enum definitions to check against

    # Build set of known enum values per enum name
    enum_values: dict[str, set[str]] = {}
    for enum_name, enum_def in framework_enums.items():
        if isinstance(enum_def, dict):
            vals = enum_def.get("values") or []
        elif isinstance(enum_def, list):
            vals = enum_def
        else:
            continue
        enum_values[enum_name] = {str(v) for v in vals}

    # Walk all entries and check string fields whose name ends with a known enum name
    for entry_id, entry in idx.entries.items():
        if not isinstance(entry.data, dict):
            continue
        _check_enum_in_data(entry.data, enum_values, entry, entry_id, issues)


def _check_enum_in_data(
    data: Any,
    enum_values: dict[str, set[str]],
    entry: Any,
    entry_id: str,
    issues: list[str],
) -> None:
    if isinstance(data, dict):
        for field_name, value in data.items():
            field_lower = field_name.lower()
            for enum_name, valid_values in enum_values.items():
                if field_lower.endswith(enum_name.lower()) or field_lower == enum_name.lower():
                    if isinstance(value, str) and value not in valid_values:
                        file_hint = f"file:{entry.file}  " if entry.file else ""
                        issues.append(
                            f"E {file_hint}entry '{entry_id}' field '{field_name}' "
                            f"has value '{value}' not in enum {enum_name}: "
                            f"{sorted(valid_values)}"
                        )
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str) and item not in valid_values:
                                file_hint = f"file:{entry.file}  " if entry.file else ""
                                issues.append(
                                    f"E {file_hint}entry '{entry_id}' field '{field_name}' "
                                    f"has value '{item}' not in enum {enum_name}: "
                                    f"{sorted(valid_values)}"
                                )
            _check_enum_in_data(value, enum_values, entry, entry_id, issues)
    elif isinstance(data, list):
        for item in data:
            _check_enum_in_data(item, enum_values, entry, entry_id, issues)


# --- Rule 10: required fields per node type --------------------------------

def _check_required_fields(idx: Any, issues: list[str]) -> None:
    for entry_id, entry in idx.entries.items():
        if not isinstance(entry.data, dict):
            continue
        for field in REQUIRED_FIELDS:
            if field not in entry.data:
                file_hint = f"file:{entry.file}  " if entry.file else ""
                issues.append(
                    f"E {file_hint}entry '{entry_id}' is missing required field '{field}'"
                )
