"""Reference reading of design section 5 (AJA-2145), for tests only.

This is not product code. It is the smallest model that turns the fake ledger in
`fixtures/blocker_lifecycle/` into blocker episodes, so the fixture test can
check the hand-written expected results and the drop-and-rebuild rule.

The product derivation lives in `safeboard.escalation` and `safeboard.kaizen`.
"""
import datetime as dt
import sqlite3
from zoneinfo import ZoneInfo

OPENED, OWNED, ESCALATED, RESOLVED, VERIFIED = (
    "Açıldı", "Sahiplendi", "Eskale edildi", "Çözüldü", "Doğrulandı")
UNCLASSIFIED = "unknown.unclassified"
MISSING_ROOT_CAUSE = "Kök neden kaydı eksik."
ASSIGN_ACTIONS = ("assign_owner", "assign_agent")


def ts(text):
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))


def blocker_id(key, opened_at):
    """Fake episode id: key plus opening time. The real format is not fixed here."""
    return "%s@%s" % (key, opened_at)


def signal(event):
    """Return (blocker_key, rule_code, is_on) when the event is a blocker signal."""
    action, payload = event["action"], event.get("payload") or {}
    if action == "pr.ci_completed":
        key = "pr:%s:gate:qual.ci_failed" % event["pr_ref"]
        return key, "qual.ci_failed", event["outcome"] == "failed"
    if action in ("interaction.opened", "interaction.resolved"):
        return "interaction:%s" % event["source_ref"], "gate.human_question", action.endswith("opened")
    if action == "agent.status_changed" and payload.get("status") in ("paused", "running"):
        key = "agent:%s:cap.agent_paused" % event["source_ref"]
        return key, "cap.agent_paused", payload["status"] == "paused"
    if action == "issue.status_changed" and "blocked" in (payload.get("from"), payload.get("to")):
        return "issue:%s" % event["issue_id"], UNCLASSIFIED, payload.get("to") == "blocked"
    return None


def period_key(moment, period):
    """Calendar-week key such as 2026-W10, in the time zone of the RTE record."""
    year, week, _ = ts(moment).astimezone(ZoneInfo(period["timezone"])).isocalendar()
    return "%d-W%02d" % (year, week)


def _linked(event, episode):
    return any(o["object_kind"] == "blocker" and o["object_id"] == episode["blocker_id"]
               for o in event.get("objects", []))


def derive(case, thresholds):
    """Fold the fake ledger into episodes. The order of the input rows must not matter."""
    context = case["context"]["blockers"]
    period = thresholds["kaizenRules"]["period"]
    timeline = [(e["occurred_at"], 0, e["event_uid"], e) for e in case["audit_events"]]
    timeline += [(c["finished_at"], 1, c["collect_run_id"], c) for c in case["collect_runs"]]
    episodes, current = [], {}

    def add(episode, stage, at, actor, **extra):
        episode["stage_history"].append(dict(stage=stage, at=at, actor=actor, **extra))

    for at, is_collect, _, item in sorted(timeline, key=lambda row: row[:3]):
        if is_collect:
            for episode in current.values():
                if episode["stage_history"][-1]["stage"] != RESOLVED:
                    continue
                waiting = context[episode["blocker_key"]]["waiting_issue_ids"]
                progressed = any(
                    e["action"] == "issue.status_changed" and e["issue_id"] in waiting
                    and e["occurred_at"] > episode["_resolved_at"] and e["recorded_at"] <= at
                    for e in case["audit_events"])
                if item["started_at"] > episode["_resolved_recorded_at"] and (progressed or not waiting):
                    add(episode, VERIFIED, at, "system")
                    if episode["root_cause_code"] == UNCLASSIFIED:
                        episode["warnings"].append(MISSING_ROOT_CAUSE)
            continue
        event, actor = item, item["actor_id"]
        found = signal(event)
        episode = current.get(found[0]) if found else None
        if found and found[0] in context:
            key, code, is_on = found
            stage = episode["stage_history"][-1]["stage"] if episode else VERIFIED
            if is_on and stage == VERIFIED:
                episode = dict(
                    blocker_id=blocker_id(key, at), blocker_key=key, opened_at=at,
                    root_cause_code=code, root_cause_basis="rule", stage_history=[], warnings=[],
                    root_cause_history=[dict(code=code, basis="rule", at=at, actor="system")])
                add(episode, OPENED, at, actor)
                episodes.append(episode)
                current[key] = episode
            elif is_on and stage == RESOLVED:
                add(episode, OPENED, at, actor, returned=True)
            elif not is_on and stage not in (RESOLVED, VERIFIED):
                add(episode, RESOLVED, at, actor)
                episode["_resolved_at"], episode["_resolved_recorded_at"] = at, event["recorded_at"]
            continue
        for episode in current.values():
            seen = [h["stage"] for h in episode["stage_history"]]
            if seen[-1] in (RESOLVED, VERIFIED):
                continue
            who = context[episode["blocker_key"]]
            payload = event.get("payload") or {}
            by_owner = (event["action"] in ("run.started", "issue.comment_added")
                        and event.get("issue_id") == who["root_issue_id"] and actor == who["owner_ref"])
            assigned = (event["action"] == "action.completed" and event.get("outcome") == "done"
                        and payload.get("action_type") in ASSIGN_ACTIONS and _linked(event, episode))
            if (by_owner or assigned) and OWNED not in seen:
                add(episode, OWNED, at, actor)
            elif event["action"] == "escalation.sent" and _linked(event, episode) and ESCALATED not in seen:
                add(episode, ESCALATED, at, actor)
            elif event["action"] == "blocker.root_cause_recorded" and _linked(event, episode):
                episode["root_cause_code"], episode["root_cause_basis"] = payload["root_cause_code"], "recorded"
                episode["root_cause_history"].append(
                    dict(code=payload["root_cause_code"], basis="recorded", at=at, actor=actor))

    for episode in episodes:
        mine = period_key(episode["opened_at"], period)
        episode["recurrence_count"] = sum(
            1 for other in episodes
            if other["blocker_key"] == episode["blocker_key"] and other["opened_at"] <= episode["opened_at"]
            and period_key(other["opened_at"], period) == mine)
        episode["stage"] = episode["stage_history"][-1]["stage"]
        for private in ("_resolved_at", "_resolved_recorded_at"):
            episode.pop(private, None)
    return episodes


