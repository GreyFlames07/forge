# Forge Discover Framework

## Purpose

Define the system shape needed to start real work:

- system intent
- project profile
- verticals
- runtime units
- bootstrap
- initial build policy

## Core Behavior

- interview first
- ask only the highest-yield questions
- do not ask for details already implied by prior answers
- stop asking once the bootstrap slice is clear enough to draft
- draft the schema files before broadening the interview

## Interview Standard

Questions must:

- reduce structural ambiguity
- affect schema shape
- affect bootstrap shape
- affect repo scaffolding

Questions must not:

- ask for implementation trivia too early
- ask the user to design internals the framework can derive later
- ask broad brainstorming questions when a narrower question will unlock the next draft

## Required Outcomes

The stage should leave behind enough truth to answer:

1. what system is this
2. what profile is it
3. what verticals matter first
4. what units must exist
5. what is the first runnable path
6. what must never be violated while building

## Files Produced

- `forge/system.yaml`
- `forge/verticals/*.yaml`
- `forge/units/*.yaml`
- `forge/bootstrap.yaml`
- `forge/build_policy.yaml`

## Effective Question Order

1. What is the system for?
2. What is the smallest valuable outcome that should work first?
3. What project profile best fits the system?
4. What are the first business verticals?
5. What runtime units are required for the bootstrap slice?
6. What environments and promotion stages matter?
7. What security or approval rules are globally non-negotiable?

## Exit Condition

The bootstrap path is concrete enough to scaffold and run.
