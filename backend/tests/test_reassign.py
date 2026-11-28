"""Tests for the three groups of "issue_reassigned" cancellations (AJA-2669).

Every record here is fake. No test reads Paperclip.
"""
import unittest
import urllib.error
from unittest import mock

from safeboard.collect import paperclip as pc
from safeboard.flow import reassign
from safeboard.web import server


def run(run_id, issue="issue-1", started=True, code="issue_reassigned", status="cancelled"):
    return {
        "id": run_id,
        "issueId": issue,
        "agentId": "agent-old-owner",
        "status": status,
        "errorCode": code,
        "createdAt": "2026-01-05T10:00:00.000Z",
        "startedAt": "2026-01-05T10:00:05.000Z" if started else None,
        "finishedAt": "2026-01-05T10:05:00.000Z",
    }


def handover(by_run, interrupted, actor_type="agent", action="issue.updated", changes=True):
    """An activity entry: the run `by_run` gave the issue away and stopped the run `interrupted`."""
    details = {"interruptedRunId": interrupted}
    if changes:
        details["changes"] = {"assigneeAgentId": {"from": "agent-old-owner", "to": "agent-new-owner"}}
    return {"action": action, "actorType": actor_type, "runId": by_run, "createdAt": "2026-01-05T10:05:00.100Z", "details": details}


OTHER_NOISE = {"action": "issue.comment_added", "actorType": "agent", "runId": "run-noise", "createdAt": "2026-01-05T09:00:00.000Z", "details": {}}


class ClassifyTest(unittest.TestCase):
    def test_run_that_gave_the_issue_away_itself_is_a_handoff(self):
        r = run("run-self")
        self.assertEqual(reassign.classify(r, [OTHER_NOISE, handover("run-self", "run-self")]), reassign.HANDOFF)

    def test_started_run_stopped_by_another_agent_is_interrupted(self):
        r = run("run-cut")
        self.assertEqual(reassign.classify(r, [handover("run-of-other-agent", "run-cut")]), reassign.INTERRUPTED)

    def test_started_run_stopped_by_a_user_is_interrupted(self):
        r = run("run-cut-by-user")
        self.assertEqual(reassign.classify(r, [handover(None, "run-cut-by-user", actor_type="user")]), reassign.INTERRUPTED)

    def test_run_that_never_started_is_an_idle_wake(self):
        r = run("run-idle", started=False)
        self.assertEqual(reassign.classify(r, [handover("run-of-other-agent", "run-idle")]), reassign.IDLE_WAKE)

    def test_never_started_and_nobody_found_is_an_idle_wake(self):
        r = run("run-idle-unknown", started=False)
        self.assertEqual(reassign.classify(r, []), reassign.IDLE_WAKE)
        self.assertEqual(reassign.classify(r, None), reassign.IDLE_WAKE)

    def test_started_and_nobody_found_is_interrupted(self):
        # Work had started and nothing proves a normal handoff, so the board does not hide it.
        r = run("run-unknown")
        self.assertEqual(reassign.classify(r, [OTHER_NOISE]), reassign.INTERRUPTED)
        self.assertIsNone(reassign.reassigner(r, [OTHER_NOISE]))

    def test_assignee_change_wins_over_a_comment_from_another_run(self):
        # Paperclip may tag a comment and the assignee change with the same interrupted run.
        r = run("run-self")
        comment = handover("run-of-other-agent", "run-self", action="issue.comment_added", changes=False)
        self.assertEqual(reassign.classify(r, [comment, handover("run-self", "run-self")]), reassign.HANDOFF)

    def test_a_handover_of_another_run_is_not_used(self):
        r = run("run-cut")
        self.assertIsNone(reassign.reassigner(r, [handover("run-x", "run-somebody-else")]))


