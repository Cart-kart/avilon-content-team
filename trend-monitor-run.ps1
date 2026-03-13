# avilonROBOTICS — Full Content Pipeline Runner
# Runs every 2 hours via Windows Task Scheduler
# Flow: trend-monitor → editor-in-chief → tech-writer/ad-writer → proofreader

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$logFile = "D:\Claude Agent\reports\trend-monitor.log"
$claudeExe = "C:\Users\A\.local\bin\claude.exe"

Add-Content $logFile "[$timestamp] Pipeline started"

# ─────────────────────────────────────────
# STEP 1: TREND MONITOR — Scan & report
# ─────────────────────────────────────────
Add-Content $logFile "[$timestamp] Step 1: trend-monitor scanning..."

$step1 = @"
You are the trend-monitor agent for avilonROBOTICS.

Read these files first:
- D:/Claude Agent/company-profile.md
- D:/Claude Agent/content-learning.md

Search for trending topics RIGHT NOW on:
- X/Twitter: warehouse, logistics, drone, automation, supply chain, Thailand, คลังสินค้า, โดรน
- Google Trends: logistics, warehouse drone, automation Thailand, ซัพพลายเชน
- News: TechCrunch, The Loadstar, Thai logistics/tech news

Relevance filter — include only if matches:
- logistics / supply chain / warehouse / inventory management
- drone technology / indoor drone / autonomous systems
- Thai e-commerce / B2B tech / automation / Industry 4.0
- EV / green logistics / smart factory / robotics

Urgency levels:
HOT     = viral now, act within 2 hours
RISING  = growing fast, act today
WATCH   = worth tracking this week
IGNORE  = not relevant

Write the full trend report to: D:/Claude Agent/reports/trend-report.md
Use this format exactly:
# TREND REPORT
Generated: [datetime] | Cycle: [morning/afternoon/evening]

## HOT
TREND: [name/hashtag]
SIGNAL: [metric]
ANGLE: [how it connects to avilonROBOTICS / Photon Inventra]
PLATFORM: [platforms]
ACTION: Post within [X] hours

## RISING
TREND: [name]
SIGNAL: [metric]
ANGLE: [content angle]
PLATFORM: [platforms]
ACTION: Post today

## WATCH
TREND: [name]
SIGNAL: [metric]
ACTION: Track for [X] days

After writing the report, output only one line:
STATUS: HOT | STATUS: RISING | STATUS: WATCH | STATUS: NONE
"@

$step1Result = & $claudeExe --print $step1
Add-Content $logFile "[$timestamp] Step 1 result: $step1Result"

# Only continue pipeline if trend is HOT or RISING
if ($step1Result -notmatch "STATUS: HOT|STATUS: RISING") {
    Add-Content $logFile "[$timestamp] No HOT/RISING trend. Pipeline stopped."
    exit 0
}

# ─────────────────────────────────────────
# STEP 2: EDITOR IN CHIEF — Assign brief
# ─────────────────────────────────────────
Add-Content $logFile "[$timestamp] Step 2: editor-in-chief assigning brief..."

$step2 = @"
You are the Editor in Chief for avilonROBOTICS content team.

Read these files:
- D:/Claude Agent/company-profile.md
- D:/Claude Agent/content-learning.md
- D:/Claude Agent/content-types.md
- D:/Claude Agent/reports/trend-report.md

A HOT or RISING trend has been detected. Your job:
1. Read the trend report
2. Decide which writer to assign: tech-writer (KNOWLEDGE/SOFT SELL/TRENDJACKING) or ad-writer (HARD SELL)
3. For a trendjacking post — assign to tech-writer
4. Write a full content brief and save it to: D:/Claude Agent/plans/current-brief.md

Brief format:
ASSIGN: [tech-writer or ad-writer]
TYPE: TRENDJACKING
PLATFORM: Facebook
TOPIC: [one-line topic based on the trend]
KEY MESSAGE: [what should the reader feel/know/do]
TREND: [the trend name and urgency level]
ANGLE: [how to connect trend to Photon Inventra warehouse drone]
DEADLINE: URGENT — post within 2 hours
TONE: [based on content-types.md TRENDJACKING guidelines]

After saving the brief, output only: ASSIGNED: tech-writer OR ASSIGNED: ad-writer
"@

$step2Result = & $claudeExe --print $step2
Add-Content $logFile "[$timestamp] Step 2 result: $step2Result"

# ─────────────────────────────────────────
# STEP 3: WRITER — Generate post
# ─────────────────────────────────────────
Add-Content $logFile "[$timestamp] Step 3: writer generating post..."

$step3 = @"
You are the tech-writer agent for avilonROBOTICS.

Read these files:
- D:/Claude Agent/company-profile.md
- D:/Claude Agent/content-learning.md
- D:/Claude Agent/content-types.md
- D:/Claude Agent/plans/current-brief.md
- D:/Claude Agent/reports/trend-report.md

Write a TRENDJACKING Facebook post following the brief exactly.

Rules:
- Thai language primary, English for tech terms only
- Voice: "ค่ะ" — น้องฟ้าใส persona
- Tone: timely, insightful, forward-thinking — tie trend to Photon Inventra naturally
- Length: 200–400 words
- CTA: medium — mention Demo + contact
- Include 📞 098-948-9743 and 📧 contact@avilonrobotics.com
- Hashtags: 8–20, mix Thai + English

Save the draft to: D:/Claude Agent/drafts/trendjacking-latest.md

Include at the top of the file:
---
TREND URGENCY: [HOT/RISING]
DEADLINE: [datetime — e.g. "Post by 14:00 today"]
GENERATED: [current datetime]
STATUS: PENDING REVIEW
---

After saving, output only: DRAFT SAVED
"@

$step3Result = & $claudeExe --print $step3
Add-Content $logFile "[$timestamp] Step 3 result: $step3Result"

# ─────────────────────────────────────────
# STEP 4: PROOFREADER — QA check
# ─────────────────────────────────────────
Add-Content $logFile "[$timestamp] Step 4: proofreader reviewing..."

$step4 = @"
You are the proofreader agent for avilonROBOTICS.

Read these files:
- D:/Claude Agent/company-profile.md
- D:/Claude Agent/content-learning.md
- D:/Claude Agent/drafts/trendjacking-latest.md

Review the draft post for:
1. Spelling and grammar (Thai + English)
2. Brand voice match — professional, warm, not salesy
3. Factual accuracy — no unverified stats or exaggerations
4. Emoji usage — as bullets/icons only, not mid-sentence
5. Hashtag count — 8 to 20, relevant only
6. CTA present — contact info included
7. Platform fit — appropriate for Facebook

If the post passes all checks:
- Update the STATUS in D:/Claude Agent/drafts/trendjacking-latest.md from PENDING REVIEW to APPROVED
- Output: VERDICT: APPROVED

If the post has issues:
- Fix them directly in the file
- Update STATUS to APPROVED after fixing
- Output: VERDICT: APPROVED (FIXED)

Only output VERDICT: BLOCKED if there is a serious brand or factual issue that requires human review.
"@

$step4Result = & $claudeExe --print $step4
Add-Content $logFile "[$timestamp] Step 4 result: $step4Result"
Add-Content $logFile "[$timestamp] Pipeline completed. Draft at: D:\Claude Agent\drafts\trendjacking-latest.md"

Write-Output "Pipeline complete. Final status: $step4Result"
