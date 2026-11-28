"""Fast checks for the fake blocker action data (AJA-2312, design sections 4.1, 4.3 and 4.5)."""
import json
import re
import unittest
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "blocker_actions"
FILES = ("cases.json", "fake_paperclip.json", "expected_events.json")

# Design section 4.2: the seven action buttons and the two link buttons.
BUTTONS = {
    "Eskalasyonu başlat": "escalate_next", "Sahibine ver": "assign_owner", "Başka ajana ver": "assign_agent",
    "Ajanı uyandır": "wake_agent", "Müşteriye sor": "customer_question", "Kaizen adayı yap": "kaizen_candidate",
    "Kök nedeni kaydet": "root_cause_record",
}
LINKS = {"Paperclip'te aç", "GitHub'da aç"}
OUTCOMES = {"done", "skipped_state_changed", "denied", "failed"}
# Design section 4.5: event name -> short name used as the last part of event_uid.
EVENTS = {"action.requested": "requested", "action.denied": "denied", "action.completed": "completed",
          "blocker.root_cause_recorded": "root_cause_recorded"}
ENVELOPE = {"event_uid", "schema_version", "occurred_at", "time_basis", "observed_after", "recorded_at", "source",
            "source_ref", "action", "actor_kind", "actor_id", "issue_id", "run_id", "pr_ref", "causation_id",
            "outcome", "source_code", "payload", "objects"}
ROW = {"id", "action_type", "blocker_id", "target", "escalation_step", "requested_by", "requested_at", "outcome",
       "listed_in_due", "dedupe", "interaction_id"}
