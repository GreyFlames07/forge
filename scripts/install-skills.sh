#!/usr/bin/env bash
# install-skills.sh — wire up forge skills and CLI for agent runtimes.
#
# Creates symlinks so:
#   - Claude Code finds the skills at ~/.claude/skills/<name>
#   - agentskills.io-compatible clients (VS Code Copilot, Cursor, etc.) find
#     them at ~/.agents/skills/<name>
#   - The `forge` CLI is on PATH for the skill's state-detection calls
#
# Idempotent: run multiple times safely. Pass `uninstall` to reverse.
#
# Usage:
#   ./scripts/install-skills.sh            # install (or update)
#   ./scripts/install-skills.sh uninstall  # remove links
#   ./scripts/install-skills.sh verify     # just check current state

set -euo pipefail

# Resolve forge repo root (this script lives at scripts/ relative to root).
FORGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="${FORGE_ROOT}/.agents/skills"
CLI_SRC="${FORGE_ROOT}/.venv/bin/forge"

# The skills that ship with forge. Add new ones here as they're built.
SKILLS=(forge-discover forge-decompose forge-atom forge-compose forge-audit forge-armour forge-implement forge-test-writer forge-implementer forge-validate)

# Global skill locations — link to all three to cover every compatible client:
#   Claude Code          → ~/.claude/skills
#   OpenAI Codex CLI     → ~/.codex/skills
#   agentskills.io (VS Code Copilot, Cursor, ...) → ~/.agents/skills
CLAUDE_SKILLS="${HOME}/.claude/skills"
CODEX_SKILLS="${HOME}/.codex/skills"
AGENTS_SKILLS="${HOME}/.agents/skills"

# CLI install target. Prefer user-writable ~/.local/bin, fall back to system.
CLI_USER_BIN="${HOME}/.local/bin"
CLI_SYS_BIN="/usr/local/bin"

# ---- helpers ---------------------------------------------------------------

