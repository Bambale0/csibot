# AGENTS.md — csibot

## Mission

Maintain the restored Qi Men Dun Jia / Ba Zi Telegram bot with small, verified changes.

## Required workflow

Before changing code, inspect relevant current guidance from:

- Bambale0/claw
- wondelai/skills
- Bambale0/dev-agents-pack
- agentskills/agentskills
- anthropics/skills
- Bambale0/ksu/.clinerules/skills

Use repository evidence and the official provider contract before changing API payloads.

## Engineering rules

- Use test-first development for behavior changes.
- Keep Telegram handlers thin; domain calculations stay framework-independent.
- Keep provider-specific HTTP payloads inside services/neironych.py.
- Never commit .env, Telegram tokens, API keys, user photos, dumps, or customer data.
- Never invent provider fields. Verify against https://api.нейроныч.online/guide.
- Preserve Idempotency-Key semantics; do not automatically create a new paid text/vision POST after an ambiguous timeout.
- Validate GLM digitization before deterministic calculation; never silently invent missing palaces.
- Escape user-controlled text before rendering Telegram HTML.
- Do not claim tests or deployment status without fresh evidence.

## Branch policy

- main is the stable line.
- dev is the integration branch.
- Feature work goes through a feature branch and PR to dev.
- Promotion dev -> main requires explicit operator instruction.

## Verification

Before completion:

    ruff check .
    pytest -q
    python -m compileall -q src
    docker compose config

Report exact results and any unverified external behavior.
