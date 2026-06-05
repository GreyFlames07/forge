---
name: forge-business
description: Market research, product discovery, business scenario framing, MVP sequencing, risk analysis, and development guidance before Forge V4 schema work. Use when validating a product idea, researching a market or competitors, defining customer segments and opportunities, mapping assumptions, prioritizing MVP scope, or producing business actions and product direction for forge-schema.
---

# forge-business

Read before starting:

- `../../FRAMEWORK_V4.md`
- `../../SCHEMA_REFERENCE_V4.md`
- `../forge-schema/SKILL.md`

Prefer when available:

- web research with cited sources
- `forge crawl --format json` when a Forge workspace already exists
- `forge context` when reviewing an existing Forge model

## Purpose

Turn a business idea, market, customer problem, or product direction into an
evidence-backed business brief that can guide Forge V4 system design.

This skill owns:

- market research
- competitor analysis
- product discovery
- business scenarios
- product framing
- MVP sequencing
- risk and assumption mapping
- development guidance for `forge-schema`

This skill does not design runtime containers or C3 annotations. Its main
handoff is clear business intent, candidate business actions, target users,
constraints, risks, and a recommended MVP sequence.

The primary output artifact is `business-plan.md`.

## Research Standard

Use current web research whenever market size, competitors, pricing, regulation,
industry trends, customer behavior, or recent product movement matters.

Research rules:

1. Cite sources with links.
2. Prefer primary sources, credible industry reports, government statistics,
   company pricing pages, product pages, app reviews, filings, and recent news.
3. Distinguish verified data from estimates.
4. Prefer data from the last two years unless older data is clearly still useful.
5. Cross-check important claims across more than one source when feasible.
6. Mark assumptions and evidence gaps plainly.

Do not fabricate market numbers, customer behavior, or competitor claims.

## Decision Log

If `forge/decisions.yaml` exists, read and maintain it.

Record non-trivial business decisions such as:

- target customer segment selection
- market or niche focus
- MVP scope choice
- major deferral
- accepted risk
- pricing or go-to-market assumption
- decision to proceed, pivot, or stop

Use the `forge.decisions` schema from `SCHEMA_REFERENCE_V4.md`.

## Workflow

### 1. Frame The Business Scenario

Clarify:

- product or business idea
- target market
- target customer or user
- current pain or desired gain
- desired business outcome
- constraints, deadlines, budget, team, and regulatory context

If the idea is early, draft a concise scenario first and ask the operator to
correct it before deep research.

### 2. Market Research

Assess:

- TAM, SAM, and reachable niche where data supports it
- growth rate and market trajectory
- key segments
- industry trends
- regulatory or economic forces
- buying triggers and barriers
- distribution channels

Use a quick research pass when the operator wants speed. Use a full research
pass when decisions depend on market quality or competitive pressure.

### 3. Target Customer Analysis

Define primary and secondary segments.

Evaluate:

- demographics or firmographics
- psychographics and jobs-to-be-done
- current workflow
- pain frequency and severity
- current workarounds
- willingness to pay or switch
- buying committee and adoption friction

Prefer observed behavior over stated preference.

### 4. Competitive Teardown

Identify direct, indirect, and adjacent competitors.

For important competitors, inspect:

- positioning and messaging
- pricing model and tiers
- feature coverage
- onboarding and activation path
- integrations and ecosystem
- reviews, complaints, praise, and feature requests
- recent launches, hiring signals, funding, or strategic moves
- security, compliance, and enterprise readiness signals

Score only where evidence exists. A 12-dimension scorecard may cover features,
pricing, UX, performance, docs, support, integrations, security, scalability,
brand, community, and innovation.

### 5. Opportunity Discovery

Build an opportunity solution tree:

```text
outcome -> opportunities -> solution ideas -> experiments
```

Rules:

1. Define one measurable outcome.
2. Identify at least three distinct opportunities before converging.
3. Tie every opportunity to evidence.
4. Propose at least two experiments for each top opportunity.
5. Keep solution ideas separate from validated opportunities.

### 6. Assumption Mapping

Map assumptions by category:

- desirability: users want this
- viability: business value exists
- feasibility: the team can build and operate it
- usability: users can succeed with it

Prioritize high-risk, low-certainty assumptions first.

For each major assumption, define:

- evidence today
- risk level
- certainty level
- fastest useful test
- proceed, pivot, or stop threshold

### 7. MVP Sequencing

Recommend the smallest useful product sequence.

Include:

- wedge customer or first segment
- MVP promise
- must-have business actions
- deferred features
- riskiest assumptions to test before build
- first release scope
- second release scope
- metrics that define progress

Do not produce a feature pile. Sequence by learning value, customer value, and
business risk reduction.

### 8. Development Guidance

Translate business findings into a handoff for `forge-schema`.

Include:

- system purpose draft
- system boundary notes
- candidate actors
- external dependencies or market integrations
- candidate business actions
- expected outcomes
- data or entity hints
- security, privacy, compliance, trust, or availability constraints
- development priorities and deferrals
- risks that should influence architecture

Do not choose containers here unless the business model imposes a hard runtime
constraint. Leave system design to `forge-schema`.

## Output

For a full pass, create or update `business-plan.md` with:

- executive summary
- market overview with sources
- target customer segments
- competitor landscape
- opportunity solution tree
- assumption map and test plan
- MVP sequence
- risk register
- development guidance for `forge-schema`
- decision recommendation: proceed, pivot, stop, or research further

For a quick pass, create or update a concise `business-plan.md` with:

- target customer
- market signal
- top competitors
- biggest opportunity
- key assumptions
- MVP recommendation
- next research/build step

`business-plan.md` should be structured, skimmable, and stable enough to serve
as the handoff into `forge-schema`. Include source links inline or in a sources
section. Do not bury key business actions, assumptions, or MVP decisions in chat
only.

## Quality Checks

Before finalizing:

1. Is every major claim supported by evidence or marked as an assumption?
2. Are opportunities grounded in customer or market evidence?
3. Are solution ideas separated from validated problems?
4. Are risks specific enough to guide action?
5. Does the MVP sequence reduce the biggest uncertainty first?
6. Are business actions clear enough for `forge-schema` to design from?
7. Are citations included for current market and competitor claims?
