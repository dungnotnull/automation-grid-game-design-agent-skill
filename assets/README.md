# assets/

Static resources, system diagrams, and JSON schemas.

## Layout
- `schemas/` - JSON Schema files for every structured skill output
  (requirements, evidence, analysis, knowledge, verdict). These are the
  canonical, audited schemas mirrored by `skills/definitions/*.json` and
  validated by `agent.schemas`.
- `diagrams/` - system diagrams (Mermaid) for the harness flow and the
  agent-framework architecture.