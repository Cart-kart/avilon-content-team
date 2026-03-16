# CLAUDE.md — avilonROBOTICS Content Team
> Auto-loaded by Claude Code on every session. Works on any PC.

---

## Project
**avilonROBOTICS AI Content Editor Team**
Thai drone technology company — autonomous Facebook content pipeline.

**Base folder:** `D:\Claude Agent`
**GitHub:** https://github.com/Cart-kart/avilon-content-team
**Dashboard:** http://localhost:5050 (run `python3 dashboard/server.py` to start)
**Public URL:** Check `D:\Claude Agent\reports\tunnel-err.log` after launching Cloudflare tunnel

---

## Agent Team
| Character | File | Role |
|---|---|---|
| Dollar 📡 | `Agents/trend-monitor.md` | Trend scan every 6h |
| Atlas 🎬 | `Agents/editor-in-chief.md` | Editor — assign → review → save to history |
| Vector ✍️ | `Agents/tech-writer.md` | KNOWLEDGE / SOFT SELL / TRENDJACKING posts |
| Spark 📢 | `Agents/ad-writer.md` | HARD SELL posts (3 variants A/B/C) |
| Sigma ✅ | `Agents/proofreader.md` | Proofreader — 7-check QA |

**Installed agents:** `~/.claude/agents/` (run `setup.ps1` to install on new PC)

## Pipeline
`Dollar → Atlas (assign) → Vector/Spark → Atlas (review) → Sigma → Atlas (save) → Dashboard`

---

## Content Schedule
| Day | Type | Writer |
|---|---|---|
| Monday | KNOWLEDGE | Vector |
| Wednesday | SOFT SELL | Vector |
| Friday | TRENDJACKING | Dollar + Vector |
| Sunday | HARD SELL | Spark (3 variants) |

---

## Key Paths
```
Agents:    D:\Claude Agent\Agents\
Dashboard: D:\Claude Agent\dashboard\server.py
Pipeline:  D:\Claude Agent\trend-monitor-run.ps1
Drafts:    D:\Claude Agent\drafts\
Reports:   D:\Claude Agent\reports\
History:   D:\Claude Agent\history\posts.json
Plans:     D:\Claude Agent\plans\current-brief.md
Logs:      D:\Claude Agent\Log\
Memory:    D:\Claude Agent\memory\MEMORY.md
AIAGENTS:  D:\Claude Agent\Agents\AIAGENTS\ (platform-agnostic prompts)
Shortcut:  D:\Claude Agent\Contect Dashboard\Open Dashboard.lnk
```

---

## Infrastructure
- **Claude CLI:** `C:\Users\A\.local\bin\claude.exe`
- **Task Scheduler:** AvilonTrendMonitor — runs every 6 hours
- **Cloudflare:** `C:\Program Files (x86)\cloudflared\cloudflared.exe tunnel --url http://localhost:5050`
- **Python:** Flask 3.1.3 — `python3 dashboard/server.py`

---

## Brand (all agents must follow)
- **Language:** Thai primary, English for tech terms
- **Voice:** "ค่ะ" — น้องฟ้าใส persona
- **Contact:** 📞 098-948-9743 | 📧 contact@avilonrobotics.com
- **Hashtags:** 8–20 per post, mix Thai + English, always include `#avilonROBOTICS`
- **Tone:** Professional, innovative, warm — NOT salesy
- **Emoji:** Bullets/icons only — never mid-Thai-sentence

---

## Known Fixes (don't re-break these)
- **Nested Claude session:** Pipeline subprocesses must unset `CLAUDECODE` + `CLAUDE_CODE_ENTRYPOINT` env vars before spawning `claude.exe` — already in `server.py` as `CLAUDE_ENV`
- **Permissions:** All `claude.exe` subprocess calls use `--dangerously-skip-permissions`
- **Sigma timeout:** Set to 300s with file fallback (reads draft STATUS if stdout empty)
- **Draft body parsing:** Use `---` count (2 dashes = frontmatter end), not meta-populated flag

---

## On a New PC — Quick Setup
1. `git clone https://github.com/Cart-kart/avilon-content-team "D:\Claude Agent"`
2. `cd "D:\Claude Agent" && powershell -File setup.ps1`
3. `python3 -m pip install flask`
4. Start dashboard: `python3 dashboard/server.py`

---

## Recent Session Work (2026-03-13 → 2026-03-16)
- Upgraded all 5 agents to v2 spec (new flow, memory, TITLE/SUBTITLE/CONTENT/NOTES format)
- Fixed nested Claude session error in pipeline
- Dashboard urgent pipeline working (Atlas→Vector→Sigma)
- Task Scheduler updated to every 6 hours
- AIAGENTS folder — all prompts exported for ChatGPT/Gemini/any API
- Dashboard shortcut created in `Contect Dashboard\`
