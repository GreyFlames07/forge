# Security profile — <project name>

Last updated: <YYYY-MM-DD>

## Data sensitivity
- <public | internal | pii | financial | health | credentials | secrets>

## Actors and trust boundaries
- <actor> — <role> — <trust level>
- <boundary> — <what crosses it>

## Tenancy model
<single-tenant | shared multi-tenant | isolated per tenant | mixed>

## Interface exposure
- Public / internet-facing: <list>
- Private / internal-only: <list>
- Operator-only: <list>

## Authentication model
- End-user auth: <method / provider>
- Service-to-service auth: <method>
- External callback auth: <method>

## Authorization model
<RBAC | ABAC | ownership-based | scoped tokens | mixed>

## Sensitive operations
- <operation> — <why sensitive>

## Compliance / contractual drivers
- <SOC 2 | ISO 27001 | customer baseline | none stated>

## Blast-radius posture
- <fail closed / scoped isolation / manual approval / regional containment / other>

## Top abuse cases
- <abuse case>
- <abuse case>

## Accepted assumptions
- <assumption that armour is relying on>

## Open questions
- <security ambiguity to resolve later>
