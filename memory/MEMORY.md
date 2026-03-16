# Memory — avilonROBOTICS Content Team
> Synced via GitHub. Works on any PC.
> Full detail: D:\Claude Agent\CLAUDE.md (auto-loaded by Claude Code)

## Project
avilonROBOTICS AI content pipeline — autonomous Facebook posts via 5 AI agents.
Base: `D:\Claude Agent` | GitHub: https://github.com/Cart-kart/avilon-content-team

## Agents
Dollar(trend) → Atlas(editor) → Vector(tech writer) → Spark(ad writer) → Sigma(proofreader)

## Fixed bugs (don't redo)
- Nested Claude session: unset CLAUDECODE + CLAUDE_CODE_ENTRYPOINT before subprocess
- All claude.exe calls use --dangerously-skip-permissions
- parse_urgent_draft: count --- markers, body = after 2nd ---
- Sigma timeout: 300s + file fallback

## Two dashboards
1. Content team: http://localhost:5050 (D:\Claude Agent\dashboard\server.py)
2. Drone ops: https://cart-kart.github.io/dashboard/ (Photon 400 at DHL, pulls Google Sheets)
