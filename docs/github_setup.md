# GitHub Setup Guide

## 1. Create the remote repository

**Option A — GitHub CLI (fastest):**
```bash
gh repo create lecturer-dss --private --source=. --remote=origin
```

**Option B — Web UI:**
1. Go to https://github.com/new
2. Name: `lecturer-dss` (or your preference)
3. Visibility: **Private** — keep it private until you've confirmed IP/publication
   rules with your supervisor (see `LICENSE.md`)
4. Do **not** initialise with a README/gitignore/license (you already have these)

## 2. Push this scaffold

From inside the unzipped project folder:
```bash
git init
git add .
git commit -m "chore: initial Flask scaffold matching reference stack, with functional/technical specs"
git branch -M main
git remote add origin https://github.com/<your-username>/lecturer-dss.git
git push -u origin main
```

## 3. Branching strategy

Given this is a solo-developer research project with a supervisor reviewing
progress, use a simple **GitHub Flow**:

- `main` — always working/demoable. Protect it (Settings → Branches → require
  PR before merging) once you have a first working version.
- `feature/<short-name>` — one branch per algorithm/page, e.g.:
  - `feature/lp-bounds`
  - `feature/participation-plan`
  - `feature/nlp-weights`
  - `feature/dashboard-ui`
- Open a PR into `main` when a feature works and its tests pass.

```bash
git checkout -b feature/lp-bounds
# ... work, commit ...
git push -u origin feature/lp-bounds
gh pr create --fill   # or open the PR from github.com
```

## 4. Commit message convention

Use [Conventional Commits](https://www.conventionalcommits.org/) so your commit
history doubles as a changelog for your final report's development narrative:

- `feat: add LP bounds calculation for Algorithm 1`
- `fix: correct PII denylist false-positive on assessment_name`
- `test: add unit tests for participation planning`
- `docs: update technical specification with deployment plan`
- `chore: scaffold repo structure`

## 5. Project board (optional but useful for your final report)

Create a GitHub Projects board with columns matching your DSRM build phases
(Research Proposal §1.4.4):

```
Requirements Analysis → System Design → Implementation → Testing & Refining → Evaluation
```

```bash
gh project create --owner <your-username> --title "Lecturer DSS"
```

Moving cards across these columns as you go gives you a ready-made, dated
record of your design-and-development process for Chapter 4 of the final report.

## 6. Protecting research data

Never commit real or partially-anonymised student data. The `.gitignore`
already excludes uploaded CSV/XLSX files. If you ever load real (anonymised)
data during the evaluation phase, keep it outside the repo entirely — pass it
in via file upload at runtime, as the app already supports.

## 7. Running the app after cloning

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```
Opens at `http://localhost:5000`.
