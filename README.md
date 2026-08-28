# CS 112 — Final Course Project (Summer 2026)

Integrated Data Science and Software Engineering project. Three components:

| Folder | Component | What it is | Stack |
|---|---|---|---|
| `01-grid-analysis/` | National Electricity Grid Network Analysis | Study a (synthetic) Ghanaian power grid as a network: clean the data, chart it, map it, find the critical substations, test what breaks if one fails | pandas · NetworkX · Plotly · Folium · Streamlit |
| `02-gridcare-lite/` | GridCare-Lite | Desktop app a utility's operations team would use: log an outage, raise a work order, assign a technician, track it to resolved | Tkinter · SQLite |
| `03-cliniccare-lite/` | ClinicCare-Lite | Web app for a clinic's admin side: clinicians assign health tasks, patients upload forms, clinicians review, both message each other | Flask · Bootstrap · JSON · bcrypt |

---

## Setup

**One-time, per machine.** Requires Python 3.12+ and Git.

```bash
git clone https://github.com/Afrifa518/cs112-final-project.git
```

Then, from inside the project folder:

```bash
python -m venv .venv
```

Activate it (Windows PowerShell):

```bash
.venv\Scripts\Activate.ps1
```

Install everything:

```bash
pip install -r requirements.txt
```

Generate the grid dataset (seeded — everyone gets identical files):

```bash
python 01-grid-analysis/scripts/generate_grid_data.py
```

Expected output: `utilities: 10 rows`, `substations: 44 rows`, `lines: 55 rows`.

Then confirm everything works:

```bash
python 01-grid-analysis/scripts/verify_setup.py
```

## Component 1: how to run it

The notebooks in `01-grid-analysis/notebooks/` run in order — 01 writes the cleaned
CSVs that 02–05 read, and 04 exports the metric tables the dashboard uses:

| notebook | covers |
|---|---|
| `01-data-cleaning` | load, inspect, clean, validate, build the master table |
| `02-eda` | the brief's eight exploratory questions, one chart each |
| `03-merged-analysis` | cross-table questions (utility/region combos, length by voltage, region pairs) |
| `04-network-analysis` | centralities, communities, bridges, N-1 contingency |
| `05-geographic-analysis` | distance verification, regional density, the interactive Folium map |

Charts land in `01-grid-analysis/outputs/` (git-ignored — regenerate by running the
notebooks). The interactive map is `outputs/grid_map.html`.

The dashboard:

```bash
cd 01-grid-analysis
streamlit run dashboard.py
```

Tests:

```bash
pytest tests/ -v
```

## Component 2: how to run it

GridCare-Lite lives in `02-gridcare-lite/`. First run:

```bash
cd 02-gridcare-lite
python import_grid_data.py
python seed_demo.py
python run.py
```

`import_grid_data.py` loads the substation/line reference data from the cleaned
component-1 CSVs (run the 01 notebook first), so outages can only be logged against
real assets. `seed_demo.py` creates the five demo accounts — usernames and passwords
are in [docs/gridcare-user-guide.md](docs/gridcare-user-guide.md), along with a
walkthrough for each role.

Layout inside `gridcare/`: `db.py` (schema + imports), `auth.py` (bcrypt logins),
`services.py` (every operation the app can perform, with the role checks and the
status state machine), `validators.py`, and `ui/` (one module per screen). The GUI
never touches SQL directly — everything goes through `services.py`, which is what
`tests/test_gridcare.py` tests.

## Component 3: how to run it

ClinicCare-Lite lives in `03-cliniccare-lite/`. First run:

```bash
cd 03-cliniccare-lite
cp .env.example .env
```

Edit `.env` and set `FLASK_SECRET_KEY` (generate one with
`python -c "import secrets; print(secrets.token_hex(32))"`). Leave `EMAIL_DRY_RUN=1`
— emails then go to `data/outbox.json` instead of a real SMTP server. Then:

