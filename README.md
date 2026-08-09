# Lecturer-Facing Decision Support System (DSS)

Research artefact for ITRI671 — *Design and Implementation of a Lecturer-Facing
Decision Support System for At-Risk Student Identification and Academic Performance
Monitoring*.

**Author:** G. O. G. Sebaetse (46997245) · **Supervisor:** Prof. C. J. Kruger
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
git clone https://github.com/<your-username>/lecturer-dss.git
cd lecturer-dss

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
by default.

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
lecturer-dss/
├── app.py                     # entry point
├── config.py                  # environment-based configuration
├── backend/
│   ├── __init__.py            # app factory, blueprint registration
│   ├── algorithms/
│   │   ├── lp_bounds.py       # Algorithm 1 — PuLP
│   │   ├── participation_plan.py  # Algorithm 2 — combinatorics
│   │   └── nlp_weights.py     # Algorithm 3 — scipy (see note below)
│   ├── models/student.py      # Assessment / Student / ClassConfig
│   ├── routes/                # home, students, cohort blueprints
│   └── data/                  # loader, in-memory store, sample_data.csv
├── frontend/
│   ├── templates/             # base.html + 3 pages
│   └── static/{css,js}
└── tests/
```

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
