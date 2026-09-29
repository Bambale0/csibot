# Restoration execution ledger

## Baseline

- Repository recreated: Bambale0/csibot
- Bootstrap SHA: 95e881c
- Integration branch: dev
- Active branch: restore/qimen-glm
- Recovery source: April 2026 project transcript and surviving /root/csibot workspace metadata.

## Intended user outcome

Restore the working Telegram bot that:
- calculates the source project's Ba Zi flow;
- digitizes Qi Men maps before interpretation;
- compares Host/Guest with v2.1 scoring;
- uses GLM through Neironych API instead of the old Kie.ai Gemini/GPT fallback.

## Provider contract

Verified against https://api.нейроныч.online/guide on 2026-09-30:
- base: https://api.нейроныч.online;
- model currently listed by GET /v1/models: glm-5.3-flash;
- endpoint: POST /v1/chat/completions;
- vision via image_url including data URL;
- Idempotency-Key required for generation POSTs;
- GLM Flash reasoning effort: high|max;
- no service_tier;
- no temperature/top_p in first integration request.

## Restoration choices

- No persistent CRM/database: the final recovered source version advertised no history storage and used memory sessions.
- Preserved formula: (S_base × K_empty) + W_struct + C_inter.
- Added a hard confirmation gate between GLM digitization and calculation.
- Provider integration isolated from domain logic.
- Fixed the recovered 值使 scoring mismatch: it is a Gate, so scoring matches door == zhi_shi.
- Corrected true-solar-time standard meridian to derive from UTC offset instead of a fixed 120°E.
- Ba Zi remains the simplified restored v2.1 algorithm; traditional-calendar accuracy is not independently validated in this task.

## Verification evidence

### RED
- Initial domain/API tests: collection failed because production classes did not exist yet.
- 值使 regression: failed with -3.0 - -3.0, proving the old stem-vs-gate defect.
- Bot helper/config/session tests: collection failed because modules did not exist yet.

### GREEN so far
- pytest -q: 21 passed after domain, provider, config, helpers, session, and bot implementation.

## Remaining before PR

- lint;
- full pytest;
- compileall;
- docker compose config;
- live non-generating /v1/models smoke;
- secret scan/diff review;
- commit + PR to dev;
- exact-head CI.

## Review note

OpenCodeReview was invoked on the complete working tree, but the host's configured DeepSeek reviewer failed before any LLM review occurred (0 input/output tokens, no comments). It is not counted as a successful review. The diff was reviewed directly and verification gates are rerun after fixes.

## Final local verification

Fresh gate after the last code change:
- ruff check . -> passed;
- pytest -q -> 25 passed;
- python -m compileall -q src -> passed;
- router construction smoke -> 9 message handlers and 9 callback handlers registered;
- docker compose config -> passed;
- docker build -> passed;
- live GET /v1/models -> glm-5.3-flash present;
- git diff --cached --check -> passed;
- local secret-pattern scan -> no credential-shaped values found in repository files.

No authenticated GLM generation was sent because this restoration does not contain or read a production API key. The provider request contract is covered with MockTransport tests; a real paid vision smoke remains a deployment-time check.
