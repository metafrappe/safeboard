"""Checks the fake dependency graph data against the rules of design sections 6.1, 6.2, 6.3 and 6.5.

The expected results are written by hand. This file recomputes them with a small,
separate reading of the rules. A mismatch means the data or the reading is wrong.
"""
import json
import re
import unittest

from tests.dependency_fixture import MAIN, SCENARIOS, TIE_SCENARIOS, load_scenario

ACTIVE = ("blocked", "in_progress", "in_review", "todo")
EDGE_FIELDS = {"from_node", "to_node", "edge_kind", "basis", "state", "broken_kind", "cross_team", "source_ref"}
NODE_KINDS = {"issue", "team", "repo", "pr", "external"}
EDGE_KINDS = {"issue", "team", "repo", "pr", "external"}
# Definition 7.3 type number -> dictionary code (design 1.5 and the event ledger dictionary).
BROKEN_CODES = {
    1: "dep.broken_cancelled",
    2: "dep.stale_done_blocker",
    3: "dep.broken_closed_base",
    4: "dep.broken_cycle",
    5: "proc.backlog_root",
    6: "dep.broken_legacy_repo",
    7: "dep.unrecorded",
    8: "dep.broken_missing_target",
}
TIE_RULE = {
    "tie_length": "length",
    "tie_active": "unlocked_active_issues",
    "tie_teams": "unlocked_teams",
    "tie_oldest": "oldest_wait",
}
RULE_ORDER = ("length", "unlocked_active_issues", "unlocked_teams", "oldest_wait")
WAIT_WORDS = ("bekliyor", "blocked by", "depends on")


def nid(identifier):
    return "issue:" + identifier


def team_of(assignee):
    m = re.match(r"Team (SAFe|[A-Z])\b", assignee or "")
    return m.group(0) if m else None


def cycle_members(pairs):
    """Nodes that can reach themselves through the given (waiting, awaited) pairs."""
    nxt = {}
    for a, b in pairs:
        nxt.setdefault(a, set()).add(b)

    def reach(start):
        seen, todo = set(), list(nxt.get(start, ()))
        while todo:
            n = todo.pop()
            if n not in seen:
                seen.add(n)
                todo.extend(nxt.get(n, ()))
        return seen

    return {n for n in nxt if n in reach(n)}


class World:
    """One scenario plus the helpers the checks share."""

    def __init__(self, name):
        self.data = load_scenario(name)
        self.inp, self.exp = self.data["input"], self.data["expected"]
        self.issues = {i["identifier"]: i for i in self.inp["issues"]}
        self.nodes = {n["id"]: n for n in self.exp["nodes"]}
        self.edges = self.exp["edges"]

    def issue_edges(self, state=None, basis="explicit"):
        return [e for e in self.edges if e["edge_kind"] == "issue" and e["basis"] == basis
                and (state is None or e["state"] == state)]

    def team(self, node_id):
        return self.nodes[node_id].get("team")

    def status(self, node_id):
        issue = self.issues.get(node_id.split(":", 1)[1])
        return issue["status"] if issue else None

    def open_pairs(self, scope=None):
        """Open explicit issue edges, narrowed to a scope: both ends must be inside it."""
        pairs = [(e["from_node"], e["to_node"]) for e in self.issue_edges("open")]
        if scope and scope["kind"] != "company":
            def inside(n):
                issue = self.issues[n.split(":", 1)[1]]
                return (issue.get("pi") if scope["kind"] == "pi" else self.team(n)) == scope["id"]
            pairs = [p for p in pairs if inside(p[0]) and inside(p[1])]
        return pairs

    def waiters(self, root, pairs):
        """(direct, indirect) active issues that wait for root. Backlog issues are left out."""
        back = {}
        for a, b in pairs:
            back.setdefault(b, set()).add(a)
        direct = set(back.get(root, ()))
        seen, todo = set(direct), list(direct)
        while todo:
            for a in back.get(todo.pop(), ()):
                if a not in seen:
                    seen.add(a)
                    todo.append(a)
        active = {n for n in seen if self.status(n) in ACTIVE}
        return direct & active, active - direct

    def candidates(self, scope=None):
        """One candidate per root: its longest open chain and the tie-break numbers."""
        pairs = self.open_pairs(scope)
        nxt = {}
        for a, b in pairs:
            nxt.setdefault(a, []).append(b)
        chains = []

        def walk(path):
            steps = nxt.get(path[-1], [])
            if not steps:
                chains.append(path)
            for b in steps:
                walk(path + [b])  # open edges hold no cycle; a cycle is broken, not open

        for start in sorted({a for a, _ in pairs} - {b for _, b in pairs}):
            walk([start])
        best = {}
        for chain in chains:
            if len(chain) > len(best.get(chain[-1], [])):
                best[chain[-1]] = chain
        out = []
        for root, chain in best.items():
            direct, indirect = self.waiters(root, pairs)
            unlocked = direct | indirect
            started = min(self.issues[n.split(":", 1)[1]]["blockedAt"] for n in chain[:-1])
            out.append({
                "root": root, "chain": chain, "edge_count": len(chain) - 1,
                "unlocked_active_issues": len(unlocked),
                "unlocked_teams": len({self.team(n) for n in unlocked}),
                "oldest_wait_started_at": started,
            })
        return out

    def critical_path(self, scope=None):
        """Winner and the rule that decided it. Order: length, active issues, teams, oldest."""
        left, decided = self.candidates(scope), "length"
        keys = (("length", lambda c: c["edge_count"]),
                ("unlocked_active_issues", lambda c: c["unlocked_active_issues"]),
                ("unlocked_teams", lambda c: c["unlocked_teams"]),
                ("oldest_wait", lambda c: [-ord(ch) for ch in c["oldest_wait_started_at"]]))
        for rule, key in keys:
            if len(left) == 1:
                break
            top = max(key(c) for c in left)
            left, decided = [c for c in left if key(c) == top], rule
        assert len(left) == 1, "the data must leave exactly one critical path"
        return left[0], decided