OPEN_ISSUE = {"todo", "in_progress", "in_review", "blocked"}
TITLES = {
    1: "yedi eylem", 2: "Tailscale", 3: "Origin", 4: "iki kez", 5: "Durdurulmuş ajan", 6: "Çalışan koşu",
    7: "açık iş", 8: "Durdurulmuş sahip", 9: "Başka takım", 10: "metni", 11: "Karar sorusu", 12: "İkinci",
    13: "Kaizen", 14: "sözlük", 15: "bağlantı",
}


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class BlockerActionFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load("cases.json")
        cls.cases = {case["id"]: case for case in cls.data["cases"]}
        cls.expected = {case["id"]: case for case in load("expected_events.json")["cases"]}
        cls.paperclip = {int(number): calls for number, calls in load("fake_paperclip.json")["cases"].items()}

    def presses(self, number, links=False):
        return [step for step in self.cases[number]["presses"] if bool(step.get("link")) == links]

    def writes(self, number):
        return [write for run in self.expected[number]["rte"] for write in run["paperclip_writes"] or []]

    def test_fifteen_cases_each_with_an_expected_result(self):
        for group in (self.cases, self.expected, self.paperclip):
            self.assertEqual(sorted(group), list(range(1, 16)))
        for number, case in self.cases.items():
            expected = self.expected[number]
            with self.subTest(case=number):
                self.assertIn(TITLES[number], case["title"])
                self.assertTrue(case["design_sections"] and case["blocker"]["blocker_id"])
                self.assertEqual(sorted(expected), ["action_requests", "id", "kaizen_events", "ledger_events",
                                                    "responses", "rte"])
                self.assertEqual(len(expected["responses"]), len(self.presses(number)))
                for step in case["presses"]:
                    if step.get("link"):
                        self.assertIn(step["button"], LINKS)
                        self.assertNotIn("action_type", step)
                    else:
                        self.assertEqual(BUTTONS[step["button"]], step["action_type"])
                        self.assertEqual(step["blocker_id"], case["blocker"]["blocker_id"])

    def test_request_rows_match_the_responses(self):
        for number, expected in self.expected.items():
            rows = expected["action_requests"]
            created = [r["request_id"] for r in expected["responses"] if r["created"]]
            with self.subTest(case=number):
                first = self.cases[number]["first_request_id"]
                self.assertEqual([row["id"] for row in rows], list(range(first, first + len(rows))))
                self.assertEqual(created, [row["id"] for row in rows])
                for row in rows:
                    self.assertEqual(set(row), ROW)
                    self.assertIn(row["action_type"], BUTTONS.values())
                    self.assertIn(row["outcome"], OUTCOMES)
                for step, response in zip(self.presses(number), expected["responses"]):
                    self.assertEqual(response["step"], step["step"])
                    allowed = step["action_type"] in self.data["permissions"].get(step["user"]["kind"], [])
                    same_origin = step["origin"] == self.data["board_origin"]
                    if not same_origin:
                        self.assertEqual((response["status"], response["request_id"]), (403, None))
                    elif not allowed:
                        self.assertEqual((response["status"], response["created"]), (403, True))
                    else:
                        self.assertIn(response["status"], (202, 400))
                    if response["status"] == 400:
                        self.assertEqual(list(response["body"]), ["error"])
                        self.assertIsNone(response["request_id"])
                    if response["request_id"] is not None:
                        self.assertIn(response["request_id"], [row["id"] for row in rows])

    def test_ledger_events_follow_section_4_5(self):
        seen = set()
        for number, expected in self.expected.items():
            rows = {row["id"]: row for row in expected["action_requests"]}
            by_row = {row_id: [] for row_id in rows}
            for event in expected["ledger_events"]:
                with self.subTest(case=number, uid=event.get("event_uid")):
                    self.assertEqual(set(event), ENVELOPE)
                    self.assertEqual((event["source"], event["schema_version"], event["time_basis"]),
                                     ("safeboard", 2, "source"))
                    row = rows[int(event["source_ref"])]
                    self.assertEqual(event["event_uid"],
                                     f"safeboard:action_request:{row['id']}:{EVENTS[event['action']]}")
                    self.assertNotIn(event["event_uid"], seen)
                    seen.add(event["event_uid"])
                    self.assertEqual(event["payload"]["action_type"], row["action_type"])
                    self.assertEqual(event["objects"], [{"object_kind": "blocker", "object_id": row["blocker_id"],
                                                         "link_basis": "explicit"}])
                    requested = f"safeboard:action_request:{row['id']}:requested"
                    first = event["action"] in ("action.requested", "action.denied")
                    self.assertEqual(event["causation_id"], None if first else requested)
                    self.assertEqual(event["outcome"], row["outcome"] if event["action"] == "action.completed" else None)
                    by_row[row["id"]].append(event["action"])
            for row_id, row in rows.items():
                with self.subTest(case=number, request=row_id):
                    if row["dedupe"] is None:  # the user had no permission; the row is born closed
                        self.assertEqual(by_row[row_id], ["action.denied"])
                        self.assertEqual((row["outcome"], row["listed_in_due"]), ("denied", False))
                    elif row["action_type"] == "root_cause_record":
                        self.assertEqual(by_row[row_id], ["action.requested", "blocker.root_cause_recorded",
                                                          "action.completed"])
                        self.assertEqual((row["outcome"], row["listed_in_due"]), ("done", False))
                    else:
                        self.assertEqual(by_row[row_id], ["action.requested", "action.completed"])
                        self.assertTrue(row["listed_in_due"])
                        self.assertEqual(set(row["dedupe"]), {"action_type", "blocker_id", "target", "step"})

    def test_rte_results_match_the_fake_paperclip(self):
        company = self.data["company_id"]
        for number, expected in self.expected.items():
            rows = {row["id"]: row for row in expected["action_requests"]}
            calls = self.paperclip[number]
            for call, response in calls.items():
                self.assertRegex(call, r"^(GET|POST|PATCH) /api/")
                self.assertEqual(sorted(response), ["body", "status"])
            due = [row_id for row_id, row in rows.items() if row["listed_in_due"]]
            self.assertEqual([run["request_id"] for run in expected["rte"]], due)
            for run in expected["rte"]:
                row = rows[run["request_id"]]
                with self.subTest(case=number, request=row["id"]):
                    self.assertEqual(run["outcome"], row["outcome"])
                    if row["action_type"] not in ("wake_agent", "assign_owner", "assign_agent"):
                        continue
                    agent = calls[f"GET /api/agents/{row['target']}"]["body"]
                    if row["action_type"] == "wake_agent":
                        runs = calls[f"GET /api/companies/{company}/live-runs"]["body"]
                        issues = calls[f"GET /api/companies/{company}/issues?assigneeAgentId={row['target']}"]["body"]
                        if agent["status"] == "paused":
                            outcome = "denied"
                        elif any(r["agentId"] == row["target"] and r["status"] == "running" for r in runs):
                            outcome = "skipped_state_changed"
                        elif not any(issue["status"] in OPEN_ISSUE for issue in issues):
                            outcome = "skipped_state_changed"
                        else:
                            outcome = "done"
                        invoke = {"method": "POST", "path": f"/api/agents/{row['target']}/heartbeat/invoke"}
                        self.assertEqual(run["paperclip_writes"], [invoke] if outcome == "done" else [])
                    else:
                        outcome = "denied" if agent["status"] == "paused" else "done"
                    self.assertEqual(run["outcome"], outcome)
                for write in run["paperclip_writes"] or []:
                    self.assertIn(f"{write['method']} {write['path']}", calls)

    def test_each_case_shows_its_own_rule(self):
        rows = {number: expected["action_requests"] for number, expected in self.expected.items()}
        status = {number: [r["status"] for r in expected["responses"]] for number, expected in self.expected.items()}
        actions = {number: [e["action"] for e in expected["ledger_events"]] for number, expected in self.expected.items()}
        outcome = {number: [row["outcome"] for row in rows[number]] for number in rows}
        # 1: seven buttons, one press each, one row each.
        self.assertEqual({s["user"]["kind"] for s in self.presses(1)}, {"local"})
        self.assertEqual(sorted(row["action_type"] for row in rows[1]), sorted(BUTTONS.values()))
        self.assertEqual((status[1], outcome[1]), ([202] * 7, ["done"] * 7))
        # 2: a Tailscale user is refused, the refusal is a closed row and one action.denied event.
        self.assertEqual(self.presses(2)[0]["user"]["kind"], "tailscale")
        self.assertEqual((status[2], outcome[2], actions[2]), ([403], ["denied"], ["action.denied"]))
        self.assertEqual(self.expected[2]["ledger_events"][0]["actor_id"], self.presses(2)[0]["user"]["login"])
        # 3: a foreign Origin is refused before anything is written.
        self.assertEqual((status[3], rows[3], actions[3]), ([403], [], []))
        # 4: two presses on the same button open one request.
        self.assertEqual(len({s["action_type"] for s in self.presses(4)}), 1)
        self.assertEqual([(r["request_id"], r["created"]) for r in self.expected[4]["responses"]],
                         [(rows[4][0]["id"], True), (rows[4][0]["id"], False)])
        self.assertEqual((len(rows[4]), actions[4]), (1, ["action.requested", "action.completed"]))
        # 5 to 8: the second layer of section 4.3.
        self.assertEqual([(rows[n][0]["action_type"], outcome[n]) for n in (5, 6, 7, 8)], [
            ("wake_agent", ["denied"]), ("wake_agent", ["skipped_state_changed"]),
            ("wake_agent", ["skipped_state_changed"]), ("assign_owner", ["denied"])])
        self.assertEqual([self.writes(n) for n in (5, 6, 7, 8)], [[], [], [], []])
        # 9: the target agent is in another team, so the issue goes to that team's PO.
        target = self.paperclip[9][f"GET /api/agents/{rows[9][0]['target']}"]["body"]
        agents = self.paperclip[9][f"GET /api/companies/{self.data['company_id']}/agents"]["body"]
        po = [a["id"] for a in agents if a["team"] == target["team"] and a["role"] == "po"]
        self.assertNotEqual(target["team"], self.cases[9]["blocker"]["root_issue_team"])
        self.assertEqual([w["body"] for w in self.writes(9)], [{"assigneeAgentId": po[0]}])
        # 10: the question text never reaches the ledger or the expected file.
        question = self.presses(10)[0]["body"]["question_text"]
        self.assertGreater(len(question), 20)
        self.assertNotIn(question, (FIXTURES / "expected_events.json").read_text(encoding="utf-8"))
        root = self.cases[10]["blocker"]["root_issue_id"]
        self.assertEqual([w["path"] for w in self.writes(10)], [f"/api/issues/{root}/interactions"])
        self.assertEqual(self.writes(10)[0]["body"], {"kind": "ask_user_questions", "resolverPolicy": "human_only"})
        # 11: no Paperclip issue behind the root, so a "Karar sorusu" issue is opened first.
        self.assertIsNone(self.cases[11]["blocker"]["root_issue_id"])
        first, second = self.writes(11)
        self.assertEqual((first["path"], first["body"]["title"]),
                         (f"/api/companies/{self.data['company_id']}/issues", "Karar sorusu"))
        self.assertEqual(first["body"]["projectId"], self.data["safeboard_project_id"])
        created = self.paperclip[11][f"POST {first['path']}"]["body"]["id"]
        self.assertEqual(second["path"], f"/api/issues/{created}/interactions")
        # 12: one open card per episode; later presses return the first request.
        self.assertEqual(len(self.presses(12)), 3)
        self.assertEqual([(r["request_id"], r["created"]) for r in self.expected[12]["responses"]],
                         [(rows[12][0]["id"], True), (rows[12][0]["id"], False), (rows[12][0]["id"], False)])
        self.assertLess(self.presses(12)[1]["at"], self.cases[12]["rte_reports"][0]["at"])
        self.assertGreater(self.presses(12)[2]["at"], self.cases[12]["rte_reports"][0]["at"])
        self.assertEqual((len(self.writes(12)), actions[12]), (1, ["action.requested", "action.completed"]))
        self.assertTrue(rows[12][0]["interaction_id"])
        # 13: an open candidate on the same subject only gets new evidence.
        self.assertEqual(len(self.cases[13]["kaizen_items"]), 1)
        self.assertEqual([e["action"] for e in self.expected[13]["kaizen_events"]], ["kaizen.evidence_added"])
        self.assertEqual([e["action"] for e in self.expected[1]["kaizen_events"]], ["kaizen.candidate_created"])
        self.assertEqual(self.expected[13]["kaizen_events"][0]["kaizen_key"]["subject"],
                         self.cases[13]["kaizen_items"][0]["subject"])
        # 14: a code outside the dictionary is refused.
        code = self.presses(14)[0]["body"]["root_cause_code"]
        self.assertNotIn(code, self.data["root_cause_codes"])
        self.assertIn(self.presses(1)[-1]["body"]["root_cause_code"], self.data["root_cause_codes"])
        self.assertEqual((status[14], rows[14], actions[14]), ([400], [], []))
        # 15: the two link buttons send nothing and write nothing.
        self.assertEqual({s["button"] for s in self.presses(15, links=True)}, LINKS)
        self.assertEqual((self.presses(15), status[15], rows[15], actions[15]), ([], [], [], []))

    def test_fake_data_holds_no_real_record(self):
        text = "".join((FIXTURES / name).read_text(encoding="utf-8") for name in FILES)
        for pattern in (r"AJA-\d+", r"metafrappe", r"(?i)token|secret|password|bearer|api[_-]?key", r"gh[pousr]_\w+",
                        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-", r"claude-0[1-5]\b", r"Team (A|B|SAFe)\b",
                        r"\.ts\.net", r":3100\b", r"@(?!example\.test\b)[\w-]+\.\w+",
                        r"https?://(?!127\.0\.0\.1:3195\b|[\w.-]*example\.test\b)"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, text))
        self.assertTrue(self.data["fake"])


if __name__ == "__main__":
    unittest.main()