say()  { printf '%s\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
err()  { printf '  \033[31m✗\033[0m %s\n' "$*"; }

require_venv() {
    if [[ ! -x "$CLI_SRC" ]]; then
        err "forge CLI not found at $CLI_SRC"
        say
        say "Build it first:"
        say "  cd $FORGE_ROOT"
        say "  uv venv --python 3.13 .venv && uv pip install -e ."
        say
        exit 1
    fi
}

safe_symlink() {
    local src="$1" dest="$2"
    if [[ -L "$dest" ]]; then
        rm "$dest"
    elif [[ -e "$dest" ]]; then
        err "$dest exists and is not a symlink — refusing to overwrite"
        return 1
    fi
    ln -s "$src" "$dest"
}

# ---- install ---------------------------------------------------------------

install_skills() {
    mkdir -p "$CLAUDE_SKILLS" "$CODEX_SKILLS" "$AGENTS_SKILLS"
    for name in "${SKILLS[@]}"; do
        local src="${SKILLS_SRC}/${name}"
        if [[ ! -d "$src" ]]; then
            err "skill source missing: $src"
            continue
        fi
        safe_symlink "$src" "${CLAUDE_SKILLS}/${name}" && \
            ok "linked ~/.claude/skills/${name}"
        safe_symlink "$src" "${CODEX_SKILLS}/${name}" && \
            ok "linked ~/.codex/skills/${name}"
        safe_symlink "$src" "${AGENTS_SKILLS}/${name}" && \
            ok "linked ~/.agents/skills/${name}"
    done
}

install_cli() {
    require_venv

    # Pick install target: user-local first, then system.
    local target
    if [[ -d "$CLI_USER_BIN" ]] || mkdir -p "$CLI_USER_BIN" 2>/dev/null; then
        target="${CLI_USER_BIN}/forge"
    elif [[ -w "$CLI_SYS_BIN" ]]; then
        target="${CLI_SYS_BIN}/forge"
    else
        warn "no writable bin dir found; will attempt sudo to ${CLI_SYS_BIN}"
        target="${CLI_SYS_BIN}/forge"
    fi

    if [[ "$target" == "${CLI_SYS_BIN}/forge" && ! -w "$CLI_SYS_BIN" ]]; then
        sudo ln -sf "$CLI_SRC" "$target"
    else
        ln -sf "$CLI_SRC" "$target"
    fi
    ok "linked $target"

    # PATH sanity check.
    if ! echo ":${PATH}:" | grep -q ":$(dirname "$target"):"; then
        warn "$(dirname "$target") is not on your PATH"
        say "     Add to your shell rc:  export PATH=\"$(dirname "$target"):\$PATH\""
    fi
}

# ---- uninstall -------------------------------------------------------------

uninstall_all() {
    for name in "${SKILLS[@]}"; do
        for target in "${CLAUDE_SKILLS}/${name}" "${CODEX_SKILLS}/${name}" "${AGENTS_SKILLS}/${name}"; do
            if [[ -L "$target" ]]; then
                rm "$target"
                ok "removed $target"
            fi
        done
    done
    for target in "${CLI_USER_BIN}/forge" "${CLI_SYS_BIN}/forge"; do
        if [[ -L "$target" ]]; then
            if [[ -w "$target" || -w "$(dirname "$target")" ]]; then
                rm "$target"
            else
                sudo rm "$target"
            fi
            ok "removed $target"
        fi
    done
}

# ---- verify ----------------------------------------------------------------

verify_install() {
    say
    say "=== Verification ==="

    # CLI.
    if command -v forge >/dev/null 2>&1; then
        ok "forge on PATH: $(command -v forge)"
        forge --help >/dev/null 2>&1 && ok "forge --help runs clean" || \
            err "forge --help failed"
    else
        err "forge NOT on PATH"
    fi

    # Skills.
    for name in "${SKILLS[@]}"; do
        local found=0
        for dir in "$CLAUDE_SKILLS" "$CODEX_SKILLS" "$AGENTS_SKILLS"; do
            if [[ -L "${dir}/${name}" ]]; then
                if [[ -f "${dir}/${name}/SKILL.md" ]]; then
                    ok "skill discoverable at ${dir}/${name}"
                    found=1
                else
                    err "${dir}/${name} links to a broken target"
                fi
            fi
        done
        (( found == 0 )) && err "skill $name not installed in any scan location"
    done

    say
    say "Next steps:"
    say "  1. Restart your agent session (skills are scanned at session start)"
    say "     - Claude Code: exit + re-run 'claude'"
    say "     - Codex:       exit + re-run 'codex'"
    say "  2. Trigger a forge skill with a natural-language prompt — works in any client:"
    say "       \"I want to build a tool that does X\"       → forge-discover"
    say "       \"Decompose the PAY module into atoms\"       → forge-decompose"
    say "       \"Elicit the spec for atm.pay.charge_card\"   → forge-atom"
    say "       \"Compose flows and journeys\"                → forge-compose"
    say "       \"Audit the specs before we implement\"       → forge-audit"
    say "       \"Harden the specs for security\"             → forge-armour"
    say "       \"Implement the project\"                      → forge-implement"
    say "       \"Validate the implementation against specs\"  → forge-validate"
    say
    say "  Claude Code also supports slash-command shortcuts:"
    say "       /forge-discover  /forge-decompose  /forge-atom"
    say "       /forge-compose   /forge-audit      /forge-armour"
    say "       /forge-implement /forge-validate"
    say
    say "  forge-test-writer and forge-implementer are subagent skills —"
    say "  dispatched by forge-implement, not typically invoked by a human."
    say
}

# ---- main ------------------------------------------------------------------

cmd="${1:-install}"
case "$cmd" in
    install)
        say "Installing forge skills + CLI..."
        install_skills
        install_cli
        verify_install
        ;;
    uninstall)
        say "Removing forge skills + CLI..."
        uninstall_all
        ;;
    verify)
        verify_install
        ;;
    *)
        say "Usage: $0 {install|uninstall|verify}"
        exit 1
        ;;
esac
