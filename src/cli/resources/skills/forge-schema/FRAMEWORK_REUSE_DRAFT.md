# Framework Reuse Draft

Draft language for `forge-schema`:

Before modeling custom runtime responsibility, classify each required capability
as core business logic or commodity functionality.

Core business logic is behavior that makes this product meaningfully different:
domain workflow, proprietary decisioning, unique data model, customer-specific
operations, or business rules that cannot be delegated without losing the point
of the system.

Commodity functionality is everything else: authentication, authorization, RAG,
search, security controls, rate limiting, payments, billing, email, analytics,
observability, background jobs, queues, file storage, feature flags, admin
tooling, import/export, notifications, scheduling, and common CRUD scaffolding.

For each commodity capability, propose existing options before designing custom
code:

- framework-native option
- managed service option
- platform primitive option
- bootstrap or starter framework option when it would remove setup burden

For each option, name:

- responsibility removed from this system
- smallest native/local alternative
- integration boundary introduced
- data ownership or compliance implication
- cost, lock-in, and operational burden
- added code, schema, configuration, infrastructure, and operating procedure
- upgrade trigger from the smallest option
- whether it should appear as an external dependency, runtime container, or
  deferred decision

YAGNI hardening:

- Propose frameworks before custom code, but do not adopt them automatically.
- Prefer the smallest option that satisfies the current build slice.
- Reject any option that adds unused flows, roles, queues, admin surfaces,
  multi-tenant models, billing products, deployment units, or configuration.
- Model a managed/framework capability as an external dependency unless this
  system deploys, operates, or owns the runtime.
- Record a decision when custom commodity functionality is chosen or when a
  reuse option materially shapes architecture.

Useful examples to consider:

- auth: Auth.js, Clerk, Supabase Auth, Django auth, Rails authentication
- RAG and AI retrieval: LangChain, LlamaIndex, provider/vector-store templates
- security: OWASP ASVS, Arcjet, framework middleware, platform WAF features
- rate limiting: Upstash Rate Limit, Arcjet, API gateway or platform limits
- payments: Stripe Checkout, Stripe Billing, Paddle, provider-hosted checkout
- bootstrap: next-forge, create-t3-app, Django, Rails, Laravel, Phoenix,
  framework starters already present in the repository

Do not select a technology because it is popular. Select it only when it reduces
owned code while preserving the system's business intent, security posture, data
ownership, deployment model, and build slice.
