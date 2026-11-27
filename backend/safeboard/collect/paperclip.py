"""Read-only Paperclip API client."""
import json
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
