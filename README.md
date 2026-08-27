# CS 112 Final Course Project — Team 14

Repository: https://github.com/jesseamoah77-dot/Team-14-cs-112-project

## Team members

| Name | ID |
| --- | --- |
| Jesse Amoah Odei | 86112029 |
| Ivana Maame Adjoa Boatemaa Koranteng | 03732029 |
| Georgina Lutterodt | 46602029 |
| Nathan Agyemang Asare | 76602029 |
| Bethany Nana Afua Wiafe | 04582029 |

## Contents

- [Components](#components)
- [Demos](#demos)
- [Setup](#setup)
- [Running Component 1](#running-component-1--grid-analysis)
- [Running Component 2](#running-component-2--gridcare-lite)
- [Running Component 3](#running-component-3--cliniccare-lite)
- [Reproducibility](#reproducibility)
- [Known limitations](#known-limitations)
- [Documentation](#documentation)

## Components

| Folder | Component | Stack |
| --- | --- | --- |
| `01-grid-analysis/` | National Electricity Grid Network Analysis | pandas, NetworkX, Plotly, Folium, Streamlit |
| `02-gridcare-lite/` | GridCare-Lite | Tkinter, SQLite, bcrypt |
| `03-cliniccare-lite/` | ClinicCare-Lite | Flask, Bootstrap, JSON, bcrypt |

### Component 1 — National Electricity Grid Network Analysis

This component studies a synthetic Ghanaian power grid as a network. A seeded generator script produces three CSVs covering utilities, substations and transmission lines, which a sequence of notebooks then cleans, validates and merges into a master table before exploring it: eight exploratory questions with one chart each, cross-table questions on utility and region combinations and on line length by voltage, then a network analysis that computes centralities, detects communities, identifies bridge lines and runs an N-1 contingency test to establish what the grid loses if a single substation fails. A geographic layer verifies inter-substation distances, measures regional density and renders an interactive Folium map. A Streamlit dashboard presents the metric tables exported by the network-analysis notebook across five tabs.

### Component 2 — GridCare-Lite

GridCare-Lite is a Tkinter desktop application for a utility's operations team, backed by SQLite. Staff log an outage against a real substation or line, raise a work order from it, assign a technician and track that order through its status state machine to resolved. Logins are role-based and passwords are hashed with bcrypt, and the reference asset data is imported from the cleaned Component 1 CSVs so outages can only be recorded against assets that exist in the dataset. The GUI never issues SQL directly — every operation goes through a service layer that enforces the role checks and status transitions, which is also the layer the test suite exercises.

### Component 3 — ClinicCare-Lite

ClinicCare-Lite is a Flask web application for the administrative side of a clinic, with a Bootstrap frontend and JSON-backed storage. Clinicians assign health tasks to patients, patients upload the completed forms, clinicians review the submissions, and both sides exchange messages through the app. Access control is enforced by decorators on the route blueprints with ownership checks on every record, passwords are hashed with bcrypt, and appointment reminders are dispatched by a standalone script. The system is strictly administrative by design: it schedules, collects and routes information, and never interprets it.

## Demos

### Component 1 — Streamlit dashboard walkthrough

<!-- Drag the video file into this section while editing the README on GitHub.
     GitHub uploads it and replaces this comment with a video URL. -->
<p float="left">
  <img width="49%" alt="Screenshot 2026-08-27 at 7 52 46 PM" src="https://github.com/user-attachments/assets/70798273-2793-4447-a4be-351513e6d22d" />
  <img width="49%" alt="Screenshot 2026-08-27 at 8 07 42 PM" src="https://github.com/user-attachments/assets/03515c4a-2b54-4286-80d0-e7b6946e2082" />
  <img width="49%" alt="Screenshot 2026-08-27 at 8 07 02 PM" src="https://github.com/user-attachments/assets/3ec50d24-d3ea-47bc-b933-074aa92be0a9" />
  <img width="49%" alt="Screenshot 2026-08-27 at 8 06 52 PM" src="https://github.com/user-attachments/assets/1888398e-ccc0-4bee-868b-56870304b6c5" />
</p>


_Grid analysis dashboard: overview metrics, network centralities, the geographic map, N-1 contingency results and substation search._

### Component 2 — GridCare-Lite

<img width="1440" height="900" alt="Screenshot 2026-08-27 at 7 23 45 PM" src="https://github.com/user-attachments/assets/e4c17d6d-3ce6-4ed6-92d9-faa749c7d3e0" />

_GridCare-Lite desktop application: logging an outage against a substation and tracking the resulting work order._

### Component 3 — ClinicCare-Lite

<!-- Drag the video file into this section while editing the README on GitHub. -->
<p float="left">
  <img width="49%" alt="Screenshot 2026-08-27 at 8 03 24 PM" src="https://github.com/user-attachments/assets/8fd378c9-c51a-473c-b298-9b55cf0640d5" />
  <img width="49%" alt="Screenshot 2026-08-27 at 8 02 49 PM" src="https://github.com/user-attachments/assets/998bae9a-12b7-4781-9345-657bdb9d73a0" />
</p>


_ClinicCare-Lite: clinician assigns a health task, patient uploads a completed form, clinician reviews the submission, and both exchange messages._

## Setup

Requires **Python 3.12 or newer** and Git. Run once per machine.

```bash
git clone https://github.com/jesseamoah77-dot/Team-14-cs-112-project.git
cd Team-14-cs-112-project
```

Create and activate a virtual environment.

macOS and Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Confirm the interpreter is 3.12 or newer before continuing:

```bash
python --version
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate the grid dataset. Run this before anything else — Components 1 and 2 both depend on its output:

```bash
python 01-grid-analysis/scripts/generate_grid_data.py
```

Expected output:

```
utilities: 10 rows
substations: 44 rows
lines: 55 rows
```

Verify the environment:

```bash
python 01-grid-analysis/scripts/verify_setup.py
```

## Running Component 1 — Grid analysis

Create the outputs directory, which is git-ignored and therefore absent from a fresh clone:

```bash
mkdir -p 01-grid-analysis/outputs
```

Run the notebooks **in order**. Notebook 01 writes the cleaned CSVs that 02 to 05 read, and 04 exports the metric tables the dashboard uses.

| Notebook | Covers |
| --- | --- |
| `01-data-cleaning` | Load, inspect, clean, validate, build the master table |
| `02-eda` | The brief's eight exploratory questions, one chart each |
| `03-merged-analysis` | Cross-table questions: utility and region combinations, length by voltage, region pairs |
| `04-network-analysis` | Centralities, communities, bridges, N-1 contingency |
| `05-geographic-analysis` | Distance verification, regional density, interactive Folium map |

Either open them in Jupyter and run all cells:

```bash
jupyter notebook 01-grid-analysis/notebooks/
```

Or execute them headless:

```bash
cd 01-grid-analysis/notebooks
python -m nbconvert --to notebook --execute --inplace 01*.ipynb
python -m nbconvert --to notebook --execute --inplace 02*.ipynb 03*.ipynb 04*.ipynb 05*.ipynb
cd ../..
```

Charts are written to `01-grid-analysis/outputs/`. The interactive map is `01-grid-analysis/outputs/grid_map.html`.

Start the dashboard:

```bash
cd 01-grid-analysis
python -m streamlit run dashboard.py
```

It opens at http://localhost:8501. Press Ctrl+C to stop it.

Run the tests:

```bash
python -m pytest tests/ -v
```

## Running Component 2 — GridCare-Lite

Run the Component 1 `01-data-cleaning` notebook first, since `import_grid_data.py` reads its cleaned CSVs.

```bash
cd 02-gridcare-lite
python import_grid_data.py
python seed_demo.py
python run.py
```

`import_grid_data.py` loads the substation and line reference data, `seed_demo.py` creates the demo accounts, and `run.py` opens the desktop window.

**Demo login credentials:** the demo accounts and their passwords are listed in [docs/gridcare-user-guide.md](docs/gridcare-user-guide.md), together with a walkthrough for each role.

Module layout inside `gridcare/`: `db.py` for the schema and imports, `auth.py` for bcrypt logins, `services.py` for every operation the app can perform including the role checks and the status state machine, `validators.py`, and `ui/` with one module per screen. Tests are in `tests/test_gridcare.py`.

## Running Component 3 — ClinicCare-Lite

```bash
cd 03-cliniccare-lite
cp .env.example .env
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Open `.env`, set `FLASK_SECRET_KEY` to that value and leave `EMAIL_DRY_RUN=1` so emails are written to `data/outbox.json` instead of being sent through a real SMTP server. Then:

```bash
python seed_demo.py
python app.py
```

Open http://localhost:5000.

**Demo login credentials:**

| Role | Username | Password |
| --- | --- | --- |
| Clinician | `12350000` | `Cl1nic!pass` |
| Patient | `11112024` | `Pat1ent!aa` |

Appointment reminders are sent by `python send_reminders.py`, run by hand during the demo or scheduled hourly.

On macOS, port 5000 is used by AirPlay Receiver by default. If the page does not load, turn it off under System Settings, General, AirDrop & Handoff.

Module layout: `models/` holds the JSON-backed entities with atomic writes and a lock, `utils/` holds validators, file handling, the structure-only completeness check, engagement, analytics and email, `routes/` holds the auth, clinician and patient blueprints with `guards.py` for the access-control decorators and ownership helpers, and `templates/` and `static/` hold the Bootstrap frontend.

## Reproducibility

The dataset generator `01-grid-analysis/scripts/generate_grid_data.py` is used verbatim from the brief, with `random.seed(42)` unchanged. The seed has not been modified, removed or overridden anywhere in our code. Every machine that runs the generator therefore produces identical CSVs of 10 utilities, 44 substations and 55 lines, so every figure, chart, centrality score and N-1 result in our reports is exactly reproducible from a clean clone.

## Known limitations

**Data**

- The grid dataset is synthetic. Utility names such as ECG, NEDCo, GRIDCo and VRA are real, as is the Ghanaian geography, but every coordinate, capacity, commissioning year and connection is invented by the generator. Nothing here describes Ghana's actual grid and no operational conclusion should be drawn from it.
- The N-1 contingency analysis is topological only. It measures connectivity loss when a node is removed and does not model load flow, generation dispatch, voltage stability or protection schemes, so a grid that stays connected in our model could still fail in reality.
- Distances are straight-line great-circle distances between substation coordinates rather than routed line lengths, so regional density figures are approximations.

**Scope**

- ClinicCare-Lite is strictly administrative. It schedules, collects and routes information. It does not diagnose, interpret symptoms, score health data or recommend treatment, and the completeness check on submissions is structural only: it verifies that fields are filled, never what they contain.

**Technical**

- GridCare-Lite is a Tkinter desktop application and is single-user per database file. It has no concurrent-access handling and cannot run as a shared client-server system.
- ClinicCare-Lite stores data in JSON files rather than a database. The store uses atomic writes and a lock, but this is not suitable for production load or many simultaneous users.
- Email is disabled by default via `EMAIL_DRY_RUN=1` and messages are written to `data/outbox.json`. Live SMTP delivery is untested in the demo configuration.
- Appointment reminders are not automatic. `send_reminders.py` must be run manually or scheduled externally.
- Both applications run as local development processes without TLS. Passwords are hashed with bcrypt, but the deployment configuration itself is not hardened.
- Generated charts, maps, databases, runtime JSON and uploaded submissions are git-ignored by design, so a fresh clone must create `01-grid-analysis/outputs/` and run the generator and notebooks before the dashboard has anything to display.

## Repository layout

```
01-grid-analysis/
  scripts/generate_grid_data.py    seeded generator, verbatim from the brief
  scripts/verify_setup.py
  data/                            the three generated CSVs
  notebooks/                       cleaning, EDA, network analysis, maps
  outputs/                         saved charts and HTML maps (git-ignored)
  dashboard.py                     Streamlit dashboard
  tests/

02-gridcare-lite/
  gridcare/                        db, auth, services, validators, ui
  import_grid_data.py
  seed_demo.py
  run.py
  data/                            gridcare.db (git-ignored)
  tests/

03-cliniccare-lite/
  models/                          User, HealthTask, TaskSubmission, Message, Clinic
  utils/                           email, file handling, validation, analytics
  routes/                          auth, clinician and patient blueprints, guards.py
  templates/  static/              Flask frontend
  app.py  seed_demo.py  send_reminders.py
  data/                            runtime JSON (git-ignored)
  submissions/                     uploaded files (git-ignored)

docs/                              reports, diagrams, user guides, media
```

## Team conventions

Secrets are never committed. Email passwords and Flask secret keys live in `.env`, which is git-ignored. Copy `03-cliniccare-lite/.env.example` to `.env` and fill it in locally.

Patient data is never committed. `03-cliniccare-lite/submissions/` and the runtime JSON files are git-ignored on purpose.

Work happens on branches, not on `main`. One branch per feature, opened as a pull request and reviewed by a teammate before merging. Commit messages state what changed.

## Documentation

| File | Contents |
| --- | --- |
| [grid-analysis-report.md](docs/grid-analysis-report.md) | Component 1 report: dataset, cleaning, findings, N-1, limitations |
| [cliniccare-technical-report.md](docs/cliniccare-technical-report.md) | Component 3 report: architecture, security, workflows, testing |
| [design-diagrams.md](docs/design-diagrams.md) | ER, state machine, use-case, class, architecture and data-flow diagrams |
| [gridcare-user-guide.md](docs/gridcare-user-guide.md) | GridCare-Lite walkthrough per role, plus demo accounts |
| [cliniccare-user-guide-clinician.md](docs/cliniccare-user-guide-clinician.md) | ClinicCare-Lite clinician guide |
| [cliniccare-user-guide-patient.md](docs/cliniccare-user-guide-patient.md) | ClinicCare-Lite patient guide |<img width="1440" height="900" alt="Screenshot 2026-08-27 at 7 23 45 PM" src="https://github.com/user-attachments/assets/601601d5-ed96-4982-bb3e-55a227aa6cc0" />




