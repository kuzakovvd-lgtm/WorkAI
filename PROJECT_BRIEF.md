# WorkAI Project Brief

## Goal

Build WorkAI v2 as a modular system to control quality of employee time accounting and run AI-based audits with explainable outputs.

## Why it exists

v1 is operational but difficult to evolve safely. v2 is a clean rewrite focused on strict module boundaries, DB-first contracts, and predictable deployment.

## Primary users

- Operations managers
- Audit/QA analysts
- Engineering/DevOps

## Core outcomes

- Reliable ingest and normalization of workday task data.
- Quantitative assessment (effort quality, ghost time, norms).
- AI audit reports suitable for review and escalation.
- Operational APIs and notifications.

## Success metrics (high level)

- Pipeline reliability and repeatability.
- Lower false positives in audit findings over time.
- Fast incident diagnosis through logs and runbooks.
- Safe iteration speed (CI green, typed code, migration discipline).

## Non-goals (current scope)

- Replacing HR systems.
- Generic BI platform functionality.
- Coupling modules through Python interfaces instead of DB contract.
