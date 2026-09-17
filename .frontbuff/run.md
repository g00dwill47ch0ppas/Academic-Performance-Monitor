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
- Test suite: `.venv\Scripts\python.exe -m pytest -q` (22 tests currently).
