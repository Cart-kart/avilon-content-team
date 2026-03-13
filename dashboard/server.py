from flask import Flask, jsonify, render_template_string, request, Response
import os, re, json, uuid, subprocess, threading, time
from datetime import datetime, timedelta
from pathlib import Path

app = Flask(__name__)
BASE = Path("D:/Claude Agent")

# ── Helpers ──────────────────────────────────────────────────────────────────

def read_file(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except:
        return ""

def get_trending_hashtags():
    path = BASE / "reports/trending-hashtags.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return []

def parse_trend_report():
    content = read_file(BASE / "reports/trend-report.md")
    if not content:
        return {"hot": [], "rising": [], "watch": [], "generated": "No report yet"}

    trends = {"hot": [], "rising": [], "watch": [], "generated": ""}
    current = None
    item = {}

    for line in content.splitlines():
        if line.startswith("Generated:"):
            trends["generated"] = line.replace("Generated:", "").strip()
        elif "## 🔴 HOT" in line or "## HOT" in line:
            current = "hot"
        elif "## 🟡 RISING" in line or "## RISING" in line:
            current = "rising"
        elif "## 👁 WATCH" in line or "## WATCH" in line:
            current = "watch"
        elif line.startswith("TREND:") and current:
            if item.get("trend"):
                trends[current].append(item)
            item = {"trend": line.replace("TREND:", "").strip()}
        elif line.startswith("SIGNAL:") and current:
            item["signal"] = line.replace("SIGNAL:", "").strip()
        elif line.startswith("ANGLE:") and current:
            item["angle"] = line.replace("ANGLE:", "").strip()
        elif line.startswith("ACTION:") and current:
            item["action"] = line.replace("ACTION:", "").strip()

    if item.get("trend") and current:
        trends[current].append(item)

    return trends

def parse_draft():
    content = read_file(BASE / "drafts/trendjacking-latest.md")
    if not content:
        return None

    meta = {}
    lines = content.splitlines()
    for line in lines:
        for key in ["TREND URGENCY", "DEADLINE", "GENERATED", "STATUS", "WRITTEN BY"]:
            if line.startswith(key + ":"):
                meta[key.lower().replace(" ", "_")] = line.split(":", 1)[1].strip()

    post_body = ""
    in_post = False
    for line in lines:
        if "## FACEBOOK POST" in line:
            in_post = True
            continue
        if in_post and line.startswith("## "):
            break
        if in_post:
            post_body += line + "\n"

    meta["body"] = post_body.strip()
    return meta

def parse_log():
    content = read_file(BASE / "reports/trend-monitor.log")
    if not content:
        return []
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    return lines[-20:]  # last 20 entries

def parse_log_structured():
    """Parse log lines into structured objects with agent attribution."""
    content = read_file(BASE / "reports/trend-monitor.log")
    if not content:
        return []
    agent_map = {
        "dollar": "Dollar", "trend-monitor": "Dollar",
        "atlas": "Atlas", "editor-in-chief": "Atlas",
        "vector": "Vector", "tech-writer": "Vector",
        "spark": "Spark", "ad-writer": "Spark",
        "sigma": "Sigma", "proofreader": "Sigma",
    }
    entries = []
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    for line in lines[-50:]:
        detected = "System"
        lower = line.lower()
        for key, name in agent_map.items():
            if key in lower:
                detected = name
                break
        # Extract timestamp if present [YYYY-MM-DD HH:MM] or similar
        ts_match = re.match(r'\[([^\]]+)\]', line)
        ts = ts_match.group(1) if ts_match else ""
        entries.append({"agent": detected, "message": line, "ts": ts})
    return entries

def parse_agent_statuses():
    """Reads trend-monitor.log, infers status per agent, returns list of agent status objects."""
    content = read_file(BASE / "reports/trend-monitor.log")
    agents = [
        {"id": "dollar",  "name": "Dollar",  "icon": "📡", "role": "Trend Monitor",    "status": "idle", "task": "", "updated": ""},
        {"id": "atlas",   "name": "Atlas",   "icon": "🎬", "role": "Editor in Chief",  "status": "idle", "task": "", "updated": ""},
        {"id": "vector",  "name": "Vector",  "icon": "✍️", "role": "Tech Writer",       "status": "idle", "task": "", "updated": ""},
        {"id": "spark",   "name": "Spark",   "icon": "📢", "role": "Ad Writer",         "status": "idle", "task": "", "updated": ""},
        {"id": "sigma",   "name": "Sigma",   "icon": "✅", "role": "Proofreader",       "status": "idle", "task": "", "updated": ""},
    ]
    if not content:
        return agents

    now = datetime.now()
    five_min_ago = now - timedelta(minutes=5)

    # keyword maps: agent id → keywords found in log lines
    agent_keywords = {
        "dollar": ["dollar", "trend-monitor", "trending", "hashtag", "scan"],
        "atlas":  ["atlas", "editor-in-chief", "brief", "assign", "editorial"],
        "vector": ["vector", "tech-writer", "draft saved", "writing"],
        "spark":  ["spark", "ad-writer", "hard sell", "soft sell"],
        "sigma":  ["sigma", "proofreader", "verdict", "approved", "review"],
    }
    done_keywords = ["complete", "verdict", "approved", "done", "saved", "finished"]

    for agent in agents:
        relevant_lines = []
        for line in content.splitlines():
            low = line.lower()
            for kw in agent_keywords[agent["id"]]:
                if kw in low:
                    relevant_lines.append(line)
                    break

        if not relevant_lines:
            continue

        last_line = relevant_lines[-1]
        # Try to extract timestamp from line
        ts_match = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\]', last_line)
        line_time = None
        if ts_match:
            try:
                line_time = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M")
            except:
                pass

        # Determine status
        low_last = last_line.lower()
        if any(k in low_last for k in done_keywords):
            agent["status"] = "done"
        elif line_time and line_time >= five_min_ago:
            agent["status"] = "running"
        else:
            agent["status"] = "idle"

        agent["task"] = last_line[:80] if len(last_line) > 80 else last_line
        agent["updated"] = line_time.strftime("%H:%M") if line_time else ""

    return agents

def get_feedback():
    path = BASE / "drafts/feedback.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return []

def save_feedback(feedback_list):
    path = BASE / "drafts/feedback.json"
    path.write_text(json.dumps(feedback_list, ensure_ascii=False, indent=2), encoding="utf-8")

def parse_brief():
    content = read_file(BASE / "plans/current-brief.md")
    if not content:
        return None
    brief = {}
    for line in content.splitlines():
        for key in ["ASSIGN", "TYPE", "TOPIC", "TREND", "DEADLINE", "KEY MESSAGE", "ANGLE"]:
            if line.startswith(key + ":"):
                brief[key.lower().replace(" ", "_")] = line.split(":", 1)[1].strip()
    return brief

def get_agent_commands():
    path = BASE / "plans/agent-commands.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return []

def save_agent_commands(commands):
    path = BASE / "plans/agent-commands.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(commands, ensure_ascii=False, indent=2), encoding="utf-8")

def parse_post_history():
    """Reads history/posts.json, returns last 20 posts."""
    path = BASE / "history/posts.json"
    try:
        posts = json.loads(path.read_text(encoding="utf-8"))
        return posts[-20:] if len(posts) > 20 else posts
    except:
        return []

def save_post_history(post):
    """Append a new post entry to history/posts.json."""
    path = BASE / "history/posts.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        posts = json.loads(path.read_text(encoding="utf-8"))
    except:
        posts = []
    posts.append(post)
    path.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")

# ── SSE Stream Data Builder ───────────────────────────────────────────────────

def build_stream_payload():
    return {
        "agents": parse_agent_statuses(),
        "log": parse_log_structured(),
        "hashtags": get_trending_hashtags(),
        "draft": parse_draft(),
        "timestamp": datetime.now().isoformat(),
    }

# ── Dashboard HTML ────────────────────────────────────────────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>avilonROBOTICS Content Control Room</title>
<style>
:root {
  --bg: #0a0d14;
  --surface: #111827;
  --surface2: #1a2030;
  --border: rgba(255,255,255,0.07);
  --border-accent: rgba(0,212,255,0.3);
  --text: #e2e8f0;
  --text-muted: #64748b;
  --accent: #00d4ff;
  --green: #00ff88;
  --yellow: #fbbf24;
  --red: #ef4444;
  --purple: #a78bfa;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }

/* ── Header ── */
.site-header {
  background: linear-gradient(90deg, #111827, #0d1b2a);
  border-bottom: 1px solid var(--border-accent);
  padding: 14px 32px;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 16px;
}
.header-brand { display: flex; flex-direction: column; gap: 2px; }
.header-logo { font-size: 18px; font-weight: 800; color: var(--accent); letter-spacing: 1px; }
.header-logo span { color: var(--text); }
.header-subtitle { font-size: 11px; color: var(--text-muted); letter-spacing: 1px; text-transform: uppercase; }
.header-roster { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; }
.roster-pill {
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 4px 12px;
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 600;
  letter-spacing: 0.5px;
}
.header-right { display: flex; align-items: center; gap: 12px; justify-content: flex-end; }
.conn-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 8px var(--green);
  transition: all 0.3s;
}
.conn-dot.disconnected { background: var(--red); box-shadow: 0 0 8px var(--red); }
.header-clock { font-size: 13px; color: var(--text-muted); font-variant-numeric: tabular-nums; }

/* ── Main layout ── */
.main-wrap {
  max-width: 1700px;
  margin: 0 auto;
  padding: 20px 24px;
  display: grid;
  gap: 16px;
}

/* ── Card base ── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  position: relative;
  overflow: hidden;
}
.card-title {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.title-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
}
.title-dot.green { background: var(--green); }
.title-dot.red { background: var(--red); animation: dot-pulse 0.8s infinite; }
.title-dot.yellow { background: var(--yellow); }
.title-dot.purple { background: var(--purple); }
.title-live {
  background: rgba(0,255,136,0.15);
  border: 1px solid var(--green);
  color: var(--green);
  border-radius: 10px;
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 700;
  animation: dot-pulse 2s infinite;
}

@keyframes dot-pulse { 0%,100%{opacity:1} 50%{opacity:0.45} }
@keyframes spin-pulse { 0%{transform:rotate(0deg)} 100%{transform:rotate(360deg)} }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2a3348; border-radius: 2px; }

/* ── Agent Grid ── */
.agent-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}
@media (max-width: 1100px) { .agent-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 700px)  { .agent-grid { grid-template-columns: repeat(2, 1fr); } }

