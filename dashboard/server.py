from flask import Flask, jsonify, render_template_string, request
import os, re, json
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
BASE = Path("D:/Claude Agent")

def read_file(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except:
        return ""

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
        for key in ["TREND URGENCY", "DEADLINE", "GENERATED", "STATUS"]:
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
</style>
</head>
<body>

<header>
  <h1>avilon<span>ROBOTICS</span> — Content Team Dashboard</h1>
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
        <div class="step-label"><strong>Trend Monitor</strong>Scanning trends</div>
      </div>
      <div class="arrow">→</div>
      <div class="step">
        <div class="step-icon" id="s2">🎬</div>
        <div class="step-label"><strong>Editor in Chief</strong>Assigning briefs</div>
      </div>
      <div class="arrow">→</div>
      <div class="step">
        <div class="step-icon" id="s3">✍️</div>
        <div class="step-label"><strong>Tech Writer</strong>Writing post</div>
      </div>
      <div class="arrow">→</div>
      <div class="step">
        <div class="step-icon" id="s4">📢</div>
        <div class="step-label"><strong>Ad Writer</strong>Ad copy (3 variants)</div>
      </div>
      <div class="arrow">→</div>
      <div class="step">
        <div class="step-icon" id="s5">✅</div>
        <div class="step-label"><strong>Proofreader</strong>QA & approve</div>
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
  <div class="card full">
    <div class="card-title">
      <div class="dot" style="background:#ffaa00"></div>
      Team Feedback
      <span id="feedback-count" style="font-size:11px;color:#555;font-weight:normal;margin-left:4px"></span>
      <button class="clear-btn" onclick="clearFeedback()">🗑 Clear all</button>
    </div>

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

</div>

<script>
async function fetchData() {
  const res = await fetch('/api/data');
  const data = await res.json();

  // Clock
  document.getElementById('clock').textContent = new Date().toLocaleString('th-TH');

  // Stats
  document.getElementById('stat-hot').textContent = data.trends.hot.length;
  document.getElementById('stat-rising').textContent = data.trends.rising.length;
  document.getElementById('stat-drafts').textContent = data.draft ? 1 : 0;

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
    const statusClass = data.draft.status === 'APPROVED' ? 'approved' : 'pending';
    ds.innerHTML = `
      <div class="draft-meta">
        <div class="meta-pill"><strong>Status:</strong> <span class="${statusClass}">${data.draft.status || '—'}</span></div>
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

// Auto-refresh every 60 seconds
fetchData();
loadFeedback();
setInterval(fetchData, 60000);
setInterval(loadFeedback, 30000);
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
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    print("avilonROBOTICS Dashboard running at http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=False)