class FixtureShape(unittest.TestCase):
    def test_every_scenario_has_input_and_expected(self):
        for name in SCENARIOS:
            data = load_scenario(name)
            self.assertEqual(data["scenario"], name)
            self.assertTrue(data["input"]["issues"] and data["expected"]["edges"], name)

    def test_edges_carry_the_design_fields_and_point_to_known_nodes(self):
        for name in SCENARIOS:
            w = World(name)
            seen = set()
            for e in w.edges:
                self.assertTrue(EDGE_FIELDS <= set(e), (name, e))
                self.assertIn(e["from_node"], w.nodes, name)
                self.assertIn(e["to_node"], w.nodes, name)
                self.assertIn(e["edge_kind"], EDGE_KINDS)
                self.assertIn(e["basis"], ("explicit", "inferred"))
                self.assertIn(e["state"], ("open", "resolved", "broken"))
                self.assertEqual(e["state"] == "broken", e["broken_kind"] is not None, (name, e))
                self.assertIsInstance(e["cross_team"], bool)
                self.assertNotIn((e["from_node"], e["to_node"], e["edge_kind"]), seen, "duplicate edge")
                seen.add((e["from_node"], e["to_node"], e["edge_kind"]))

    def test_nodes_match_the_input(self):
        for name in SCENARIOS:
            w = World(name)
            for n in w.nodes.values():
                self.assertIn(n["kind"], NODE_KINDS)
                self.assertTrue(n["id"].startswith(n["kind"] + ":"), n)
            issue_nodes = {i for i, n in w.nodes.items() if n["kind"] == "issue" and not n.get("missing")}
            self.assertEqual(issue_nodes, {nid(i) for i in w.issues}, name)
            for ident, issue in w.issues.items():
                self.assertEqual(w.team(nid(ident)), team_of(issue["assignee"]), ident)
            teams = {"team:" + n["team"] for n in w.nodes.values() if n.get("team")}
            self.assertEqual({i for i, n in w.nodes.items() if n["kind"] == "team"}, teams, name)

    def test_explicit_issue_edges_are_exactly_the_blocked_by_links(self):
        for name in SCENARIOS:
            w = World(name)
            links = {(nid(i["identifier"]), nid(b)) for i in w.issues.values() for b in i.get("blockedBy", [])}
            self.assertEqual({(e["from_node"], e["to_node"]) for e in w.issue_edges()}, links, name)

    def test_team_edges_are_the_open_cross_team_issue_edges_grouped_by_team_pair(self):
        for name in SCENARIOS:
            w = World(name)
            want = {}
            for e in w.issue_edges("open"):
                if e["cross_team"]:
                    key = ("team:" + w.team(e["from_node"]), "team:" + w.team(e["to_node"]))
                    want.setdefault(key, []).append(e["from_node"] + "->" + e["to_node"])
            got = {(e["from_node"], e["to_node"]): sorted(e["members"])
                   for e in w.edges if e["edge_kind"] == "team"}
            self.assertEqual(got, {k: sorted(v) for k, v in want.items()}, name)
            for e in w.edges:
                if e["edge_kind"] in ("team", "repo"):
                    self.assertEqual(e["count"], len(e["members"]), (name, e))

    def test_issue_edge_state_follows_the_rules(self):
        for name in SCENARIOS:
            w = World(name)
            pairs = [(e["from_node"], e["to_node"]) for e in w.issue_edges()]
            in_cycle = cycle_members(pairs)
            for e in w.issue_edges():
                a, b = e["from_node"], e["to_node"]
                blockers = [w.status(nid(x)) for x in w.issues[a.split(":", 1)[1]]["blockedBy"]]
                if w.nodes[b].get("missing"):
                    want = ("broken", BROKEN_CODES[8])
                elif a in in_cycle and b in in_cycle:
                    want = ("broken", BROKEN_CODES[4])
                elif w.status(b) == "cancelled":
                    want = ("broken", BROKEN_CODES[1])
                elif w.status(b) == "done":
                    stale = w.status(a) == "blocked" and all(s == "done" for s in blockers)
                    want = ("broken", BROKEN_CODES[2]) if stale else ("resolved", None)
                elif w.status(b) == "backlog" and w.status(a) in ACTIVE:
                    want = ("broken", BROKEN_CODES[5])
                else:
                    want = ("open", None)
                self.assertEqual((e["state"], e["broken_kind"]), want, (name, a, b))


