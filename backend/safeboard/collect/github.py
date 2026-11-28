"""Read-only GitHub summary through the user's `gh` session."""
import datetime as dt
import json
import subprocess

from safeboard import config
from safeboard.timeutil import ts


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def checks(p):
    st = [c.get("conclusion") or c.get("state") or c.get("status") for c in p.get("statusCheckRollup") or []]
    if not st:
        return "yok"
    if any(s in ("FAILURE", "ERROR", "CANCELLED", "TIMED_OUT") for s in st):
        return "kırmızı"
    if all(s in ("SUCCESS", "SKIPPED", "NEUTRAL") for s in st):
        return "yeşil"
    return "sürüyor"


def repo_summary(repo, prs, run, now):
    open_prs = [p for p in prs if p["state"] == "OPEN"]
    cs = {}
    for p in open_prs:
        k = checks(p)
        cs[k] = cs.get(k, 0) + 1
    merged = [p for p in prs if p.get("mergedAt")]
    return {
        "repo": repo,
        "url": f"https://github.com/{repo}/pulls",
        "open": len(open_prs),
        "toMain": sum(1 for p in open_prs if p["baseRefName"] == "main"),
        "autoMerge": sum(1 for p in open_prs if any(l["name"] == "auto-merge" for l in p["labels"])),
        "checks": cs,
        "merged": len(merged),
        "merged24": sum(1 for p in merged if (now - ts(p["mergedAt"])).total_seconds() < 86400),
        "main": (run or [{}])[0].get("conclusion") or ((run or [{}])[0].get("status") or "bilinmiyor"),
        "latest": [{"n": p["number"], "title": p["title"], "at": p["mergedAt"], "url": f"https://github.com/{repo}/pull/{p['number']}"} for p in sorted(merged, key=lambda p: p["mergedAt"], reverse=True)[:5]],
    }


def github():
    now = dt.datetime.now(dt.timezone.utc)
    out = []
    for repo in config.REPOS:
        prs = gh("pr", "list", "-R", repo, "--state", "all", "--limit", "300", "--json", "number,title,state,createdAt,mergedAt,labels,baseRefName,statusCheckRollup") or []
        run = gh("run", "list", "-R", repo, "--branch", "main", "--limit", "1", "--json", "conclusion,status")
        out.append(repo_summary(repo, prs, run, now))
    return out
