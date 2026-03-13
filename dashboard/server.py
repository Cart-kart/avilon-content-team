from flask import Flask, jsonify, render_template_string, request
import os, re, json, uuid, subprocess, threading
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
BASE = Path("D:/Claude Agent")

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

    # Extract post body (between ## FACEBOOK POST and ## METADATA)
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

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>avilonROBOTICS Content Team Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #0f1117; color: #e0e0e0; min-height: 100vh; }

  header {
    background: linear-gradient(90deg, #1a1f2e, #0d1b2a);
    border-bottom: 1px solid #00d4ff33;
    padding: 16px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  header h1 { font-size: 20px; color: #00d4ff; letter-spacing: 1px; }
  header h1 span { color: #fff; }
  .header-roster { font-size: 11px; color: #555; margin-top: 4px; letter-spacing: 0.5px; }
  .live-badge {
    background: #00ff8833;
    border: 1px solid #00ff88;
    color: #00ff88;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
    animation: pulse 2s infinite;
  }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }

  .grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    padding: 24px 32px;
    max-width: 1600px;
    margin: 0 auto;
  }
  .card {
    background: #1a1f2e;
    border: 1px solid #ffffff10;
    border-radius: 12px;
    padding: 20px;
    position: relative;
    overflow: hidden;
  }
  .card.full { grid-column: 1 / -1; }
  .card.half { grid-column: span 2; }
  .card-title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #888;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .card-title .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #00d4ff;
  }

  /* Pipeline */
  .pipeline {
    display: flex;
    align-items: center;
    gap: 0;
    justify-content: space-between;
  }
  .step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    flex: 1;
  }
  .step-icon {
    width: 52px; height: 52px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    border: 2px solid #ffffff15;
    background: #0f1117;
    position: relative;
    z-index: 1;
  }
  .step-icon.done { border-color: #00ff88; background: #00ff8815; }
  .step-icon.active { border-color: #00d4ff; background: #00d4ff15; animation: pulse 1.5s infinite; }
  .step-icon.idle { border-color: #333; }
  .step-label { font-size: 11px; color: #888; text-align: center; }
  .step-label strong { display: block; font-size: 12px; color: #ccc; }
  .arrow { color: #333; font-size: 20px; margin: 0 -4px; }

  /* Trend cards */
  .trend-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    margin-bottom: 12px;
  }
  .hot { background: #ff333322; border: 1px solid #ff3333; color: #ff6666; }
  .rising { background: #ffaa0022; border: 1px solid #ffaa00; color: #ffcc44; }
  .watch { background: #8888ff22; border: 1px solid #8888ff; color: #aaaaff; }
  .approved { background: #00ff8822; border: 1px solid #00ff88; color: #00ff88; }
  .pending { background: #ffaa0022; border: 1px solid #ffaa00; color: #ffcc44; }

  .trend-item {
    background: #0f1117;
    border: 1px solid #ffffff08;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
  }
  .trend-item h4 { font-size: 14px; color: #fff; margin-bottom: 4px; }
  .trend-item p { font-size: 12px; color: #888; line-height: 1.5; }
  .trend-item .angle { color: #00d4ff; font-size: 12px; margin-top: 4px; }
  .empty { color: #555; font-size: 13px; text-align: center; padding: 20px 0; }

  /* Draft */
  .draft-post {
    background: #0f1117;
    border: 1px solid #ffffff08;
    border-radius: 8px;
    padding: 16px;
    font-size: 13px;
    line-height: 1.8;
    white-space: pre-wrap;
    word-wrap: break-word;
    max-height: 320px;
    overflow-y: auto;
    color: #ccc;
  }
  .draft-meta {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 12px;
  }
  .meta-pill {
    background: #ffffff0a;
    border: 1px solid #ffffff15;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 11px;
    color: #aaa;
  }
  .meta-pill strong { color: #fff; }

  /* Log */
  .log-list { max-height: 200px; overflow-y: auto; }
  .log-item {
    font-size: 12px;
    color: #666;
    padding: 4px 0;
    border-bottom: 1px solid #ffffff05;
    font-family: monospace;
  }
  .log-item:last-child { color: #aaa; }

  /* Weekly calendar */
  .calendar {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
  }
  .cal-day {
    background: #0f1117;
    border: 1px solid #ffffff08;
    border-radius: 8px;
    padding: 12px;
  }
  .cal-day .day-name { font-size: 11px; color: #666; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 1px; }
  .cal-day .type-name { font-size: 13px; font-weight: 700; color: #fff; margin-bottom: 4px; }
  .cal-day .type-desc { font-size: 11px; color: #888; }
  .cal-day.today { border-color: #00d4ff44; background: #00d4ff08; }

  /* Stats row */
  .stats { display: flex; gap: 16px; }
  .stat { flex: 1; background: #0f1117; border-radius: 8px; padding: 14px; border: 1px solid #ffffff08; }
  .stat-num { font-size: 28px; font-weight: 700; color: #00d4ff; }
  .stat-label { font-size: 11px; color: #666; margin-top: 2px; }

  .refresh-time { font-size: 11px; color: #444; text-align: right; margin-top: 8px; }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }

  .copy-btn {
    background: #00d4ff22;
    border: 1px solid #00d4ff55;
    color: #00d4ff;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    margin-top: 10px;
    transition: all 0.2s;
  }
  .copy-btn:hover { background: #00d4ff33; }

  /* Feedback */
  .feedback-list { max-height: 260px; overflow-y: auto; margin-bottom: 14px; }
  .feedback-item {
    background: #0f1117;
    border: 1px solid #ffffff08;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
  }
  .feedback-item .fb-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }
  .fb-author { font-size: 12px; font-weight: 700; color: #00d4ff; }
  .fb-time { font-size: 11px; color: #555; }
  .fb-text { font-size: 13px; color: #ccc; line-height: 1.6; }
  .fb-verdict {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
    margin-top: 6px;
  }
  .fb-verdict.approve { background: #00ff8822; border: 1px solid #00ff88; color: #00ff88; }
  .fb-verdict.revise { background: #ff333322; border: 1px solid #ff3333; color: #ff6666; }
  .fb-verdict.comment { background: #ffffff11; border: 1px solid #ffffff22; color: #888; }

  .feedback-form { display: flex; flex-direction: column; gap: 10px; }
  .feedback-form input, .feedback-form textarea, .feedback-form select {
    background: #0f1117;
    border: 1px solid #ffffff15;
    border-radius: 8px;
    padding: 10px 12px;
    color: #e0e0e0;
    font-size: 13px;
    font-family: 'Segoe UI', sans-serif;
    outline: none;
    transition: border 0.2s;
  }
  .feedback-form input:focus, .feedback-form textarea:focus, .feedback-form select:focus {
    border-color: #00d4ff55;
  }
  .feedback-form textarea { resize: vertical; min-height: 80px; }
  .feedback-form select option { background: #1a1f2e; }
  .fb-row { display: flex; gap: 10px; }
  .fb-row input { flex: 1; }
  .fb-row select { flex: 0 0 140px; }
  .submit-btn {
    background: linear-gradient(90deg, #00d4ff22, #00ff8822);
    border: 1px solid #00d4ff55;
    color: #00d4ff;
    padding: 10px 20px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
    align-self: flex-end;
  }
  .submit-btn:hover { background: linear-gradient(90deg, #00d4ff33, #00ff8833); }
  .clear-btn {
    background: transparent;
    border: 1px solid #ff333344;
    color: #ff6666;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11px;
    cursor: pointer;
    margin-left: 8px;
  }

  /* Hashtag feed */
  .hashtag-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    cursor: default;
    transition: transform 0.1s;
  }
  .hashtag-pill:hover { transform: scale(1.05); }
  .hashtag-pill.hot { background: #ff333322; border: 1px solid #ff3333; color: #ff6666; }
  .hashtag-pill.rising { background: #ffaa0022; border: 1px solid #ffaa00; color: #ffcc44; }
  .hashtag-pill.watch { background: #8888ff22; border: 1px solid #8888ff; color: #aaaaff; }
  .hashtag-pill .pill-platform { font-size: 9px; color: #666; font-weight: normal; }

  /* ── Agent Command Center ── */
  .acc-tabs {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 20px;
  }
  .acc-tab {
    background: #0f1117;
    border: 1px solid #ffffff15;
    color: #888;
    padding: 7px 18px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    letter-spacing: 0.5px;
  }
  .acc-tab:hover { border-color: #00d4ff55; color: #ccc; }
  .acc-tab.active {
    background: #00d4ff18;
    border-color: #00d4ff;
    color: #00d4ff;
  }

  .acc-panel { display: none; }
  .acc-panel.active { display: block; }

  .acc-agent-header {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 16px;
  }
  .acc-agent-icon {
    width: 48px; height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    background: #00d4ff12;
    border: 1px solid #00d4ff33;
    flex-shrink: 0;
  }
  .acc-agent-name { font-size: 15px; font-weight: 700; color: #fff; }
  .acc-agent-role { font-size: 12px; color: #666; margin-top: 2px; }

  .acc-body {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  @media (max-width: 900px) { .acc-body { grid-template-columns: 1fr; } }

  .acc-input-col, .acc-output-col { display: flex; flex-direction: column; gap: 10px; }

  .acc-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #555;
    margin-bottom: 2px;
  }

  .acc-textarea {
    background: #0f1117;
    border: 1px solid #ffffff15;
    border-radius: 8px;
    padding: 12px;
    color: #e0e0e0;
    font-size: 13px;
    font-family: 'Segoe UI', sans-serif;
    outline: none;
    resize: vertical;
    min-height: 90px;
    transition: border 0.2s;
    width: 100%;
  }
  .acc-textarea:focus { border-color: #00d4ff55; }

  .acc-send-btn {
    background: linear-gradient(90deg, #00d4ff22, #00ff8822);
    border: 1px solid #00d4ff66;
    color: #00d4ff;
    padding: 10px 22px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
    align-self: flex-start;
  }
  .acc-send-btn:hover { background: linear-gradient(90deg, #00d4ff33, #00ff8833); border-color: #00d4ff99; }
  .acc-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  .acc-confirm {
    font-size: 12px;
    color: #00ff88;
    font-weight: 700;
    display: none;
    margin-top: 2px;
  }

  .acc-suggestions { display: flex; flex-direction: column; gap: 6px; }
  .acc-suggestion-btn {
    background: #0f1117;
    border: 1px solid #ffffff10;
    color: #aaa;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 12px;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s;
  }
  .acc-suggestion-btn:hover { border-color: #00d4ff44; color: #e0e0e0; background: #00d4ff08; }

  .acc-response-area {
    background: #0f1117;
    border: 1px solid #ffffff08;
    border-radius: 8px;
    padding: 12px;
    min-height: 120px;
    max-height: 260px;
    overflow-y: auto;
    font-size: 12px;
    color: #888;
    font-family: monospace;
    line-height: 1.6;
  }

  .acc-cmd-item {
    padding: 6px 0;
    border-bottom: 1px solid #ffffff06;
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }
  .acc-cmd-item:last-child { border-bottom: none; }
  .acc-cmd-agent {
    font-size: 10px;
    font-weight: 700;
    color: #00d4ff;
    white-space: nowrap;
    flex-shrink: 0;
    min-width: 90px;
  }
  .acc-cmd-text { flex: 1; color: #ccc; font-size: 12px; }
  .acc-cmd-time { font-size: 10px; color: #444; white-space: nowrap; flex-shrink: 0; }
  .acc-cmd-status {
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
    flex-shrink: 0;
  }
  .acc-cmd-status.pending { background: #ffaa0022; border: 1px solid #ffaa00; color: #ffcc44; }
  .acc-cmd-status.done    { background: #00ff8822; border: 1px solid #00ff88; color: #00ff88; }
  .acc-cmd-status.error   { background: #ff333322; border: 1px solid #ff3333; color: #ff6666; }
</style>
</head>
<body>

<header>
  <div>
    <h1>avilon<span>ROBOTICS</span> — Content Team Dashboard</h1>
    <div class="header-roster">Dollar · Atlas · Vector · Spark · Sigma</div>
  </div>
  <div style="display:flex;align-items:center;gap:16px">
    <span id="clock" style="font-size:13px;color:#666"></span>
    <div class="live-badge">● LIVE</div>
  </div>
</header>

<div class="grid">

  <!-- Pipeline Status -->
  <div class="card full">
    <div class="card-title"><div class="dot"></div>Pipeline Status</div>
    <div class="pipeline" id="pipeline">
      <div class="step">
        <div class="step-icon" id="s1">📡</div>
        <div class="step-label"><strong>Dollar</strong>Trend Monitor</div>
      </div>
      <div class="arrow">→</div>
      <div class="step">
        <div class="step-icon" id="s2">🎬</div>
        <div class="step-label"><strong>Atlas</strong>Editor in Chief</div>
      </div>
      <div class="arrow">→</div>
      <div class="step">
        <div class="step-icon" id="s3">✍️</div>
        <div class="step-label"><strong>Vector</strong>Tech Writer</div>
      </div>
      <div class="arrow">→</div>
      <div class="step">
        <div class="step-icon" id="s4">📢</div>
        <div class="step-label"><strong>Spark</strong>Ad Writer</div>
      </div>
      <div class="arrow">→</div>
      <div class="step">
        <div class="step-icon" id="s5">✅</div>
        <div class="step-label"><strong>Sigma</strong>Proofreader</div>
      </div>
      <div class="arrow">→</div>
      <div class="step">
        <div class="step-icon" id="s6">🚀</div>
        <div class="step-label"><strong>Ready to Post</strong>Facebook</div>
      </div>
    </div>
  </div>

  <!-- Stats -->
  <div class="card">
    <div class="card-title"><div class="dot" style="background:#00ff88"></div>This Week</div>
    <div class="stats">
      <div class="stat"><div class="stat-num" id="stat-hot">–</div><div class="stat-label">HOT Trends</div></div>
      <div class="stat"><div class="stat-num" id="stat-rising">–</div><div class="stat-label">RISING</div></div>
      <div class="stat"><div class="stat-num" id="stat-drafts">–</div><div class="stat-label">Drafts Ready</div></div>
    </div>
  </div>

  <!-- Live Hashtag Feed -->
  <div class="card half">
    <div class="card-title">
      <div class="dot" style="background:#ff3333;animation:pulse 1s infinite"></div>
      🏷️ Trending Hashtags — Live Feed
      <span id="hashtag-scan-time" style="font-size:10px;color:#444;font-weight:normal;margin-left:8px"></span>
    </div>
    <div id="hashtag-feed" style="display:flex;flex-wrap:wrap;gap:8px;min-height:60px">
      <div class="empty">Waiting for Dollar's next scan...</div>
    </div>
  </div>

  <!-- Weekly Calendar -->
  <div class="card half">
    <div class="card-title"><div class="dot" style="background:#ffaa00"></div>Weekly Schedule</div>
    <div class="calendar">
      <div class="cal-day" id="cal-mon">
        <div class="day-name">Monday</div>
        <div class="type-name">KNOWLEDGE</div>
        <div class="type-desc">Tech article</div>
      </div>
      <div class="cal-day" id="cal-wed">
        <div class="day-name">Wednesday</div>
        <div class="type-name">SOFT SELL</div>
        <div class="type-desc">Pain point story</div>
      </div>
      <div class="cal-day" id="cal-fri">
        <div class="day-name">Friday</div>
        <div class="type-name">TRENDJACKING</div>
        <div class="type-desc">Ride trending topic</div>
      </div>
      <div class="cal-day" id="cal-sun">
        <div class="day-name">Sunday</div>
        <div class="type-name">HARD SELL</div>
        <div class="type-desc">Demo CTA</div>
      </div>
    </div>
  </div>

  <!-- HOT Trends -->
  <div class="card">
    <div class="card-title"><div class="dot" style="background:#ff3333"></div>🔴 HOT Trends</div>
    <div id="hot-trends"><div class="empty">No HOT trends right now</div></div>
  </div>

  <!-- Rising Trends -->
  <div class="card">
    <div class="card-title"><div class="dot" style="background:#ffaa00"></div>🟡 Rising Trends</div>
    <div id="rising-trends"><div class="empty">No RISING trends right now</div></div>
  </div>

  <!-- Watch Trends -->
  <div class="card">
    <div class="card-title"><div class="dot" style="background:#8888ff"></div>👁 Watch List</div>
    <div id="watch-trends"><div class="empty">No trends to watch</div></div>
  </div>

  <!-- Latest Draft -->
  <div class="card half">
    <div class="card-title"><div class="dot" style="background:#00ff88"></div>Latest Draft</div>
    <div id="draft-section"><div class="empty">No draft available yet</div></div>
  </div>

  <!-- Activity Log -->
  <div class="card">
    <div class="card-title"><div class="dot" style="background:#888"></div>Activity Log</div>
    <div class="log-list" id="log-list"><div class="empty">No activity yet</div></div>
    <div class="refresh-time" id="last-refresh"></div>
  </div>

  <!-- Feedback Box -->
  <!-- URGENT NEWS BOX -->
  <div class="card full" id="urgent-box" style="border-color:#ff333344;background:linear-gradient(135deg,#1a1f2e,#1f1520)">
    <div class="card-title">
      <div class="dot" style="background:#ff3333;animation:pulse 0.8s infinite"></div>
      🚨 Urgent Company News — Push to Atlas Now
      <span id="urgent-status-badge" style="margin-left:12px;font-size:11px;font-weight:normal;color:#888"></span>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <!-- Input form -->
      <div style="display:flex;flex-direction:column;gap:10px">
        <div style="display:flex;gap:10px">
          <div style="flex:1">
            <div class="acc-label" style="margin-bottom:4px">Post Type</div>
            <select id="urgent-type" style="width:100%;background:#0f1117;border:1px solid #ff333344;border-radius:8px;padding:8px 12px;color:#e0e0e0;font-size:13px;outline:none">
              <option value="NEWS">📰 Company News</option>
              <option value="SUCCESS">🏆 Success / Achievement</option>
              <option value="PARTNERSHIP">🤝 Partnership / MOU</option>
              <option value="EVENT">🎉 Event / Exhibition</option>
              <option value="ANNOUNCEMENT">📣 Announcement</option>
            </select>
          </div>
          <div style="flex:1">
            <div class="acc-label" style="margin-bottom:4px">Submitted by</div>
            <input type="text" id="urgent-submitter" placeholder="Your name..." style="width:100%;background:#0f1117;border:1px solid #ff333344;border-radius:8px;padding:8px 12px;color:#e0e0e0;font-size:13px;outline:none">
          </div>
        </div>
        <div>
          <div class="acc-label" style="margin-bottom:4px">Headline / News Title *</div>
          <input type="text" id="urgent-headline" placeholder="e.g. avilonROBOTICS signs MOU with Bangkok Airways for drone delivery expansion..." style="width:100%;background:#0f1117;border:1px solid #ff333344;border-radius:8px;padding:10px 12px;color:#e0e0e0;font-size:13px;outline:none">
        </div>
        <div>
          <div class="acc-label" style="margin-bottom:4px">News Details (optional but recommended)</div>
          <textarea id="urgent-details" placeholder="Add context — who, what, where, when, why. Any specific message or quote to include..." style="width:100%;background:#0f1117;border:1px solid #ff333344;border-radius:8px;padding:10px 12px;color:#e0e0e0;font-size:13px;outline:none;resize:vertical;min-height:80px;font-family:Segoe UI,sans-serif"></textarea>
        </div>
        <button id="urgent-push-btn" onclick="pushUrgentNews()" style="background:linear-gradient(90deg,#ff333322,#ff660022);border:1px solid #ff3333;color:#ff6666;padding:12px 24px;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;transition:all 0.2s;align-self:flex-start">
          🚨 Push to Atlas — Generate Post Now
        </button>
        <div id="urgent-confirm" style="font-size:12px;color:#00ff88;display:none;font-weight:700"></div>
      </div>

      <!-- Draft output -->
      <div style="display:flex;flex-direction:column;gap:10px">
        <div class="acc-label">Draft Output — After Pipeline Completes</div>
        <div id="urgent-pipeline-status" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:4px"></div>
        <div id="urgent-draft-output" style="background:#0f1117;border:1px solid #ffffff08;border-radius:8px;padding:12px;min-height:140px;max-height:280px;overflow-y:auto;font-size:13px;color:#888;line-height:1.7;white-space:pre-wrap">
          Waiting for urgent news push...
        </div>
        <button id="urgent-copy-btn" onclick="copyUrgentDraft()" style="display:none;background:#00d4ff22;border:1px solid #00d4ff55;color:#00d4ff;padding:6px 14px;border-radius:6px;font-size:12px;cursor:pointer;align-self:flex-start">
          📋 Copy Post
        </button>
      </div>
    </div>
  </div>

  <!-- Team Feedback on Draft -->
  <div class="card full">
    <div class="card-title">
      <div class="dot" style="background:#ffaa00"></div>
      Team Feedback on Draft
      <span id="feedback-count" style="font-size:11px;color:#555;font-weight:normal;margin-left:4px"></span>
      <button class="clear-btn" onclick="clearFeedback()">🗑 Clear all</button>
    </div>
    <div style="font-size:11px;color:#555;margin-bottom:14px;margin-top:-8px">Leave comments for the team — Dollar, Atlas, Vector, Spark, Sigma</div>

    <div class="feedback-list" id="feedback-list">
      <div class="empty">No feedback yet — be the first to comment</div>
    </div>

    <div class="feedback-form">
      <div class="fb-row">
        <input type="text" id="fb-author" placeholder="Your name (e.g. ฟ้าใส, P'Arm...)" maxlength="40">
        <select id="fb-verdict">
          <option value="comment">💬 Comment</option>
          <option value="approve">✅ Approve</option>
          <option value="revise">🔄 Needs Revision</option>
        </select>
      </div>
      <textarea id="fb-text" placeholder="Write your feedback on this draft... (e.g. แก้ hashtag, เพิ่ม CTA, โทนดีแล้ว)"></textarea>
      <button class="submit-btn" onclick="submitFeedback()">Send Feedback →</button>
    </div>
  </div>

  <!-- Agent Command Center -->
  <div class="card full">
    <div class="card-title">
      <div class="dot" style="background:#00d4ff"></div>
      Agent Command Center
    </div>

    <!-- Agent tabs -->
    <div class="acc-tabs">
      <button class="acc-tab active" onclick="switchAccTab('trend-monitor', this)">📡 Dollar (Trend Monitor)</button>
      <button class="acc-tab" onclick="switchAccTab('editor-in-chief', this)">🎬 Atlas (Editor in Chief)</button>
      <button class="acc-tab" onclick="switchAccTab('tech-writer', this)">✍️ Vector (Tech Writer)</button>
      <button class="acc-tab" onclick="switchAccTab('ad-writer', this)">📢 Spark (Ad Writer)</button>
      <button class="acc-tab" onclick="switchAccTab('proofreader', this)">✅ Sigma (Proofreader)</button>
    </div>

    <!-- trend-monitor panel -->
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
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
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
          <div class="acc-response-area" id="resp-trend-monitor">
            <span style="color:#444">No response yet — send a command to get started.</span>
          </div>
        </div>
      </div>
    </div>

    <!-- editor-in-chief panel -->
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
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
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
          <div class="acc-response-area" id="resp-editor-in-chief">
            <span style="color:#444">No response yet — send a command to get started.</span>
          </div>
        </div>
      </div>
    </div>

    <!-- tech-writer panel -->
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
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
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
          <div class="acc-response-area" id="resp-tech-writer">
            <span style="color:#444">No response yet — send a command to get started.</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ad-writer panel -->
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
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
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
          <div class="acc-response-area" id="resp-ad-writer">
            <span style="color:#444">No response yet — send a command to get started.</span>
          </div>
        </div>
      </div>
    </div>

    <!-- proofreader panel -->
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
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
            <button class="acc-send-btn" onclick="sendAgentCommand('proofreader')">Send to Agent →</button>
            <span class="acc-confirm" id="confirm-proofreader">Command queued ✓</span>
          </div>
          <div class="acc-label" style="margin-top:8px">Quick Suggestions</div>
          <div class="acc-suggestions">
            <button class="acc-suggestion-btn" onclick="fillCmd('proofreader','✅ Review & approve latest draft')">✅ Review & approve latest draft</button>
            <button class="acc-suggestion-btn" onclick="fillCmd('proofreader','🔍 Full QA — facts + tone + hashtags')">🔍 Full QA — facts + tone + hashtags</button>
            <button class="acc-suggestion-btn" onclick="fillCmd('proofreader','🔄 Fix and approve')">🔄 Fix and approve</button>
          </div>
        </div>
        <div class="acc-output-col">
          <div class="acc-label">Last Agent Response / Output</div>
          <div class="acc-response-area" id="resp-proofreader">
            <span style="color:#444">No response yet — send a command to get started.</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Command History -->
    <div style="margin-top:24px;border-top:1px solid #ffffff08;padding-top:16px">
      <div class="acc-label" style="margin-bottom:10px">Recent Command History <span id="acc-history-refresh" style="color:#444;font-size:10px;font-weight:normal;margin-left:6px"></span></div>
      <div id="acc-cmd-history" style="max-height:200px;overflow-y:auto">
        <div class="empty">No commands sent yet</div>
      </div>
    </div>
  </div>

</div>

<script>
const AGENT_NAMES = {
  'trend-monitor': 'Dollar',
  'editor-in-chief': 'Atlas',
  'tech-writer': 'Vector',
  'ad-writer': 'Spark',
  'proofreader': 'Sigma'
};

async function fetchData() {
  const res = await fetch('/api/data');
  const data = await res.json();

  // Clock
  document.getElementById('clock').textContent = new Date().toLocaleString('th-TH');

  // Stats
  document.getElementById('stat-hot').textContent = data.trends.hot.length;
  document.getElementById('stat-rising').textContent = data.trends.rising.length;
  document.getElementById('stat-drafts').textContent = data.draft ? 1 : 0;

  // Live Hashtag Feed
  const hashFeed = document.getElementById('hashtag-feed');
  const hashTime = document.getElementById('hashtag-scan-time');
  if (data.hashtags && data.hashtags.length) {
    hashTime.textContent = '— Dollar scanned ' + new Date().toLocaleTimeString('th-TH');
    hashFeed.innerHTML = data.hashtags.map(h => `
      <span class="hashtag-pill ${h.urgency || 'watch'}" title="${h.signal || ''}">
        ${h.tag}
        <span class="pill-platform">${h.platform || ''}</span>
      </span>`).join('');
  } else {
    hashTime.textContent = '';
    hashFeed.innerHTML = '<div class="empty">Waiting for Dollar\'s next scan...</div>';
  }

  // Pipeline status
  const hasDraft = data.draft !== null;
  const isApproved = data.draft?.status === 'APPROVED';
  const hasHot = data.trends.hot.length > 0 || data.trends.rising.length > 0;

  const steps = ['s1','s2','s3','s4','s5','s6'];
  steps.forEach(s => document.getElementById(s).className = 'step-icon idle');

  if (isApproved) {
    ['s1','s2','s3','s5','s6'].forEach(s => document.getElementById(s).className = 'step-icon done');
  } else if (hasDraft) {
    ['s1','s2','s3'].forEach(s => document.getElementById(s).className = 'step-icon done');
    document.getElementById('s5').className = 'step-icon active';
  } else if (hasHot) {
    document.getElementById('s1').className = 'step-icon done';
    document.getElementById('s2').className = 'step-icon active';
  } else if (data.trends.generated !== 'No report yet') {
    document.getElementById('s1').className = 'step-icon done';
  }

  // Trends
  function renderTrends(items, level) {
    if (!items.length) return '<div class="empty">None right now</div>';
    return items.map(t => `
      <div class="trend-item">
        <h4>${t.trend || '—'}</h4>
        ${t.signal ? `<p>${t.signal}</p>` : ''}
        ${t.angle ? `<p class="angle">💡 ${t.angle}</p>` : ''}
        ${t.action ? `<p style="color:#666;font-size:11px;margin-top:4px">⏱ ${t.action}</p>` : ''}
      </div>`).join('');
  }
  document.getElementById('hot-trends').innerHTML = renderTrends(data.trends.hot, 'hot');
  document.getElementById('rising-trends').innerHTML = renderTrends(data.trends.rising, 'rising');
  document.getElementById('watch-trends').innerHTML = renderTrends(data.trends.watch, 'watch');

  // Draft
  const ds = document.getElementById('draft-section');
  if (data.draft) {
    const st = data.draft.status || '';
    let statusDisplay = '';
    if (st.includes('APPROVED')) {
      statusDisplay = '<span style="color:#00ff88">✅ Approved by Sigma</span>';
    } else if (st.includes('BLOCKED')) {
      statusDisplay = '<span style="color:#ff6666">🚫 Blocked by Sigma — needs review</span>';
    } else if (st.includes('PENDING')) {
      statusDisplay = '<span style="color:#ffcc44">⏳ Pending Sigma review</span>';
    } else {
      statusDisplay = `<span>${st || '—'}</span>`;
    }
    const writtenBy = data.draft.written_by ? `<div class="meta-pill"><strong>Written by</strong> Vector</div>` : '';
    ds.innerHTML = `
      <div class="draft-meta">
        <div class="meta-pill"><strong>Status:</strong> ${statusDisplay}</div>
        ${writtenBy}
        <div class="meta-pill"><strong>Urgency:</strong> ${data.draft.trend_urgency || '—'}</div>
        <div class="meta-pill"><strong>Deadline:</strong> ${data.draft.deadline || '—'}</div>
        <div class="meta-pill"><strong>Generated:</strong> ${data.draft.generated || '—'}</div>
      </div>
      <div class="draft-post" id="draft-body">${data.draft.body || 'No content'}</div>
      <button class="copy-btn" onclick="copyDraft()">📋 Copy Post</button>`;
  } else {
    ds.innerHTML = '<div class="empty">No draft available — waiting for HOT trend</div>';
  }

  // Calendar highlight today
  const days = {1:'mon',3:'wed',5:'fri',0:'sun'};
  const today = new Date().getDay();
  Object.values(days).forEach(d => document.getElementById('cal-'+d)?.classList.remove('today'));
  if (days[today]) document.getElementById('cal-'+days[today])?.classList.add('today');

  // Log
  const logEl = document.getElementById('log-list');
  if (data.log.length) {
    logEl.innerHTML = data.log.map(l => `<div class="log-item">${l}</div>`).join('');
    logEl.scrollTop = logEl.scrollHeight;
  }

  document.getElementById('last-refresh').textContent = 'Last refresh: ' + new Date().toLocaleTimeString('th-TH');
}

function copyDraft() {
  const body = document.getElementById('draft-body');
  if (body) {
    navigator.clipboard.writeText(body.innerText);
    event.target.textContent = '✅ Copied!';
    setTimeout(() => event.target.textContent = '📋 Copy Post', 2000);
  }
}

async function loadFeedback() {
  const res = await fetch('/api/feedback');
  const items = await res.json();
  const el = document.getElementById('feedback-list');
  const count = document.getElementById('feedback-count');
  count.textContent = items.length ? `(${items.length})` : '';
  if (!items.length) {
    el.innerHTML = '<div class="empty">No feedback yet — be the first to comment</div>';
    return;
  }
  const verdictLabel = { approve: '✅ Approved', revise: '🔄 Needs Revision', comment: '💬 Comment' };
  el.innerHTML = items.map((f, i) => `
    <div class="feedback-item">
      <div class="fb-header">
        <span class="fb-author">${f.author || 'Anonymous'}</span>
        <span class="fb-time">${f.time}</span>
      </div>
      <div class="fb-text">${f.text}</div>
      <span class="fb-verdict ${f.verdict}">${verdictLabel[f.verdict] || '💬 Comment'}</span>
    </div>`).join('');
  el.scrollTop = el.scrollHeight;
}

async function submitFeedback() {
  const author = document.getElementById('fb-author').value.trim() || 'Anonymous';
  const text = document.getElementById('fb-text').value.trim();
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
  const ta = document.getElementById('cmd-' + agentId);
  const confirm = document.getElementById('confirm-' + agentId);
  const btn = ta.closest('.acc-input-col').querySelector('.acc-send-btn');
  const command = ta.value.trim();
  if (!command) { ta.focus(); ta.style.borderColor = '#ff333388'; setTimeout(() => ta.style.borderColor = '', 1000); return; }

  btn.disabled = true;
  try {
    const res = await fetch('/api/agent/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent: agentId, command })
    });
    const data = await res.json();
    if (data.ok) {
      confirm.style.display = 'inline';
      ta.value = '';
      setTimeout(() => { confirm.style.display = 'none'; }, 3000);
      loadAgentCommands();
    }
  } catch (e) {
    alert('Error sending command — is the server running?');
  } finally {
    btn.disabled = false;
  }
}

async function loadAgentCommands() {
  try {
    const res = await fetch('/api/agent/commands');
    const items = await res.json();
    const el = document.getElementById('acc-cmd-history');
    const ts = document.getElementById('acc-history-refresh');
    ts.textContent = '— refreshed ' + new Date().toLocaleTimeString('th-TH');

    if (!items.length) {
      el.innerHTML = '<div class="empty">No commands sent yet</div>';
      return;
    }

    const statusClass = { pending: 'pending', done: 'done', error: 'error' };
    el.innerHTML = items.map(c => `
      <div class="acc-cmd-item">
        <span class="acc-cmd-agent">${AGENT_NAMES[c.agent] || c.agent}</span>
        <span class="acc-cmd-text">${c.command}</span>
        <span class="acc-cmd-time">${c.timestamp ? c.timestamp.replace('T',' ').slice(0,16) : ''}</span>
        <span class="acc-cmd-status ${statusClass[c.status] || 'pending'}">${c.status || 'pending'}</span>
      </div>`).join('');

    // Populate last response per agent
    const agents = ['trend-monitor','editor-in-chief','tech-writer','ad-writer','proofreader'];
    agents.forEach(a => {
      const last = items.filter(c => c.agent === a && c.response).pop();
      const respEl = document.getElementById('resp-' + a);
      if (respEl && last && last.response) {
        respEl.textContent = last.response;
      }
    });
  } catch (e) {
    // silently fail — server may not have the route yet
  }
}

// ── Urgent News ──
let urgentPolling = null;

async function pushUrgentNews() {
  const headline = document.getElementById('urgent-headline').value.trim();
  const details = document.getElementById('urgent-details').value.trim();
  const type = document.getElementById('urgent-type').value;
  const submitter = document.getElementById('urgent-submitter').value.trim() || 'Dashboard User';
  if (!headline) {
    document.getElementById('urgent-headline').style.borderColor = '#ff3333';
    setTimeout(() => document.getElementById('urgent-headline').style.borderColor = '#ff333344', 1500);
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
    const stepsEl = document.getElementById('urgent-pipeline-status');
    const outputEl = document.getElementById('urgent-draft-output');
    const btn = document.getElementById('urgent-push-btn');

    const steps = [
      {id: 'ps-atlas', label: 'Atlas', done: pipeline.step && pipeline.step !== 'Atlas assigning...'},
      {id: 'ps-vector', label: 'Vector', done: pipeline.step && !pipeline.step.includes('Vector') && !pipeline.step.includes('Atlas')},
      {id: 'ps-sigma', label: 'Sigma', done: pipeline.status === 'done'}
    ];

    stepsEl.innerHTML = ['Atlas 🎬','Vector ✍️','Sigma ✅'].map((s,i) => {
      const isDone = pipeline.status === 'done' || (i === 0 && pipeline.step && pipeline.step.includes('Vector')) || (i <= 1 && pipeline.step && pipeline.step.includes('Sigma'));
      const isActive = pipeline.status === 'running' && pipeline.step && pipeline.step.toLowerCase().includes(s.split(' ')[0].toLowerCase());
      const cls = isDone ? 'approved' : isActive ? 'pending' : '';
      return `<span class="fb-verdict ${cls}" style="font-size:11px">${s}</span>`;
    }).join(' → ');

    if (pipeline.status === 'running') {
      statusEl.textContent = '⏳ ' + (pipeline.step || 'Running...');
      outputEl.textContent = pipeline.step || 'Pipeline running...';
    } else if (pipeline.status === 'done') {
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

// On load — check if urgent pipeline was already running
checkUrgentStatus();

// Auto-refresh every 60 seconds
fetchData();
loadFeedback();
loadAgentCommands();
setInterval(fetchData, 60000);
setInterval(loadFeedback, 30000);
setInterval(loadAgentCommands, 30000);
setInterval(() => {
  document.getElementById('clock').textContent = new Date().toLocaleString('th-TH');
}, 1000);
</script>
</body>
</html>
"""

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

URGENT_STATUS_FILE = BASE / "plans/urgent-status.json"
CLAUDE_EXE = "C:/Users/A/.local/bin/claude.exe"

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

    result1 = subprocess.run([CLAUDE_EXE, "--print", atlas_prompt], capture_output=True, text=True, timeout=120)
    log_it(f"Atlas: {result1.stdout.strip()[:100]}")
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

    result2 = subprocess.run([CLAUDE_EXE, "--print", vector_prompt], capture_output=True, text=True, timeout=180)
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

    result3 = subprocess.run([CLAUDE_EXE, "--print", sigma_prompt], capture_output=True, text=True, timeout=180)
    verdict = result3.stdout.strip()
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
    for line in lines:
        for key in ["TYPE", "WRITTEN BY", "ASSIGNED BY", "STATUS", "GENERATED", "DEADLINE"]:
            if line.startswith(key + ":"):
                meta[key.lower().replace(" ", "_")] = line.split(":", 1)[1].strip()
    post_body = ""
    in_post = False
    for line in lines:
        if line.startswith("---") and in_post:
            break
        if in_post:
            post_body += line + "\n"
        if line.startswith("---") and not in_post and meta:
            in_post = True
    meta["body"] = post_body.strip()
    return meta

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
