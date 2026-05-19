# Releasing Forge

This document is for maintainers publishing Forge artifacts.

## Pre-Release Checks

Run the full local verification path before cutting a release:

```bash
make check
```

That verifies:

- linting
- type checking
- unit and integration-style tests
- Python bytecode compilation
- source and wheel builds
- clean-wheel install smoke test
- `forge init` onboarding smoke test

## Release Order

1. Update docs and examples if the framework changed.
2. Run `make check`.
3. Bump `project.version` in `pyproject.toml`.
4. Build release artifacts:

```bash
.venv/bin/python -m build
```

5. Validate distribution metadata:

```bash
make check-dist
```

6. Validate the installed wheel in a clean environment:

```bash
make verify-package
```

7. Create a GitHub release with tag `v<project.version>`.
8. Let `.github/workflows/release.yml` publish to PyPI through trusted publishing.
9. Treat the release as valid only if the skills, CLI, and audit artifact still align.

## PyPI Trusted Publishing

The publish workflow assumes PyPI trusted publishing is configured for this repository.

On the PyPI project settings page, add a trusted publisher for:

- owner: this GitHub repository owner
- repository: `forge`
- workflow: `.github/workflows/release.yml`
- environment: `pypi`

Until that is configured in PyPI, the GitHub release workflow will build and
verify artifacts correctly but PyPI will reject the final publish step.
