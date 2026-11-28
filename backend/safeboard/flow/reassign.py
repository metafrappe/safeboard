"""Groups of "issue_reassigned" run cancellations. Pure: no network calls.

Paperclip cancels the run on an issue when the issue goes to another assignee.
Most of these cancellations are a normal handoff, so the board splits them:

- IDLE_WAKE: the run never started. Nothing was lost.
- HANDOFF: the run started and gave the issue away itself. Nothing was lost.
- INTERRUPTED: the run started and another agent or a user gave the issue away.
  Only this group is lost work.
"""

CODE = "issue_reassigned"
HANDOFF, INTERRUPTED, IDLE_WAKE = "handoff", "interrupted", "idleWake"
_ASSIGNEE = ("assigneeAgentId", "assigneeUserId")


def reassigner(run, activity):
    """The activity entry of the reassignment that stopped this run, or None."""
    hits = [e for e in activity or [] if (e.get("details") or {}).get("interruptedRunId") == run["id"]]
    for e in hits:
        changes = (e.get("details") or {}).get("changes") or {}
        if any(k in changes for k in _ASSIGNEE):
            return e
    return hits[0] if hits else None


def classify(run, activity):
    """Group of one "issue_reassigned" run. activity: the issue's entries, or None when unreadable."""
    if not run.get("startedAt"):
        return IDLE_WAKE
    by = reassigner(run, activity)
    # A started run with no known reassigner stays in the lost group: nothing proves a normal handoff.
    return HANDOFF if by and by.get("runId") == run["id"] else INTERRUPTED


def counts(runs, activity_of):
    """runs: recent heartbeat runs; activity_of(issue_id) -> activity entries or None."""
    out = {HANDOFF: 0, INTERRUPTED: 0, IDLE_WAKE: 0, "unknownActor": 0}
    seen = {}
    for r in runs:
        if r.get("errorCode") != CODE:
            continue
        activity = None
        issue = r.get("issueId")
        if r.get("startedAt") and issue:  # an unstarted run is an idle wake whoever reassigned
            if issue not in seen:
                seen[issue] = activity_of(issue)
            activity = seen[issue]
        group = classify(r, activity)
        out[group] += 1
        if group == INTERRUPTED and reassigner(r, activity) is None:
            out["unknownActor"] += 1
    out["runs"] = len(runs)
    out["since"] = min((r["createdAt"] for r in runs if r.get("createdAt")), default=None)
    return out
