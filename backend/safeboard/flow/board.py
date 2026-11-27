"""Board summary from Paperclip issues and agents. Pure: no network calls."""
import datetime as dt

from safeboard.config import OPEN
from safeboard.timeutil import team_of, ts


def summary(issues, agents, now):
    """issues: project issues; agents: {id: agent}; now: aware UTC datetime."""
    status = {}
    for i in issues:
        status[i["status"]] = status.get(i["status"], 0) + 1

    # Burndown: open work at each point of the last 14 days (every 6 hours).
    life = []
    for i in issues:
        c = ts(i["createdAt"])
        end = ts(i.get("completedAt")) or ts(i.get("cancelledAt"))
        if end is None and i["status"] not in OPEN:
            end = ts(i["updatedAt"])
        life.append((c, end))
    start = (now - dt.timedelta(days=14)).replace(minute=0, second=0, microsecond=0)
    burn = []
    t = start
    while t <= now:
        burn.append({"t": t.isoformat(), "open": sum(1 for c, e in life if c <= t and (e is None or e > t))})
        t += dt.timedelta(hours=6)
    burn.append({"t": now.isoformat(), "open": sum(1 for c, e in life if e is None)})

    daily = []
    for k in range(13, -1, -1):
        day = (now - dt.timedelta(days=k)).date()
        daily.append({
            "d": day.isoformat(),
            "new": sum(1 for c, _ in life if c.date() == day),
            "done": sum(1 for i in issues if i["status"] == "done" and ts(i.get("completedAt")) and ts(i["completedAt"]).date() == day),
        })

    load = {}
    for i in issues:
        if i["status"] not in OPEN:
            continue
        a = agents.get(i.get("assigneeAgentId") or "")
        name = a["name"] if a else "Sahipsiz"
        row = load.setdefault(name, {"name": name, "team": team_of(name), "state": a["status"] if a else "-", "todo": 0, "in_progress": 0, "in_review": 0, "blocked": 0, "backlog": 0})
        row[i["status"]] += 1
    workload = sorted(load.values(), key=lambda r: -(r["todo"] + r["in_progress"] + r["in_review"] + r["blocked"]))

    roots = {}
    stale = 0
    for i in issues:
        if i["status"] != "blocked":
            continue
        if (now - ts(i["updatedAt"])).total_seconds() > 3 * 86400:
            stale += 1
        tb = (i.get("blockerAttention") or {}).get("terminalBlocker") or {}
        key = tb.get("identifier") or "Engeli tanımsız"
        r = roots.setdefault(key, {"id": key, "title": tb.get("title") or "Paperclip'te engel yazılmamış", "count": 0, "status": ""})
        r["count"] += 1
    byid = {i["identifier"]: i for i in issues}
    for r in roots.values():
        src = byid.get(r["id"])
        if src:
            r["status"] = src["status"]
            a = agents.get(src.get("assigneeAgentId") or "")
            r["owner"] = a["name"] if a else "Sahipsiz"
    blocked = sorted(roots.values(), key=lambda r: -r["count"])[:40]

    agent_state = {}
    for a in agents.values():
        agent_state[a["status"]] = agent_state.get(a["status"], 0) + 1

    done_recent = sorted((i for i in issues if i["status"] == "done" and i.get("completedAt")), key=lambda i: i["completedAt"], reverse=True)[:15]
    return {
        "status": status,
        "burn": burn,
        "daily": daily,
        "workload": workload,
        "blocked": blocked,
        "staleBlocked": stale,
        "agents": agent_state,
        "recent": [{"id": i["identifier"], "title": i["title"], "at": i["completedAt"]} for i in done_recent],
    }