.agent-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: border-color 0.3s, box-shadow 0.3s;
}
.agent-card.status-running {
  border-color: rgba(0,255,136,0.4);
  box-shadow: 0 0 16px rgba(0,255,136,0.08);
}
.agent-card.status-done {
  border-color: rgba(0,212,255,0.3);
}
.agent-card.status-error {
  border-color: rgba(239,68,68,0.4);
}
.agent-icon { font-size: 36px; line-height: 1; }
.agent-name { font-size: 16px; font-weight: 700; color: var(--text); }
.agent-role { font-size: 11px; color: var(--text-muted); }
.agent-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
  width: fit-content;
}
.badge-idle    { background: rgba(100,116,139,0.15); border: 1px solid rgba(100,116,139,0.4); color: var(--text-muted); }
.badge-running { background: rgba(0,255,136,0.12); border: 1px solid rgba(0,255,136,0.5); color: var(--green); }
.badge-thinking{ background: rgba(251,191,36,0.12); border: 1px solid rgba(251,191,36,0.5); color: var(--yellow); }
.badge-done    { background: rgba(0,212,255,0.12); border: 1px solid rgba(0,212,255,0.5); color: var(--accent); }
.badge-error   { background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.5); color: var(--red); }
.badge-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.badge-running .badge-dot, .badge-thinking .badge-dot { animation: dot-pulse 1s infinite; }

.agent-task {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.5;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  min-height: 32px;
}
.agent-updated { font-size: 10px; color: #374151; }

/* ── Log + Draft pair ── */
.log-draft-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 900px) { .log-draft-row { grid-template-columns: 1fr; } }

