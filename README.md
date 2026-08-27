# CS 112 — Final Course Project (Summer 2026)

*Team 14*

Repository: **https://github.com/jesseamoah77-dot/Team-14-cs-112-project**

## Team members

| Name | ID |
|---|---|
| Jesse Amoah Odei | 86112029 |
| Ivana Maame Adjoa Boatemaa Koranteng | 03732029 |
| Georgina Lutterodt | 46602029 |
| Nathan Agyemang Asare | 76602029 |
| Bethany Nana Afua Wiafe | 04582029 |

---

## The three components

| Folder | Component | Stack |
|---|---|---|
| 01-grid-analysis/ | National Electricity Grid Network Analysis | pandas · NetworkX · Plotly · Folium · Streamlit |
| 02-gridcare-lite/ | GridCare-Lite | Tkinter · SQLite |
| 03-cliniccare-lite/ | ClinicCare-Lite | Flask · Bootstrap · JSON · bcrypt |

### Component 1 — National Electricity Grid Network Analysis

This component studies a synthetic Ghanaian power grid as a network. A seeded generator script produces three CSVs (utilities, substations, transmission lines), which a sequence of notebooks then cleans, validates and merges into a master table before exploring it: eight exploratory questions with one chart each, cross-table questions on utility/region combinations and line length by voltage, then a network analysis that computes centralities, detects communities, identifies bridge lines and runs an N-1 contingency test to see what the grid loses if a single substation fails. A geographic layer verifies inter-substation distances, measures regional density, and renders an interactive Folium map. A Streamlit dashboard presents the metric tables exported by the network-analysis notebook.

### Component 2 — GridCare-Lite

GridCare-Lite is a Tkinter desktop application for a utility's operations team, backed by SQLite. Staff log an outage against a real substation or line, raise a work order from it, assign a technician, and track that order through its status state machine to resolved. Logins are role-based and password-hashed with bcrypt, and the reference asset data is imported from the cleaned Component 1 CSVs so outages can only be recorded against assets that exist in the dataset. The GUI never issues SQL directly — every operation goes through a service layer that enforces the role checks and status transitions, which is also the layer the test suite exercises.

### Component 3 — ClinicCare-Lite

ClinicCare-Lite is a Flask web application for the administrative side of a clinic, with a Bootstrap frontend and JSON-backed storage. Clinicians assign health tasks to patients; patients upload the completed forms; clinicians review the submissions; and both sides exchange messages through the app. Access control is enforced by decorators on the route blueprints with ownership checks on every record, passwords are hashed with bcrypt, and appointment reminders are dispatched by a standalone script. The system is strictly administrative by design: it schedules, collects and routes information, and never interprets it.

---

## Setup

*One-time, per machine.* Requires Python 3.12+ and Git.

bash
git clone https://github.com/jesseamoah77-dot/Team-14-cs-112-project.git
cd Team-14-cs-112-project


Create and activate a virtual environment:

bash
python -m venv .venv


Windows (PowerShell):

bash
.venv\Scripts\Activate.ps1


macOS / Linux:

bash
source .venv/bin/activate


Install all dependencies:

bash
pip install -r requirements.txt


Generate the grid dataset — *run this before anything else*, since Components 1 and 2 both depend on its output:

bash
python 01-grid-analysis/scripts/generate_grid_data.py


Expected output: utilities: 10 rows, substations: 44 rows, lines: 55 rows.

Confirm the environment is correct:

bash
python 01-grid-analysis/scripts/verify_setup.py


---

## Component 1: how to run it

The notebooks in 01-grid-analysis/notebooks/ must run *in order* — 01 writes the cleaned CSVs that 02–05 read, and 04 exports the metric tables the dashboard uses.

| Notebook | Covers |
|---|---|
| 01-data-cleaning | load, inspect, clean, validate, build the master table |
| 02-eda | the brief's eight exploratory questions, one chart each |
| 03-merged-analysis | cross-table questions (utility/region combos, length by voltage, region pairs) |
| 04-network-analysis | centralities, communities, bridges, N-1 contingency |
| 05-geographic-analysis | distance verification, regional density, the interactive Folium map |

Charts are written to 01-grid-analysis/outputs/ (git-ignored — regenerate by running the notebooks). The interactive map is outputs/grid_map.html.

Start the dashboard:

bash
cd 01-grid-analysis
streamlit run dashboard.py


Run the tests:

bash
pytest tests/ -v


## Component 2: how to run it

Run the Component 1 01-data-cleaning notebook first — import_grid_data.py reads its cleaned CSVs.

bash
cd 02-gridcare-lite
python import_grid_data.py
python seed_demo.py
python run.py


import_grid_data.py loads the substation and line reference data. seed_demo.py creates the five demo accounts. run.py opens the desktop window.

*Demo login credentials:* the five demo accounts and their passwords are listed in [docs/gridcare-user-guide.md](docs/gridcare-user-guide.md), along with a walkthrough for each role.

Module layout inside gridcare/: db.py (schema + imports), auth.py (bcrypt logins), services.py (every operation the app can perform, with role checks and the status state machine), validators.py, and ui/ (one module per screen). Tests live in tests/test_gridcare.py.

## Component 3: how to run it

bash
cd 03-cliniccare-lite
cp .env.example .env


Edit .env and set FLASK_SECRET_KEY. Generate one with:

bash
python -c "import secrets; print(secrets.token_hex(32))"


Leave EMAIL_DRY_RUN=1 — emails then go to data/outbox.json instead of a real SMTP server. Then:

