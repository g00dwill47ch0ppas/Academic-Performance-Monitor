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
    name: str              # the ITEM's own name ("Class Test 2")
    weight: float          # W of the whole TYPE it belongs to, in (0, 1]
    mark: float | None     # y_i, None = not written yet (a recorded 0 IS a mark)
    completed: bool
    group: str = ""        # the type this item belongs to (""; "" = its own type)
    items: int = 1         # M — how many items the type has
    count_best: int = 1    # N — how many of them count (1 <= N <= M)
    item_max: float = 100.0  # max mark for this item; ranking uses mark / item_max

@dataclass
class Student:
    student_code: str               # anonymised code, never a real name/number
    assessments: list[Assessment]   # flat list of ITEMS across every type
    # p_mark_current delegates to backend/services/participation.py

@dataclass
class ClassConfig:
    pass_threshold: float = 50.0
    target_class_average: float = 60.0
```

A module's plan (`module.assessments`) holds one record per assessment **type**
(name, W, M, N); each student holds one record per **item**. `Module.plan_item_specs()`
flattens the types into items — `"<Type> 1" … "<Type> M"`, or the type's own name when
M = 1 — and `Module.plan_items()` returns the same as blank `Assessment` records. Item
metadata is copied onto every item record so the rule engine can work from a bare list
(`M = N = 1` is exactly the pre-extension behaviour: p = Σ yᵢwᵢ).

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
- **`backend/services/participation.py`** — **the single source of truth for the
  participation mark and the best-N-of-M rule.** Routes, algorithms, the at-risk
  logic, exports and templates all call it; no other module re-implements the drop
  rule. Public surface:
  - `analyse(items) -> Participation` — groups items by type and returns, per type,
    the counted / dropped / remaining items, accrued marks, current standing, the
    remaining counted slots and the min/max achievable contribution;
  - `final_participation(items)` / `current_standing(items)` / `min_max_final(items)` —
    the three numbers the app displays;
  - `final_with_marks(items, overrides)` — re-runs the best-N rule with specific items
    re-marked, which is how the projection answers “what if every remaining item scores
    x%?” without duplicating the rule.

  Full precision throughout: this module never rounds.
- **`backend/services/rounding.py`** — display rounding, the only place a number is
  rounded for the user. `fmt2(value)` rounds to at most two decimals (half-up, via
  `Decimal`, so 0.005 → 0.01 and 2.675 → 2.68 rather than Python's banker's rounding),
  trims trailing zeros (70, 70.5, 70.25), never shows `-0.00`, and returns an em dash
  for `None`/NaN/infinity. It is registered as the Jinja filter `|r2` in
  `create_app()` and mirrored in the browser by `fmt2()` in
  `frontend/static/js/format.js` (loaded from `base.html`), so a live JS summary and a
  server-rendered page cannot disagree. Exports call `fmt2` too, and templates use
  `|r2` instead of `round(...)`, `|format(...)` or `toFixed(...)` — there are no
  other rounding calls left in the templates or the JS.
- **`backend/algorithms/lp_bounds.py`** — Algorithm 1. Per-student min/max bounds,
  now delegated to the participation service (see the deviation list in §7):
  min = accrued mark, max = top-N of (completed marks + 100% for everything
  outstanding). `is_at_risk(max, threshold)` is unchanged.
- **`backend/algorithms/participation_plan.py`** — Algorithm 2, rebuilt around the
  feasible region and an absolute target (`feasible_region`, `build_projection`,
  `required_uniform_percentage`). The old scenario enumeration is gone; §5.2 records
  why it could not be carried over.
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

### 5.2 The participation rule, droppable assessments and the feasible region

**The rule (one implementation: `backend/services/participation.py`).** An assessment
type holds M items of which the best N count. With type weight W, every counted slot is
worth `W / N` of the final mark, and the counted slots are the top `min(k, N)` completed
items **by percentage** (`mark / item_max`), so items with different maxima compare
fairly; ties go to the earliest item in plan order. Consequences the app depends on:

| Case | Result |
|---|---|
| blank mark | “not written yet” — it is *not* zero and never fills a slot |
| recorded 0 | a real mark: it fills a slot and drags the standing down |
| k <= N | every completed item counts; nothing is dropped yet |
| k > N | the lowest ranked completed items are **dropped** (badge + strikethrough) |
| accrued | `Σ(carried percentages) × W / N` — the participation mark earned so far |
| standing | accrued re-based on the counted slots filled so far (a mean percentage) |
| min final | the accrued mark — remaining items can score 0 and are then dropped |
| max final | top-N of (completed marks + 100% for every remaining item): a strong remaining item *displaces* a dropped one |

`W`, `M`, `N` are validated at three layers: the plan form (`min="1"`, and the store’s
`validate_type` rejects `N > M`, `N < 1` or `M < 1`), the route (whole numbers, 1 ≤ N ≤ M,
1 ≤ M) and the store itself, which is the arbiter for every path including CSV import.
Changing M, N or W re-derives every student’s item list from the plan while matching
existing marks **by item name**, so a recorded mark is never lost by an edit.

**The feasible region.** `[min_final, max_final]` per student, shown as a bar on the
student page with the accrued mark and the pass threshold marked on the same 0–100 axis.
When the whole region lies below the threshold the page says passing is no longer
possible. The cohort-level view of the same quantity is the per-student min/max columns
on the dashboard, students and at-risk tables.

**The target projection.** The lecturer picks an absolute target inside the region (a
slider plus a number input, both bounded by the region) and the page solves the minimum
uniform percentage `x` that every remaining item must reach:

- `final(x)` is monotone non-decreasing, so `x` is solved by bisection (200 halvings,
tolerance 1e-6 marks) with the best-N rule applied inside **every** evaluation — never
approximated. Target at the region minimum gives x = 0; at the maximum it gives x = 100.
- **All** remaining items appear in the plan table; nothing is set to zero as a shortcut.
- Skipping is handled honestly: for each type the code re-solves the level the *other*
items need once t of them are left unwritten, and reports the largest t that still
reaches the target (“you can skip 1 item if the other 1 scores at least 80%”).
- Edge cases: nothing left to write collapses the region to a point and the page says the
mark is fixed; a target equal to the accrued mark needs nothing further; a target outside
the region is blocked by the slider **and** rejected by the route with a message that
names the region.

**Why the old Algorithm 2 was replaced (no dead code left).** The published algorithm
enumerates mark combinations for a percentage *improvement* over the current p-mark and
treats not-yet-written assessments as zero. Two things made that unusable here: the
inputs changed (an absolute target, and every remaining item as a variable), and with
drops a “scenario” is no longer a plain mark vector — *which marks are dropped* is part
of the outcome, so the enumeration would have had to rank inside each combination. The
`generate_participation_plan` enumeration and its test file were therefore removed rather
than left as an unused second implementation of the same idea.

### 5.3 Demo data

`backend/data/sample_data.csv` is simulated data (`# deterministic, seed 2018`) built to
exercise every new rule: **Class Test** — 3 items, best 2 count, 30%; **Assignment** —
2 items, both count, 20%; **Practical** — 1 item, 15%; **Attendance** — 12 sessions, best
10 count, 35%. Its 15 students sit at different completion stages, including one with
nothing recorded, one who has written everything, one with a recorded 0 at an attendance
session (a real mark, not a blank), and one with two low attendance marks that are
dropped. Columns: `student_code, assessment_name, weight, mark, completed, group,
items, count_best, item_max`; the first five are the original format, so older files
still import with every assessment as its own M = N = 1 type.

