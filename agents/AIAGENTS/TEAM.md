# avilonROBOTICS — AI Content Team
> Complete agent team for Facebook content production
> Compatible with: ChatGPT / Claude / Gemini / Mistral / any LLM API

---

## THE TEAM

| Agent | Character | Role | Model suggested |
|---|---|---|---|
| **Dollar** | Age 23, Gen Z, Female | Trend scanner | Any (GPT-4o / Claude / Gemini) |
| **Atlas** | Age 42, Gen X, Male | Editor in Chief | Best available (GPT-4o / Claude Opus) |
| **Vector** | Age 35, Millennial, Male | Tech writer | Mid-tier (GPT-4o-mini / Claude Sonnet) |
| **Spark** | Age 29, Millennial, Female | Ad writer (HARD SELL) | Mid-tier (GPT-4o-mini / Claude Sonnet) |
| **Sigma** | Age 38, Millennial, Male | Proofreader | Mid-tier (GPT-4o-mini / Claude Sonnet) |

---

## PIPELINE FLOW

```
Dollar (trend scan)
   ↓
   Saves: TREND REPORT
   ↓
Atlas (Step A — read trends, create brief)
   ↓
   Saves: CONTENT BRIEF
   ↓
Vector OR Spark (write draft based on brief)
   ↓
   Saves: DRAFT (STATUS: PENDING ATLAS REVIEW)
   ↓
Atlas (Step B — review: duplicate / topic / tone / quality)
   ↓ PASS                    ↓ REVISE
   ↓                         → back to Vector/Spark
Sigma (fix grammar/tone/repeat)
   ↓ APPROVED               ↓ BLOCKED
   ↓                         → human review
Atlas (Step C — save to history, set STATUS: DRAFT)
   ↓
Dashboard (wait for human to approve & publish)
```

---

## HOW TO USE ON ANY AI PLATFORM

### Option 1 — One agent at a time (simple)
Copy the SYSTEM PROMPT section from the relevant `.md` file → paste as system prompt in ChatGPT, Claude, Gemini, etc. → provide the input → get the output.

### Option 2 — API chain (automated)
Use `agents.json` to get all system prompts in JSON format. Build a pipeline that:
1. Calls Dollar with "Scan now"
2. Passes Dollar's output to Atlas (Step A)
3. Passes Atlas's brief to Vector or Spark
4. Passes draft to Atlas (Step B)
5. Passes approved draft to Sigma
6. Passes Sigma's output back to Atlas (Step C)

### Option 3 — n8n / Make / Zapier
Import `agents.json` → create HTTP nodes for each AI API call → chain with conditions (check STATUS line output to route).

---

## WEEKLY SCHEDULE

| Day | Post Type | Writer | Length |
|---|---|---|---|
| Monday | KNOWLEDGE | Vector | 400–800 words |
| Wednesday | SOFT SELL | Vector | 200–400 words |
| Friday | TRENDJACKING | Vector (needs Dollar first) | 200–400 words |
| Sunday | HARD SELL | Spark (3 variants) | 150–300 words |

---

## INPUT → OUTPUT CHAIN (detailed)

### Dollar receives:
- "Scan now"
- OR "Scan: [topic area]"
- OR list of recent post topics to avoid

### Dollar outputs:
- Full TREND REPORT with HOT/RISING/WATCH trends + hashtags
- STATUS line: `STATUS: HOT | RISING | WATCH | NONE`

### Atlas (Step A) receives:
- Dollar's TREND REPORT
- OR "Create brief for [post type]" (manual request)
- OR "It's [day of week] — what should we post today?"

### Atlas (Step A) outputs:
- CONTENT BRIEF (ASSIGN / TYPE / TOPIC / KEY MESSAGE / ANGLE / TONE / DEADLINE)
- Status: `BRIEF CREATED — [topic] → assigned to [Vector/Spark]`

### Vector / Spark receives:
- Atlas's CONTENT BRIEF

### Vector / Spark outputs:
- Full draft (TITLE / SUBTITLE / CONTENT / NOTES)
- Status header: `STATUS: PENDING ATLAS REVIEW`

### Atlas (Step B) receives:
- The draft from Vector or Spark

### Atlas (Step B) outputs:
- `ATLAS REVIEW: PASS — send to Sigma`
- OR `ATLAS REVIEW: REVISE — [check]: [reason]`

### Sigma receives:
- Draft with `STATUS: PENDING SIGMA REVIEW`

### Sigma outputs:
- Corrected draft (if needed)
- `VERDICT: APPROVED — Sigma`
- OR `VERDICT: BLOCKED — Sigma | REASON: [reason]`

### Atlas (Step C) receives:
- Sigma's approved draft

### Atlas (Step C) outputs:
- Confirms saving to history
- Updates draft STATUS to: `DRAFT — Ready for publishing ✅`

---

## BRAND QUICK REFERENCE (all agents need this)

| Field | Value |
|---|---|
| Company | avilonROBOTICS |
| Tagline | "We carry the future" |
| Language | Thai primary, English for tech terms |
| Voice | "ค่ะ" — น้องฟ้าใส persona |
| Contact | น้องฟ้าใส 📞 098-948-9743 | 📧 contact@avilonrobotics.com |
| Hashtags | 8–20 per post, mix Thai + English |
| Core hashtag | #avilonROBOTICS (always) |
| Emoji rule | Bullets/icons only — never mid-sentence |
| No-go | Invented stats, unverified superlatives, hard-sell in KNOWLEDGE posts |

---

## FILES IN THIS FOLDER

| File | Agent | Use |
|---|---|---|
| `DOLLAR.md` | Dollar | Trend scanner system prompt |
| `ATLAS.md` | Atlas | Editor in Chief system prompt (3 steps) |
| `VECTOR.md` | Vector | Tech writer system prompt |
| `SPARK.md` | Spark | Ad writer system prompt (HARD SELL, 3 variants) |
| `SIGMA.md` | Sigma | Proofreader system prompt |
| `TEAM.md` | All | This file — team overview and pipeline |
| `agents.json` | All | JSON format for API integration |
