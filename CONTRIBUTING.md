# Contributing

Thanks for your interest. forge is a small, opinionated spec-driven agent toolkit. Contributions are welcome — the repo is set up to make the path deterministic.

## Ground rules

1. **No direct pushes to `main`.** Every change lands via pull request. Branch protection enforces this.
2. **PRs require approval from a code owner** before they can merge. See `.github/CODEOWNERS`.
3. **CI must pass.** The `pytest` job runs on every PR; red CI blocks merge.
4. **Linear history on `main`.** We use squash or rebase merges, not merge commits.
5. **Conventional Commits** for commit messages (see below).

## Workflow

```bash
# 1. Fork (external contributors) or clone.
git clone https://github.com/GreyFlames07/forge.git
cd forge

# 2. Create a working branch from main. Use a descriptive name.
git checkout -b feat/my-change          # for new features
git checkout -b fix/broken-audit         # for bug fixes
git checkout -b docs/readme-cleanup      # for doc-only changes

# 3. Set up local dev environment.
uv venv --python 3.13 .venv
uv pip install -e . pytest

# 4. Make changes. Test locally.
.venv/bin/pytest

# 5. Commit using Conventional Commits.
git add .
git commit -m "feat(cli): add forge find --json flag"

# 6. Push and open a PR.
git push -u origin feat/my-change
gh pr create --fill
```

## Commit message convention

[Conventional Commits](https://www.conventionalcommits.org/). Format:

```
<type>(<scope>): <short summary>

<optional body>

<optional footer — BREAKING CHANGE, Refs, etc.>
```

**Types:**

| Type | Use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code change with no behaviour change |
| `test` | Add or fix tests |
| `chore` | Tooling, build, non-code infra |
| `ci` | CI configuration |
| `perf` | Performance improvement |
| `style` | Formatting only (no semantic change) |

**Scope** is the affected area: `cli`, `skills/forge-discover`, `schemas/l2`, `tests`, `docs`, etc. Omit if change is repo-wide.

**Breaking changes** get a `!` and a `BREAKING CHANGE:` footer:

```
feat(cli)!: rename forge init --spec-subdir to --spec-dir

BREAKING CHANGE: The --spec-subdir flag has been renamed. Update any
wrapper scripts to use --spec-dir instead.
```

## PR requirements

Every PR needs:

1. A clear summary (see `.github/pull_request_template.md`).
2. All test-plan checkboxes ticked.
3. Green CI (`pytest` job passes).
4. `CHANGELOG.md` updated under the `Unreleased` section for any user-visible change.
5. At least one approving review from a code owner.

## Solo-maintainer escape hatch

This repo currently has one code owner. For PRs authored by the owner, GitHub still requires an approving review (you can't approve your own PR). Three valid paths:

1. **Request review from another collaborator** — the cleanest path if a second trusted reviewer exists.
2. **Admin merge** — `gh pr merge --admin` bypasses the approval rule. Reserved for solo-maintainer flows; every admin merge should be justified in the PR body.
3. **Pair-review via comment** — the owner leaves a written self-review in a PR comment explaining what was checked, then admin-merges. Serves as an audit trail.

External contributors' PRs always require code-owner approval — no bypass.

## Testing expectations

- Run `.venv/bin/pytest` locally before pushing.
- New features add tests under `tests/`.
- Skill changes (SKILL.md, framework.md) don't have direct tests but should be smoke-tested by running the affected skill in a Claude Code / Codex session against the `src/example/` fixture.
- Schema changes (L0–L5 templates) require updating both the schema doc and the matching validation rules in `src/cli/walker.py` or wherever the schema is consumed.

## Release process

1. Update `CHANGELOG.md` — move `Unreleased` items into a new version section with today's date.
2. Bump version in `pyproject.toml`.
3. Commit: `chore(release): 0.X.Y`.
4. Tag: `git tag v0.X.Y && git push --tags`.
5. `gh release create v0.X.Y --generate-notes`.

## Reporting issues

Use the templates at `.github/ISSUE_TEMPLATE/`. Security issues go through `SECURITY.md` (do not open public issues for vulnerabilities).

## Code of conduct

Be a decent human. No specific CoC is enforced yet — standard expectations apply.
