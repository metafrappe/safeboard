"""Scrum burndown for the configured sprint. Counts issues; no estimates are invented."""
import datetime as dt

from safeboard.timeutil import team_of, ts


def burndown(issues, agent_names, conf, team, today, tz):
    """issues: project issues; agent_names: {id: name}; conf: sprint settings."""
    start = dt.date.fromisoformat(conf["start"]); end = dt.date.fromisoformat(conf["end"])
    if team != "Hepsi":
        issues = [i for i in issues if team_of(agent_names.get(i.get("assigneeAgentId") or "", "")) == team]
    day = lambda s: ts(s).astimezone(tz).date() if s else None
    rows = []
    for i in issues:
        c = day(i["createdAt"])
        done = day(i.get("completedAt")) if i["status"] == "done" else None
        drop = day(i.get("cancelledAt")) if i["status"] == "cancelled" else None
        if i["status"] in ("done", "cancelled") and not (done or drop):
            if i["status"] == "done": done = day(i["updatedAt"])
            else: drop = day(i["updatedAt"])
        if c > end:
            continue
        if (done and done < start) or (drop and drop < start):
            continue  # closed before the sprint began
        rows.append((c, done, drop))
    committed = sum(1 for c, _, _ in rows if c < start)
    days, d = [], start
    last_day = min(end, today)
    while d <= end:
        if d > last_day:
            days.append({"d": d.isoformat(), "future": True}); d += dt.timedelta(days=1); continue
        scope = sum(1 for c, _, drop in rows if c <= d and not (drop and drop <= d))
        remaining = sum(1 for c, done, drop in rows if c <= d and not (done and done <= d) and not (drop and drop <= d))
        days.append({
            "d": d.isoformat(), "scope": scope, "remaining": remaining,
            "done": sum(1 for _, done, _ in rows if done == d),
            "added": sum(1 for c, _, _ in rows if c == d and c >= start),
            "removed": sum(1 for _, _, drop in rows if drop == d),
        })
        d += dt.timedelta(days=1)
    return {"sprint": conf, "team": team, "today": today.isoformat(), "committed": committed, "days": days}
