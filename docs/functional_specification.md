# Functional Specification
## Lecturer-Facing Decision Support System (DSS) for At-Risk Student Identification

**Author:** G. O. G. Sebaetse (46997245) — ITRI671
**Supervisor:** Prof. C. J. Kruger
**Traceability:** Derived from Research Proposal §1.3.5 (Aim & Objectives) and §1.3.4 (Research Questions)

---

## 1. Purpose and Scope

The artefact is a standalone web-based DSS that gives lecturers real-time, model-driven
visibility into class-wide academic performance and generates prescriptive, individualised
improvement guidance — without lecturers performing manual calculations.

**In scope:** single-module, single-lecturer view; simulated or anonymised historical data;
research-prototype evaluation at NWU Potchefstroom Campus.
**Out of scope:** multi-tenant/institution deployment, real student PII, LMS integration,
authentication/authorisation beyond a single-session demo.

## 2. Actors

| Actor | Description |
|---|---|
| Lecturer | Primary user. Views cohort/student performance, runs what-if scenarios, receives recommendations. |
| Researcher (you) | Configures demo data, facilitates the evaluation session, collects survey/observation data. |

## 3. Functional Requirements

### 3.1 Data Handling
- **FR1** — The system shall allow import of class assessment data (student codes,
  per-assessment marks `y`, per-assessment weights `w`) via CSV or XLSX upload, or
  use a bundled simulated dataset by default.
- **FR2** — The system shall validate on load: reject any column resembling a real
  name, ID number, or email (ethics requirement — proposal §1.5.2).
- **FR3** — The system shall compute the current participation mark for every student:
  `p = y1w1 + y2w2 + ... + ynwn`.

### 3.2 Algorithm 1 — Performance Bounds (LP)
- **FR4** — The system shall compute, per student, the minimum and maximum achievable
  p-mark given current marks and the weights of remaining (not-yet-written) assessments,
  using linear programming.
- **FR5** — The system shall flag a student "at-risk" when their maximum achievable
  p-mark falls below a lecturer-configurable pass threshold.

### 3.3 Algorithm 2 — Participation Planning
- **FR6** — For a lecturer-selected target percentage improvement, the system shall
  enumerate feasible score combinations across remaining assessments and present the
  marks required in each scenario to reach that target.
- **FR7** — The system shall present participation-plan output per student in a
  human-readable table (assessment → required mark).

### 3.4 Algorithm 3 — Cohort Weight Optimisation (NLP)
- **FR8** — For a lecturer-specified target class average, the system shall compute the
  assessment-weight combination (non-linear optimisation) required to achieve it, subject
  to a lecturer-supplied weight **range** `[min%, max%]` per assessment in the module's
  assessment plan.
- **FR9** — The system shall present current vs. proposed weights so the lecturer can
  compare them directly, alongside the range each weight was constrained to.
- **FR14** — The system shall enforce the following hard rules, in both the page and the
  server:
  1. **no assessment may ever be weighted to zero** — every minimum must be greater than
     0%, and the solver never returns a weight below a 1% floor;
  2. `min <= max` for each assessment;
  3. the weights must sum to exactly 100%, so the ranges must be feasible:
     `sum(min) <= 100 <= sum(max)`.
  A violation shall be reported as a message that names the assessment (or the class-wide
  sum) and states by how much the condition failed — never a crash or an empty result.
- **FR15** — The system shall show a live summary of the sum of minimums and maximums,
  disable the *Calculate weights* control while the ranges are invalid, and always surface
  the solver status (optimal / infeasible / did not converge) together with how close the
  resulting class average is to the target.

### 3.5 Dashboard & Interaction
- **FR10** — The system shall present a class-wide dashboard: cohort average, at-risk
  count, and full cohort table.
- **FR11** — The system shall present a per-student detail view combining current p-mark,
  bounds (Algorithm 1), and participation plan (Algorithm 2).
- **FR12** — The system shall let the lecturer adjust the pass threshold and target class
  average via a form control, recomputing and re-rendering results on submit. The pass
  threshold can also be set when a module is created.
- **FR13** — The system shall allow the lecturer to switch between students from the
  detail view without returning to the dashboard first.

### 3.6 Navigation & Guidance
- **FR16** — Every page except the dashboard shall show a *Back* control that returns to
  the previous page when the lecturer arrived from within the system, and otherwise to the
  page's logical parent (cohort planning → dashboard, student detail → students, module
  detail → modules). It shall be keyboard accessible and carry an `aria-label`.
