# Content Editor Team — avilonROBOTICS

AI-powered content team built on Claude Code agents for managing PR and social media content for [avilonROBOTICS](https://avilonrobotics.com).

## Team Structure

| Agent | Role | Model |
|---|---|---|
| `editor-in-chief` | Orchestrator — runs campaigns, assigns briefs | claude-opus-4-5 |
| `trend-monitor` | Scans social media & news for trending topics | claude-sonnet-4-5 |
| `tech-writer` | Writes fact-backed knowledge articles | claude-sonnet-4-5 |
| `ad-writer` | Writes 3-variant ad copy | claude-sonnet-4-5 |
| `proofreader` | Final QA gate — APPROVED or BLOCKED verdict | claude-sonnet-4-5 |

## Workflow

```
Trend Monitor → Editor in Chief → Tech Writer / Ad Writer → Proofreader
```

## Files

```
agents/                    # Claude Code subagent definitions
  editor-in-chief.md
  trend-monitor.md
  tech-writer.md
  ad-writer.md
  proofreader.md
company-profile.md         # Brand identity, services, target customers
content-learning.md        # Learnings from past Facebook posts
RAW DATA/                  # Source data from Meta Business Suite
```

## Setup

1. Copy `agents/*.md` files to `~/.claude/agents/`
2. Restart Claude Code
3. Start a campaign: `use editor-in-chief to run a campaign for [product/event]`

## Brand

- **Language:** Thai primary, English for tech terms
- **Tone:** Professional, innovative, warm — not salesy
- **Contact persona:** "น้องฟ้าใส" — 098-948-9743
