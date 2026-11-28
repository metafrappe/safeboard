"""HTTP server: serves the built page and the JSON API on 127.0.0.1."""
import datetime as dt
import json
import os
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from safeboard import config
from safeboard.collect import github as gh_reader
from safeboard.collect import paperclip as pc
from safeboard.flow.board import summary
from safeboard.flow.burndown import burndown as burndown_calc
from safeboard.flow.reassign import counts as reassign_counts
from safeboard.pi import sprint
from safeboard.web.cache import cached, drop

LOCAL = dt.datetime.now().astimezone().tzinfo


def machine():
    la = os.getloadavg()
    return {"load": round(la[0]), "cpus": os.cpu_count()}


def paperclip():
    issues = pc.project_issues(pc.all_issues())
    agents = {a["id"]: a for a in pc.all_agents()}
    return summary(issues, agents, dt.datetime.now(dt.timezone.utc))


def reassign():
    """Counts of "issue_reassigned" cancellations in the recent runs, in three groups."""
    def activity_of(issue_id):
        try:
            return pc.issue_activity(issue_id)
        except urllib.error.HTTPError as e:
            if e.code == 404:  # the issue is gone; the run is counted with an unknown reassigner
                return None
            raise

    return reassign_counts(pc.heartbeat_runs(config.RUN_LIMIT), activity_of)


def burndown(team="Hepsi"):
    issues = pc.project_issues(cached("raw:issues", 20, pc.all_issues))
    agents = {a["id"]: a["name"] for a in cached("raw:agents", 60, pc.all_agents)}
    return burndown_calc(issues, agents, sprint.sprint_conf(), team, dt.datetime.now(LOCAL).date(), LOCAL)


STATIC = {"/font.woff2": ("font.woff2", "font/woff2")}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def file(self, name, ctype):
        try:
            with open(config.STATIC_DIR / name, "rb") as f:
                return self.send(200, f.read(), ctype)
        except FileNotFoundError:
            return self.send(503, "Arayüz derlenmemiş. frontend klasöründe npm run build çalıştırın.".encode(), "text/plain; charset=utf-8")

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            return self.file("index.html", "text/html; charset=utf-8")
        if self.path in STATIC:
            return self.file(*STATIC[self.path])
        if self.path == "/api/data":
            data = {"at": dt.datetime.now(dt.timezone.utc).isoformat(), "machine": machine()}
            errors = []
            try:
                data["paperclip"] = cached("pc", 25, paperclip)
            except Exception as e:  # report the failure on the page instead of a blank board
                errors.append(f"Paperclip okunamadı: {e}")
            try:
                data["reassign"] = cached("runs", 120, reassign)
            except Exception as e:
                errors.append(f"Çalışma kayıtları okunamadı: {e}")
            try:
                data["github"] = cached("gh", 90, gh_reader.github)
            except Exception as e:
                errors.append(f"GitHub okunamadı: {e}")
            data["errors"] = errors
            return self.send(200, json.dumps(data, ensure_ascii=False).encode(), "application/json")
        if self.path.startswith("/api/burndown"):
            team = parse_qs(urlparse(self.path).query).get("team", ["Hepsi"])[0]
            try:
                data = cached("bd:" + team, 25, lambda: burndown(team))
            except Exception as e:
                data = {"error": f"Burndown hesaplanamadı: {e}"}
            return self.send(200, json.dumps(data, ensure_ascii=False).encode(), "application/json")
        self.send(404, b"not found", "text/plain")

    def do_PUT(self):
        if self.path != "/api/sprint" or self.headers.get("Origin") not in (None, f"http://127.0.0.1:{config.PORT}"):
            return self.send(403, b"forbidden", "text/plain")
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0")) or 0))
            conf = sprint.parse(body)
        except Exception as e:
            return self.send(400, json.dumps({"error": str(e)}, ensure_ascii=False).encode(), "application/json")
        sprint.save(conf)
        drop("bd:")
        self.send(200, json.dumps(conf, ensure_ascii=False).encode(), "application/json")


def warm():
    for key, ttl, fn in (("pc", 25, paperclip), ("runs", 120, reassign), ("gh", 90, gh_reader.github), ("bd:Hepsi", 25, lambda: burndown("Hepsi"))):
        threading.Thread(target=lambda k=key, t=ttl, f=fn: cached(k, t, f), daemon=True).start()


def main():
    warm()
    ThreadingHTTPServer(("127.0.0.1", config.PORT), H).serve_forever()


if __name__ == "__main__":
    main()
