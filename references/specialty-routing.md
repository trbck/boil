# Specialty → Subagent Routing

Routing is platform-specific. At bootstrap, copy the profile that matches the current client into `.boil/routing.md` and adapt per-project (e.g., add language-specific routes if the project is Python-heavy or Rails-heavy).

The orchestrator reads this table when dispatching tickets. `ticket.specialty` is the key; the value is the platform's dispatch target (`agent_type` in Codex, `subagent_type` in Claude-style Agent tools, or whatever the local client exposes).

## Codex routing table

Codex currently exposes a small set of subagent roles (`worker`, `explorer`, `default`) through `spawn_agent`. Collapse specialty routing to those roles unless your local Codex install exposes more.

```yaml
# .boil/routing.md
platform: codex
dispatch_tool: multi_agent_v1.spawn_agent
dispatch_field: agent_type
routes:
  # Implementation / modification work
  frontend: worker
  backend: worker
  fullstack: worker
  api-design: worker
  mobile: worker
  ui-design: worker
  websocket: worker
  graphql: worker
  microservices: worker
  electron: worker
  qa: worker
  debugger: worker
  test-automation: worker
  performance: worker
  security: worker
  accessibility: worker
  data-engineering: worker
  ml: worker
  ai: worker
  database: worker
  python: worker
  javascript: worker
  typescript: worker
  go: worker
  rust: worker
  java: worker
  cli: worker
  deps: worker
  docs: worker
  dx: worker
  refactor: worker
  tooling: worker
  general: worker

  # Read-only or judgment-style work
  explore: explorer
  research: explorer
  data-analysis: explorer
  code-review: explorer
  judge: worker        # writes .boil/iterations/iter-NNN/judges/R-*.md
  evaluator: worker    # alias for judge

  # Planning/product work
  plan: default
  product: default
  project: default
```

## Superpowers-compatible development roles

Use this profile when the current client exposes `superpowers:*` agents/skills
or an equivalent local agent set. If the exact superpowers agent is not
available, keep the `specialty` name and route it to the nearest platform
agent in the Codex or rich-agent table. Do not block a boil run just because
the named superpower is unavailable; log the fallback in `.boil/routing.md`.

```yaml
# .boil/routing.md
platform: superpowers-compatible
dispatch_field: subagent_type
routes:
  # Goal shaping / planning
  brainstorm: superpowers:brainstorming
  plan: superpowers:brainstorming
  product: superpowers:brainstorming
  architecture: superpowers:brainstorming

  # Implementation
  frontend: superpowers:test-driven-development
  backend: superpowers:test-driven-development
  fullstack: superpowers:test-driven-development
  api-design: superpowers:test-driven-development
  cli: superpowers:test-driven-development
  python: superpowers:test-driven-development
  javascript: superpowers:test-driven-development
  typescript: superpowers:test-driven-development
  rust: superpowers:test-driven-development
  go: superpowers:test-driven-development
  general: superpowers:test-driven-development

  # Proof / quality gates
  qa: superpowers:verification-before-completion
  test-automation: superpowers:test-driven-development
  verification: superpowers:verification-before-completion
  debugger: superpowers:systematic-debugging
  error-detective: superpowers:systematic-debugging
  code-review: superpowers:requesting-code-review
  review: superpowers:requesting-code-review

  # Coordination
  parallel-dispatch: superpowers:dispatching-parallel-agents
  orchestrator: superpowers:dispatching-parallel-agents
  ticket-triage: superpowers:dispatching-parallel-agents

  # Judgment / read-only analysis
  research: superpowers:brainstorming
  explore: superpowers:brainstorming
  judge: superpowers:verification-before-completion
  evaluator: superpowers:verification-before-completion
```

### Superpowers parallel batch patterns

When using the superpowers-compatible profile, form batches by role, not by
file path. A single iteration should usually dispatch one implementer, one
verifier, and optionally one debugger/reviewer in parallel:

```yaml
batch_patterns:
  feature_slice:
    - specialty: frontend | backend | fullstack
      role: superpowers:test-driven-development
      job: write red proof, implement, run focused proof
    - specialty: qa
      role: superpowers:verification-before-completion
      job: independently define the regression proof and verify after implementation lands
  failing_verification:
    - specialty: debugger
      role: superpowers:systematic-debugging
      job: isolate root cause from logs/repro
    - specialty: qa
      role: superpowers:verification-before-completion
      job: preserve the failing repro and define the green signal
  pre_termination:
    - specialty: code-review
      role: superpowers:requesting-code-review
      job: review the iteration diff after tests pass
    - specialty: qa
      role: superpowers:verification-before-completion
      job: rerun direct and adversarial verification
```