## 6. Non-Functional Implementation Notes

- **Performance (NFR1):** algorithms run on-demand per request (not eagerly cached),
  which is fine at the class sizes this prototype targets (~15–200 students); scipy's
  SLSQP solve returns well under a second, the participation rule is a sort per type,
  and the projection bisection is ~200 cheap evaluations.
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

## 9. Deviations from Van der Merwe et al. (2018b)

Every place the implemented model goes beyond, or reads differently from, the published
one is marked in the source with `# TODO: confirm against source paper`. Collected here:

| # | Location | Deviation | Why |
|---|---|---|---|
| 1 | `algorithms/lp_bounds.py` | Bounds are computed in closed form instead of by two LP solves | Once a type drops its weakest items, which items contribute is decided by a ranking, so the objective is piecewise-linear and no LP can express it. The closed form returns exactly the LP's answer when N = M (nothing dropped) — see README, “A note on the tech stack”. |
| 2 | `algorithms/lp_bounds.py` | The `[0, 100]` assumption per remaining mark is kept; no cross-assessment constraint | Carried over from the original implementation; still unconfirmed. |
| 3 | `services/participation.py` | The drop rule itself (best N of M, ranked by percentage, ties by plan order) | Not in the paper — this project's extension. The ranking key (`mark / item_max`) and the tie rule were chosen here. |
| 4 | `algorithms/participation_plan.py` | Algorithm 2 plans from an absolute target inside a feasible region instead of a percentage improvement, and includes every remaining item | Requested behaviour; the published enumeration could not be reconciled with drops (see §5.2). |
| 5 | `algorithms/participation_plan.py` | The optional-item (“skip”) analysis | New; the paper defines no such analysis. |
| 6 | `routes/cohort.py::_mark_matrix` | A type's entry in the class-average matrix is its counted standing, and an assessment nobody has written yet still contributes 0 | The objective is unchanged; only the mark data feeding it is chosen. The paper does not describe droppable types or unwritten assessments, so the choice is flagged, not silently made. |
| 7 | `algorithms/nlp_weights.py` | Solver tolerances, the 1% floor and the “on target” tolerance are implementation choices | Pre-existing; ranges themselves come from the lecturer's input (flagged in the module docstring). |

Nothing in the three published objectives was changed: Algorithm 1's min/max, Algorithm 3's
`minimise (class average − target)²` and Algorithm 2's “minimum marks needed” intent are all
intact — the deviations above concern the *feasible set* the drop rule introduces, the half
of Algorithm 2 that no longer had a defined input, and the choice of mark data.
