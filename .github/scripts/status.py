"""Daily status for the Brazil trip repo.

- Labels open issues past their deadline as `overdue` (and removes it when no longer true).
- On decision issues past their deadline, posts the default once and labels `default-applied`.
- Regenerates README.md with progress bars per milestone, overdue items and what's next.
"""
import datetime as dt
import json
import os
import re
import urllib.request
from zoneinfo import ZoneInfo

REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GITHUB_TOKEN"]
API = f"https://api.github.com/repos/{REPO}"
DOC = "https://claude.ai/code/artifact/34968c96-3842-4b4a-8ebb-d26ef0847290"
TRIP_START = dt.date(2026, 10, 31)
VISA_LIMIT = dt.date(2027, 1, 28)


def call(method, path, body=None):
    req = urllib.request.Request(
        path if path.startswith("http") else API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def all_issues():
    out, page = [], 1
    while True:
        batch = call("GET", f"/issues?state=all&per_page=100&page={page}")
        out += [i for i in batch if "pull_request" not in i]
        if len(batch) < 100:
            return out
        page += 1


def field(body, name):
    m = re.search(rf"\*\*{name}:\*\*\s*(.+)", body or "")
    return m.group(1).strip() if m else None


def deadline(issue):
    v = field(issue["body"], "Deadline")
    try:
        return dt.date.fromisoformat(v[:10]) if v else None
    except ValueError:
        return None


def bar(done, total, cells=20):
    if total == 0:
        return "⬜" * cells
    full = round(cells * done / total)
    return "🟩" * full + "⬜" * (cells - full)


def fmt(d):
    return d.strftime("%a %d %b") if d else "no date"


tz = ZoneInfo("America/Bogota" if dt.date.today() < TRIP_START else "America/Sao_Paulo")
today = dt.datetime.now(tz).date()

issues = all_issues()
labels_of = lambda i: {l["name"] for l in i["labels"]}

# --- overdue labels and defaults -------------------------------------------
for i in issues:
    d, labels = deadline(i), labels_of(i)
    is_overdue = i["state"] == "open" and d is not None and d < today
    if is_overdue and "overdue" not in labels:
        call("POST", f"/issues/{i['number']}/labels", {"labels": ["overdue"]})
        i["labels"].append({"name": "overdue"})
    if not is_overdue and "overdue" in labels:
        call("DELETE", f"/issues/{i['number']}/labels/overdue")
        i["labels"] = [l for l in i["labels"] if l["name"] != "overdue"]
    default = field(i["body"], "Default if undecided")
    if is_overdue and "decision" in labels and "default-applied" not in labels and default:
        call("POST", f"/issues/{i['number']}/comments", {
            "body": f"⚖️ **Default applied** on {today.isoformat()}: {default}\n\n"
                    "No decision came in before the deadline, so the plan now assumes this. "
                    "Close this issue once you've acted on it, or comment to override."})
        call("POST", f"/issues/{i['number']}/labels", {"labels": ["default-applied"]})
        i["labels"].append({"name": "default-applied"})

# --- README ------------------------------------------------------------------
milestones = sorted(call("GET", "/milestones?state=all&per_page=100"), key=lambda m: m["due_on"] or "")
open_issues = [i for i in issues if i["state"] == "open"]
closed = [i for i in issues if i["state"] == "closed"]
total, done = len(issues), len(closed)
pct = round(100 * done / total) if total else 0

lines = [
    "# 🇧🇷 Brazil Work Trip · 31 Oct 2026 → 16–21 Jan 2027",
    "",
    f"**{done}/{total} done · {pct}%**",
    "",
    bar(done, total),
    "",
]
if today >= TRIP_START:
    day = (today - TRIP_START).days + 1
    lines += [f"🛂 **Visa: day {day} of 90** · limit {fmt(VISA_LIMIT)} · {(VISA_LIMIT - today).days} days left", ""]
else:
    lines += [f"✈️ **{(TRIP_START - today).days} days to departure** (Sat 31 Oct)", ""]

overdue = sorted([i for i in open_issues if deadline(i) and deadline(i) < today], key=deadline)
lines += ["## ⏰ Overdue", ""]
lines += [f"- [ ] [{i['title']}]({i['html_url']}) · was due {fmt(deadline(i))}" for i in overdue] or ["Nothing overdue. 🎉"]
lines += [""]

upcoming = sorted([i for i in open_issues if deadline(i) and deadline(i) >= today], key=deadline)[:5]
lines += ["## 👉 Next up", ""]
lines += [f"- [ ] [{i['title']}]({i['html_url']}) · **{fmt(deadline(i))}**" for i in upcoming] or ["All done."]
lines += ["", "## 📊 Phases", "", "| Phase | Progress | Done | Due |", "| --- | --- | --- | --- |"]
for m in milestones:
    t = m["open_issues"] + m["closed_issues"]
    due = dt.date.fromisoformat(m["due_on"][:10]) if m["due_on"] else None
    lines.append(f"| [{m['title']}]({m['html_url']}) | {bar(m['closed_issues'], t, 10)} | {m['closed_issues']}/{t} | {fmt(due)} |")

recent = sorted(closed, key=lambda i: i["closed_at"] or "", reverse=True)[:5]
lines += ["", "## ✅ Recently done", ""]
lines += [f"- [x] {i['title']}" for i in recent] or ["Nothing yet. Close your first issue!"]
lines += [
    "",
    "---",
    "",
    "**How it works:** every task is an issue. Close it when it's done. "
    "This page updates itself every morning and whenever an issue changes.",
    "",
    f"📄 [Master plan (details, budget, stays)]({DOC}) · 📅 BRAZIL calendar for times · "
    f"updated {dt.datetime.now(tz).strftime('%d %b %H:%M')} ({tz.key.split('/')[-1].replace('_', ' ')})",
    "",
]

with open("README.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"{done}/{total} done, {len(overdue)} overdue")