```bash
python seed_demo.py
python app.py
```

Open http://localhost:5000. Demo accounts are listed in `seed_demo.py`
(clinician `12350000` / `Cl1nic!pass`, patient `11112024` / `Pat1ent!aa`).
Appointment reminders are sent by `python send_reminders.py` (run it by hand in the
demo, or schedule it hourly).

Layout: `models/` (JSON-backed entities — the store does atomic writes and holds a
lock), `utils/` (validators, file handling, the structure-only completeness check,
engagement, analytics, email), `routes/` (auth + clinician + patient blueprints;
`guards.py` holds the access-control decorators and ownership helpers), `templates/`
+ `static/` (Bootstrap frontend, dark/colourful themes). The scope rule everywhere:
this system schedules, collects and routes information — it never interprets it.

---

## Ground rules

**Never commit secrets.** Email passwords and Flask secret keys go in a `.env` file, which is
git-ignored. Copy `03-cliniccare-lite/.env.example` to `.env` and fill it in locally. The brief
awards marks for this and deducts them for hardcoded credentials.

**Never commit patient data.** `03-cliniccare-lite/submissions/` and the runtime JSON files are
git-ignored on purpose.

**Branch, don't push to `main`.** One branch per feature:

```bash
git checkout -b feature/patient-dashboard
```

Open a pull request, get one teammate to review, then merge. The brief grades commit history,
pull requests, and code reviews as *individual* marks — your git log is your evidence of
contribution. A feature that only exists on someone's laptop scores zero.

**Commit messages that say what changed:** `Add clinician ID validation`, not `update`.

---

## Repo layout

```
01-grid-analysis/
  scripts/generate_grid_data.py   # seeded generator, verbatim from the brief
  data/                           # the three generated CSVs
  notebooks/                      # cleaning, EDA, network analysis, maps
  outputs/                        # saved charts + HTML maps (git-ignored)

02-gridcare-lite/
  app/                            # Tkinter screens + SQLite layer
  data/                           # gridcare.db (git-ignored)

03-cliniccare-lite/
  models/                         # User, HealthTask, TaskSubmission, Message, Clinic
  utils/                          # email, file handling, validation
  templates/  static/             # Flask frontend
  data/                           # runtime JSON (git-ignored)
  submissions/                    # uploaded files (git-ignored)

docs/                             # report, diagrams, test plan, meeting notes
tests/                            # pytest suites
```

---

## Documentation

Everything the submission package needs lives in `docs/`:

| file | what it is |
|---|---|
| [grid-analysis-report.md](docs/grid-analysis-report.md) | Component 1 report: dataset, cleaning, findings, N-1, limitations |
| [cliniccare-technical-report.md](docs/cliniccare-technical-report.md) | Component 3 report: architecture, security, workflows, testing |
| [design-diagrams.md](docs/design-diagrams.md) | ER, state machines, use-case, class, architecture, data-flow (Mermaid — renders on GitHub) |
| [gridcare-user-guide.md](docs/gridcare-user-guide.md) | GridCare walkthrough per role + demo accounts |
| [cliniccare-user-guide-clinician.md](docs/cliniccare-user-guide-clinician.md) | ClinicCare clinician guide |
| [cliniccare-user-guide-patient.md](docs/cliniccare-user-guide-patient.md) | ClinicCare patient guide |

## Important caveat about the data

The grid dataset is **synthetic**. Utility names (ECG, NEDCo, GRIDCo, VRA) and Ghanaian
geography are real; every coordinate, capacity, commissioning year, and connection is
invented by the generator script. Nothing here describes Ghana's actual grid, and the
report must say so. The brief marks you on stating this limitation.

Likewise, ClinicCare-Lite is **strictly administrative**. It schedules, collects, and routes
information. It must never diagnose, interpret symptoms, score health data, or recommend
treatment. This is a hard requirement — the rubric says a submission that crosses this line
loses the relevant marks regardless of how well it is built.
