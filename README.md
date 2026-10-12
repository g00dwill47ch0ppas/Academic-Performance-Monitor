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
study, extended with droppable assessments (best N of M), a feasible-region
target picker for participation planning, and display rounding. Tech stack (Flask +
PuLP + pandas + openpyxl) and visual theme are matched to the
[Student-Performance-Assistant](https://github.com/45000794Ndlakuse/Student-Performance-Assistant)
reference project; `# TODO: confirm against source paper` marks every place the
extension goes beyond the published model (listed in the technical specification).

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
pytest tests/ -v      # 108 tests
```

## Features

- **Class dashboard** — cohort average, class size, at-risk count and a full cohort
  table, all for the module the lecturer is currently working in.
- **Droppable assessments (best N of M)** — an assessment type holds M items of
  which the best N count (best 2 of 3 tests, best 10 of 12 attendance sessions;
  N = M by default, so nothing is dropped). Items are ranked by *percentage*, so
  items with different maxima compare fairly, ties go to the earliest item, and the
  lowest marks are shown as **dropped** rather than silently removed. Each counted
  slot is worth `weight ÷ N`; a blank mark means “not written yet” and is never
  treated as a zero (a recorded 0 is a real mark).
  All of it lives in one place — `backend/services/participation.py` — which every
  page, algorithm and export calls.
- **At-risk identification (Algorithm 1)** — per-student best/worst-case
  participation-mark bounds against the module's pass threshold. With the drop rule
  the extrema are exact and closed-form, so the bounds come from the participation
  service rather than a solver (see the note on PuLP below).
- **Participation planning (Algorithm 2)** — from a *feasible region* to a target:
  the page shows the lowest and highest final participation mark a student can still
  reach (with their mark so far and the pass threshold marked on the same bar), the
  lecturer picks an **absolute target** inside that region, and the plan then lists
  every remaining item with the minimum percentage it needs. Nothing is treated as a
  zero. Where a type drops its weakest marks the page says how many remaining items
  can be skipped and what the others must then reach, and if the whole region sits
  below the pass mark it says plainly that passing is no longer possible.
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
  plan (name, weight, number of items M, count best N), import CSV/XLSX class data,
  export data and per-student summary.
- **Consistent display rounding** — every displayed number is rounded to at most two
  decimals through one helper (`|r2` in Jinja, `fmt2()` in the browser), so nothing
  shows `54.86111111` and `-0.00` never appears. Calculations and stored values keep
  full precision; only the output edge rounds.
- **Consistent navigation** — a shared *Back* control on every page (returns to the
  previous page when the lecturer came from inside the app, otherwise to the page's
  logical parent) and a contextual help panel on every page.
- **Guided tutorial + first-run welcome** — a first-visit popup explains what the system
  does, then a spotlight tour (36 steps) walks through the whole workflow on the live
  pages: create a module, define the assessment plan (including *best N of M*), add
  students and marks, read the dashboard and at-risk indicators, open one student's
  feasible region and pick a target, and plan the cohort's weights. It advances when you
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
│   │   ├── lp_bounds.py       # Algorithm 1 — min/max bounds via the service
│   │   ├── participation_plan.py  # Algorithm 2 — region + target projection
│   │   └── nlp_weights.py     # Algorithm 3 — scipy (see note below)
│   ├── services/
│   │   ├── participation.py   # THE best-N-of-M rule (single source of truth)
│   │   └── rounding.py        # display rounding behind the |r2 filter
│   ├── models/student.py      # Assessment / Student / Module / ClassConfig
│   ├── routes/                # home, students, cohort, modules blueprints
│   └── data/                  # loader, in-memory store (modules), sample_data.csv
├── frontend/
│   ├── templates/             # base.html (nav, back control, help panel) + pages
│   └── static/{css,js}        # format.js (fmt2 rounding), app.js (nav/theme/back),
│                              # cohort.js (range checks), tutorial.js/.css
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

A second, smaller note: Algorithm 1's bounds are no longer computed by PuLP. Once
assessments can drop their weakest items, which items contribute is decided by a
ranking, so the objective is piecewise-linear and an LP cannot describe it. The two
extrema are still exact — the minimum is the mark already accrued, the maximum is the
top-N of (completed marks + 100% for everything outstanding) — and they are computed
in closed form in `backend/services/participation.py`. PuLP remains a declared
project dependency but is not called by the shipped code; the deviation and the
reason are recorded in `docs/technical_specification.md`.

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
