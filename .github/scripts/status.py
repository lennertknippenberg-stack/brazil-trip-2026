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


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(today, done, total, overdue_n, week_n, milestones, next_items):
    W, H = 1200, 760
    t0, t1 = dt.date(2026, 10, 12), dt.date(2027, 1, 31)
    X0, X1 = 60, 1140
    x = lambda d: X0 + (X1 - X0) * (d - t0).days / (t1 - t0).days
    pct = done / total if total else 0
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
           '<style>.bg{fill:#ffffff}.card{fill:#f6f8fa}.ink{fill:#1f2328}.mute{fill:#656d76}.line{stroke:#d0d7de}.track{fill:#e6e9ed}'
           '@media (prefers-color-scheme:dark){.bg{fill:#0d1117}.card{fill:#161b22}.ink{fill:#e6edf3}.mute{fill:#8d96a0}.line{stroke:#30363d}.track{fill:#262c36}}</style>',
           f'<rect class="bg" width="{W}" height="{H}" rx="16"/>']
    # header + ring
    out += ['<text class="ink" x="60" y="70" font-size="34" font-weight="700">Brazil Work Trip</text>',
            '<text class="mute" x="60" y="102" font-size="17">Medellín → Florianópolis → Rio de Janeiro → Brussels · 31 Oct 2026 – Jan 2027</text>']
    cx, cy, r = 1075, 92, 52
    circ = 2 * 3.14159 * r
    out += [f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke-width="14" class="line" stroke="#d0d7de"/>',
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#2da44e" stroke-width="14" stroke-linecap="round" '
            f'stroke-dasharray="{circ * pct:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cy})"/>',
            f'<text class="ink" x="{cx}" y="{cy + 4}" font-size="26" font-weight="700" text-anchor="middle">{round(pct * 100)}%</text>',
            f'<text class="mute" x="{cx}" y="{cy + 26}" font-size="13" text-anchor="middle">{done}/{total} done</text>']
    # stat chips
    if today < TRIP_START:
        chips = [(f"{(TRIP_START - today).days} days", "to departure", "#0969da")]
    else:
        chips = [(f"Day {(today - TRIP_START).days + 1} of 90", "visa · limit 28 Jan", "#0969da")]
    chips += [(str(week_n), "due in the next 7 days", "#bf8700"),
              (str(overdue_n), "overdue", "#cf222e" if overdue_n else "#2da44e")]
    for k, (big, small, col) in enumerate(chips):
        bx = 60 + k * 300
        out += [f'<rect class="card" x="{bx}" y="130" width="280" height="76" rx="12"/>',
                f'<rect x="{bx}" y="130" width="6" height="76" rx="3" fill="{col}"/>',
                f'<text class="ink" x="{bx + 24}" y="166" font-size="26" font-weight="700">{esc(big)}</text>',
                f'<text class="mute" x="{bx + 24}" y="192" font-size="14">{esc(small)}</text>']
    # route timeline
    ty = 300
    out.append('<text class="ink" x="60" y="250" font-size="19" font-weight="700">Route</text>')
    for m, label in [(dt.date(2026, 11, 1), "Nov"), (dt.date(2026, 12, 1), "Dec"), (dt.date(2027, 1, 1), "Jan")]:
        out += [f'<line class="line" x1="{x(m):.0f}" y1="{ty - 26}" x2="{x(m):.0f}" y2="{ty + 70}" stroke-dasharray="3 5"/>',
                f'<text class="mute" x="{x(m) + 6:.0f}" y="{ty - 14}" font-size="13">{label}</text>']
    segs = [(dt.date(2026, 10, 12), dt.date(2026, 10, 31), "Medellín · prep", "#8250df"),
            (dt.date(2026, 10, 31), dt.date(2026, 12, 27), "Florianópolis · work base", "#1a7f37"),
            (dt.date(2026, 12, 27), dt.date(2027, 1, 20), "Rio", "#bf8700"),
            (dt.date(2027, 1, 20), dt.date(2027, 1, 31), "Home", "#0969da")]
    for a, b, label, col in segs:
        out += [f'<rect x="{x(a):.0f}" y="{ty}" width="{x(b) - x(a) - 3:.0f}" height="34" rx="8" fill="{col}"/>',
                f'<text x="{x(a) + 10:.0f}" y="{ty + 22}" font-size="14" font-weight="600" fill="#ffffff">{esc(label)}</text>']
    events = [(dt.date(2026, 10, 31), "Fly 31 Oct"), (dt.date(2026, 11, 12), "Francisco"),
              (dt.date(2026, 11, 21), "Itajaí"), (dt.date(2026, 11, 27), "Curitiba"),
              (dt.date(2026, 12, 27), "Rio 27 Dec"), (dt.date(2026, 12, 31), "NYE")]
    for k, (d, label) in enumerate(events):
        ex, ey = x(d), ty + 56 + (k % 2) * 18
        out += [f'<path d="M{ex:.0f} {ty + 40} l6 6 l-6 6 l-6 -6z" fill="#57606a"/>',
                f'<text class="ink" x="{ex:.0f}" y="{ey + 12}" font-size="13" text-anchor="middle">{esc(label)}</text>']
    vx = x(VISA_LIMIT)
    out += [f'<line x1="{vx:.0f}" y1="{ty - 8}" x2="{vx:.0f}" y2="{ty + 44}" stroke="#cf222e" stroke-width="2.5" stroke-dasharray="5 4"/>',
            f'<text x="{vx - 6:.0f}" y="{ty - 14}" font-size="12" fill="#cf222e" text-anchor="end">visa limit 28 Jan</text>']
    if t0 <= today <= t1:
        tx = x(today)
        out += [f'<line x1="{tx:.0f}" y1="{ty - 30}" x2="{tx:.0f}" y2="{ty + 44}" stroke="#cf222e" stroke-width="3"/>',
                f'<circle cx="{tx:.0f}" cy="{ty - 30}" r="5" fill="#cf222e"/>',
                f'<text x="{tx + 9:.0f}" y="{ty - 26}" font-size="13" font-weight="700" fill="#cf222e">today</text>']
    # phases
    py = 430
    out.append(f'<text class="ink" x="60" y="{py}" font-size="19" font-weight="700">Phases</text>')
    pw = 255
    for k, m in enumerate(milestones[:4]):
        t = m["open_issues"] + m["closed_issues"]
        f_ = m["closed_issues"] / t if t else 0
        due = dt.date.fromisoformat(m["due_on"][:10]) if m["due_on"] else None
        if t and m["open_issues"] == 0:
            col, state = "#1a7f37", "done"
        elif due and due < today:
            col, state = "#cf222e", "late"
        elif due and due <= today + dt.timedelta(days=7):
            col, state = "#bf8700", "this week"
        else:
            col, state = "#57606a", "upcoming"
        bx, by = 60 + k * (pw + 20), py + 18
        out += [f'<rect class="card" x="{bx}" y="{by}" width="{pw}" height="118" rx="12"/>',
                f'<text class="ink" x="{bx + 18}" y="{by + 32}" font-size="16" font-weight="700">{esc(m["title"])}</text>',
                f'<text class="mute" x="{bx + 18}" y="{by + 54}" font-size="13">due {esc(fmt(due))} · {state}</text>',
                f'<rect class="track" x="{bx + 18}" y="{by + 70}" width="{pw - 36}" height="12" rx="6"/>',
                f'<rect x="{bx + 18}" y="{by + 70}" width="{max(0, (pw - 36) * f_):.0f}" height="12" rx="6" fill="{col}"/>',
                f'<text class="ink" x="{bx + 18}" y="{by + 104}" font-size="15" font-weight="700">{m["closed_issues"]}/{t}</text>']
    # next up
    ny = 610
    out.append(f'<text class="ink" x="60" y="{ny}" font-size="19" font-weight="700">Next up</text>')
    for k, i in enumerate(next_items):
        d = deadline(i)
        late = d < today
        col = "#cf222e" if late else ("#bf8700" if d <= today + dt.timedelta(days=1) else "#57606a")
        cxk, cyk = 60 + (k % 2) * 550, ny + 30 + (k // 2) * 40
        title = i["title"] if len(i["title"]) <= 44 else i["title"][:42].rstrip(" ,:") + "…"
        out += [f'<circle cx="{cxk + 7}" cy="{cyk - 5}" r="7" fill="{col}"/>',
                f'<text class="mute" x="{cxk + 24}" y="{cyk}" font-size="14" font-weight="600">{"LATE " if late else ""}{esc(d.strftime("%d %b"))}</text>',
                f'<text class="ink" x="{cxk + 104}" y="{cyk}" font-size="15">#{i["number"]} {esc(title)}</text>']
    out.append('</svg>')
    return "\n".join(out)


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

overdue_n = sum(1 for i in open_issues if deadline(i) and deadline(i) < today)
week_n = sum(1 for i in open_issues if deadline(i) and today <= deadline(i) <= today + dt.timedelta(days=7))
next_items = sorted([i for i in open_issues if deadline(i)], key=deadline)[:6]
with open("status.svg", "w", encoding="utf-8") as f:
    f.write(render_svg(today, done, total, overdue_n, week_n, milestones, next_items))

lines = [
    "# 🇧🇷 Brazil Work Trip · 31 Oct 2026 → 16–21 Jan 2027",
    "",
    f'<img src="status.svg" alt="Trip status: {done} of {total} done" width="100%">',
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

# index.html is a static page that reads issues live from the GitHub API.

print(f"{done}/{total} done, {len(overdue)} overdue")