Keep the dispatch prompts self-contained just like other boil agents. The
superpower name is a role hint; the ticket, goal slice, memory slice, proof
strategy, and return schema remain authoritative.

## Claude / rich-agent routing table

```yaml
# .boil/routing.md (copy this YAML into a code block in that file)
platform: claude
dispatch_field: subagent_type
routes:

# Core development
  frontend:        voltagent-core-dev:frontend-developer
  backend:         voltagent-core-dev:backend-developer
  fullstack:       voltagent-core-dev:fullstack-developer
  api-design:      voltagent-core-dev:api-designer
  mobile:          voltagent-core-dev:mobile-developer
  ui-design:       voltagent-core-dev:ui-designer
  websocket:       voltagent-core-dev:websocket-engineer
  graphql:         voltagent-core-dev:graphql-architect
  microservices:   voltagent-core-dev:microservices-architect
  electron:        voltagent-core-dev:electron-pro

# QA & security
  qa:              voltagent-qa-sec:qa-expert
  debugger:        voltagent-qa-sec:debugger
  code-review:     voltagent-qa-sec:code-reviewer
  judge:           voltagent-research:research-analyst   # semantic rubric evaluator (see references/rubrics.md)
  evaluator:       voltagent-research:research-analyst   # alias for `judge`
  test-automation: voltagent-qa-sec:test-automator
  performance:     voltagent-qa-sec:performance-engineer
  security:        voltagent-qa-sec:security-auditor
  penetration:     voltagent-qa-sec:penetration-tester
  accessibility:   voltagent-qa-sec:accessibility-tester
  architecture:    voltagent-qa-sec:architect-reviewer
  chaos:           voltagent-qa-sec:chaos-engineer
  error-detective: voltagent-qa-sec:error-detective
  compliance:      voltagent-qa-sec:compliance-auditor

  # Data & AI
  data-analysis:   voltagent-data-ai:data-analyst
  data-engineering: voltagent-data-ai:data-engineer
  data-science:    voltagent-data-ai:data-scientist
  ml:              voltagent-data-ai:ml-engineer
  ai:              voltagent-data-ai:ai-engineer
  mlops:           voltagent-data-ai:mlops-engineer
  nlp:             voltagent-data-ai:nlp-engineer
  llm:             voltagent-data-ai:llm-architect
  prompt:          voltagent-data-ai:prompt-engineer
  database:        voltagent-data-ai:database-optimizer
  postgres:        voltagent-data-ai:postgres-pro

  # Languages (use when work is language-specific in a polyglot repo)
  python:          voltagent-lang:python-pro
  javascript:      voltagent-lang:javascript-pro
  typescript:      voltagent-lang:typescript-pro
  go:              voltagent-lang:golang-pro
  rust:            voltagent-lang:rust-engineer
  java:            voltagent-lang:java-architect
  csharp:          voltagent-lang:csharp-developer
  cpp:             voltagent-lang:cpp-pro
  php:             voltagent-lang:php-pro
  ruby-rails:      voltagent-lang:rails-expert
  swift:           voltagent-lang:swift-expert
  kotlin:          voltagent-lang:kotlin-specialist
  elixir:          voltagent-lang:elixir-expert
  django:          voltagent-lang:django-developer
  nextjs:          voltagent-lang:nextjs-developer
  react:           voltagent-lang:react-specialist
  vue:             voltagent-lang:vue-expert
  angular:         voltagent-lang:angular-architect
  flutter:         voltagent-lang:flutter-expert
  laravel:         voltagent-lang:laravel-specialist
  spring:          voltagent-lang:spring-boot-engineer
  sql:             voltagent-lang:sql-pro
  powershell-7:    voltagent-lang:powershell-7-expert
  powershell-5:    voltagent-lang:powershell-5.1-expert
  dotnet:          voltagent-lang:dotnet-core-expert
  dotnet-fx:       voltagent-lang:dotnet-framework-4.8-expert

  # Developer experience
  build:           voltagent-dev-exp:build-engineer
  cli:             voltagent-dev-exp:cli-developer
  deps:            voltagent-dev-exp:dependency-manager
  docs:            voltagent-dev-exp:documentation-engineer
  dx:              voltagent-dev-exp:dx-optimizer
  git:             voltagent-dev-exp:git-workflow-manager
  legacy:          voltagent-dev-exp:legacy-modernizer
  mcp:             voltagent-dev-exp:mcp-developer
  refactor:        voltagent-dev-exp:refactoring-specialist
  slack:           voltagent-dev-exp:slack-expert
  tooling:         voltagent-dev-exp:tooling-engineer

  # Domains (use for vertical-specific work)
  api-docs:        voltagent-domains:api-documenter
  blockchain:      voltagent-domains:blockchain-developer
  embedded:        voltagent-domains:embedded-systems
  fintech:         voltagent-domains:fintech-engineer
  game:            voltagent-domains:game-developer
  iot:             voltagent-domains:iot-engineer
  m365:            voltagent-domains:m365-admin
  mobile-app:      voltagent-domains:mobile-app-developer
  payment:         voltagent-domains:payment-integration
  quant:           voltagent-domains:quant-analyst
  risk:            voltagent-domains:risk-manager
  seo:             voltagent-domains:seo-specialist
  wordpress:       voltagent-biz:wordpress-master

  # Research & analysis
  research:        voltagent-research:research-analyst
  data-research:   voltagent-research:data-researcher
  market:          voltagent-research:market-researcher
  competitive:     voltagent-research:competitive-analyst
  search:          voltagent-research:search-specialist
  trend:           voltagent-research:trend-analyst

  # Business / product (rarely needed inside a code loop, but available)
  product:         voltagent-biz:product-manager
  project:         voltagent-biz:project-manager
  business:        voltagent-biz:business-analyst
  content:         voltagent-biz:content-marketer
  technical-writer: voltagent-biz:technical-writer
  ux-research:     voltagent-biz:ux-researcher

  # Fallbacks
  plan:            Plan
  explore:         Explore
  general:         general-purpose
```

