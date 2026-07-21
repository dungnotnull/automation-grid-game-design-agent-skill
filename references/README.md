# references/

Domain knowledge, prompt base-templates, and raw context guidelines used for
RAG / agent grounding.

## Layout
- `prompt_templates/` - base prompt templates for each skill (gather, evidence,
  core, knowledge, advisor, quality_gate). Referenced by
  `skills/definitions/*.json` via the `prompt_template` field.
- `domain_methods.md` - the authoritative methods (ratio solving, Little's Law,
  belt balancing, tradeoffs, flow-shop scheduling, evidence hierarchy) that
  ground every numeric claim.

These references are consumed by the `agent` framework's LLM providers and by
the markdown sub-skills (`skills/sub-*.md`) for human-readable grounding.