bash
python seed_demo.py
python app.py


Open *http://localhost:5000*.

*Demo login credentials (created by seed_demo.py):*

| Role | Username | Password |
|---|---|---|
| Clinician | 12350000 | Cl1nic!pass |
| Patient | 11112024 | Pat1ent!aa |

Appointment reminders are sent by python send_reminders.py — run it by hand during the demo, or schedule it hourly.

Module layout: models/ (JSON-backed entities; the store does atomic writes and holds a lock), utils/ (validators, file handling, the structure-only completeness check, engagement, analytics, email), routes/ (auth, clinician and patient blueprints, with guards.py holding the access-control decorators and ownership helpers), templates/ and static/ (Bootstrap frontend, dark and colourful themes).

---

## Reproducibility

The dataset generator 01-grid-analysis/scripts/generate_grid_data.py is used *verbatim from the brief, with random.seed(42) unchanged*. The seed has not been modified, removed, or overridden anywhere in our code. Every machine that runs the generator therefore produces identical CSVs — 10 utilities, 44 substations, 55 lines — so every figure, chart, centrality score and N-1 result in our reports is exactly reproducible from a clean clone.

---

## Known limitations

*Data*

- The grid dataset is *synthetic*. Utility names (ECG, NEDCo, GRIDCo, VRA) and Ghanaian geography are real; every coordinate, capacity, commissioning year and connection is invented by the generator. Nothing here describes Ghana's actual grid, and no operational conclusion should be drawn from it.
- The N-1 contingency analysis is topological only. It measures connectivity loss when a node is removed and does not model load flow, generation dispatch, voltage stability or protection schemes — a grid that stays connected in our model could still fail in reality.
- Distances are straight-line (great-circle) between substation coordinates, not routed line lengths, so regional density figures are approximations.

*Scope*

- ClinicCare-Lite is *strictly administrative*. It schedules, collects and routes information. It does not diagnose, interpret symptoms, score health data, or recommend treatment, and the completeness check on submissions is structural only — it verifies that fields are filled, never what they contain.

*Technical*

- GridCare-Lite is a Tkinter desktop application and is single-user per database file; it has no concurrent-access handling and cannot be run as a shared client-server system.
- ClinicCare-Lite stores data in JSON files rather than a database. The store uses atomic writes and a lock, but this is not suitable for production load or for many simultaneous users.
- Email is disabled by default (EMAIL_DRY_RUN=1); messages are written to data/outbox.json. Live SMTP delivery is untested in the demo configuration.
- Appointment reminders are not automatic — send_reminders.py must be run manually or scheduled externally.
- Both applications run as local development processes without TLS. Passwords are hashed with bcrypt, but the deployment configuration itself is not hardened.
- Generated charts, maps, databases, runtime JSON and uploaded submissions are git-ignored by design, so a fresh clone must run the generator and the notebooks before the dashboard has anything to display.

---

## Ground rules for the team

*Never commit secrets.* Email passwords and Flask secret keys go in .env, which is git-ignored. Copy 03-cliniccare-lite/.env.example to .env and fill it in locally. The brief awards marks for this and deducts them for hardcoded credentials.

*Never commit patient data.* 03-cliniccare-lite/submissions/ and the runtime JSON files are git-ignored on purpose.

*Branch, don't push to main.* One branch per feature:

bash
git checkout -b feature/patient-dashboard


Open a pull request, get one teammate to review, then merge. The brief grades commit history, pull requests and code reviews as individual marks — your git log is your evidence of contribution. A feature that only exists on someone's laptop scores zero.

*Commit messages that say what changed:* Add clinician ID validation, not update.

---

## Repo layout


01-grid-analysis/
  scripts/generate_grid_data.py   # seeded generator, verbatim from the brief
  scripts/verify_setup.py
  data/                           # the three generated CSVs
  notebooks/                      # cleaning, EDA, network analysis, maps
  outputs/                        # saved charts + HTML maps (git-ignored)
  dashboard.py                    # Streamlit dashboard

02-gridcare-lite/
  gridcare/                       # db, auth, services, validators, ui/
  import_grid_data.py
  seed_demo.py
  run.py
  data/                           # gridcare.db (git-ignored)

03-cliniccare-lite/
  models/                         # User, HealthTask, TaskSubmission, Message, Clinic
  utils/                          # email, file handling, validation, analytics
  routes/                         # auth + clinician + patient blueprints, guards.py
  templates/  static/             # Flask frontend
  app.py  seed_demo.py  send_reminders.py
  data/                           # runtime JSON (git-ignored)
  submissions/                    # uploaded files (git-ignored)

docs/                             # reports, diagrams, user guides
tests/                            # pytest suites


---

## Documentation

| File | What it is |
|---|---|
| [grid-analysis-report.md](docs/grid-analysis-report.md) | Component 1 report: dataset, cleaning, findings, N-1, limitations |
| [cliniccare-technical-report.md](docs/cliniccare-technical-report.md) | Component 3 report: architecture, security, workflows, testing |
| [design-diagrams.md](docs/design-diagrams.md) | ER, state machines, use-case, class, architecture, data-flow (Mermaid — renders on GitHub) |
| [gridcare-user-guide.md](docs/gridcare-user-guide.md) | GridCare walkthrough per role + demo accounts |
| [cliniccare-user-guide-clinician.md](docs/cliniccare-user-guide-clinician.md) | ClinicCare clinician guide |
| [cliniccare-user-guide-patient.md](docs/cliniccare-user-guide-patient.md) | ClinicCare patient guide |
