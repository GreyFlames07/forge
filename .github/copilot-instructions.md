# Copilot Instructions

## Project Overview

**forge** is a Python project. Test runner: pytest.

Forge is a skills-first Python CLI for V4 system design and delivery. It keeps
C1/C2 architecture central, keeps C3 implementation architecture beside code,
and packages Forge skills for initialized repositories.

## Commands

- `make lint`: run Ruff on `src` and `tests`
- `make typecheck`: run mypy
- `make test`: run pytest
- `make compile`: compile CLI Python modules
- `make build`: sync package resources and build distributions
- `make verify-package`: build and smoke-test the wheel in a fresh venv
- `make smoke-init`: smoke-test `forge init`
- `make check`: run the full local verification path

## Code Quality

### Python Conventions

- Use type hints on all function signatures
- Write docstrings for public functions and classes (Google style)
- Use virtual environments for dependency isolation
- Follow PEP 8 naming: `snake_case` for functions/variables, `PascalCase` for
  classes
- Prefer `pathlib.Path` over `os.path` for file operations
- Use `dataclasses` or `pydantic` for structured data

## Task Management

1. **Plan First**: Write plan with checkable items before starting
2. **Track Progress**: Mark items complete as you go
3. **Verify**: Run tests and demonstrate correctness before marking done
4. **Capture Lessons**: Update lessons file after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