- **FR17** — Every page shall offer a contextual **help panel** (the question-mark button)
  that opens and stays open until the lecturer closes it, dismisses it with `Esc`, or
  clicks outside it; the panel text explains the rules of that page.

### 3.7 Onboarding & Tutorial
- **FR18** — On the very first visit the system shall show a **welcome message** explaining,
  in a few lines, that it identifies at-risk students, monitors class performance, and
  plans assessment weights and participation for a cohort. The message shall carry one
  primary action (“Let's start, create a module”) with a glow animation that is disabled
  under `prefers-reduced-motion`, plus a secondary **Skip** link. It shall not appear again
  once seen, and it shall not be stacked on top of the Tutorial page.
- **FR19** — The system shall provide a **guided tour** that walks the lecturer through the
  whole workflow on the live pages, in this order: open the navigation panel (pages +
  module switcher), create a module (code, name, pass threshold), define the assessment
  plan (assessments, weights, running total), add students and enter marks (every field
  explained), read the dashboard and at-risk indicators, plan the cohort's weight ranges
  (including the rule that a weight can never be zero), and finish with a recap. The tour
  shall:
  1. dim the page and highlight only the current target, leaving that element interactive;
  2. advance when the lecturer performs the action (click, value entered, selection made),
     not only on a Next button, and offer a “Fill an example for me” helper for typing
     steps;
  3. persist its step across page navigations (session storage) so it survives the
     multi-page flow;
  4. offer Back, Skip step and Exit tutorial on every step, with a “Step n of m” indicator;
  5. reposition the highlight and callout on scroll/resize and flip the callout when there
     is no room;
  6. be keyboard operable, announce each step through `aria-live`, and exit on `Esc`;
  7. never submit data on the lecturer's behalf (except the module the tour is told to
     create) and never request or display real student data.
  The tour shall be runnable either as a whole or as one **part** at a time
  (create a module / assessment plan / students & marks / results & at-risk /
  cohort planning); a part shall start on the page it belongs to, carry its own
  “Step n of m” counter and label, end on its own with “Finish part”, and leave the
  other parts untouched.
- **FR20** — The system shall provide a **Tutorial page** (`/tutorial`), linked from the
  navigation panel, with a “Start / Replay tutorial” control, a **part chooser** that
  starts any one part of the tour (derived from the tour data, so the two cannot drift),
  a written summary of the
  workflow, and a control that restores the first-run welcome message. It shall repeat the
  warning that data is held in memory only and resets on restart, and that no real student
  data may be entered.

### 3.8 Non-Functional Requirements
- **NFR1 (Performance)** — Recompute all three algorithms for a class of ≤200 students
  in under 2 seconds per request, so the lecturer isn't waiting during the live session.
- **NFR2 (Usability)** — Interface follows choice-architecture principles (Jameson et al.,
  2014) referenced in the evaluation instrument — minimal clicks to reach a
  recommendation, sensible defaults, clear at-risk visual cues (colour + label, not
  colour alone).
- **NFR3 (Privacy)** — No identifiable data persisted to disk; the in-memory store holds
  only the current session's simulated/anonymised data and is cleared on server restart.
- **NFR4 (Portability)** — Runs locally (researcher's laptop) with no external database
  or institutional infrastructure dependency.

## 4. Traceability to Research Questions

| Research Question | Addressed by |
|---|---|
| RQ1: functional requirements for a lecturer-facing DSS | This document |
| RQ2: implementing LP/NLP models in a usable interface | FR4–FR9, NFR2 |
| RQ3: lecturer evaluation of usability/usefulness | Out of artefact scope — captured via survey instrument (Chapter 3 methodology) |

## 5. Open Items to Confirm Against Van der Merwe et al. (2018b)

Before finalising Algorithm 1–3 logic, confirm against the source paper:
1. Exact LP constraint set for Algorithm 1 (bounds on remaining assessment marks — e.g. 0–100?).
2. Exact combinatorial step size for Algorithm 2 scenario generation (mark increments, e.g. 5% steps).
3. Exact NLP objective/constraints for Algorithm 3 (whether weights must sum to 1, and
   whether the paper prescribes default per-assessment bounds). The [min%, max%] ranges
   enforced here currently come from the lecturer's input on the cohort-planning page,
   with the 1% strictly-positive floor added by this implementation.
4. Whether assessments the class has not written yet should count as 0 in the class
   average that Algorithm 3 compares against the target (`backend/routes/cohort.py`,
   `_mark_matrix`), or be projected/ignored.

These are marked as `# TODO: confirm against source` comments in the algorithm modules
so they're easy to locate and finish once you've re-read the paper's equations.