def rule7_subjects(episodes, thresholds):
    """Return the (subject_kind, subject, period) triples for which Rule 7 holds."""
    rules = thresholds["kaizenRules"]
    rule, period = rules["rules"]["rule7"], rules["period"]
    openings, keys_by_code = {}, {}
    for episode in episodes:
        when = period_key(episode["opened_at"], period)
        openings[(episode["blocker_key"], when)] = openings.get((episode["blocker_key"], when), 0) + 1
        code = episode["root_cause_code"]
        if code not in rule["byRootCause"]["excludeCodes"]:
            keys_by_code.setdefault((code, when), set()).add(episode["blocker_key"])
    held = {("blocker_key", key, when) for (key, when), count in openings.items()
            if count >= rule["byBlockerKey"]["opensInPeriodAtLeast"]}
    held |= {("root_cause_code", code, when) for (code, when), keys in keys_by_code.items()
             if len(keys) >= rule["byRootCause"]["distinctBlockerKeysInPeriodAtLeast"]}
    return held


def rebuild(connection, episodes):
    """Drop the derived tables and build them again from the derived episodes."""
    connection.executescript(
        "DROP TABLE IF EXISTS blocker; DROP TABLE IF EXISTS blocker_stage_history;"
        "CREATE TABLE blocker (blocker_id TEXT PRIMARY KEY, blocker_key TEXT, opened_at TEXT,"
        " stage TEXT, root_cause_code TEXT, root_cause_basis TEXT, recurrence_count INTEGER);"
        "CREATE TABLE blocker_stage_history (blocker_id TEXT, seq INTEGER, stage TEXT, at TEXT, actor TEXT);")
    for e in episodes:
        connection.execute("INSERT INTO blocker VALUES (?,?,?,?,?,?,?)", (
            e["blocker_id"], e["blocker_key"], e["opened_at"], e["stage"],
            e["root_cause_code"], e["root_cause_basis"], e["recurrence_count"]))
        connection.executemany("INSERT INTO blocker_stage_history VALUES (?,?,?,?,?)", [
            (e["blocker_id"], seq, h["stage"], h["at"], h["actor"]) for seq, h in enumerate(e["stage_history"])])


def read_stages(connection):
    rows = connection.execute(
        "SELECT b.blocker_id, b.stage, h.seq, h.stage FROM blocker b JOIN blocker_stage_history h"
        " USING (blocker_id) ORDER BY b.opened_at, b.blocker_id, h.seq").fetchall()
    return [tuple(row) for row in rows]


def memory_db():
    return sqlite3.connect(":memory:")
