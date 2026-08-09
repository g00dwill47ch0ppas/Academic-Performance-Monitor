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
  assessment-weight combination (non-linear optimisation) required to achieve it.
- **FR9** — The system shall present current vs. proposed weights so the lecturer can
  compare them directly.

### 3.5 Dashboard & Interaction
- **FR10** — The system shall present a class-wide dashboard: cohort average, at-risk
  count, and full cohort table.
- **FR11** — The system shall present a per-student detail view combining current p-mark,
  bounds (Algorithm 1), and participation plan (Algorithm 2).
- **FR12** — The system shall let the lecturer adjust the pass threshold and target class
  average via a form control, recomputing and re-rendering results on submit.
- **FR13** — The system shall allow the lecturer to switch between students from the
  detail view without returning to the dashboard first.

### 3.6 Non-Functional Requirements
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
3. Exact NLP objective/constraints for Algorithm 3 (weight bounds, whether weights must sum to 1).

These are marked as `# TODO: confirm against source` comments in the algorithm modules
so they're easy to locate and finish once you've re-read the paper's equations.