class MainScenario(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = World(MAIN)

    def edge(self, a, b):
        found = [e for e in self.w.edges if (e["from_node"], e["to_node"]) == (a, b)]
        self.assertEqual(len(found), 1, (a, b))
        return found[0]

    def test_case_01_all_five_node_and_edge_kinds_appear(self):
        self.assertEqual({n["kind"] for n in self.w.nodes.values()}, NODE_KINDS)
        self.assertEqual({e["edge_kind"] for e in self.w.edges}, EDGE_KINDS)

    def test_case_02_team_b_issue_waits_for_team_a_issue(self):
        e = self.edge("issue:ORN-101", "issue:ORN-102")
        self.assertEqual((self.w.team(e["from_node"]), self.w.team(e["to_node"])), ("Team B", "Team A"))
        self.assertIs(e["cross_team"], True)
        self.assertEqual(e["state"], "open")

    def test_case_03_same_team_edge_is_not_cross_team(self):
        e = self.edge("issue:ORN-102", "issue:ORN-103")
        self.assertEqual(self.w.team(e["from_node"]), self.w.team(e["to_node"]))
        self.assertIs(e["cross_team"], False)

    def test_cross_team_follows_the_two_teams_on_every_edge(self):
        for e in self.w.edges:
            if e["edge_kind"] == "team":
                self.assertIs(e["cross_team"], True)
                continue
            a, b = self.w.team(e["from_node"]), self.w.team(e["to_node"])
            self.assertIs(e["cross_team"], bool(a and b and a != b), e)

    def test_case_04_three_open_issue_edges_become_one_team_edge(self):
        team_edges = [e for e in self.w.edges if e["edge_kind"] == "team"]
        self.assertEqual(len(team_edges), 1)
        e = team_edges[0]
        self.assertEqual((e["from_node"], e["to_node"], e["count"]), ("team:Team B", "team:Team A", 3))

    def test_case_05_parent_link_is_not_a_blocker(self):
        parents = [(i["identifier"], i["parentId"]) for i in self.w.issues.values() if i.get("parentId")]
        self.assertEqual(len(parents), 1)
        child, parent = parents[0]
        self.assertEqual(self.w.exp["parent_links"],
                         [{"child": nid(child), "parent": nid(parent), "counts_as_blocker": False}])
        both = {nid(child), nid(parent)}
        self.assertFalse([e for e in self.w.edges if {e["from_node"], e["to_node"]} == both])

    def test_case_06_comment_link_is_inferred_and_not_counted(self):
        inferred = [e for e in self.w.edges if e["basis"] == "inferred"]
        self.assertEqual(len(inferred), 1)
        e = inferred[0]
        waiting, awaited = e["from_node"].split(":")[1], e["to_node"].split(":")[1]
        self.assertEqual((e["state"], e["broken_kind"], e["source_ref"]), ("broken", "dep.unrecorded", "comment"))
        comments = [c["body"] for c in self.w.inp["comments"] if c["issue"] == waiting]
        self.assertTrue(any(awaited in c and any(word in c.lower() for word in WAIT_WORDS) for c in comments))
        self.assertNotIn(awaited, self.w.issues[waiting].get("blockedBy", []))
        counts = {c["root"]: c for c in self.w.exp["waiting_counts"]}
        self.assertEqual(counts[e["to_node"]]["total_waiting"], 0)

    def test_waiting_counts_use_open_explicit_edges_only(self):
        pairs = self.w.open_pairs()
        self.assertTrue(self.w.exp["waiting_counts"])
        for c in self.w.exp["waiting_counts"]:
            direct, indirect = self.w.waiters(c["root"], pairs)
            self.assertEqual((c["direct_waiting"], c["indirect_waiting"], c["total_waiting"]),
                             (len(direct), len(indirect), len(direct) + len(indirect)), c["root"])

    def test_case_07_each_of_the_eight_broken_kinds_appears_once(self):
        cases = self.w.exp["broken_cases"]
        self.assertEqual([c["type_no"] for c in cases], list(range(1, 9)))
        claimed = []
        for c in cases:
            self.assertEqual(c["broken_kind"], BROKEN_CODES[c["type_no"]])
            self.assertTrue(c["edges"] and c["note"])
            for ref in c["edges"]:
                a, b = ref.split("->")
                self.assertEqual(self.edge(a, b)["broken_kind"], c["broken_kind"], ref)
                claimed.append(ref)
            self.assertEqual(len(c["edges"]), 3 if c["type_no"] == 4 else 1)
        broken = sorted(e["from_node"] + "->" + e["to_node"] for e in self.w.edges if e["state"] == "broken")
        self.assertEqual(sorted(claimed), broken)

    def test_case_07_non_issue_broken_kinds_match_the_input(self):
        prs = {"pr:%s#%d" % (p["repo"], p["number"]): p for p in self.w.inp["pull_requests"]}
        repos = {r["name"]: r for r in self.w.inp["repos"]}
        by_kind = {c["type_no"]: c["edges"][0].split("->") for c in self.w.exp["broken_cases"]}
        upper, base = by_kind[3]
        self.assertEqual(prs[upper]["state"], "open")
        self.assertEqual((prs[base]["state"], prs[base]["merged"]), ("closed", False))
        self.assertEqual(prs[upper]["baseRefName"], prs[base]["headRefName"])
        issue, old_pr = by_kind[6]
        self.assertIn(self.w.status(issue), ACTIVE)
        self.assertIs(repos[prs[old_pr]["repo"]]["archived"], True)
        self.assertIn(old_pr[3:], self.w.issues[issue.split(":")[1]]["workProducts"])
        self.assertEqual(self.w.inp["missing_issues"], [by_kind[8][1].split(":")[1]])

    def test_case_08_cycle_edges_are_broken_cycle(self):
        pairs = [(e["from_node"], e["to_node"]) for e in self.w.issue_edges()]
        members = cycle_members(pairs)
        self.assertEqual(len(members), 3)
        ring = sorted(a + "->" + b for a, b in pairs if a in members and b in members)
        marked = sorted(e["from_node"] + "->" + e["to_node"] for e in self.w.edges
                        if e["broken_kind"] == "dep.broken_cycle")
        self.assertEqual(marked, ring)
        entering = [e for e in self.w.issue_edges("open") if e["to_node"] in members]
        self.assertEqual(len(entering), 1, "one open edge must lead into the cycle")

    def test_case_10_critical_path_in_three_scopes(self):
        cp = self.w.exp["critical_path"]
        scopes = [cp["company"]] + cp["pi"] + cp["team"]
        self.assertEqual([s["scope"]["kind"] for s in scopes], ["company", "pi", "pi", "team"])
        for s in scopes:
            winner, decided = self.w.critical_path(s["scope"])
            self.assertEqual((s["chain"], s["edge_count"], s["decided_by"]),
                             (winner["chain"], winner["edge_count"], decided), s["scope"])
            self.assertEqual(s["root"], s["chain"][-1])
        self.assertEqual(len({tuple(s["chain"]) for s in scopes}), 3, "the scopes must give three different paths")

    def test_on_critical_path_marks_the_company_chain(self):
        chain = self.w.exp["critical_path"]["company"]["chain"]
        on_path = set(zip(chain, chain[1:]))
        for e in self.w.edges:
            self.assertIs(e.get("on_critical_path", False),
                          e["edge_kind"] == "issue" and (e["from_node"], e["to_node"]) in on_path, e)


class TieScenarios(unittest.TestCase):
    def test_case_09_each_tie_rule_decides_exactly_one_scenario(self):
        for name in TIE_SCENARIOS:
            w = World(name)
            cp = w.exp["critical_path"]["company"]
            winner, decided = w.critical_path()
            self.assertEqual(decided, TIE_RULE[name], name)
            self.assertEqual((cp["chain"], cp["edge_count"], cp["decided_by"]),
                             (winner["chain"], winner["edge_count"], decided), name)
            mine = sorted(w.candidates(), key=lambda c: c["root"])
            for c in mine:
                del c["chain"]
            self.assertEqual(sorted(cp["candidates"], key=lambda c: c["root"]), mine, name)

    def test_case_09_the_next_rules_alone_would_pick_the_other_chain(self):
        """Guards the order: a wrong rule order must give a wrong answer on this data."""
        value = {"length": lambda c: c["edge_count"],
                 "unlocked_active_issues": lambda c: c["unlocked_active_issues"],
                 "unlocked_teams": lambda c: c["unlocked_teams"],
                 "oldest_wait": lambda c: c["oldest_wait_started_at"]}
        for name in TIE_SCENARIOS:
            cp = load_scenario(name)["expected"]["critical_path"]["company"]
            self.assertEqual(len(cp["candidates"]), 2, name)
            win = [c for c in cp["candidates"] if c["root"] == cp["root"]][0]
            lose = [c for c in cp["candidates"] if c["root"] != cp["root"]][0]
            at = RULE_ORDER.index(cp["decided_by"])
            for rule in RULE_ORDER[:at]:
                self.assertEqual(value[rule](win), value[rule](lose), (name, rule))
            for rule in RULE_ORDER[at + 1:]:
                if rule == "oldest_wait":
                    self.assertGreater(value[rule](win), value[rule](lose), (name, rule))
                else:
                    self.assertLess(value[rule](win), value[rule](lose), (name, rule))


class FixtureHygiene(unittest.TestCase):
    def test_expected_results_hold_no_time_estimate(self):
        banned = re.compile(r"estimat|eta\b|duration|tahmin|süre|remaining|days|hours|deadline", re.I)
        for name in SCENARIOS:
            text = json.dumps(load_scenario(name)["expected"], ensure_ascii=False)
            self.assertIsNone(banned.search(text), name)

    def test_data_is_fake_and_holds_no_personal_or_secret_value(self):
        banned = re.compile(r"AJA-|@|https?://|token|secret|password|şifre|metafrappe|atonota|turksab", re.I)
        for name in SCENARIOS:
            data = load_scenario(name)
            self.assertIsNone(banned.search(json.dumps(data, ensure_ascii=False)), name)
            for issue in data["input"]["issues"]:
                self.assertRegex(issue["identifier"], r"^ORN-\d+$")
                self.assertRegex(issue["assignee"], r"^Team (A|B|SAFe) [A-Za-z ]+$")


if __name__ == "__main__":
    unittest.main()
