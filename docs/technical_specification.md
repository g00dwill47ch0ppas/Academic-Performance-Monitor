# Technical Specification
## Lecturer-Facing DSS — Architecture & Implementation

---

## 1. Architecture

Traditional Flask web app using the **application factory + blueprints** pattern,
matching the reference project's structure. Server-rendered HTML (Jinja2) rather
than a client-side framework — no build step, no API layer, fast to iterate.

```
┌───────────────────────────────────────────────┐
│              Flask App (backend/__init__.py)    │
│   Blueprints: home │ students │ cohort           │
└───────────────────┬───────────────────────────┘
                     │
┌───────────────────▼───────────────────────────┐
│            Algorithm Layer (backend/algorithms)  │
│  lp_bounds.py (PuLP) │ participation_plan.py     │
│  (itertools) │ nlp_weights.py (scipy)             │
└───────────────────┬───────────────────────────┘
                     │
┌───────────────────▼───────────────────────────┐
│         Data Layer (backend/data)                │
│  loader.py — CSV/XLSX import, PII validation      │
│  store.py — in-memory DataStore (no database)     │
│  sample_data.csv — bundled simulated cohort        │
└─────────────────────────────────────────────────┘
                     │
┌───────────────────▼───────────────────────────┐
│      Presentation (frontend/templates, static)    │
│  base.html + index / student_detail / cohort_planning │
└─────────────────────────────────────────────────┘
```

## 2. Technology Stack

Matched to the reference repo, with one addition flagged below.

| Layer | Choice | Rationale |
|---|---|---|
| Web framework | Flask 3.x (app factory + blueprints) | Matches reference stack; minimal, well-understood |
| Templates | Jinja2 | Ships with Flask; server-rendered, no build tooling |
| LP (Algorithm 1) | **PuLP** (CBC solver) | Matches reference stack's LP library |
| NLP (Algorithm 3) | **scipy.optimize.minimize (SLSQP)** | *Addition* — PuLP is LP/MILP-only and cannot express a non-linear objective. Using it here would force a linear approximation of Algorithm 3, modifying the published model (Research Proposal §1.4.6 rules this out). |
| Combinatorics (Algorithm 2) | `itertools` | No solver needed — pure enumeration |
| Data handling | `pandas` | Tabular student data |
| File formats | `openpyxl` (via pandas) | CSV and XLSX import, matching reference stack |
| Config | `python-dotenv` | `.env`-based configuration, matching reference stack |
| Testing | `pytest` | Unit-test the three algorithms independently of routes |
| CI | GitHub Actions | Runs tests on every push/PR |
| Deployment | Any WSGI host (Render, PythonAnywhere, or local) | No external DB dependency — easy to self-host for the demo session |

## 3. Data Model (`backend/models/student.py`)

```python
@dataclass
class Assessment:
    name: str
    weight: float          # w_i, in [0, 1]
    mark: float | None     # y_i, None if not completed
    completed: bool

@dataclass
class Student:
    student_code: str               # anonymised code, never a real name/number
    assessments: list[Assessment]
    # p_mark_current computed as a property: sum(y_i * w_i) over completed assessments

@dataclass
class ClassConfig:
    pass_threshold: float = 50.0
    target_class_average: float = 60.0
```

## 4. State Management — In-Memory Store, No Database

`backend/data/store.py` holds a single shared `DataStore` instance (the currently
loaded `pandas.DataFrame` + `ClassConfig`) in server memory. This is a deliberate
simplification appropriate to the artefact's scope:

- The proposal (§1.4.6) scopes this as a **single-lecturer research prototype**
  evaluated in **one session at a time** — not a multi-tenant production system.
- No database means no persisted identifiable data ever exists on disk, directly
  supporting the ethics requirements (§1.5.2–1.5.3).
- It keeps the stack exactly as minimal as the reference project's.

**Trade-off to be aware of:** because this is a single shared instance, concurrent
users would see each other's uploaded data. This is acceptable for the demonstration
session (one lecturer, one researcher) but would need a proper session or per-user
store before any wider use.

## 5. Module Responsibilities

- **`backend/data/loader.py`** — reads CSV/XLSX, validates schema, rejects PII-like
  columns (FR2).
- **`backend/data/store.py`** — in-memory `DataStore`; converts flat rows into
  `Student`/`Assessment` objects for the algorithm layer.
- **`backend/algorithms/lp_bounds.py`** — Algorithm 1 (PuLP). Per-student min/max
  p-mark.
- **`backend/algorithms/participation_plan.py`** — Algorithm 2. Scenario enumeration
  for a target % improvement.
- **`backend/algorithms/nlp_weights.py`** — Algorithm 3 (scipy). Cohort weight
  optimisation for a target class average.
- **`backend/routes/home.py`** — `/` dashboard, `/threshold` (POST), `/upload` (POST).
- **`backend/routes/students.py`** — `/student/<code>` detail view.
- **`backend/routes/cohort.py`** — `/cohort` GET/POST what-if planning.

## 6. Non-Functional Implementation Notes

- **Performance (NFR1):** algorithms run on-demand per request (not eagerly cached),
  which is fine at the class sizes this prototype targets (~15–200 students); PuLP's
  CBC solve and scipy's SLSQP both return well under a second for these sizes.
- **Privacy (NFR3):** `loader.py`'s column-name denylist (`student_name`, `surname`,
  `id_number`, `email`, etc.) raises `PIIValidationError` rather than silently
  accepting a column that could contain identifiable data. Deliberately specific
  patterns avoid false positives on legitimate columns like `assessment_name`.
- **Testing:** each algorithm module has a corresponding file in `tests/` with
  known-input/known-output cases, run independently of Flask routes.

## 7. Deployment Plan

1. **Local development:** `python app.py` (reads `.env` via python-dotenv).
2. **Demonstration session:** run locally on your laptop and project the screen —
   simplest and most reliable for a single live session, no hosting dependency.
3. **Optional hosted demo:** any small WSGI host (Render free tier, PythonAnywhere)
   works since there's no database — just the Flask app + bundled sample data.

## 8. Suggested Build Order (maps to proposal §1.4.4 phases)

1. Data loader + in-memory store + sample dataset
2. Algorithm 1 (PuLP LP bounds) + unit tests
3. Dashboard route/template (cohort view)
4. Algorithm 2 (participation planning) + student detail route/template
5. Algorithm 3 (scipy NLP weights) + cohort planning route/template
6. Polish pass: at-risk styling, threshold/target controls, upload flow
7. Dry-run with fabricated data before the real lecturer session
