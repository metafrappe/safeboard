"""Time helpers shared by the modules."""
import datetime as dt


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def team_of(name):
    for t in ("Team A", "Team B", "Team SAFe"):
        if name.startswith(t):
            return t
    return "Diğer"
