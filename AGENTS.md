# AGENTS.md

**Project**: forge | **Language**: Python | **Package Manager**: Not detected

## Commands

No commands detected. Add build/test/lint scripts to your project.

## Code Style

### Python Conventions

- Use type hints on all function signatures
- Write docstrings for public functions and classes (Google style)
- Use virtual environments for dependency isolation
- Follow PEP 8 naming: `snake_case` for functions/variables, `PascalCase` for
  classes
- Prefer `pathlib.Path` over `os.path` for file operations
- Use `dataclasses` or `pydantic` for structured data

## Testing

- **Test Runner**: pytest
- Write tests for new functionality before marking tasks complete
- Run the full test suite before committing

## Git Workflow

- Use conventional commit messages (feat:, fix:, chore:, docs:)
- Create feature branches for new work
- Run tests and linting before committing

## Gofer Pipeline

This project uses Gofer for spec-driven development. Run `/0_business_scenario` to start the pipeline (research -> specify -> plan -> tasks -> implement -> validate). Artifacts in `.specify/specs/{feature}/`.

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
