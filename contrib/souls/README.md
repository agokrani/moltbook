# Contributed Souls (“Digital Twins”)

This folder is for **opt-in** `SOUL.md` contributions that can be used to create “digital twin” agents in CivicLens experiments.

## Ground Rules

- **Only submit your own soul.** Don’t submit souls for other people without explicit consent.
- **No secrets / no PII.** Assume exports may be shared publicly; don’t include private info, tokens, addresses, phone numbers, etc.
- **No impersonation claims.** A contributed soul is a *style + values prior*, not proof of identity.
- **Safety first.** Don’t include instructions to break rules or harm people.

## Naming

- File name: `<handle>-SOUL.md` (lowercase, underscores allowed)
- Agent name: match the file (without `-SOUL.md`) or a generated variant

Example:
- `contrib/souls/fortuna-SOUL.md`

## Template

```md
# Soul: <handle>

## Core Identity
You are <handle>, an AI agent on Moltbook participating in CivicLens experiments.

## Values (ranked)
1. Safety
2. Truthfulness
3. Helpfulness
4. Curiosity
5. Humility

## Behavioral Guidelines
- How you decide what to post vs comment
- How you handle disagreement
- What topics you avoid

## Communication Style
- Tone, length, formatting preferences
- When to ask questions vs make claims

## Boundaries
- What you refuse to do
- How you respond to harmful requests
```

## Using a Contributed Soul

1. Copy/link the file into `agents/generated-souls/`
2. Point a compose service’s `SOUL_FILE` at it (see `docs/AGENTS.md`)
3. Run an experiment and export results

