# Lecturer-Facing Decision Support System (DSS)

Research artefact for ITRI671 — *Design and Implementation of a Lecturer-Facing
Decision Support System for At-Risk Student Identification and Academic Performance
Monitoring*.

**Author:** G. O. G. Sebaetse (46997245) 
**Supervisor:** Prof. C. J. Kruger
**Institution:** North-West University, Potchefstroom Campus

This is a research prototype, not a production system. It implements the three
mathematical models of Van der Merwe et al. (2018b) within a lecturer-facing web
dashboard, per the DSRM (Peffers et al., 2007) design-and-development phase of the
study. Tech stack (Flask + PuLP + pandas + openpyxl) and visual theme are matched to
the [Student-Performance-Assistant](https://github.com/45000794Ndlakuse/Student-Performance-Assistant)
reference project.

## Documentation

- [Functional Specification](docs/functional_specification.md)
- [Technical Specification](docs/technical_specification.md)
- [GitHub Setup Guide](docs/github_setup.md)

## Quick Start

```bash
# 1. Clone and enter the repo
git clone https://github.com/g00dwill47ch0ppas/Academic-Performance-Monitor.git
cd Academic-Performance-Monitor

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (optional — sensible defaults are built in)
cp .env.example .env

# 5. Run the app
python app.py
```

The app opens at `http://localhost:5000` with the bundled simulated dataset loaded
as a demo module (CS101) by default. Create your own modules from the **Modules**
page — each module has its own assessment plan, students, and pass threshold.
Data lives only in server memory and is reset when the app restarts.

## Running Tests

```bash
pytest tests/ -v
```

## Features

- **Class dashboard** — cohort average, class size, at-risk count and a full cohort
  table, all for the module the lecturer is currently working in.
- **At-risk identification (Algorithm 1, PuLP)** — per-student best/worst-case
  p-mark bounds against the module's pass threshold.
- **Participation planning (Algorithm 2)** — feasible mark combinations for a
  student to reach a target improvement on the assessments still to be written.
- **Cohort planning (Algorithm 3, scipy SLSQP)** — the lecturer sets a target class
  average and a weight *range* `[min%, max%]` per assessment; those ranges are the
  constraints of the optimisation:
  - every assessment keeps a strictly positive weight (a 1% floor is enforced),
  - `min <= max` for each assessment,
  - the weights must sum to exactly 100%, so `sum(min) <= 100 <= sum(max)` — the page
    states exactly which condition fails and by how much,
  - the page shows the live sum of minimums/maximums, disables *Calculate weights*
    while the ranges are invalid, and always reports the solver's status
    (optimal / infeasible / failed to converge) plus how close the target was reached,
  - results are shown as a table and as bars comparing each proposed weight with the
    range it was allowed to move in.
- **Module management** — create/rename/delete/switch modules, edit the assessment
  plan, import CSV/XLSX class data, export data and per-student summary.
- **Consistent navigation** — a shared *Back* control on every page (returns to the
  previous page when the lecturer came from inside the app, otherwise to the page's
  logical parent) and a contextual help panel on every page.
- **Guided tutorial + first-run welcome** — a first-visit popup explains what the system
  does, then a spotlight tour (30 steps) walks through the whole workflow on the live
  pages: create a module, define the assessment plan, add students and marks, read the
  dashboard and at-risk indicators, and plan the cohort's weights. It advances when you
  actually do the step, offers a “Fill an example for me” helper, survives page
  navigation, and can be replayed any time from the menu (Tutorial) or the dedicated
  **Tutorial** page, which also carries a written summary of the workflow. Too long to
  sit through? The Tutorial page also lets you run **just one part** — create a module,
  assessment plan, students & marks, results & at-risk, or cohort planning — each starting
  on its own page with its own “step x of y” counter.
- **Light/dark theme** remembered per browser; responsive layout down to phone widths.

## Project Structure

```
Academic-Performance-Monitor/
├── app.py                     # entry point
├── config.py                  # environment-based configuration
├── backend/
│   ├── __init__.py            # app factory, blueprint registration
│   ├── algorithms/
│   │   ├── lp_bounds.py       # Algorithm 1 — PuLP
│   │   ├── participation_plan.py  # Algorithm 2 — combinatorics
│   │   └── nlp_weights.py     # Algorithm 3 — scipy (see note below)
│   ├── models/student.py      # Assessment / Student / Module / ClassConfig
│   ├── routes/                # home, students, cohort, modules blueprints
│   └── data/                  # loader, in-memory store (modules), sample_data.csv
├── frontend/
│   ├── templates/             # base.html (nav, back control, help panel) + pages
│   └── static/{css,js}        # app.js (nav/theme/back), cohort.js (range checks),
│                              # tutorial.js/.css (welcome + guided tour)
└── tests/
```

## User interface

The visual theme and the navigation mirror the
[Student-Performance-Assistant](https://github.com/45000794Ndlakuse/Student-Performance-Assistant)
reference project:

- **Palette & type:** purple primary (#4E2A84) with a (#F5B301) accent on a
  #F8F9FC background; Inter for body text, Poppins for headings.
- **Navigation:** a purple navbar (logo, title, active-module subtitle) whose
  menu button opens the navigation panel sliding in from the right. The panel
  lists the active module's pages above the module switcher.
- **Components:** card panels with header strips, icon stat cards, hover
  tables, pill badges, and a light/dark colour-scheme toggle that is
  remembered per browser.

Presentational only — every calculation remains in `backend/algorithms/`. The
cohort-planning page only supplies the constraints (the lecturer's weight ranges);
the published Algorithm 3 objective is unchanged.

## A note on the tech stack

This project intentionally matches the reference repo above: **Flask**, **PuLP**,
**pandas**, **numpy**, **openpyxl**, **python-dotenv**. One addition was necessary:
**scipy** is used for Algorithm 3 only, because PuLP solves linear/mixed-integer
problems and cannot express the non-linear objective that algorithm requires.
Reformulating it as a linear approximation would modify Van der Merwe et al.'s
published model, which the research proposal explicitly rules out.

## Project Status

Tracking against the DSRM phases from the research proposal (§1.4.4):

- [x] Requirements Analysis — see `docs/functional_specification.md`
- [x] System Design — see `docs/technical_specification.md`
- [x] Implementation (v1) — algorithms in `backend/algorithms/`, verified end-to-end
- [ ] Confirm algorithm assumptions against Van der Merwe et al. (2018b) — see
      `# TODO: confirm against source paper` comments in each algorithm module
- [ ] Testing and Refining — dry-run with fabricated data before the live session
- [ ] Evaluation session with lecturer participants

## Ethical Note

This repository must never contain real student data. Only simulated data
(`backend/data/sample_data.csv`) or fully anonymised historical records with
legitimate access may be used, per the study's ethical clearance (Research
Proposal §1.5). The data loader actively rejects columns that look identifiable
(see `backend/data/loader.py`).
