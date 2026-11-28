"""Fast checks for the fake lifecycle and Rule 7 data (AJA-2321, design section 5)."""
import json
import re
import unittest
from pathlib import Path

from . import blocker_lifecycle_reference as ref

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "blocker_lifecycle"
STAGES = [ref.OPENED, ref.OWNED, ref.ESCALATED, ref.RESOLVED, ref.VERIFIED]

# Every event type the designs name (AJA-2140 section 1.3, AJA-2145 section 4.5).
# There is no stage-change event in this list, and there must never be one.
SOURCE_ACTIONS = {
    "issue.status_changed", "issue.comment_added", "run.started", "pr.ci_completed",
    "interaction.opened", "interaction.resolved", "agent.status_changed", "escalation.sent",
    "action.requested", "action.completed", "blocker.root_cause_recorded",
    "kaizen.candidate_created", "kaizen.evidence_added",
}
KAIZEN_ACTIONS = {"kaizen.candidate_created", "kaizen.evidence_added"}
EPISODE_FIELDS = ("blocker_id", "blocker_key", "opened_at", "stage", "stage_history", "root_cause_code",
                  "root_cause_basis", "root_cause_history", "recurrence_count", "warnings")


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class BlockerLifecycleFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.thresholds = load("rte_thresholds.json")
        cls.cases = {case["id"]: case for case in load("cases.json")["cases"]}
        cls.expected = {case["id"]: case for case in load("expected.json")["cases"]}
        cls.rule7 = cls.thresholds["kaizenRules"]["rules"]["rule7"]

    def test_twelve_cases_each_with_an_expected_result(self):
        self.assertEqual(sorted(self.cases), list(range(1, 13)))
        self.assertEqual(sorted(self.expected), list(range(1, 13)))
        for number, expected in self.expected.items():
            with self.subTest(case=number):
                self.assertEqual(expected["episode_count"], len(expected["episodes"]))
                self.assertIsInstance(expected["ledger_events"], list)
                self.assertIsInstance(expected["kaizen_candidates"], list)
                for episode in expected["episodes"]:
                    self.assertEqual(sorted(episode), sorted(EPISODE_FIELDS))
                    self.assertEqual(episode["stage"], episode["stage_history"][-1]["stage"])
                    for entry in episode["stage_history"]:
                        self.assertIn(entry["stage"], STAGES)
                        self.assertTrue(entry["at"] and entry["actor"])

    def test_no_stage_change_event_in_the_ledger(self):
        for number, case in self.cases.items():
            written = self.expected[number]["ledger_events"]
            with self.subTest(case=number):
                for event in case["audit_events"] + written:
                    self.assertIn(event["action"], SOURCE_ACTIONS)
                    self.assertNotIn("stage", json.dumps(event.get("payload") or {}))
                self.assertTrue({e["action"] for e in written} <= KAIZEN_ACTIONS)
                uids = [event["event_uid"] for event in case["audit_events"]]
                self.assertEqual(len(uids), len(set(uids)))

    def test_fake_data_holds_no_real_record(self):
        text = "".join((FIXTURES / name).read_text(encoding="utf-8")
                       for name in ("cases.json", "expected.json", "rte_thresholds.json"))
        for pattern in (r"[\w.+-]+@[\w-]+\.\w+", r"AJA-\d+", r"metafrappe", r"(?i)token|secret|password|bearer",
                        r"gh[pousr]_\w+", r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-", r"claude-0[1-5]\b", r"https?://"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, text))
        self.assertTrue(self.thresholds["fake"])

    def test_expected_episodes_follow_from_the_source_events(self):
        for number, case in self.cases.items():
            with self.subTest(case=number):
                self.assertEqual(ref.derive(case, self.thresholds), self.expected[number]["episodes"])

    def test_stages_stay_the_same_after_drop_and_rebuild(self):
        for number, case in self.cases.items():
            with self.subTest(case=number):
                expected = [(e["blocker_id"], e["stage"], seq, h["stage"])
                            for e in sorted(self.expected[number]["episodes"],
                                            key=lambda e: (e["opened_at"], e["blocker_id"]))
                            for seq, h in enumerate(e["stage_history"])]
                connection = ref.memory_db()
                ref.rebuild(connection, ref.derive(case, self.thresholds))
                first = ref.read_stages(connection)
                # Second build reads the same ledger in the opposite row order.
                reordered = dict(case, audit_events=case["audit_events"][::-1],
                                 collect_runs=case["collect_runs"][::-1])
                ref.rebuild(connection, ref.derive(reordered, self.thresholds))
                self.assertEqual(first, expected)
                self.assertEqual(ref.read_stages(connection), expected)
                connection.close()

    def test_lifecycle_cases_show_what_the_task_asks(self):
        def history(number, index=0):
            return [h["stage"] for h in self.expected[number]["episodes"][index]["stage_history"]]

        self.assertEqual(history(1), STAGES)
        self.assertEqual(history(2), [ref.OPENED, ref.OWNED, ref.ESCALATED])
        self.assertEqual(self.expected[2]["episodes"][0]["stage"], ref.ESCALATED)
        self.assertEqual(history(3), [ref.OPENED, ref.RESOLVED, ref.VERIFIED])
        self.assertEqual(self.cases[3]["context"]["blockers"][self.expected[3]["episodes"][0]["blocker_key"]]
                         ["waiting_issue_ids"], [])
        self.assertEqual(history(4), [ref.OPENED, ref.RESOLVED, ref.OPENED])
        self.assertTrue(self.expected[4]["episodes"][0]["stage_history"][-1]["returned"])
        self.assertEqual(self.expected[4]["episode_count"], 1)
        self.assertEqual(self.expected[5]["episode_count"], 2)
        self.assertEqual(history(5, 0)[-1], ref.VERIFIED)
        self.assertEqual([e["recurrence_count"] for e in self.expected[5]["episodes"]], [1, 2])
        recorded = self.expected[6]["episodes"][0]
        self.assertEqual([h["basis"] for h in recorded["root_cause_history"]], ["rule", "recorded"])
        self.assertEqual(recorded["root_cause_basis"], "recorded")
        self.assertNotEqual(recorded["root_cause_history"][0]["code"], recorded["root_cause_code"])
        unknown = self.expected[7]["episodes"][0]
        self.assertEqual((unknown["root_cause_code"], unknown["stage"]), (ref.UNCLASSIFIED, ref.VERIFIED))
        self.assertEqual(unknown["warnings"], [ref.MISSING_ROOT_CAUSE])
        for number in (1, 2, 3, 4, 5, 6, 7):
            self.assertEqual(self.expected[number]["ledger_events"], [])

    def test_root_cause_action_writes_three_events(self):
        # Design section 4.5: request, record and completion are written in one transaction.
        requests = [e for case in self.cases.values() for e in case["audit_events"]
                    if e["action"] == "action.requested" and e["payload"]["action_type"] == "root_cause_record"]
        self.assertTrue(requests)
        for request in requests:
            ref_id = request["source_ref"]
            events = {e["action"]: e for case in self.cases.values() for e in case["audit_events"]
                      if e["source_ref"] == ref_id}
            with self.subTest(request=ref_id):
                self.assertEqual(sorted(events),
                                 ["action.completed", "action.requested", "blocker.root_cause_recorded"])
                done = events["action.completed"]
                self.assertEqual(done["event_uid"], "safeboard:action_request:%s:completed" % ref_id)
                self.assertEqual(done["outcome"], "done")
                self.assertEqual(done["payload"]["action_type"], "root_cause_record")
                self.assertEqual({e["occurred_at"] for e in events.values()}, {request["occurred_at"]})
                self.assertEqual(done["objects"], request["objects"])

    def test_rule7_looks_at_every_root_cause_code(self):
        # Design section 5.4 names no exception, so the fake record must not carry one.
        by_code = self.rule7["byRootCause"]
        self.assertEqual(sorted(by_code), ["distinctBlockerKeysInPeriodAtLeast",
                                           "maxDistinctBlockerKeysPerPeriod", "subject"])
        opened_at = self.expected[9]["episodes"][0]["opened_at"]
        episodes = [dict(blocker_key="issue:DEMO-%d" % n, opened_at=opened_at, root_cause_code=ref.UNCLASSIFIED)
                    for n in range(by_code["distinctBlockerKeysInPeriodAtLeast"])]
        period = ref.period_key(opened_at, self.thresholds["kaizenRules"]["period"])
        self.assertEqual(ref.rule7_subjects(episodes, self.thresholds),
                         {("root_cause_code", ref.UNCLASSIFIED, period)})

    def test_rule7_cases_agree_with_the_fake_rte_record(self):
        for number in range(1, 13):
            case, expected = self.cases[number], self.expected[number]
            held = ref.rule7_subjects(expected["episodes"], self.thresholds)
            already_open = {(i["subject_kind"], i["subject"], i["period"])
                            for i in case["context"]["kaizen_items"] if i["rule_key"] == "rule7"}
            created = [e for e in expected["ledger_events"] if e["action"] == "kaizen.candidate_created"]
            added = [e for e in expected["ledger_events"] if e["action"] == "kaizen.evidence_added"]
            with self.subTest(case=number):
                automatic = {(c["subject_kind"], c["subject"], c["period"])
                             for c in expected["kaizen_candidates"] if c["rule_key"] == "rule7"}
                self.assertEqual(automatic, held)
                self.assertEqual({(e["kaizen_key"]["subject_kind"], e["kaizen_key"]["subject"],
                                   e["kaizen_key"]["period"]) for e in added}, held & already_open)
                self.assertEqual(len(created), len(expected["kaizen_candidates"]) - len(case["context"]["kaizen_items"]))
                for candidate in expected["kaizen_candidates"]:
                    self.assertEqual(sorted(candidate["evidence"]),
                                     ["episodes", "root_cause_code", "total_waiting_issues"])

        by_key, by_code = self.rule7["byBlockerKey"], self.rule7["byRootCause"]
        self.assertEqual(self.expected[8]["episode_count"], by_key["opensInPeriodAtLeast"])
        self.assertEqual(len(self.expected[8]["kaizen_candidates"]), 1)
        nine = self.expected[9]
        self.assertEqual(len({e["blocker_key"] for e in nine["episodes"]}), by_code["distinctBlockerKeysInPeriodAtLeast"])
        self.assertEqual([c["subject_kind"] for c in nine["kaizen_candidates"]], ["root_cause_code"])
        ten = self.expected[10]
        self.assertEqual([e["action"] for e in ten["ledger_events"]], ["kaizen.evidence_added"])
        self.assertEqual(len(ten["kaizen_candidates"]), 1)
        eleven = self.expected[11]
        self.assertEqual((eleven["kaizen_candidates"], eleven["ledger_events"]), ([], []))
        periods = [ref.period_key(e["opened_at"], self.thresholds["kaizenRules"]["period"]) for e in eleven["episodes"]]
        self.assertEqual(max(periods.count(p) for p in periods), by_key["maxOpeningsPerPeriod"])
        self.assertGreater(len(periods), by_key["maxOpeningsPerPeriod"])
        twelve = self.expected[12]
        self.assertEqual([c["rule_key"] for c in twelve["kaizen_candidates"]], [self.rule7["manualRule"]])
        self.assertEqual([e["action"] for e in twelve["ledger_events"]], ["kaizen.candidate_created"])
        self.assertEqual(self.rule7["manualRule"], "manual.blocker")


if __name__ == "__main__":
    unittest.main()