## How the orchestrator uses this

1. Read `ticket.specialty` from the ticket file.
2. Read `platform`, `dispatch_field`, and `routes` from `.boil/routing.md`.
3. Look up `routes[ticket.specialty]`.
4. If found → dispatch using the configured field (e.g. Codex `agent_type=worker`, Claude `subagent_type=voltagent-core-dev:frontend-developer`).
5. If not found → log a TODO at the bottom of `routing.md` ("specialty `xyz` referenced by T-NNNN, not routed") and dispatch with the platform fallback (`worker` on Codex, `general-purpose` on Claude-style rich-agent installs). Address the gap on next iteration.

## Adapting to your project

Edit `.boil/routing.md` after bootstrap:

- **Polyglot repo** — keep the language-specific routes if your client exposes specialists; on Codex, many of them still collapse to `worker`.
- **Single-language repo** — collapse to the most relevant ones. E.g., a Next.js project on a rich-agent install might map `frontend` → `voltagent-lang:nextjs-developer` directly.
- **Specialized stack** — add new specialty keys for things that don't fit the defaults. E.g., `wordpress`, `salesforce-apex`, `airflow-dag`. Add the route to whichever specialist comes closest.
- **Custom subagent types** — if the user has their own subagent definitions (`.claude/agents/<name>.md`, `.codex` agent profiles, or client-specific equivalents), use those names directly as the routing target.

## Gotchas

- **Don't over-route.** Three or four routes covering 90% of work beats fifty routes covering 100%. The platform fallback is fine for the long tail.
- **Specialty ≠ language.** A `frontend` ticket in a TypeScript repo doesn't necessarily need the TypeScript specialist — `frontend-developer` already knows TS. Use language-specific routes only when the work is fundamentally about the language (e.g., a tricky type-system problem, a build-tool config, a perf-sensitive algorithm).
- **`Plan` and `Explore` are special.** `Plan` is for design/architecture deliberation; `Explore` is for read-only code search. Route research-style tickets to these — they're fast and don't write code.
- **Don't route `code-review` to the specialist mid-iteration unless asked.** Code review at the end of an iteration is fine, but routing every ticket through review doubles the loop length. Use `superpowers:requesting-code-review` at termination instead.
- **`judge` is context-isolated on purpose.** Route semantic rubric evaluation to `judge` (or `evaluator`) only — never to the specialty that implemented the work. Sharing priors with the implementer is the bias `references/rubrics.md` is built to avoid. The default mapping is to a research-style agent for this reason; if you swap it for a different subagent, keep that property.
