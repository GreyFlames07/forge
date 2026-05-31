from __future__ import annotations

import importlib.resources
import json
import shutil
import tomllib
from pathlib import Path

import yaml

from cli import __version__
from cli.commands.audit import _edge_label, _state_machine_partitions, render_live_audit_html
from cli.forge import main

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ROOT = REPO_ROOT / "examples" / "forge_v2_ordering_example"
COMPLEX_EXAMPLE_ROOT = REPO_ROOT / "examples" / "forge_v2_fulfillment_control_example"


def test_package_version_matches_pyproject() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert __version__ == pyproject["project"]["version"]


def test_vertical_context_json(capsys) -> None:
    assert main(["context", "--project-dir", str(EXAMPLE_ROOT), "--vertical", "place_order"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["target"]["type"] == "vertical"
    assert payload["target"]["id"] == "place_order"
    assert payload["artifacts"]["runtime_flows"][0]["id"] == "place_order_runtime"
    assert "ordering_api" in payload["implementation_scope"]["involved_containers"]


def test_container_context_yaml(capsys) -> None:
    assert main(
        [
            "context",
            "--project-dir",
            str(EXAMPLE_ROOT),
            "--container",
            "ordering_api",
            "--format",
            "yaml",
        ]
    ) == 0
    output = capsys.readouterr().out
    assert "# Context: ordering_api" in output
    payload = yaml.safe_load("\n".join(line for line in output.splitlines() if not line.startswith("# ")))
    assert payload["artifacts"]["runtime_container"]["id"] == "ordering_api"
    assert payload["artifacts"]["container"]["id"] == "ordering_api"


def test_component_context_json(capsys) -> None:
    assert main(
        [
            "context",
            "--project-dir",
            str(EXAMPLE_ROOT),
            "--component",
            "payment_service",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["target"]["type"] == "component"
    assert payload["artifacts"]["component"]["id"] == "payment_service"
    assert payload["artifacts"]["container"]["id"] == "ordering_api"


def test_flow_context_markdown(capsys) -> None:
    assert main(
        [
            "context",
            "--project-dir",
            str(EXAMPLE_ROOT),
            "--flow",
            "place_order_runtime",
            "--format",
            "md",
        ]
    ) == 0
    output = capsys.readouterr().out
    assert "Context: place_order_runtime" in output
    assert "runtime_flow:" in output


def test_init_scaffolds_traversable_repo(tmp_path: Path, capsys) -> None:
    root = tmp_path / "demo"
    assert main(["init", "--root", str(root), "--name", "Demo System", "--id", "demo_system", "--no-animation"]) == 0
    forge_root = root / "forge"
    output = capsys.readouterr().out
    assert "Forge initialized at" in output
    assert "forge workspace:" in output
    assert "Start With Skills" in output
    assert "Use Forge In This Order" in output
    assert "How To Get The Most Out Of The Framework" in output
    assert "forge/skills/forge-schema/SKILL.md" in output
    assert "forge/skills/forge-review/SKILL.md" in output
    assert "forge/skills/forge-security/SKILL.md" in output
    assert "Run `forge-review` and `forge-security` before building." in output
    assert "the CLI supports the active skill" in output
    assert "CLI Support Workflow" in output
    assert "forge audit --project-dir" in output
    assert (forge_root / "system.yaml").exists()
    assert (forge_root / "runtime.yaml").exists()
    assert (forge_root / "SCHEMA_REFERENCE_V3.md").exists()
    assert (forge_root / "FRAMEWORK_V3.md").exists()
    assert (forge_root / "USING_FORGE.md").exists()
    assert (forge_root / "skills" / "forge-schema" / "SKILL.md").exists()
    assert "dist/" in (root / ".gitignore").read_text(encoding="utf-8")
    assert "*.egg-info/" in (root / ".gitignore").read_text(encoding="utf-8")
    codex_skill = root / ".codex" / "skills" / "forge-build"
    assert codex_skill.is_dir()
    assert not codex_skill.is_symlink()
    assert (codex_skill / "SKILL.md").exists()
    assert (codex_skill / "coding_agent_skills_reference").is_symlink()
    surfaced_skill = (codex_skill / "SKILL.md").read_text(encoding="utf-8")
    assert "../../../forge/SCHEMA_REFERENCE_V3.md" in surfaced_skill
    assert "../../../forge/USING_FORGE.md" in surfaced_skill
    assert "../forge-schema/SKILL.md" in surfaced_skill
    assert (root / ".claude" / "skills" / "forge-schema" / "SKILL.md").exists()
    assert (root / ".agents" / "skills" / "forge-review" / "SKILL.md").exists()
    rewritten_skill = (forge_root / "skills" / "forge-schema" / "SKILL.md").read_text(encoding="utf-8")
    assert "../../SCHEMA_REFERENCE_V3.md" in rewritten_skill
    assert "../../USING_FORGE.md" in rewritten_skill
    usage_doc = (forge_root / "USING_FORGE.md").read_text(encoding="utf-8")
    assert "Forge is **skills-first**." in usage_doc
    assert "Use Forge In This Order" in usage_doc
    assert "Skill Roles" in usage_doc
    assert main(["context", "--project-dir", str(root), "--system", "--format", "json"]) == 0
    context_output = capsys.readouterr().out
    payload = json.loads(context_output)
    assert payload["target"]["type"] == "system"
    assert payload["target"]["id"] == "demo_system"


def test_packaged_init_docs_exist() -> None:
    package_resources = importlib.resources.files("cli").joinpath("resources")
    assert package_resources.joinpath("SCHEMA_REFERENCE_V3.md").is_file()
    assert package_resources.joinpath("FRAMEWORK_V3.md").is_file()
    assert package_resources.joinpath("skills", "forge-schema", "SKILL.md").is_file()
    assert package_resources.joinpath("skills", "forge-build", "SKILL.md").is_file()


def test_packaged_skill_frontmatter_is_valid_yaml() -> None:
    package_skills = importlib.resources.files("cli").joinpath("resources", "skills")
    for skill_file in package_skills.glob("forge-*/SKILL.md"):
        text = skill_file.read_text(encoding="utf-8")
        _, frontmatter, _ = text.split("---", 2)
        payload = yaml.safe_load(frontmatter)
        assert isinstance(payload, dict), f"{skill_file} frontmatter must parse to a mapping"
        assert payload.get("name"), f"{skill_file} frontmatter must include a name"
        assert payload.get("description"), f"{skill_file} frontmatter must include a description"


def test_audit_generates_html(tmp_path: Path, capsys) -> None:
    output = tmp_path / "forge-audit.html"
    assert main(
        [
            "audit",
            "--project-dir",
            str(EXAMPLE_ROOT),
            "--artifact",
            "--output",
            str(output),
            "--no-open",
        ]
    ) == 0
    text = output.read_text(encoding="utf-8")
    assert "Forge Audit" in text
    assert "class=\"subnav\"" in text
    assert 'id="overview"' in text
    assert '>Overview<' in text
    assert "system-overview" in text
    assert "runtime-overview" in text
    assert "data-overview" in text
    assert "deployment-overview" in text
    assert "container-ordering_api" in text
    assert "artisan_goods_marketplace / Flow: place_order" in text
    assert "High-level flow with nested runtime and component realization." in text
    assert "place_order_runtime" in text
    assert "&quot;order_id&quot;: &quot;string&quot;" in text
    assert "&quot;payment_status&quot;: &quot;enum[initiated, authorized, failed]&quot;" in text
    assert 'id="data-item-order"' in text
    assert "Early State" in text
    assert "Data Shape" in text
    assert "Persistent Shape" in text


def test_complex_vertical_context_json(capsys) -> None:
    assert (
        main(
            [
                "context",
                "--project-dir",
                str(COMPLEX_EXAMPLE_ROOT),
                "--vertical",
                "recover_inventory_shortage",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["target"]["type"] == "vertical"
    assert payload["target"]["id"] == "recover_inventory_shortage"
    assert payload["artifacts"]["runtime_flows"][0]["id"] == "recover_inventory_shortage_runtime"
    assert "orchestration_worker" in payload["implementation_scope"]["involved_containers"]


def test_complex_audit_generates_html(tmp_path: Path, capsys) -> None:
    output = tmp_path / "forge-audit-complex.html"
    assert main(
        [
            "audit",
            "--project-dir",
            str(COMPLEX_EXAMPLE_ROOT),
            "--artifact",
            "--output",
            str(output),
            "--no-open",
        ]
    ) == 0
    text = output.read_text(encoding="utf-8")
    assert "place_fulfillment_order_runtime" in text
    assert "recover_inventory_shortage_runtime" in text
    assert "process_return_and_refund_runtime" in text
    assert "container-orchestration_api" in text
    assert "container-orchestration_worker" in text
    assert 'id="data-item-shortage_case"' in text
    assert "&quot;resolution_status&quot;: &quot;enum[awaiting_recovery, rerouted, partial_shipment, canceled, failed]&quot;" in text


def test_context_requires_explicit_scope(capsys) -> None:
    assert main(["context", "--project-dir", str(EXAMPLE_ROOT)]) == 1
    output = capsys.readouterr().out
    assert "No context target selected." in output
    assert "Start from the active skill" in output


def test_schema_validation_reports_broken_references(tmp_path: Path, capsys) -> None:
    broken_root = tmp_path / "broken-example"
    shutil.copytree(EXAMPLE_ROOT, broken_root)
    broken_vertical = broken_root / "verticals" / "place_order.yaml"
    broken_vertical.write_text(
        broken_vertical.read_text(encoding="utf-8").replace("orders_db", "missing_orders_db", 1),
        encoding="utf-8",
    )
    assert main(["context", "--project-dir", str(broken_root), "--system"]) == 1
    output = capsys.readouterr().out
    assert "Schema validation failed" in output
    assert "vertical `place_order` runtime_containers references unknown id `missing_orders_db`." in output


def test_component_flow_terminal_outgoing_is_valid_and_rendered(tmp_path: Path) -> None:
    copied_root = tmp_path / "terminal-outgoing-example"
    shutil.copytree(EXAMPLE_ROOT, copied_root)

    container_path = copied_root / "containers" / "ordering_api.yaml"
    container_payload = yaml.safe_load(container_path.read_text(encoding="utf-8"))
    terminal_step = container_payload["container"]["component_flows"][0]["steps"][-1]
    terminal_step["outgoing"] = "ref[order_confirmation_response]"
    container_path.write_text(yaml.safe_dump(container_payload, sort_keys=False), encoding="utf-8")

    html = render_live_audit_html(copied_root)
    assert "Outgoing: ref[order_confirmation_response]" in html


def test_live_audit_rerenders_from_current_schema(tmp_path: Path) -> None:
    copied_root = tmp_path / "example"
    shutil.copytree(EXAMPLE_ROOT, copied_root)

    initial_html = render_live_audit_html(copied_root)
    assert "purchase through its lifecycle." in initial_html

    persistent_shape = copied_root / "persistent_shapes" / "order.yaml"
    persistent_shape.write_text(
        persistent_shape.read_text(encoding="utf-8").replace(
            "Persisted order shape representing a customer's purchase through its lifecycle.",
            "Updated live schema description for audit refresh.",
            1,
        ),
        encoding="utf-8",
    )

    updated_html = render_live_audit_html(copied_root)
    assert "Updated live schema description for audit refresh." in updated_html
    assert "purchase through its lifecycle." not in updated_html


def test_live_audit_renders_cyclic_persistent_state_machine(tmp_path: Path) -> None:
    copied_root = tmp_path / "cyclic-example"
    shutil.copytree(EXAMPLE_ROOT, copied_root)

    persistent_shape = copied_root / "persistent_shapes" / "order.yaml"
    persistent_shape.write_text(
        persistent_shape.read_text(encoding="utf-8").replace(
            "        - from: confirmed\n          to: cancelled\n          condition: The order is cancelled before fulfillment completes.\n",
            "        - from: confirmed\n          to: cancelled\n          condition: The order is cancelled before fulfillment completes.\n"
            "        - from: cancelled\n          to: confirmed\n          condition: The cancellation is reversed before fulfillment resumes.\n",
            1,
        ),
        encoding="utf-8",
    )

    partitions = _state_machine_partitions(
        ["pending_payment", "confirmed", "fulfilled", "cancelled", "failed"],
        [
            {"from": "pending_payment", "to": "confirmed", "condition": "Payment is authorized successfully."},
            {"from": "pending_payment", "to": "failed", "condition": "Payment authorization fails."},
            {"from": "confirmed", "to": "fulfilled", "condition": "Fulfillment is completed successfully."},
            {"from": "confirmed", "to": "cancelled", "condition": "The order is cancelled before fulfillment completes."},
            {"from": "cancelled", "to": "confirmed", "condition": "The cancellation is reversed before fulfillment resumes."},
        ],
    )
    assert partitions["pending_payment"] == 0
    assert partitions["confirmed"] == 1
    assert partitions["cancelled"] == 2

    html = render_live_audit_html(copied_root)
    assert "Forge Audit" in html
    assert "Persistent lifecycle states and transition conditions." in html


def test_edge_label_caps_descriptions_to_five_words() -> None:
    assert _edge_label("Order record persisted for reconciliation and downstream fulfillment workflows.") == (
        "Order record persisted for reconciliation"
    )
    assert _edge_label("depends on") == "depends on"
