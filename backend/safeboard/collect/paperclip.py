"""Read-only Paperclip API client."""
import json
import urllib.parse
import urllib.request

from safeboard import config


def get(path):
    with urllib.request.urlopen(config.API + path, timeout=20) as r:
        d = json.load(r)
    return d if isinstance(d, list) else d.get("items", d)


def all_issues():
    return get(f"/companies/{config.COMPANY}/issues?limit=5000")


def project_issues(issues):
    return [i for i in issues if i.get("projectId") == config.PROJECT]


def all_agents():
    return get(f"/companies/{config.COMPANY}/agents")


def heartbeat_runs(limit):
    """The most recent runs of the company, newest first."""
    return get(f"/companies/{config.COMPANY}/heartbeat-runs?limit={int(limit)}")


def issue_activity(issue_id):
    return get(f"/issues/{urllib.parse.quote(str(issue_id), safe='')}/activity")