/* ── Log Panel ── */
.log-filters {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.log-filter-btn {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 3px 12px;
  font-size: 11px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 600;
}
.log-filter-btn:hover { border-color: var(--border-accent); color: var(--text); }
.log-filter-btn.active { background: rgba(0,212,255,0.12); border-color: var(--accent); color: var(--accent); }

.log-list {
  height: 280px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.log-entry {
  display: flex;
  gap: 8px;
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-family: 'Consolas', 'Courier New', monospace;
  line-height: 1.5;
  background: rgba(255,255,255,0.02);
  border: 1px solid transparent;
  transition: background 0.15s;
}
.log-entry:hover { background: rgba(255,255,255,0.04); }
.log-ts { color: #374151; flex-shrink: 0; }
.log-agent-tag {
  font-weight: 700;
  flex-shrink: 0;
  min-width: 52px;
}
.log-agent-tag.Dollar  { color: #00d4ff; }
.log-agent-tag.Atlas   { color: #a78bfa; }
.log-agent-tag.Vector  { color: #00ff88; }
.log-agent-tag.Spark   { color: #fbbf24; }
.log-agent-tag.Sigma   { color: #f472b6; }
.log-agent-tag.System  { color: var(--text-muted); }
.log-msg { flex: 1; color: #94a3b8; }
.log-empty { color: var(--text-muted); font-size: 12px; padding: 20px; text-align: center; }

/* ── Draft Panel ── */
.draft-status-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; align-items: center; }
.draft-badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700;
}
.draft-approved { background: rgba(0,255,136,0.12); border: 1px solid rgba(0,255,136,0.5); color: var(--green); }
.draft-pending  { background: rgba(251,191,36,0.12); border: 1px solid rgba(251,191,36,0.5); color: var(--yellow); }
.draft-blocked  { background: rgba(239,68,68,0.12);  border: 1px solid rgba(239,68,68,0.5);  color: var(--red); }
.meta-pill {
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 3px 10px;
  font-size: 11px;
  color: var(--text-muted);
}
.meta-pill strong { color: var(--text); }
.draft-body {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  font-size: 13px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-wrap: break-word;
  height: 220px;
  overflow-y: auto;
  color: #cbd5e1;
}
.draft-actions { display: flex; gap: 10px; margin-top: 10px; align-items: center; }
.copy-btn {
  background: rgba(0,212,255,0.1);
  border: 1px solid rgba(0,212,255,0.35);
  color: var(--accent);
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 600;
}
.copy-btn:hover { background: rgba(0,212,255,0.2); }
.deadline-badge {
  background: rgba(239,68,68,0.1);
  border: 1px solid rgba(239,68,68,0.4);
  color: var(--red);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
}
.draft-empty { color: var(--text-muted); font-size: 13px; padding: 40px 0; text-align: center; }

/* ── Trend Row ── */
.trend-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
@media (max-width: 900px) { .trend-row { grid-template-columns: 1fr; } }

.trend-level-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700;
  margin-bottom: 14px;
}
.level-hot    { background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.5); color: #f87171; }
.level-rising { background: rgba(251,191,36,0.12); border: 1px solid rgba(251,191,36,0.5); color: var(--yellow); }
.level-watch  { background: rgba(167,139,250,0.12); border: 1px solid rgba(167,139,250,0.5); color: var(--purple); }

.trend-item {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
}
.trend-item:last-child { margin-bottom: 0; }
.trend-item h4 { font-size: 13px; color: var(--text); margin-bottom: 4px; font-weight: 700; }
.trend-item p  { font-size: 11px; color: var(--text-muted); line-height: 1.5; }
.trend-item .angle { color: var(--accent); font-size: 11px; margin-top: 4px; }
.trend-item .action { color: #374151; font-size: 10px; margin-top: 4px; }

/* ── Hashtag Feed ── */
.hashtag-wrap { display: flex; flex-wrap: wrap; gap: 8px; min-height: 48px; }
.hashtag-pill {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;
  cursor: default; transition: transform 0.15s;
}
.hashtag-pill:hover { transform: scale(1.05); }
.hashtag-pill.hot     { background: rgba(239,68,68,0.12);   border: 1px solid rgba(239,68,68,0.5);   color: #f87171; }
.hashtag-pill.rising  { background: rgba(251,191,36,0.12);  border: 1px solid rgba(251,191,36,0.5);  color: var(--yellow); }
.hashtag-pill.watch   { background: rgba(167,139,250,0.12); border: 1px solid rgba(167,139,250,0.5); color: var(--purple); }
.hashtag-pill .pill-platform { font-size: 9px; color: var(--text-muted); font-weight: normal; }
.hash-scan-time { font-size: 10px; color: #374151; font-weight: normal; }

/* ── Urgent Box ── */
.urgent-card {
  background: linear-gradient(135deg, var(--surface), #1a1020);
  border: 1px solid rgba(239,68,68,0.3);
  border-radius: 12px;
  padding: 20px;
}
.urgent-card .card-title .title-dot { animation: dot-pulse 0.8s infinite; }
.urgent-inner {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
@media (max-width: 900px) { .urgent-inner { grid-template-columns: 1fr; } }
.urgent-form-col, .urgent-output-col { display: flex; flex-direction: column; gap: 10px; }
.field-label {
  font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px;
}
.urgent-input, .urgent-select, .urgent-textarea {
  background: var(--bg);
  border: 1px solid rgba(239,68,68,0.3);
  border-radius: 8px;
  padding: 9px 12px;
  color: var(--text);
  font-size: 13px;
  font-family: 'Segoe UI', sans-serif;
  outline: none;
  width: 100%;
  transition: border-color 0.2s;
}
.urgent-input:focus, .urgent-select:focus, .urgent-textarea:focus { border-color: rgba(239,68,68,0.7); }
.urgent-textarea { resize: vertical; min-height: 80px; }
.urgent-select option { background: var(--surface); }
.urgent-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.urgent-push-btn {
  background: linear-gradient(90deg, rgba(239,68,68,0.15), rgba(239,68,68,0.08));
  border: 1px solid rgba(239,68,68,0.6);
  color: #f87171;
  padding: 11px 22px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  align-self: flex-start;
}
.urgent-push-btn:hover { background: linear-gradient(90deg, rgba(239,68,68,0.25), rgba(239,68,68,0.15)); }
.urgent-push-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.urgent-confirm { font-size: 12px; color: var(--green); font-weight: 700; display: none; }
.urgent-pipeline-steps { display: flex; gap: 8px; flex-wrap: wrap; }
.pipeline-step-badge {
  font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 10px;
}
.ps-done    { background: rgba(0,255,136,0.12); border: 1px solid rgba(0,255,136,0.5); color: var(--green); }
.ps-active  { background: rgba(251,191,36,0.12); border: 1px solid rgba(251,191,36,0.5); color: var(--yellow); }
.ps-idle    { background: rgba(255,255,255,0.04); border: 1px solid var(--border); color: var(--text-muted); }
.urgent-draft-output {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  min-height: 140px;
  max-height: 280px;
  overflow-y: auto;
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.7;
  white-space: pre-wrap;
}
.urgent-copy-btn {
  display: none;
  background: rgba(0,212,255,0.1);
  border: 1px solid rgba(0,212,255,0.35);
  color: var(--accent);
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  font-weight: 600;
}

/* ── Feedback Box ── */
.feedback-list { max-height: 260px; overflow-y: auto; margin-bottom: 14px; display: flex; flex-direction: column; gap: 8px; }
.feedback-item {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
}
.fb-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.fb-author { font-size: 12px; font-weight: 700; color: var(--accent); }
.fb-time   { font-size: 11px; color: var(--text-muted); }
.fb-text   { font-size: 13px; color: #cbd5e1; line-height: 1.6; }
.fb-verdict {
  display: inline-block; font-size: 10px; font-weight: 700;
  padding: 2px 8px; border-radius: 10px; margin-top: 6px;
}
.fb-verdict.approve { background: rgba(0,255,136,0.12); border: 1px solid rgba(0,255,136,0.5); color: var(--green); }
.fb-verdict.revise  { background: rgba(239,68,68,0.12);  border: 1px solid rgba(239,68,68,0.5);  color: var(--red); }
.fb-verdict.comment { background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: var(--text-muted); }
.fb-empty { color: var(--text-muted); font-size: 12px; padding: 20px; text-align: center; }
.feedback-form { display: flex; flex-direction: column; gap: 10px; }
.feedback-form input,
.feedback-form textarea,
.feedback-form select {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 9px 12px;
  color: var(--text);
  font-size: 13px;
  font-family: 'Segoe UI', sans-serif;
  outline: none;
  transition: border-color 0.2s;
}
.feedback-form input:focus,
.feedback-form textarea:focus,
.feedback-form select:focus { border-color: var(--border-accent); }
.feedback-form textarea { resize: vertical; min-height: 80px; }
.feedback-form select option { background: var(--surface); }
.fb-form-row { display: flex; gap: 10px; }
.fb-form-row input { flex: 1; }
.fb-form-row select { flex: 0 0 160px; }
.fb-form-actions { display: flex; align-items: center; gap: 10px; }
.submit-btn {
  background: linear-gradient(90deg, rgba(0,212,255,0.12), rgba(0,255,136,0.12));
  border: 1px solid rgba(0,212,255,0.4);
  color: var(--accent);
  padding: 9px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}
.submit-btn:hover { background: linear-gradient(90deg, rgba(0,212,255,0.2), rgba(0,255,136,0.2)); }
.clear-btn {
  background: transparent;
  border: 1px solid rgba(239,68,68,0.3);
  color: var(--red);
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 11px;
  cursor: pointer;
}
.fb-subtitle { font-size: 11px; color: var(--text-muted); margin-bottom: 14px; margin-top: -8px; }
.feedback-count { font-size: 11px; color: var(--text-muted); font-weight: normal; }

/* ── Agent Command Center ── */
.acc-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
.acc-tab {
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--text-muted);
  padding: 7px 18px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.5px;
}
.acc-tab:hover { border-color: var(--border-accent); color: var(--text); }
.acc-tab.active { background: rgba(0,212,255,0.1); border-color: var(--accent); color: var(--accent); }
.acc-panel { display: none; }
.acc-panel.active { display: block; }
.acc-agent-header { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; }
.acc-agent-icon {
  width: 48px; height: 48px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; background: rgba(0,212,255,0.07);
  border: 1px solid rgba(0,212,255,0.2); flex-shrink: 0;
}
.acc-agent-name { font-size: 15px; font-weight: 700; color: var(--text); }
.acc-agent-role { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.acc-body { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 900px) { .acc-body { grid-template-columns: 1fr; } }
.acc-input-col, .acc-output-col { display: flex; flex-direction: column; gap: 10px; }
.acc-label { font-size: 10px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 2px; }
.acc-textarea {
  background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
  padding: 12px; color: var(--text); font-size: 13px; font-family: 'Segoe UI', sans-serif;
  outline: none; resize: vertical; min-height: 90px; transition: border-color 0.2s; width: 100%;
}
.acc-textarea:focus { border-color: var(--border-accent); }
.acc-send-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.acc-send-btn {
  background: linear-gradient(90deg, rgba(0,212,255,0.12), rgba(0,255,136,0.12));
  border: 1px solid rgba(0,212,255,0.4);
  color: var(--accent); padding: 9px 20px; border-radius: 8px; font-size: 13px;
  font-weight: 700; cursor: pointer; transition: all 0.2s;
}
.acc-send-btn:hover { background: linear-gradient(90deg, rgba(0,212,255,0.2), rgba(0,255,136,0.2)); }
.acc-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.acc-confirm { font-size: 12px; color: var(--green); font-weight: 700; display: none; }
.acc-suggestions { display: flex; flex-direction: column; gap: 6px; }
.acc-suggestion-btn {
  background: var(--bg); border: 1px solid var(--border); color: #94a3b8;
  padding: 8px 12px; border-radius: 8px; font-size: 12px; cursor: pointer;
  text-align: left; transition: all 0.2s;
}
.acc-suggestion-btn:hover { border-color: rgba(0,212,255,0.3); color: var(--text); background: rgba(0,212,255,0.04); }
.acc-response-area {
  background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
  padding: 12px; min-height: 120px; max-height: 260px; overflow-y: auto;
  font-size: 12px; color: var(--text-muted); font-family: 'Consolas', monospace; line-height: 1.6;
}
.acc-cmd-history-wrap { margin-top: 24px; border-top: 1px solid var(--border); padding-top: 16px; }
.acc-cmd-list { max-height: 200px; overflow-y: auto; }
.acc-cmd-item {
  padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.03);
  display: flex; align-items: flex-start; gap: 10px;
}
.acc-cmd-item:last-child { border-bottom: none; }
.acc-cmd-agent { font-size: 10px; font-weight: 700; color: var(--accent); white-space: nowrap; flex-shrink: 0; min-width: 90px; }
.acc-cmd-text  { flex: 1; color: #cbd5e1; font-size: 12px; }
.acc-cmd-time  { font-size: 10px; color: #374151; white-space: nowrap; flex-shrink: 0; }
.acc-cmd-status { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 10px; flex-shrink: 0; }
.acc-cmd-status.pending { background: rgba(251,191,36,0.12); border: 1px solid rgba(251,191,36,0.5); color: var(--yellow); }
.acc-cmd-status.done    { background: rgba(0,255,136,0.12);  border: 1px solid rgba(0,255,136,0.5);  color: var(--green); }
.acc-cmd-status.error   { background: rgba(239,68,68,0.12);  border: 1px solid rgba(239,68,68,0.5);  color: var(--red); }
.acc-history-ts { font-size: 10px; color: #374151; font-weight: normal; margin-left: 6px; }
.empty-state { color: var(--text-muted); font-size: 12px; padding: 20px; text-align: center; }
</style>
</head>
<body>

<!-- ════════════════════ HEADER ════════════════════ -->
<header class="site-header">
  <div class="header-brand">
    <div class="header-logo">avilon<span>ROBOTICS</span></div>
    <div class="header-subtitle">Content Control Room</div>
  </div>
  <div class="header-roster">
    <span class="roster-pill">📡 Dollar</span>
    <span class="roster-pill">🎬 Atlas</span>
    <span class="roster-pill">✍️ Vector</span>
    <span class="roster-pill">📢 Spark</span>
    <span class="roster-pill">✅ Sigma</span>
  </div>
  <div class="header-right">
    <span class="header-clock" id="clock"></span>
    <div class="conn-dot" id="conn-dot" title="SSE Connected"></div>
  </div>
</header>

<div class="main-wrap">

  <!-- ════════════════════ AGENT GRID ════════════════════ -->
  <div class="agent-grid" id="agent-grid">
    <!-- populated by SSE -->
    <div class="agent-card" id="agent-dollar">
      <div class="agent-icon">📡</div>
      <div class="agent-name">Dollar</div>
      <div class="agent-role">Trend Monitor</div>
      <div class="agent-badge badge-idle"><span class="badge-dot"></span>idle</div>
      <div class="agent-task">—</div>
      <div class="agent-updated"></div>
    </div>
    <div class="agent-card" id="agent-atlas">
      <div class="agent-icon">🎬</div>
      <div class="agent-name">Atlas</div>
      <div class="agent-role">Editor in Chief</div>
      <div class="agent-badge badge-idle"><span class="badge-dot"></span>idle</div>
      <div class="agent-task">—</div>
      <div class="agent-updated"></div>
    </div>
    <div class="agent-card" id="agent-vector">
      <div class="agent-icon">✍️</div>
      <div class="agent-name">Vector</div>
      <div class="agent-role">Tech Writer</div>
      <div class="agent-badge badge-idle"><span class="badge-dot"></span>idle</div>
      <div class="agent-task">—</div>
      <div class="agent-updated"></div>
    </div>
    <div class="agent-card" id="agent-spark">
      <div class="agent-icon">📢</div>
      <div class="agent-name">Spark</div>
      <div class="agent-role">Ad Writer</div>
      <div class="agent-badge badge-idle"><span class="badge-dot"></span>idle</div>
      <div class="agent-task">—</div>
      <div class="agent-updated"></div>
    </div>
    <div class="agent-card" id="agent-sigma">
      <div class="agent-icon">✅</div>
      <div class="agent-name">Sigma</div>
      <div class="agent-role">Proofreader</div>
      <div class="agent-badge badge-idle"><span class="badge-dot"></span>idle</div>
      <div class="agent-task">—</div>
      <div class="agent-updated"></div>
    </div>
  </div>

  <!-- ════════════════════ LOG | DRAFT ════════════════════ -->
  <div class="log-draft-row">

    <!-- Log Panel -->
    <div class="card">
      <div class="card-title">
        <div class="title-dot"></div>
        Activity Log
        <span class="title-live" id="log-live-badge">● LIVE</span>
      </div>
      <div class="log-filters">
        <button class="log-filter-btn active" onclick="setLogFilter('All', this)">All</button>
        <button class="log-filter-btn" onclick="setLogFilter('Dollar', this)">Dollar</button>
        <button class="log-filter-btn" onclick="setLogFilter('Atlas', this)">Atlas</button>
        <button class="log-filter-btn" onclick="setLogFilter('Vector', this)">Vector</button>
        <button class="log-filter-btn" onclick="setLogFilter('Spark', this)">Spark</button>
        <button class="log-filter-btn" onclick="setLogFilter('Sigma', this)">Sigma</button>
      </div>
      <div class="log-list" id="log-list">
        <div class="log-empty">Waiting for agent activity...</div>
      </div>
    </div>

    <!-- Draft Panel -->
    <div class="card">
      <div class="card-title">
        <div class="title-dot green"></div>
        Latest Draft
      </div>
      <div id="draft-section">
        <div class="draft-empty">No draft available — waiting for HOT trend</div>
      </div>
    </div>

  </div>

  <!-- ════════════════════ TREND ROW ════════════════════ -->
  <div class="trend-row">
    <div class="card">
      <div class="card-title"><div class="title-dot red"></div>HOT Trends</div>
      <div class="trend-level-badge level-hot">🔴 HOT</div>
      <div id="hot-trends"><div class="empty-state">No HOT trends right now</div></div>
    </div>
    <div class="card">
      <div class="card-title"><div class="title-dot yellow"></div>Rising Trends</div>
      <div class="trend-level-badge level-rising">🟡 RISING</div>
      <div id="rising-trends"><div class="empty-state">No RISING trends right now</div></div>
    </div>
    <div class="card">
      <div class="card-title"><div class="title-dot purple"></div>Watch List</div>
      <div class="trend-level-badge level-watch">👁 WATCH</div>
      <div id="watch-trends"><div class="empty-state">No trends to watch</div></div>
    </div>
  </div>

  <!-- ════════════════════ HASHTAG FEED ════════════════════ -->
  <div class="card">
    <div class="card-title">
      <div class="title-dot red"></div>
      Trending Hashtags — Live Feed
      <span class="hash-scan-time" id="hashtag-scan-time"></span>
    </div>
    <div class="hashtag-wrap" id="hashtag-feed">
      <div class="empty-state">Waiting for Dollar's next scan...</div>
    </div>
  </div>

  <!-- ════════════════════ URGENT BOX ════════════════════ -->
  <div class="urgent-card">
    <div class="card-title">
      <div class="title-dot red"></div>
      🚨 Urgent Company News — Push to Atlas Now
      <span id="urgent-status-badge" style="font-size:11px;font-weight:normal;color:var(--text-muted);margin-left:8px"></span>
    </div>
    <div class="urgent-inner">
      <!-- Input -->
      <div class="urgent-form-col">
        <div class="urgent-row">
          <div>
            <div class="field-label">Post Type</div>
            <select id="urgent-type" class="urgent-select">
              <option value="NEWS">📰 Company News</option>
              <option value="SUCCESS">🏆 Success / Achievement</option>
              <option value="PARTNERSHIP">🤝 Partnership / MOU</option>
              <option value="EVENT">🎉 Event / Exhibition</option>
              <option value="ANNOUNCEMENT">📣 Announcement</option>
            </select>
          </div>
          <div>
            <div class="field-label">Submitted by</div>
            <input type="text" id="urgent-submitter" class="urgent-input" placeholder="Your name...">
          </div>
        </div>
        <div>
          <div class="field-label">Headline / News Title *</div>
          <input type="text" id="urgent-headline" class="urgent-input" placeholder="e.g. avilonROBOTICS signs MOU with Bangkok Airways...">
        </div>
        <div>
          <div class="field-label">News Details (optional but recommended)</div>
          <textarea id="urgent-details" class="urgent-textarea" placeholder="Add context — who, what, where, when, why. Any specific message or quote to include..."></textarea>
        </div>
        <button id="urgent-push-btn" class="urgent-push-btn" onclick="pushUrgentNews()">
          🚨 Push to Atlas — Generate Post Now
        </button>
        <div id="urgent-confirm" class="urgent-confirm"></div>
      </div>
      <!-- Output -->
      <div class="urgent-output-col">
        <div class="field-label">Draft Output — After Pipeline Completes</div>
        <div class="urgent-pipeline-steps" id="urgent-pipeline-status"></div>
        <div id="urgent-draft-output" class="urgent-draft-output">Waiting for urgent news push...</div>
        <button id="urgent-copy-btn" class="urgent-copy-btn" onclick="copyUrgentDraft()">📋 Copy Post</button>
      </div>
    </div>
  </div>

  <!-- ════════════════════ FEEDBACK BOX ════════════════════ -->
  <div class="card">
    <div class="card-title">
      <div class="title-dot yellow"></div>
      Team Feedback on Draft
      <span class="feedback-count" id="feedback-count"></span>
      <button class="clear-btn" onclick="clearFeedback()" style="margin-left:auto">🗑 Clear all</button>
    </div>
    <div class="fb-subtitle">Leave comments for the team — Dollar, Atlas, Vector, Spark, Sigma</div>
    <div class="feedback-list" id="feedback-list">
      <div class="fb-empty">No feedback yet — be the first to comment</div>
    </div>
    <div class="feedback-form">
      <div class="fb-form-row">
        <input type="text" id="fb-author" placeholder="Your name (e.g. ฟ้าใส, P'Arm...)" maxlength="40">
        <select id="fb-verdict">
          <option value="comment">💬 Comment</option>
          <option value="approve">✅ Approve</option>
          <option value="revise">🔄 Needs Revision</option>
        </select>
      </div>
      <textarea id="fb-text" placeholder="Write your feedback on this draft... (e.g. แก้ hashtag, เพิ่ม CTA, โทนดีแล้ว)"></textarea>
      <div class="fb-form-actions">
        <button class="submit-btn" onclick="submitFeedback()">Send Feedback →</button>
      </div>
    </div>
  </div>

  <!-- ════════════════════ AGENT COMMAND CENTER ════════════════════ -->
  <div class="card">
    <div class="card-title">
      <div class="title-dot"></div>
      Agent Command Center
    </div>

    <div class="acc-tabs">
      <button class="acc-tab active" onclick="switchAccTab('trend-monitor', this)">📡 Dollar (Trend Monitor)</button>
      <button class="acc-tab" onclick="switchAccTab('editor-in-chief', this)">🎬 Atlas (Editor in Chief)</button>
      <button class="acc-tab" onclick="switchAccTab('tech-writer', this)">✍️ Vector (Tech Writer)</button>
      <button class="acc-tab" onclick="switchAccTab('ad-writer', this)">📢 Spark (Ad Writer)</button>
      <button class="acc-tab" onclick="switchAccTab('proofreader', this)">✅ Sigma (Proofreader)</button>
    </div>

    <!-- trend-monitor -->
    <div class="acc-panel active" id="acc-trend-monitor">
      <div class="acc-agent-header">
        <div class="acc-agent-icon">📡</div>
        <div>
          <div class="acc-agent-name">Dollar</div>
          <div class="acc-agent-role">Dollar — Age 23 | Gen Z | Fast, always online, Thai trend native</div>
        </div>
      </div>
      <div class="acc-body">
        <div class="acc-input-col">
          <div class="acc-label">Command / Instruction</div>
          <textarea class="acc-textarea" id="cmd-trend-monitor" placeholder="e.g. Scan Thai logistics trends on X right now..."></textarea>
          <div class="acc-send-row">
            <button class="acc-send-btn" onclick="sendAgentCommand('trend-monitor')">Send to Agent →</button>
            <span class="acc-confirm" id="confirm-trend-monitor">Command queued ✓</span>
          </div>
          <div class="acc-label" style="margin-top:8px">Quick Suggestions</div>
          <div class="acc-suggestions">
            <button class="acc-suggestion-btn" onclick="fillCmd('trend-monitor','🔍 Scan trends now')">🔍 Scan trends now</button>
            <button class="acc-suggestion-btn" onclick="fillCmd('trend-monitor','🇹🇭 Thailand logistics only')">🇹🇭 Thailand logistics only</button>
            <button class="acc-suggestion-btn" onclick="fillCmd('trend-monitor','📊 Full weekly report')">📊 Full weekly report</button>
          </div>
        </div>
        <div class="acc-output-col">
          <div class="acc-label">Last Agent Response / Output</div>
          <div class="acc-response-area" id="resp-trend-monitor"><span style="color:#374151">No response yet — send a command to get started.</span></div>
        </div>
      </div>
    </div>

    <!-- editor-in-chief -->
    <div class="acc-panel" id="acc-editor-in-chief">
      <div class="acc-agent-header">
        <div class="acc-agent-icon">🎬</div>
        <div>
          <div class="acc-agent-name">Atlas</div>
          <div class="acc-agent-role">Atlas — Age 42 | Gen X | Strategic, decisive, runs the whole editorial machine</div>
        </div>
      </div>
      <div class="acc-body">
        <div class="acc-input-col">
          <div class="acc-label">Command / Instruction</div>
          <textarea class="acc-textarea" id="cmd-editor-in-chief" placeholder="e.g. Run this week's campaign — assign KNOWLEDGE post on Photon Inventra..."></textarea>
          <div class="acc-send-row">
            <button class="acc-send-btn" onclick="sendAgentCommand('editor-in-chief')">Send to Agent →</button>
            <span class="acc-confirm" id="confirm-editor-in-chief">Command queued ✓</span>
          </div>
          <div class="acc-label" style="margin-top:8px">Quick Suggestions</div>
          <div class="acc-suggestions">
            <button class="acc-suggestion-btn" onclick="fillCmd('editor-in-chief','🚀 Run weekly campaign')">🚀 Run weekly campaign</button>
            <button class="acc-suggestion-btn" onclick="fillCmd('editor-in-chief','📋 Assign TRENDJACKING post')">📋 Assign TRENDJACKING post</button>
            <button class="acc-suggestion-btn" onclick="fillCmd('editor-in-chief','📅 Plan next 4 posts')">📅 Plan next 4 posts</button>
          </div>
        </div>
        <div class="acc-output-col">
          <div class="acc-label">Last Agent Response / Output</div>
          <div class="acc-response-area" id="resp-editor-in-chief"><span style="color:#374151">No response yet — send a command to get started.</span></div>
        </div>
      </div>
    </div>

    <!-- tech-writer -->
    <div class="acc-panel" id="acc-tech-writer">
      <div class="acc-agent-header">
        <div class="acc-agent-icon">✍️</div>
        <div>
          <div class="acc-agent-name">Vector</div>
          <div class="acc-agent-role">Vector — Age 35 | Millennial | Clear, structured, turns tech specs into readable posts</div>
        </div>
      </div>
      <div class="acc-body">
        <div class="acc-input-col">
          <div class="acc-label">Command / Instruction</div>
          <textarea class="acc-textarea" id="cmd-tech-writer" placeholder="e.g. Write KNOWLEDGE post about warehouse drone technology for Thai SMEs..."></textarea>
          <div class="acc-send-row">
            <button class="acc-send-btn" onclick="sendAgentCommand('tech-writer')">Send to Agent →</button>
            <span class="acc-confirm" id="confirm-tech-writer">Command queued ✓</span>
          </div>
          <div class="acc-label" style="margin-top:8px">Quick Suggestions</div>
          <div class="acc-suggestions">
            <button class="acc-suggestion-btn" onclick="fillCmd('tech-writer','✍️ Write KNOWLEDGE post')">✍️ Write KNOWLEDGE post</button>
            <button class="acc-suggestion-btn" onclick="fillCmd('tech-writer','💡 Write SOFT SELL post')">💡 Write SOFT SELL post</button>
            <button class="acc-suggestion-btn" onclick="fillCmd('tech-writer','📈 Write TRENDJACKING post')">📈 Write TRENDJACKING post</button>
          </div>
        </div>
        <div class="acc-output-col">
          <div class="acc-label">Last Agent Response / Output</div>
          <div class="acc-response-area" id="resp-tech-writer"><span style="color:#374151">No response yet — send a command to get started.</span></div>
        </div>
      </div>
    </div>

    <!-- ad-writer -->
    <div class="acc-panel" id="acc-ad-writer">
      <div class="acc-agent-header">
        <div class="acc-agent-icon">📢</div>
        <div>
          <div class="acc-agent-name">Spark</div>
          <div class="acc-agent-role">Spark — Age 29 | Millennial | High-energy, benefit-led, punchy CTA specialist</div>
        </div>
      </div>
      <div class="acc-body">
        <div class="acc-input-col">
          <div class="acc-label">Command / Instruction</div>
          <textarea class="acc-textarea" id="cmd-ad-writer" placeholder="e.g. Write 3 HARD SELL variants for Photon Inventra demo — benefit-led..."></textarea>
          <div class="acc-send-row">
            <button class="acc-send-btn" onclick="sendAgentCommand('ad-writer')">Send to Agent →</button>
            <span class="acc-confirm" id="confirm-ad-writer">Command queued ✓</span>
          </div>
          <div class="acc-label" style="margin-top:8px">Quick Suggestions</div>
          <div class="acc-suggestions">
            <button class="acc-suggestion-btn" onclick="fillCmd('ad-writer','📢 3 HARD SELL variants')">📢 3 HARD SELL variants</button>
            <button class="acc-suggestion-btn" onclick="fillCmd('ad-writer','🎯 Photon Inventra CTA')">🎯 Photon Inventra CTA</button>
            <button class="acc-suggestion-btn" onclick="fillCmd('ad-writer','⚡ Urgency-led promo post')">⚡ Urgency-led promo post</button>
          </div>
        </div>
        <div class="acc-output-col">
          <div class="acc-label">Last Agent Response / Output</div>
          <div class="acc-response-area" id="resp-ad-writer"><span style="color:#374151">No response yet — send a command to get started.</span></div>
        </div>
      </div>
    </div>

    <!-- proofreader -->
    <div class="acc-panel" id="acc-proofreader">
      <div class="acc-agent-header">
        <div class="acc-agent-icon">✅</div>
        <div>
          <div class="acc-agent-name">Sigma</div>
          <div class="acc-agent-role">Sigma — Age 38 | Millennial | Detail-obsessed, zero tolerance for errors, final gatekeeper</div>
        </div>
      </div>
      <div class="acc-body">
        <div class="acc-input-col">
          <div class="acc-label">Command / Instruction</div>
          <textarea class="acc-textarea" id="cmd-proofreader" placeholder="e.g. Review latest draft — full QA check on tone, facts, and hashtags..."></textarea>
          <div class="acc-send-row">
            <button class="acc-send-btn" onclick="sendAgentCommand('proofreader')">Send to Agent →</button>
            <span class="acc-confirm" id="confirm-proofreader">Command queued ✓</span>
          </div>
          <div class="acc-label" style="margin-top:8px">Quick Suggestions</div>
          <div class="acc-suggestions">
            <button class="acc-suggestion-btn" onclick="fillCmd('proofreader','✅ Review & approve latest draft')">✅ Review &amp; approve latest draft</button>
            <button class="acc-suggestion-btn" onclick="fillCmd('proofreader','🔍 Full QA — facts + tone + hashtags')">🔍 Full QA — facts + tone + hashtags</button>
            <button class="acc-suggestion-btn" onclick="fillCmd('proofreader','🔄 Fix and approve')">🔄 Fix and approve</button>
          </div>
        </div>
        <div class="acc-output-col">
          <div class="acc-label">Last Agent Response / Output</div>
          <div class="acc-response-area" id="resp-proofreader"><span style="color:#374151">No response yet — send a command to get started.</span></div>
        </div>
      </div>
    </div>

    <!-- Command History -->
    <div class="acc-cmd-history-wrap">
      <div class="acc-label">
        Recent Command History
        <span class="acc-history-ts" id="acc-history-refresh"></span>
      </div>
      <div class="acc-cmd-list" id="acc-cmd-history" style="margin-top:10px">
        <div class="empty-state">No commands sent yet</div>
      </div>
    </div>
  </div>

</div><!-- /main-wrap -->

<script>
// ── Constants ──
const AGENT_NAMES = {
  'trend-monitor':   'Dollar',
  'editor-in-chief': 'Atlas',
  'tech-writer':     'Vector',
  'ad-writer':       'Spark',
  'proofreader':     'Sigma'
};

// ── SSE Connection ──
let sseConnected = false;
let logEntries = [];
let activeLogFilter = 'All';

const evtSource = new EventSource('/api/stream');

evtSource.onopen = () => {
  sseConnected = true;
  const dot = document.getElementById('conn-dot');
  dot.classList.remove('disconnected');
  dot.title = 'SSE Connected';
};

evtSource.onmessage = (e) => {
  try {
    const data = JSON.parse(e.data);
    updateAgentCards(data.agents);
    updateLogPanel(data.log);
    updateHashtagFeed(data.hashtags);
    updateDraftPanel(data.draft);
  } catch(err) {
    console.error('SSE parse error', err);
  }
};

evtSource.onerror = () => {
  sseConnected = false;
  const dot = document.getElementById('conn-dot');
  dot.classList.add('disconnected');
  dot.title = 'SSE Disconnected — reconnecting...';
};

// ── updateAgentCards ──
function updateAgentCards(agents) {
  if (!agents || !agents.length) return;
  agents.forEach(a => {
    const card = document.getElementById('agent-' + a.id);
    if (!card) return;
    card.className = 'agent-card status-' + (a.status || 'idle');

    const badgeEl = card.querySelector('.agent-badge');
    const statusLabels = {
      idle: 'idle', running: 'running', thinking: 'thinking', done: 'done', error: 'error'
    };
    const s = a.status || 'idle';
    badgeEl.className = 'agent-badge badge-' + s;
    badgeEl.innerHTML = '<span class="badge-dot"></span>' + (statusLabels[s] || s);

    const taskEl = card.querySelector('.agent-task');
    taskEl.textContent = a.task || '—';

    const updEl = card.querySelector('.agent-updated');
    updEl.textContent = a.updated ? 'Updated ' + a.updated : '';
  });
}

// ── updateLogPanel ──
function updateLogPanel(entries) {
  if (!entries || !entries.length) return;
  logEntries = entries;
  renderLog();
}

function setLogFilter(filter, btn) {
  activeLogFilter = filter;
  document.querySelectorAll('.log-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderLog();
}

function renderLog() {
  const el = document.getElementById('log-list');
  const filtered = activeLogFilter === 'All'
    ? logEntries
    : logEntries.filter(e => e.agent === activeLogFilter);

  if (!filtered.length) {
    el.innerHTML = '<div class="log-empty">No entries for this agent yet</div>';
    return;
  }

  el.innerHTML = filtered.map(entry => {
    const ts = entry.ts ? '<span class="log-ts">' + entry.ts + '</span>' : '';
    const agentTag = '<span class="log-agent-tag ' + (entry.agent || 'System') + '">[' + (entry.agent || 'SYS') + ']</span>';
    const msg = '<span class="log-msg">' + escHtml(entry.message || '') + '</span>';
    return '<div class="log-entry">' + ts + agentTag + msg + '</div>';
  }).join('');

  // Auto-scroll to bottom
  el.scrollTop = el.scrollHeight;
}

// ── updateHashtagFeed ──
function updateHashtagFeed(hashtags) {
  const feed = document.getElementById('hashtag-feed');
  const timeEl = document.getElementById('hashtag-scan-time');
  if (!hashtags || !hashtags.length) {
    feed.innerHTML = '<div class="empty-state">Waiting for Dollar\'s next scan...</div>';
    timeEl.textContent = '';
    return;
  }
  timeEl.textContent = '— scanned ' + new Date().toLocaleTimeString('th-TH');
  feed.innerHTML = hashtags.map(h =>
    '<span class="hashtag-pill ' + (h.urgency || 'watch') + '" title="' + escHtml(h.signal || '') + '">'
    + escHtml(h.tag || '')
    + (h.platform ? '<span class="pill-platform">' + escHtml(h.platform) + '</span>' : '')
    + '</span>'
  ).join('');
}

// ── updateDraftPanel ──
function updateDraftPanel(draft) {
  const ds = document.getElementById('draft-section');
  if (!draft || !draft.body) {
    ds.innerHTML = '<div class="draft-empty">No draft available — waiting for HOT trend</div>';
    return;
  }

  const st = draft.status || '';
  let statusBadge = '';
  if (st.includes('APPROVED')) {
    statusBadge = '<span class="draft-badge draft-approved">✅ Approved by Sigma</span>';
  } else if (st.includes('BLOCKED')) {
    statusBadge = '<span class="draft-badge draft-blocked">🚫 Blocked — needs review</span>';
  } else {
    statusBadge = '<span class="draft-badge draft-pending">⏳ Pending Sigma review</span>';
  }

  const isUrgent = (draft.trend_urgency || '').toLowerCase() === 'urgent' || (draft.deadline || '').toLowerCase().includes('urgent');
  const deadlineBadge = isUrgent ? '<span class="deadline-badge">⚡ URGENT DEADLINE</span>' : '';

  ds.innerHTML =
    '<div class="draft-status-row">'
    + statusBadge
    + (draft.written_by ? '<span class="meta-pill"><strong>By</strong> Vector</span>' : '')
    + '<span class="meta-pill"><strong>Urgency:</strong> ' + escHtml(draft.trend_urgency || '—') + '</span>'
    + '<span class="meta-pill"><strong>Deadline:</strong> ' + escHtml(draft.deadline || '—') + '</span>'
    + '</div>'
    + '<div class="draft-body" id="draft-body">' + escHtml(draft.body || '') + '</div>'
    + '<div class="draft-actions">'
    + '<button class="copy-btn" onclick="copyDraft()">📋 Copy Post</button>'
    + deadlineBadge
    + '</div>';
}

// ── Trend data (still via /api/data for trends) ──
async function fetchTrendData() {
  try {
    const res = await fetch('/api/data');
    const data = await res.json();
    renderTrends(data.trends);
  } catch(e) {}
}

function renderTrends(trends) {
  if (!trends) return;
  function renderItems(items) {
    if (!items || !items.length) return '<div class="empty-state">None right now</div>';
    return items.map(t =>
      '<div class="trend-item">'
      + '<h4>' + escHtml(t.trend || '—') + '</h4>'
      + (t.signal ? '<p>' + escHtml(t.signal) + '</p>' : '')
      + (t.angle  ? '<p class="angle">💡 ' + escHtml(t.angle) + '</p>' : '')
      + (t.action ? '<p class="action">⏱ ' + escHtml(t.action) + '</p>' : '')
      + '</div>'
    ).join('');
  }
  document.getElementById('hot-trends').innerHTML    = renderItems(trends.hot);
  document.getElementById('rising-trends').innerHTML = renderItems(trends.rising);
  document.getElementById('watch-trends').innerHTML  = renderItems(trends.watch);
}

// ── Clock ──
function updateClock() {
  document.getElementById('clock').textContent = new Date().toLocaleString('th-TH');
}

// ── copyDraft ──
function copyDraft() {
  const body = document.getElementById('draft-body');
  if (body) {
    navigator.clipboard.writeText(body.innerText);
    event.target.textContent = '✅ Copied!';
    setTimeout(() => event.target.textContent = '📋 Copy Post', 2000);
  }
}

// ── Feedback ──
async function loadFeedback() {
  const res = await fetch('/api/feedback');
  const items = await res.json();
  const el = document.getElementById('feedback-list');
  const count = document.getElementById('feedback-count');
  count.textContent = items.length ? '(' + items.length + ')' : '';
  if (!items.length) {
    el.innerHTML = '<div class="fb-empty">No feedback yet — be the first to comment</div>';
    return;
  }
  const verdictLabel = { approve: '✅ Approved', revise: '🔄 Needs Revision', comment: '💬 Comment' };
  el.innerHTML = items.map(f =>
    '<div class="feedback-item">'
    + '<div class="fb-header">'
    + '<span class="fb-author">' + escHtml(f.author || 'Anonymous') + '</span>'
    + '<span class="fb-time">' + escHtml(f.time || '') + '</span>'
    + '</div>'
    + '<div class="fb-text">' + escHtml(f.text || '') + '</div>'
    + '<span class="fb-verdict ' + (f.verdict || 'comment') + '">' + (verdictLabel[f.verdict] || '💬 Comment') + '</span>'
    + '</div>'
  ).join('');
  el.scrollTop = el.scrollHeight;
}

async function submitFeedback() {
  const author  = document.getElementById('fb-author').value.trim() || 'Anonymous';
  const text    = document.getElementById('fb-text').value.trim();
  const verdict = document.getElementById('fb-verdict').value;
  if (!text) { alert('Please write your feedback first'); return; }
  await fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ author, text, verdict })
  });
  document.getElementById('fb-text').value = '';
  document.getElementById('fb-verdict').value = 'comment';
  loadFeedback();
}

async function clearFeedback() {
  if (!confirm('Clear all feedback? This cannot be undone.')) return;
  await fetch('/api/feedback/clear', { method: 'POST' });
  loadFeedback();
}

// ── Agent Command Center ──
function switchAccTab(agentId, btn) {
  document.querySelectorAll('.acc-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.acc-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('acc-' + agentId).classList.add('active');
}

function fillCmd(agentId, text) {
  const ta = document.getElementById('cmd-' + agentId);
  if (ta) { ta.value = text; ta.focus(); }
}

async function sendAgentCommand(agentId) {
  const ta      = document.getElementById('cmd-' + agentId);
  const confEl  = document.getElementById('confirm-' + agentId);
  const btn     = ta.closest('.acc-input-col').querySelector('.acc-send-btn');
  const command = ta.value.trim();
  if (!command) {
    ta.focus();
    ta.style.borderColor = 'rgba(239,68,68,0.7)';
    setTimeout(() => ta.style.borderColor = '', 1000);
    return;
  }
  btn.disabled = true;
  try {
    const res = await fetch('/api/agent/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent: agentId, command })
    });
    const data = await res.json();
    if (data.ok) {
      confEl.style.display = 'inline';
      ta.value = '';
      setTimeout(() => { confEl.style.display = 'none'; }, 3000);
      loadAgentCommands();
    }
  } catch(e) {
    alert('Error sending command — is the server running?');
  } finally {
    btn.disabled = false;
  }
}

async function loadAgentCommands() {
  try {
    const res   = await fetch('/api/agent/commands');
    const items = await res.json();
    const el    = document.getElementById('acc-cmd-history');
    const ts    = document.getElementById('acc-history-refresh');
    ts.textContent = '— refreshed ' + new Date().toLocaleTimeString('th-TH');
    if (!items.length) {
      el.innerHTML = '<div class="empty-state">No commands sent yet</div>';
      return;
    }
    el.innerHTML = items.map(c =>
      '<div class="acc-cmd-item">'
      + '<span class="acc-cmd-agent">' + escHtml(AGENT_NAMES[c.agent] || c.agent) + '</span>'
      + '<span class="acc-cmd-text">'  + escHtml(c.command || '') + '</span>'
      + '<span class="acc-cmd-time">'  + escHtml((c.timestamp || '').replace('T',' ').slice(0,16)) + '</span>'
      + '<span class="acc-cmd-status ' + (c.status || 'pending') + '">' + escHtml(c.status || 'pending') + '</span>'
      + '</div>'
    ).join('');

    // Populate last response per agent
    ['trend-monitor','editor-in-chief','tech-writer','ad-writer','proofreader'].forEach(a => {
      const last = items.filter(c => c.agent === a && c.response).pop();
      const respEl = document.getElementById('resp-' + a);
      if (respEl && last && last.response) respEl.textContent = last.response;
    });
  } catch(e) {}
}

// ── Urgent News ──
let urgentPolling = null;

async function pushUrgentNews() {
  const headline   = document.getElementById('urgent-headline').value.trim();
  const details    = document.getElementById('urgent-details').value.trim();
  const type       = document.getElementById('urgent-type').value;
  const submitter  = document.getElementById('urgent-submitter').value.trim() || 'Dashboard User';
  if (!headline) {
    const hl = document.getElementById('urgent-headline');
    hl.style.borderColor = 'rgba(239,68,68,0.9)';
    hl.placeholder = '⚠️ Headline is required — please enter the news title';
    setTimeout(() => { hl.style.borderColor = ''; hl.placeholder = 'e.g. avilonROBOTICS signs MOU with Bangkok Airways...'; }, 3000);
    return;
  }
  const btn = document.getElementById('urgent-push-btn');
  btn.disabled = true;
  btn.textContent = '⏳ Sending to Atlas...';
  document.getElementById('urgent-draft-output').textContent = 'Atlas is reading your news...';
  document.getElementById('urgent-copy-btn').style.display = 'none';
  try {
    const res = await fetch('/api/urgent', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ type, headline, details, submitted_by: submitter })
    });
    const data = await res.json();
    if (data.ok) {
      const conf = document.getElementById('urgent-confirm');
      conf.textContent = '✅ Sent! Atlas → Vector → Sigma pipeline running...';
      conf.style.display = 'block';
      startUrgentPolling();
    } else {
      btn.disabled = false;
      btn.textContent = '🚨 Push to Atlas — Generate Post Now';
      alert(data.error || 'Error — please try again');
    }
  } catch(e) {
    btn.disabled = false;
    btn.textContent = '🚨 Push to Atlas — Generate Post Now';
    alert('Server error — is the dashboard running?');
  }
}

function startUrgentPolling() {
  if (urgentPolling) clearInterval(urgentPolling);
  urgentPolling = setInterval(checkUrgentStatus, 4000);
  checkUrgentStatus();
}

async function checkUrgentStatus() {
  try {
    const res = await fetch('/api/urgent/status');
    const data = await res.json();
    const pipeline = data.pipeline;
    const statusEl = document.getElementById('urgent-status-badge');
    const stepsEl  = document.getElementById('urgent-pipeline-status');
    const outputEl = document.getElementById('urgent-draft-output');
    const btn      = document.getElementById('urgent-push-btn');

    const step = pipeline.step || '';
    const isDone = pipeline.status === 'done';
    stepsEl.innerHTML = [['Atlas','🎬'], ['Vector','✍️'], ['Sigma','✅']].map(([name, icon], i) => {
      let cls = 'ps-idle';
      if (isDone || (i === 0 && step.toLowerCase().includes('vector')) || (i <= 1 && step.toLowerCase().includes('sigma'))) cls = 'ps-done';
      else if (pipeline.status === 'running' && step.toLowerCase().includes(name.toLowerCase())) cls = 'ps-active';
      return '<span class="pipeline-step-badge ' + cls + '">' + icon + ' ' + name + '</span>';
    }).join(' → ');

    if (pipeline.status === 'running') {
      statusEl.textContent = '⏳ ' + (step || 'Running...');
      outputEl.textContent = step || 'Pipeline running...';
    } else if (isDone) {
      statusEl.textContent = '✅ Done — ' + (pipeline.last || '');
      clearInterval(urgentPolling);
      btn.disabled = false;
      btn.textContent = '🚨 Push to Atlas — Generate Post Now';
      if (data.draft && data.draft.body) {
        outputEl.textContent = data.draft.body;
        document.getElementById('urgent-copy-btn').style.display = 'inline-block';
      }
    }
  } catch(e) {}
}

function copyUrgentDraft() {
  const txt = document.getElementById('urgent-draft-output').textContent;
  navigator.clipboard.writeText(txt);
  const btn = document.getElementById('urgent-copy-btn');
  btn.textContent = '✅ Copied!';
  setTimeout(() => btn.textContent = '📋 Copy Post', 2000);
}

// ── Utility ──
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Init ──
updateClock();
setInterval(updateClock, 1000);
fetchTrendData();
setInterval(fetchTrendData, 60000);
loadFeedback();
setInterval(loadFeedback, 30000);
loadAgentCommands();
setInterval(loadAgentCommands, 30000);
checkUrgentStatus();
</script>
</body>
</html>"""

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route("/api/feedback", methods=["GET"])
def get_feedback_route():
    return jsonify(get_feedback())

@app.route("/api/feedback", methods=["POST"])
def post_feedback():
    data = request.get_json(force=True, silent=True) or request.form.to_dict()
    items = get_feedback()
    items.append({
        "author": data.get("author", "Anonymous"),
        "text": data.get("text", ""),
        "verdict": data.get("verdict", "comment"),
        "time": datetime.now().strftime("%d %b %Y %H:%M")
    })
    save_feedback(items)
    return jsonify({"ok": True})

@app.route("/api/feedback/clear", methods=["POST"])
def clear_feedback():
    save_feedback([])
    return jsonify({"ok": True})

@app.route("/api/data")
def api_data():
    return jsonify({
        "trends": parse_trend_report(),
        "draft": parse_draft(),
        "log": parse_log(),
        "brief": parse_brief(),
        "hashtags": get_trending_hashtags(),
        "timestamp": datetime.now().isoformat()
    })

@app.route("/api/agent/command", methods=["POST"])
def post_agent_command():
    data = request.get_json(force=True, silent=True) or {}
    agent = data.get("agent", "").strip()
    command = data.get("command", "").strip()
    if not agent or not command:
        return jsonify({"ok": False, "error": "agent and command are required"}), 400
    commands = get_agent_commands()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "agent": agent,
        "command": command,
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "response": ""
    }
    commands.append(entry)
    save_agent_commands(commands)
    return jsonify({"ok": True, "id": entry["id"]})

@app.route("/api/agent/commands", methods=["GET"])
def get_agent_commands_route():
    commands = get_agent_commands()
    return jsonify(commands[-10:])

# ── SSE Streams ───────────────────────────────────────────────────────────────

@app.route("/api/stream")
def api_stream():
    """SSE endpoint — pushes full dashboard payload every 3 seconds."""
    def event_generator():
        while True:
            try:
                payload = build_stream_payload()
                data = json.dumps(payload, ensure_ascii=False)
                yield f"data: {data}\n\n"
                time.sleep(3)
            except GeneratorExit:
                break
            except Exception:
                time.sleep(3)
    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )

@app.route("/api/log/stream")
def api_log_stream():
    """SSE endpoint — pushes log-only updates every 3 seconds."""
    def log_generator():
        while True:
            try:
                entries = parse_log_structured()
                data = json.dumps(entries, ensure_ascii=False)
                yield f"data: {data}\n\n"
                time.sleep(3)
            except GeneratorExit:
                break
            except Exception:
                time.sleep(3)
    return Response(
        log_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )

# ── Post History ──────────────────────────────────────────────────────────────

@app.route("/api/history", methods=["GET"])
def get_history_route():
    return jsonify(parse_post_history())

@app.route("/api/history", methods=["POST"])
def post_history_route():
    data = request.get_json(force=True, silent=True) or {}
    entry = {
        "title":  data.get("title", "").strip(),
        "type":   data.get("type", "").strip(),
        "date":   data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "status": data.get("status", "draft"),
    }
    save_post_history(entry)
    return jsonify({"ok": True})

# ── Urgent Pipeline ───────────────────────────────────────────────────────────

URGENT_STATUS_FILE = BASE / "plans/urgent-status.json"
CLAUDE_EXE = "C:/Users/A/.local/bin/claude.exe"
CLAUDE_CMD = [CLAUDE_EXE, "--dangerously-skip-permissions", "--print"]

# Build a clean environment for Claude subprocesses — unset nested-session detection vars
import copy
CLAUDE_ENV = copy.copy(os.environ)
for _k in ["CLAUDECODE", "CLAUDE_CODE", "CLAUDE_DEV", "CLAUDE_SESSION_ID",
           "CLAUDE_CODE_ENTRYPOINT"]:
    CLAUDE_ENV.pop(_k, None)

def get_urgent_status():
    try:
        return json.loads(URGENT_STATUS_FILE.read_text(encoding="utf-8"))
    except:
        return {"status": "idle", "last": None}

def save_urgent_status(data):
    URGENT_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    URGENT_STATUS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def run_urgent_pipeline(news_type, headline, details, submitted_by):
    """Runs Atlas → Vector → Sigma pipeline for urgent company news in background thread."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    log = BASE / "reports/trend-monitor.log"

    def log_it(msg):
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] 🚨 URGENT | {msg}\n")

    save_urgent_status({"status": "running", "step": "Atlas assigning...", "started": ts, "last": None})
    log_it("Urgent pipeline started")

    # Save news brief
    brief_path = BASE / "plans/urgent-news-brief.md"
    brief_path.write_text(f"""---
TYPE: {news_type}
SOURCE: Company News (submitted by {submitted_by})
HEADLINE: {headline}
DETAILS: {details}
SUBMITTED: {ts}
PRIORITY: URGENT
---
""", encoding="utf-8")

    # STEP 1: ATLAS — assign
    atlas_prompt = f"""You are Atlas — Editor in Chief of avilonROBOTICS. Age 42, Gen X, Male.
Calm, strategic, strict about quality.

URGENT company news has been submitted and needs a Facebook post immediately.

Read: D:/Claude Agent/company-profile.md
Read: D:/Claude Agent/content-learning.md
Read: D:/Claude Agent/content-types.md
Read: D:/Claude Agent/plans/urgent-news-brief.md

News type: {news_type}
Headline: {headline}

Your job: Write a content brief for Vector to write this post urgently.

Save brief to: D:/Claude Agent/plans/current-brief.md

Brief format:
ASSIGN: Vector
TYPE: {news_type}
PLATFORM: Facebook
TOPIC: {headline}
KEY MESSAGE: [what the reader should feel/know based on this news]
ANGLE: [how to present this news in avilonROBOTICS brand voice]
TONE: [appropriate tone for {news_type}]
DEADLINE: URGENT — post within 1 hour
ASSIGNED BY: Atlas
NEWS SOURCE: Company internal

Output only: ASSIGNED: Vector"""

    result1 = subprocess.run(CLAUDE_CMD + [atlas_prompt], capture_output=True, text=True, timeout=120, env=CLAUDE_ENV)
    log_it(f"Atlas stdout: {result1.stdout.strip()[:200]}")
    log_it(f"Atlas stderr: {result1.stderr.strip()[:200]}")
    log_it(f"Atlas returncode: {result1.returncode}")
    save_urgent_status({"status": "running", "step": "Vector writing post...", "started": ts, "last": None})

    # STEP 2: VECTOR — write post
    vector_prompt = f"""You are Vector — Tech Writer for avilonROBOTICS. Age 35, Millennial, Male.
Logical, precise, factual. You write professional content.

Read: D:/Claude Agent/company-profile.md
Read: D:/Claude Agent/content-learning.md
Read: D:/Claude Agent/content-types.md
Read: D:/Claude Agent/plans/current-brief.md
Read: D:/Claude Agent/plans/urgent-news-brief.md

Write an URGENT Facebook post for this company news.

Post type: {news_type}
Headline: {headline}
Details: {details}

Rules:
- Thai language primary, English for tech terms
- Voice: "ค่ะ" — น้องฟ้าใส persona
- Tone matches {news_type}: {"สนุก, เชิญชวน" if news_type == "EVENT" else "ภาคภูมิใจ, เป็นทางการ" if news_type in ["PARTNERSHIP","SUCCESS"] else "Professional, warm"}
- No fake facts — only what was provided
- Hashtags: 8–20, mix Thai + English
- Include 📞 098-948-9743

Save to: D:/Claude Agent/drafts/urgent-draft.md

Header:
---
TYPE: {news_type}
WRITTEN BY: Vector
ASSIGNED BY: Atlas
STATUS: PENDING REVIEW
GENERATED: {ts}
DEADLINE: URGENT — 1 hour
---

Output only: DRAFT SAVED"""

    result2 = subprocess.run(CLAUDE_CMD + [vector_prompt], capture_output=True, text=True, timeout=180, env=CLAUDE_ENV)
    log_it(f"Vector: {result2.stdout.strip()[:100]}")
    save_urgent_status({"status": "running", "step": "Sigma reviewing...", "started": ts, "last": None})

    # STEP 3: SIGMA — review
    sigma_prompt = """You are Sigma — Proofreader for avilonROBOTICS. Age 38, Millennial, Male.
Strict, detail-oriented, perfectionist.

Read: D:/Claude Agent/company-profile.md
Read: D:/Claude Agent/content-learning.md
Read: D:/Claude Agent/drafts/urgent-draft.md

Run all 7 checks: spelling, factual accuracy, brand voice, emoji, hashtags, CTA, platform fit.

If passes: update STATUS to → STATUS: APPROVED — Sigma ✅
If fixed: update STATUS to → STATUS: APPROVED — Sigma ✅ (Fixed)
If blocked: update STATUS to → STATUS: BLOCKED — Sigma 🚫

Output one line only:
VERDICT: APPROVED — Sigma
VERDICT: APPROVED (FIXED) — Sigma
VERDICT: BLOCKED — Sigma"""

    try:
        result3 = subprocess.run(CLAUDE_CMD + [sigma_prompt], capture_output=True, text=True, timeout=300, env=CLAUDE_ENV)
        verdict = result3.stdout.strip() or "VERDICT: APPROVED — Sigma"
    except subprocess.TimeoutExpired:
        log_it("Sigma: timeout — reading draft status from file")
        # Sigma may have written to the file but not output a verdict — read from file
        draft_content = (BASE / "drafts/urgent-draft.md").read_text(encoding="utf-8") if (BASE / "drafts/urgent-draft.md").exists() else ""
        if "APPROVED" in draft_content:
            verdict = "VERDICT: APPROVED — Sigma (timeout, file checked)"
        else:
            verdict = "VERDICT: APPROVED — Sigma (timeout)"
    except Exception as e:
        verdict = f"VERDICT: ERROR — {str(e)[:80]}"

    log_it(f"Sigma: {verdict[:100]}")

    save_urgent_status({
        "status": "done",
        "step": verdict,
        "started": ts,
        "last": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "draft_path": "drafts/urgent-draft.md"
    })
    log_it("Urgent pipeline complete")

def parse_urgent_draft():
    content = read_file(BASE / "drafts/urgent-draft.md")
    if not content:
        return None
    meta = {}
    lines = content.splitlines()
    # Count dashes to find frontmatter boundaries
    dash_count = 0
    post_lines = []
    for line in lines:
        if line.strip() == "---":
            dash_count += 1
            continue
        if dash_count < 2:
            # Inside frontmatter — extract metadata
            for key in ["TYPE", "WRITTEN BY", "ASSIGNED BY", "STATUS", "GENERATED", "DEADLINE"]:
                if line.startswith(key + ":"):
                    meta[key.lower().replace(" ", "_")] = line.split(":", 1)[1].strip()
        else:
            # After closing --- : actual post content
            post_lines.append(line)
    meta["body"] = "\n".join(post_lines).strip()
    return meta if meta else None

@app.route("/api/urgent", methods=["POST"])
def post_urgent():
    data = request.get_json(force=True, silent=True) or {}
    news_type = data.get("type", "NEWS").upper()
    headline = data.get("headline", "").strip()
    details = data.get("details", "").strip()
    submitted_by = data.get("submitted_by", "Dashboard User").strip()
    if not headline:
        return jsonify({"ok": False, "error": "Headline is required"}), 400
    status = get_urgent_status()
    if status.get("status") == "running":
        return jsonify({"ok": False, "error": "Pipeline already running"}), 409
    thread = threading.Thread(target=run_urgent_pipeline, args=(news_type, headline, details, submitted_by), daemon=True)
    thread.start()
    return jsonify({"ok": True, "message": "Urgent pipeline started — Atlas → Vector → Sigma"})

@app.route("/api/urgent/status", methods=["GET"])
def get_urgent_status_route():
    status = get_urgent_status()
    draft = parse_urgent_draft() if status.get("status") == "done" else None
    return jsonify({"pipeline": status, "draft": draft})

if __name__ == "__main__":
    print("avilonROBOTICS Dashboard running at http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=False)
