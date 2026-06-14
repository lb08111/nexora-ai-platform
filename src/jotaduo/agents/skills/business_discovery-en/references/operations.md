# Business Discovery — operation reference

Detailed input/output contract for each `business_*_pt` operation. Load
this only when you need the exact arguments or return shape; the SKILL.md
body is enough for the normal flow.

All operations take `tenant_id` (the source of truth) and return a JSON
object. None of them ever publishes an agent.

## business_discovery_start_pt
- **in**: `tenant_id`, `owner_name?`, `company_name?`, `initial_context?`
- **out**: `message`, `objective`, `internal_agents_note`, `known_fields`,
  `missing_key_data`, `mandatory_agents_status`, `next_question`
- Seeds owner/company/notes only when empty (never overwrites).

## business_profile_update_pt
- **in**: `tenant_id`, `profile_patch` (object or JSON-object string)
- **out**: `profile`, `changed_fields`, `ignored_fields`, `blocked_fields`,
  `warnings`, `conflicts`
- Lists merge (dedup); scalars/niche/working-hours **do not** silently
  overwrite — a disagreement is returned in `conflicts`
  (`{field, existing, incoming}`) and the existing value is kept. To force
  an overwrite, add the field name to `profile_patch["_replace"]`.
- PII (CPF/card) is blocked, never stored. `lgpd_consent: true` records
  consent.

## business_niche_analyzer_pt
- **in**: `tenant_id`
- **out**: `niche_detected`, `confidence`, `business_type`,
  `detected_signals`, `possible_needs`, `likely_agents`, `likely_plugins`,
  `questions_to_confirm`

## business_missing_info_pt
- **in**: `tenant_id`, `optional_agent_name?`
- **out**: `has_profile`, `per_agent`, `compliance`, `critical_gaps`,
  `important_gaps`, `desirable_gaps`, `recommended_questions`
- `compliance.runtime_requirements` lists the runtime LGPD duties every
  client-facing agent must honour.

## business_next_question_pt
- **in**: `tenant_id`, `conversation_context?`, `last_owner_answer?`,
  `focus?`
- **out**: `next_question`, `reason`, `expected_information`,
  `related_agents`, `related_plugins`, `unblocks_agents`,
  `should_request_file`, `suggested_source_types`, `asked_count`
- Records the asked gap (loop-guard + resume). `unblocks_agents` shows how
  many agents the answer helps unblock.

## business_source_request_pt
- **in**: `tenant_id`, `goal?`
- **out**: `source_requests` (typed templates), `already_registered`

## business_knowledge_ingest_pt
- **in**: `tenant_id`, `source_id`
- **out**: `found`, `status`, `added_to_profile`, `ignored`, `blocked`,
  `conflicts`, `warnings`, `remaining_gaps`, `message_to_owner`,
  `next_question`, `should_rerun_activation_advisor`
- Merges extracted knowledge via the same conflict-safe patch logic.

## business_activation_advisor_pt
- **in**: `tenant_id`
- **out**: `agent_plan`, `plugin_plan`, `readiness_report`, `compliance`,
  `mandatory_agents`, `recommended_agents`, `blocked_agents`,
  `recommended_plugins`, `summary`, `next_steps`
- Each agent record carries `requires_approval` (review mode: functional
  internally, but outbound needs owner approval until human review).

## business_readiness_explainer_pt
- **in**: `tenant_id`, `agent_name`
- **out**: `status`, `score`, `can_go_public` (always false),
  `explanation`, `missing_information`, `recommended_actions`,
  `message_to_owner`

## business_diagnostic_summary_pt
- **in**: `tenant_id`
- **out**: consolidated company summary, agents/plugins, blocked agents,
  missing data, recommended sources, next steps, executive message.

## Readiness / gap rules (summary)
- Score = passed / total criteria. A failed **critical** criterion blocks
  the agent; score ≥ 0.7 with no critical gap → ready; < 0.4 → blocked.
- Niche-aware recommended criteria refine the score without blocking
  (e.g. cancellation policy for booking niches, payment methods for
  sales, service area for local services).
- Regulated niches (clínica, advocacia, imobiliária, contabilidade) stay
  blocked for client-facing agents until the professional credential and
  LGPD consent are recorded.