class CountsTest(unittest.TestCase):
    def setUp(self):
        self.activity = {
            "issue-a": [handover("run-self", "run-self")],
            "issue-b": [handover("run-of-other-agent", "run-cut")],
            "issue-c": [handover("run-of-other-agent", "run-idle")],
            "issue-d": [],
        }
        self.asked = []

    def activity_of(self, issue_id):
        self.asked.append(issue_id)
        return self.activity[issue_id]

    def test_one_fake_record_per_group_lands_in_its_group(self):
        runs = [run("run-self", "issue-a"), run("run-cut", "issue-b"), run("run-idle", "issue-c", started=False)]
        got = reassign.counts(runs, self.activity_of)
        self.assertEqual((got["handoff"], got["interrupted"], got["idleWake"]), (1, 1, 1))
        self.assertEqual(got["unknownActor"], 0)
        self.assertEqual(got["runs"], 3)

    def test_other_runs_are_not_counted(self):
        runs = [
            run("run-ok", "issue-a", code=None, status="succeeded"),
            run("run-other-code", "issue-a", code="issue_assignee_changed"),
            run("run-self", "issue-a"),
        ]
        got = reassign.counts(runs, self.activity_of)
        self.assertEqual((got["handoff"], got["interrupted"], got["idleWake"]), (1, 0, 0))
        self.assertEqual(got["runs"], 3)

    def test_activity_is_not_read_for_runs_that_never_started(self):
        got = reassign.counts([run("run-idle-unknown", "issue-d", started=False)], self.activity_of)
        self.assertEqual(got["idleWake"], 1)
        self.assertEqual(self.asked, [])

    def test_activity_is_read_once_per_issue(self):
        self.activity["issue-a"].append(handover("run-of-other-agent", "run-cut-2"))
        got = reassign.counts([run("run-self", "issue-a"), run("run-cut-2", "issue-a")], self.activity_of)
        self.assertEqual((got["handoff"], got["interrupted"]), (1, 1))
        self.assertEqual(self.asked, ["issue-a"])

    def test_started_run_without_a_known_actor_is_interrupted_and_reported(self):
        self.activity["issue-gone"] = None  # activity could not be read
        got = reassign.counts([run("run-unknown", "issue-d"), run("run-gone", "issue-gone"), run("run-no-issue", None)], self.activity_of)
        self.assertEqual(got["interrupted"], 3)
        self.assertEqual(got["unknownActor"], 3)

    def test_since_is_the_oldest_run_in_the_window(self):
        old = dict(run("run-old", "issue-a", code=None, status="succeeded"), createdAt="2026-01-04T08:00:00.000Z")
        got = reassign.counts([run("run-self", "issue-a"), old], self.activity_of)
        self.assertEqual(got["since"], "2026-01-04T08:00:00.000Z")

    def test_no_runs(self):
        got = reassign.counts([], self.activity_of)
        self.assertEqual((got["handoff"], got["interrupted"], got["idleWake"], got["runs"], got["since"]), (0, 0, 0, 0, None))


class ReaderTest(unittest.TestCase):
    def test_reader_asks_only_read_endpoints(self):
        with mock.patch.object(pc, "get", return_value=[]) as get:
            pc.heartbeat_runs(250)
            pc.issue_activity("issue a/1")
        paths = [c.args[0] for c in get.call_args_list]
        self.assertEqual(paths[0], f"/companies/{pc.config.COMPANY}/heartbeat-runs?limit=250")
        self.assertEqual(paths[1], "/issues/issue%20a%2F1/activity")


class ServerTest(unittest.TestCase):
    def test_data_endpoint_function_returns_the_three_counts(self):
        runs = [run("run-self", "issue-a"), run("run-cut", "issue-b"), run("run-idle", "issue-c", started=False)]
        activity = {"issue-a": [handover("run-self", "run-self")], "issue-b": [handover("run-x", "run-cut")]}
        with mock.patch.object(pc, "heartbeat_runs", return_value=runs) as hr, mock.patch.object(pc, "issue_activity", side_effect=activity.__getitem__):
            got = server.reassign()
        hr.assert_called_once_with(server.config.RUN_LIMIT)
        self.assertEqual((got["handoff"], got["interrupted"], got["idleWake"]), (1, 1, 1))

    def test_missing_issue_activity_counts_as_unknown_actor(self):
        gone = urllib.error.HTTPError("http://x", 404, "Not Found", None, None)
        with mock.patch.object(pc, "heartbeat_runs", return_value=[run("run-gone", "issue-gone")]), mock.patch.object(pc, "issue_activity", side_effect=gone):
            got = server.reassign()
        self.assertEqual((got["interrupted"], got["unknownActor"]), (1, 1))

    def test_other_read_failures_are_not_hidden(self):
        with mock.patch.object(pc, "heartbeat_runs", return_value=[run("run-x", "issue-x")]), mock.patch.object(pc, "issue_activity", side_effect=OSError("down")):
            with self.assertRaises(OSError):
                server.reassign()


if __name__ == "__main__":
    unittest.main()
