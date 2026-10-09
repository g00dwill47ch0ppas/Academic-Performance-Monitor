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
  optimisation for a target class average, constrained by the lecturer's
  per-assessment weight ranges. Public surface:
  - `validate_weight_ranges(lower, upper, names)` — enforces min > 0, `min <= max` and
    `sum(min) <= 1 <= sum(max)`, raising `WeightRangeError` with a message that names the
    offender and states by how much it failed;
  - `solve_weight_ranges(...) -> WeightSolution` — returns `status`
    (`optimal` / `infeasible` / `failed`) plus a human-readable `message`, the weights and
    the resulting class average. The returned vector is *verified* against the sum and
    range constraints instead of trusting the solver's success flag;
  - `optimise_weights(...)` — thin backwards-compatible wrapper returning just the vector
    (used by the algorithm unit tests).
  Only the constraint builder changed for the range-based UI; the published objective
  (`minimise (class average − target)²`) is untouched.
- **`backend/routes/home.py`** — `/` dashboard, `/threshold` (POST), `/upload` (POST).
- **`backend/routes/students.py`** — `/student/<code>` detail view.
- **`backend/routes/cohort.py`** — `/cohort` GET/POST weight planning. One form submits
  the target average *and* every `min_<assessment>` / `max_<assessment>` field together;
  the route parses them, validates the hard rules, applies the 1% floor, calls
  `solve_weight_ranges` and renders the status, table and range chart. A blank field falls
  back to the pre-filled default (the current weight ±10 points, clamped to the 1% floor
  and 100%) rather than to zero, and a missing target field keeps the stored target.
- **`frontend/static/js/cohort.js`** — the same rules again in the browser for immediate
  feedback: it recomputes the sum of minimums/maximums on every keystroke, keeps the
  number inputs and sliders in step, marks the offending field with `aria-invalid` and
  disables *Calculate weights* while anything is invalid. The server remains the arbiter.
- **`backend/routes/tutorial.py`** — `/tutorial`: the replay page (written workflow summary,
  “Start / Replay tutorial”, and a control that restores the first-run welcome message).
  The tour itself is client-side; this route only serves the page it is launched from.
- **`frontend/templates/modules.html` + `backend/routes/modules.py`** — module creation also
  accepts an optional pass threshold (`module_threshold`), validated 0–100 and stored on the
  module's `ClassConfig`; blank falls back to `Config.DEFAULT_PASS_THRESHOLD`.

### 5.1 Guided tutorial (`frontend/static/js/tutorial.js`, `css/tutorial.css`)

Loaded from `base.html` on **every** page, because the tour moves between pages. It is
entirely data-driven: one `STEPS` array holds, per step, the `route` it belongs to, the
`selector` to highlight, the `action` that advances it (`click` / `type` / `select` /
`submit` / `next`), the instructional text, an optional `hint`, `missing` text for when the
target is not on the page, an optional `fill` example, and an `inMenu` flag for targets in
the navigation panel. Each step also names the `section` it belongs to.

- **Parts:** `SECTIONS` gives each section a title, a one-line blurb and an icon; a
  section's first/last step are **derived from `STEPS`** (never hand-entered), so the
  chooser on `/tutorial` renders straight from the same data and a step cannot fall
  outside its part. Starting a part stores `dss_tutorial_section`, and every “Step n of m”
  indicator, the `aria-live` announcement and the final “Finish part” button are computed
  from that range rather than from the full step list — the whole tour is simply the range
  with no section. A step that talks about the navigation panel keeps it open (the
  `#navSidebar` selector counts as an in-panel target), otherwise the panel would close on
  the step that explains it.

- **Spotlight:** four fixed dim panels surround the target's bounding box, leaving a clear
  hole, so only the highlighted element stays interactive. A single `requestAnimationFrame`
  loop re-reads the target rect and re-positions the panels, the ring and the callout, which
  is what keeps the hole glued to an element while the page scrolls or the side panel slides.
- **Callout:** positioned next to the target, flipping between below/above/right/left by
  available space, with an arrow on the edge facing the element and clamping to the viewport.
- **Advancement:** document-level `click`, `input`, `change` and `submit` listeners compare
  the event target against the current step's selector, so the step completes when the user
  really does the thing. A short debounce on typing steps stops mid-word jumps, and the
  re-render is deferred out of the click's dispatch so the tour never interferes with the
  link or form being clicked. Typing steps offer a “Fill an example for me” helper.
- **Persistence:** `sessionStorage` holds `dss_tutorial_active` and `dss_tutorial_step`; the
  next index is written *before* a navigation, so the tour resumes on the following page.
  `localStorage` holds `dss_tutorial_seen`, which suppresses the first-run welcome modal.
- **Accessibility:** the callout is a labelled dialog that takes focus (except for typing
  steps, where focus goes to the field), each step is announced through an `aria-live`
  region, `Esc` exits, and every control is a real button.
- **Harmless by design:** the tour submits only the module it is told to create; the
  assessment, student and marks steps stop short of committing anything, so the bundled
  CS101 dataset stays intact. The data note (memory-only, resets on restart, never enter
  real student data) is shown on every step.

## 6. Non-Functional Implementation Notes

- **Performance (NFR1):** algorithms run on-demand per request (not eagerly cached),
  which is fine at the class sizes this prototype targets (~15–200 students); PuLP's
  CBC solve and scipy's SLSQP both return well under a second for these sizes.
- **Privacy (NFR3):** `loader.py`'s column-name denylist (`student_name`, `surname`,
  `id_number`, `email`, etc.) raises `PIIValidationError` rather than silently
  accepting a column that could contain identifiable data. Deliberately specific
  patterns avoid false positives on legitimate columns like `assessment_name`.
- **Testing:** each algorithm module has a corresponding file in `tests/` with
  known-input/known-output cases, run independently of Flask routes. Cohort planning has
  both layers covered in `tests/test_cohort_planning.py`: the solver (sum = 100%, weights
  inside their ranges, never zero, infeasible ranges reported as a status) and the route
  (zero/negative minimums, `min > max`, minimums totalling more than 100%, maximums
  totalling less than 100%, non-numeric input, and the missing-target regression).
- **Shared chrome:** `frontend/templates/base.html` renders the navigation panel, the
  *Back* control, the help panel and the tutorial assets once for every page. `app.js`
  decides whether *Back* should walk browser history (same-origin referrer) or follow the
  logical parent link (per-endpoint fallback map in `base.html`).
- **Testing the tutorial:** the JavaScript tour is verified in the browser (first-run modal,
  spotlight geometry, action-driven advancement, cross-page resume, final recap); the
  server-rendered contract it depends on is covered by `tests/test_tutorial.py`, which also
  walks every `route` in `STEPS` to catch a renamed page.

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
