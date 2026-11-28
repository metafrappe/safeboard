"""Loader for the fake dependency graph data (design section 6). No live data is read."""
import json
import os

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "dependency_graph")
MAIN = "main"
TIE_SCENARIOS = ("tie_length", "tie_active", "tie_teams", "tie_oldest")
SCENARIOS = (MAIN,) + TIE_SCENARIOS


def load_scenario(name):
    """Returns {"scenario", "input", "expected"} for one scenario file."""
    with open(os.path.join(FIXTURE_DIR, name + ".json"), encoding="utf-8") as f:
        return json.load(f)
