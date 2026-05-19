#!/usr/bin/env bash
set -euo pipefail

FORGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="${FORGE_ROOT}/.agents/skills"
CLI_SRC="${FORGE_ROOT}/.venv/bin/forge"

SKILLS=(forge-discover forge-spec forge-plan forge-build forge-review forge-validate forge-cast)

CLAUDE_SKILLS="${HOME}/.claude/skills"
CODEX_SKILLS="${HOME}/.codex/skills"
AGENTS_SKILLS="${HOME}/.agents/skills"
COPILOT_SKILLS="${HOME}/.copilot/skills"
CLI_USER_BIN="${HOME}/.local/bin"

say()  { printf '%s\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
err()  { printf '  \033[31m✗\033[0m %s\n' "$*"; }

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

install_skills() {
    mkdir -p "$CLAUDE_SKILLS" "$CODEX_SKILLS" "$AGENTS_SKILLS"
    [[ -d "${HOME}/.copilot" ]] && mkdir -p "$COPILOT_SKILLS"
    for name in "${SKILLS[@]}"; do
        local src="${SKILLS_SRC}/${name}"
        if [[ ! -d "$src" ]]; then
            err "skill source missing: $src"
            continue
        fi
        safe_symlink "$src" "${CLAUDE_SKILLS}/${name}" && ok "linked ~/.claude/skills/${name}"
        safe_symlink "$src" "${CODEX_SKILLS}/${name}" && ok "linked ~/.codex/skills/${name}"
        safe_symlink "$src" "${AGENTS_SKILLS}/${name}" && ok "linked ~/.agents/skills/${name}"
        if [[ -d "${HOME}/.copilot" ]]; then
            safe_symlink "$src" "${COPILOT_SKILLS}/${name}" && ok "linked ~/.copilot/skills/${name}"
        fi
    done
}

install_cli() {
    mkdir -p "$CLI_USER_BIN"
    if [[ ! -x "$CLI_SRC" ]]; then
        err "forge CLI not found at $CLI_SRC"
        say "Build it first:"
        say "  cd $FORGE_ROOT"
        say "  uv venv --python 3.13 .venv && uv pip install -e ."
        exit 1
    fi
    ln -sf "$CLI_SRC" "${CLI_USER_BIN}/forge"
    ok "linked ${CLI_USER_BIN}/forge"
    if ! echo ":${PATH}:" | grep -q ":${CLI_USER_BIN}:"; then
        warn "${CLI_USER_BIN} is not on your PATH"
        say "     Add to your shell rc: export PATH=\"${CLI_USER_BIN}:\$PATH\""
    fi
}

uninstall_all() {
    for name in "${SKILLS[@]}"; do
        for target in "${CLAUDE_SKILLS}/${name}" "${CODEX_SKILLS}/${name}" "${AGENTS_SKILLS}/${name}" "${COPILOT_SKILLS}/${name}"; do
            [[ -L "$target" ]] && rm "$target" && ok "removed $target"
        done
    done
    [[ -L "${CLI_USER_BIN}/forge" ]] && rm "${CLI_USER_BIN}/forge" && ok "removed ${CLI_USER_BIN}/forge"
}

verify_install() {
    say
    say "=== Verification ==="
    if command -v forge >/dev/null 2>&1; then
        ok "forge on PATH: $(command -v forge)"
        forge --help >/dev/null 2>&1 && ok "forge --help runs clean" || err "forge --help failed"
    else
        err "forge NOT on PATH"
    fi
    for name in "${SKILLS[@]}"; do
        local found=0
        for dir in "$CLAUDE_SKILLS" "$CODEX_SKILLS" "$AGENTS_SKILLS" "$COPILOT_SKILLS"; do
            if [[ -L "${dir}/${name}" && -f "${dir}/${name}/SKILL.md" ]]; then
                ok "skill discoverable at ${dir}/${name}"
                found=1
            fi
        done
        (( found == 0 )) && err "skill $name not installed in any scan location"
    done
}

cmd="${1:-install}"
case "$cmd" in
    install)
        say "Installing forge V2 skills + CLI..."
        install_skills
        install_cli
        verify_install
        ;;
    uninstall)
        say "Removing forge V2 skills + CLI..."
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
