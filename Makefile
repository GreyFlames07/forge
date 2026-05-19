PYTHON ?= .venv/bin/python
PYTEST ?= .venv/bin/pytest
RUFF ?= .venv/bin/ruff
MYPY ?= .venv/bin/mypy
TWINE ?= .venv/bin/twine

.PHONY: clean lint typecheck test compile build check-dist verify-package smoke-init check

clean:
	rm -rf build dist /tmp/forge-dist

test:
	$(PYTEST) -q

lint:
	$(RUFF) check src tests

typecheck:
	$(MYPY)

compile:
	$(PYTHON) -m compileall -q src

build:
	rm -rf dist
	$(PYTHON) -m build

check-dist: build
	$(TWINE) check dist/*

verify-package:
	rm -rf /tmp/forge-dist
	$(PYTHON) -m build --outdir /tmp/forge-dist
	$(TWINE) check /tmp/forge-dist/*
	tmpvenv=$$(mktemp -d); \
	$(PYTHON) -m venv "$$tmpvenv"; \
	"$$tmpvenv/bin/python" -m ensurepip --upgrade >/dev/null; \
	"$$tmpvenv/bin/python" -m pip install /tmp/forge-dist/*.whl >/dev/null; \
	"$$tmpvenv/bin/forge" --help >/dev/null

smoke-init:
	tmpdir=$$(mktemp -d); \
	.venv/bin/forge init --root "$$tmpdir" --name "Smoke Project" --id smoke_project --no-animation >/dev/null; \
	test -f "$$tmpdir/docs/USING_FORGE.md"; \
	grep -q "Start With Skills" "$$tmpdir/docs/USING_FORGE.md"

check: lint typecheck test compile check-dist verify-package smoke-init
