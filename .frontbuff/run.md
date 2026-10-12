# Running this worktree

## How to reproduce the uncommitted artifacts

- Copy `.env` from the main checkout (same values as `.env.example` are already checked in here):
  - On Windows (PowerShell):
    `Copy-Item ..\.env.example .env` (or copy from the main checkout if `.env` there was customized)
- No node dependencies — this is a Flask app with no package.json; the only install step is Python deps:
  - `.venv\Scripts\python.exe -m pip install -r requirements.txt` (already done in this worktree)

## How to run the server

- Working directory: the repo root (`C:\Users\goseg\Documents\Projects\Academic-Performance-Monitor`).
- Port: **5000** (Flask default; nothing else binds to it in this worktree).
- Start (detached, Windows):
  ```
  powershell -NoProfile -Command "(Start-Process -FilePath 'C:\Users\goseg\Documents\Projects\Academic-Performance-Monitor\.venv\Scripts\python.exe' -ArgumentList 'app.py' -WorkingDirectory 'C:\Users\goseg\Documents\Projects\Academic-Performance-Monitor' -RedirectStandardOutput '<log>' -RedirectStandardError '<log>.err' -WindowStyle Hidden -PassThru).Id"
  ```
  - stdout and stderr go to DIFFERENT files (PowerShell fails if both paths are equal).
  - Log file used here: `.freebuff\preview-6f8e0435-4599-4ce7-9abd-b9174452e3b2.log`
- URL once running: `http://127.0.0.1:5000`
- Confirm it is alive: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000` should print `200`.
- Simpler foreground-style start used in the latest session (no reloader, logs to `.frontbuff/flask.log`):
  ```
  .venv/Scripts/python.exe -c "from backend import create_app; create_app().run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)" > .frontbuff/flask.log 2>&1 &
  ```
  Find the owning PID with `netstat -ano | grep -E "127.0.0.1:5000.*LISTENING"`; stop it with `taskkill //F //PID <pid>`.
- Test suite: `.venv\Scripts\python.exe -m pytest -q` (108 tests currently).

## Participation rules, drops and display rounding

- The best-N-of-M rule lives in exactly one place: `backend/services/participation.py`
  (`analyse`, `final_participation`, `current_standing`, `min_max_final`,
  `final_with_marks`). Routes, algorithms, exports and templates all call it; if a number
  about participation looks wrong, fix it there and nowhere else.
- An assessment TYPE has M items and counts the best N of them (`module.assessments`);
  students hold one record per ITEM (`module.plan_items()` derives them). Every student
  item carries `group`, `items`, `count_best` and `item_max`, so the rule engine works on a
  bare list.
- Demo data: `backend/data/sample_data.csv` (Class Test 3 items/best 2 · 30%,
  Assignment 2/2 · 20%, Practical 1/1 · 15%, Attendance 12/10 · 35%). Regenerate it with
  the generator in the git history if you need different stages; keep it simulated.
- Algorithm 2 is now a projection: `feasible_region`, `build_projection`,
  `required_uniform_percentage` in `backend/algorithms/participation_plan.py`. The old
  `generate_participation_plan` enumeration was removed (see technical spec §5.2).
- Display rounding: `backend/services/rounding.py::fmt2` (Jinja filter `|r2`, registered in
  `backend/__init__.py`) and its browser twin `fmt2()` in `frontend/static/js/format.js`.
  Add no `round()`, `|format()` or `toFixed()` anywhere else.
- Quick sanity check from the console:
  `__import__('backend.services.rounding', fromlist=['fmt2']).fmt2(0.005) == '0.01'`, or in
  the browser `fmt2(2.675)` → `"2.68"`.

## Guided tutorial (Task 3)

- Tour data lives in `frontend/static/js/tutorial.js` (`STEPS` array); styles in
  `frontend/static/css/tutorial.css`; both are loaded from `base.html` on every page so the
  tour survives navigation. Replay page: `http://127.0.0.1:5000/tutorial`.
- The 36 steps are grouped into five parts (`SECTIONS`: create a module, assessment plan,
  students & marks, results & at-risk, cohort planning). Each part's step range is derived
  from `STEPS`, and `/tutorial` renders one “Start this part” card per part. A part keeps
  its own “Step n of m · <part>” counter and finishes with “Finish part”. The plan part
  covers number-of-items / count-best, and the results part walks one student's feasible
  region and target picker (it clicks View for STU001 on `/students`, so the sample module
  must still contain STU001).
- Storage keys: `localStorage['dss_tutorial_seen']` (first-run welcome), and
  `sessionStorage['dss_tutorial_active']` / `['dss_tutorial_step']` /
  `['dss_tutorial_section']` (resume position and which part is running; empty = full tour).
- To re-test the first-run popup: clear `localStorage` and reload any page except `/tutorial`.
- To jump straight to a step from the browser console: `__dssTour.start(<index>, "<part>")`
  (index 0 = first step; the tour navigates to the step's page itself). Omitting the part id
  runs the full 36-step tour; `__dssTour.sections` lists the part ids and titles.
- To leave the tour: `Esc`, the “Exit tutorial” button in the callout, or reload with the
  session storage cleared.
