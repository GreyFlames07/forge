# Copilot Instructions

## Project Overview

**forge** is a Python project. Test runner: pytest.

## Gofer Pipeline

This project uses Gofer for spec-driven development. Run `/0_business_scenario` to start the full pipeline: research -> specify -> plan -> tasks -> implement -> validate.

Key commands: `/1_gofer_research`, `/2_gofer_specify`, `/3_gofer_plan`, `/4_gofer_tasks`, `/5_gofer_implement`, `/6_gofer_validate`. Use `/7_gofer_save` and `/8_gofer_resume` for session continuity. Artifacts in `.specify/specs/{feature}/`.

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
