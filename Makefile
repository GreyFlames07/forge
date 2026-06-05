PYTHON ?= .venv/bin/python
PYTEST ?= .venv/bin/pytest
RUFF ?= .venv/bin/ruff
MYPY ?= .venv/bin/mypy
TWINE ?= .venv/bin/twine

.PHONY: clean clean-package-resources sync-package-resources lint typecheck test compile build check-dist verify-package smoke-init check

clean:
	rm -rf build dist /tmp/forge-dist

clean-package-resources:
	find src/cli/resources/skills -type d -name '__pycache__' -prune -exec rm -rf {} +
	find src/cli/resources/skills -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

sync-package-resources:
	$(PYTHON) scripts/sync_package_resources.py

test:
	$(PYTEST) -q

lint:
	$(RUFF) check src tests

typecheck:
	$(MYPY)

compile:
	$(PYTHON) -m compileall -q src/cli/__init__.py src/cli/__main__.py src/cli/common.py src/cli/forge.py src/cli/yaml_io.py src/cli/commands

build: clean-package-resources sync-package-resources
	rm -rf build dist
	$(PYTHON) -m build

check-dist: build
	$(TWINE) check dist/*

verify-package: clean-package-resources sync-package-resources
	rm -rf build /tmp/forge-dist
	$(PYTHON) -m build --outdir /tmp/forge-dist
	$(TWINE) check /tmp/forge-dist/*
	tmpvenv=$$(mktemp -d); \
	tmpdir=$$(mktemp -d); \
	$(PYTHON) -m venv "$$tmpvenv"; \
	"$$tmpvenv/bin/python" -m ensurepip --upgrade >/dev/null; \
	"$$tmpvenv/bin/python" -m pip install /tmp/forge-dist/*.whl >/dev/null; \
	"$$tmpvenv/bin/forge" --help >/dev/null; \
	"$$tmpvenv/bin/forge" init --root "$$tmpdir" --name "Wheel Smoke Project" --id wheel_smoke_project --no-animation >/dev/null; \
	test -f "$$tmpdir/business-plan.md"; \
	test -f "$$tmpdir/forge/SCHEMA_REFERENCE_V4.md"; \
	test -f "$$tmpdir/forge/FRAMEWORK_V4.md"; \
	test -f "$$tmpdir/forge/decisions.yaml"; \
	test -f "$$tmpdir/forge/skills/forge-business/SKILL.md"; \
	test -f "$$tmpdir/forge/skills/forge-schema/SKILL.md"; \
	test -f "$$tmpdir/forge/skills/forge-hydrate/SKILL.md"

smoke-init:
	tmpdir=$$(mktemp -d); \
	.venv/bin/forge init --root "$$tmpdir" --name "Smoke Project" --id smoke_project --no-animation >/dev/null; \
	test -f "$$tmpdir/business-plan.md"; \
	test -f "$$tmpdir/forge/USING_FORGE.md"; \
	test -f "$$tmpdir/forge/decisions.yaml"; \
	test -f "$$tmpdir/forge/skills/forge-business/SKILL.md"; \
	test -f "$$tmpdir/forge/skills/forge-hydrate/SKILL.md"; \
	test -f "$$tmpdir/forge/skills/forge-build/SKILL.md"; \
	grep -q "Start With Skills" "$$tmpdir/forge/USING_FORGE.md"

check: lint typecheck test compile check-dist verify-package smoke-init
