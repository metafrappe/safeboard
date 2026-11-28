# SAFeBoard

SAFeBoard is a live delivery board for SAFe and Scrum teams. It reads work items from Paperclip and pull requests from GitHub.

It shows Program Increments, sprint burndown, flow metrics, DORA metrics, blocker escalation and the Kaizen lifecycle.

The board runs on localhost first. Deployment happens only after the product owner approves it.

## Licence

The code is released under the MIT Licence. See `LICENSE`.

## Layout

```text
backend/safeboard/      Python package (standard library only)
  collect/              Paperclip and GitHub readers
  history/              snapshots and database (later work)
  pi/                   PI calendar and sprint settings
  flow/                 flow metrics: board summary and burndown
  escalation/           blocker age and escalation (later work)
  dora/                 DORA metrics (later work)
  kaizen/               Kaizen lifecycle (later work)
  web/                  HTTP server and JSON API
backend/tests/          unittest tests with fake data
frontend/               the board page, built with Vite
frontend/tests/         Playwright tests
docs/decisions/         decision records
```

## Run on localhost

1. Build the page once: `cd frontend && npm ci && npm run build`.
2. Start the backend: `cd backend && python3 -m safeboard`.
3. Open `http://127.0.0.1:3195/`.

The backend listens only on `127.0.0.1`. It reads Paperclip and GitHub. It never writes to them.

## Cancelled runs in three groups

Paperclip cancels the run on an issue when the issue goes to another assignee. It writes the code `issue_reassigned`. The board reads the recent runs and the activity of each issue. It only reads. It puts each cancellation in one group:

- "Boş uyanma": the run never started.
- "Normal devir": the run started and gave the issue away itself.
- "Kesilen çalışma": the run started and another agent or a user gave the issue away. Only this group is shown as lost work.

A started run with no known reassigner counts as "Kesilen çalışma". The page says how many such runs there are.

## Tests

Tests use fake data. They never read Paperclip or GitHub.

- Backend: `python3 -I -m unittest discover -s backend/tests -t backend -v`
- Page, quick local run (one browser, 320 px): `cd frontend && npm run test:quick`
- Page, full matrix (Chromium and WebKit, six widths): `cd frontend && npm test`. CI runs this on every pull request.

## Settings

Environment variables override the defaults:

| Variable | Default |
| --- | --- |
| `SAFEBOARD_PORT` (or `PANO_PORT`) | `3195` |
| `SAFEBOARD_PAPERCLIP_API` | `http://127.0.0.1:3100/api` |
| `SAFEBOARD_COMPANY_ID` | the Paperclip company of the MVP |
| `SAFEBOARD_PROJECT_ID` | the Paperclip project of the MVP |
| `SAFEBOARD_RUN_LIMIT` | `1000` recent runs read for the cancellation groups |
| `SAFEBOARD_REPOS` | `metafrappe/backend,metafrappe/frontend` |
| `SAFEBOARD_DATA_DIR` | `~/Library/Application Support/safeboard` |
| `SAFEBOARD_STATIC_DIR` | `frontend/dist` |

Data stays outside the repository. The sprint settings file is `SAFEBOARD_DATA_DIR/sprint.json`. The repository holds no secret, no live data and no database file.

GitHub is read through your existing `gh` session. The backend keeps no token.
