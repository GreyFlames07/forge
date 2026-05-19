---
name: forge-design
description: >
  Forge system design skill. Use when a user wants to start a new project or system with Forge,
  design a new system from scratch, or establish the foundation that all downstream spec work builds on.
  Drives a value-focused discovery interview that produces the full spec skeleton: conception.yaml,
  system.yaml, domain and module files, a general environment sketch, and workbench/discovery.md.
  Triggers on: "start a new forge project", "design a new system", "let's build X with forge",
  "forge-design", or any request to begin Forge spec work from scratch.
---

# forge-design

Read `references/framework.md` before starting — you need the full schema.

## Purpose

Drive a value-focused interview that produces the complete spec skeleton. The interview is about **what the system does and how it creates value** — not pain points, benchmarks, or hypothetical comparisons. Every question should extract something that will directly shape a spec node.

## Output Artifacts

| File | Contents |
|------|----------|
| `spec/conception.yaml` | Conception, actors, glossary |
| `spec/<system>/system.yaml` | System node with platform, language, deployment |
| `spec/<system>/<domain>/domain.yaml` | One per domain |
| `spec/<system>/<domain>/<module>/module.yaml` | Skeleton per module — no elements yet |
| `spec/<system>/implementation/environments.yaml` | General environment sketch |
| `spec/<system>/workbench/discovery.md` | Living document; all downstream skills read this |

## Interview Phases

Work through phases in order. Batch questions within a phase; never batch across phases. Ground each question in prior answers — never ask generic questions when you already have context.

### Phase 1 — System Intent

Establish what the system is and the value it creates. Keep it concrete.

- What does this system do? (one clear statement)
- Who benefits from it, and what can they accomplish that they couldn't before?
- What is explicitly out of scope — what will this system never do?
- What's the single most important thing it must get right?

Write the conception `intent` from the answers. Do not move on until the scope boundary is clear.

### Phase 2 — Actors

- Who or what interacts with the system? (humans, services, partners, other systems)
- For each actor: what do they want to accomplish? What auth mechanism do they use?
- Are there actors who read only vs. actors who write/mutate?

### Phase 3 — Domain Model

- What are the major responsibilities this system has? (aim for 2–5 natural groupings)
- For each responsibility: what does it own exclusively? What does it explicitly hand off?
- Where do the natural seams fall — where would changes in one area NOT require changes in another?

Resist naming domains until their boundaries are clear. Use descriptive placeholders.

### Phase 4 — Module Boundaries

For each domain:
- What distinct units of deployment or ownership exist within it?
- What does each unit manage exclusively? (data, logic, state)
- What does each unit depend on from other modules?
- What external services or integrations does it need?

One module = one deployable unit with clear ownership. When unsure whether something is one module or two, ask: "can these be deployed and scaled independently?"

### Phase 5 — Platform and Environment Sketch

Critical decisions — always present options with tradeoffs, never silently default:
- Cloud/platform? (AWS / GCP / Azure / on-prem / hybrid)
- Primary language?
- Deployment model? (cloud / on_prem / hybrid / edge)
- What environment types are needed? (development / staging / production / test)

Environments are **general only** at this stage — no connection strings, instance classes, or concrete config. Those are captured in `forge-spec`.

### Phase 6 — Glossary and Naming

- Are there domain terms with precise meanings that differ from everyday usage?
- Are there terms that should NOT be used (synonyms to avoid)?

Capture these in the conception glossary. They govern naming across the entire spec.

## Assembly

After the interview, before writing any files:
1. Restate all major decisions as a summary and ask for confirmation.
2. On confirmation, write all files simultaneously.
3. Populate `workbench/discovery.md` with: system intent, actors, domain model, module map, platform decisions, open questions, and any decisions deferred to `forge-spec`.

**`workbench/discovery.md` is the primary artifact.** Every downstream skill reads it. Be thorough — include the reasoning behind decisions, not just the decisions themselves.

## Exit Condition

State: *"Design is complete. Here's what we've produced: [list files]. Ready to move to `forge-spec` for module & element elicitation."*

Wait for human confirmation before closing the session.

## Key Constraints

- Do not create element files, types, errors, policies, contracts, interactions, or flows — those belong in `forge-spec`.
- Do not invent structure the human hasn't described. If you don't have evidence for a module, don't create it.
- Module `elements` list stays empty — just `[]`. Populated by `forge-spec`.
- Use `status: draft` on all generated nodes.
