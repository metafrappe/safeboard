"""Settings. Defaults match the MVP; environment variables override them.

No secret lives here. Paperclip is read without a key on 127.0.0.1 and GitHub is
read through the user's existing `gh` session.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PORT = int(os.environ.get("SAFEBOARD_PORT") or os.environ.get("PANO_PORT") or "3195")
API = os.environ.get("SAFEBOARD_PAPERCLIP_API", "http://127.0.0.1:3100/api")
COMPANY = os.environ.get("SAFEBOARD_COMPANY_ID", "7a5ebc45-2e84-41af-a4ad-8d767b014f19")
PROJECT = os.environ.get("SAFEBOARD_PROJECT_ID", "9610132e-ee0b-4fcc-a038-9490795e9e76")
REPOS = [r.strip() for r in os.environ.get("SAFEBOARD_REPOS", "metafrappe/backend,metafrappe/frontend").split(",") if r.strip()]

# Data stays outside the repository (architecture decision, question 2).
DATA_DIR = Path(os.environ.get("SAFEBOARD_DATA_DIR") or Path.home() / "Library" / "Application Support" / "safeboard")
# Built frontend (npm run build in frontend/).
STATIC_DIR = Path(os.environ.get("SAFEBOARD_STATIC_DIR") or ROOT / "frontend" / "dist")

OPEN = {"todo", "in_progress", "in_review", "blocked", "backlog"}
