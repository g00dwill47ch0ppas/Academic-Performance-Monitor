"""Guided tutorial — the /tutorial page, its assets, and the module-threshold field.

The tour behaviour itself lives in JavaScript and is verified in the browser;
these tests cover the server-rendered contract it depends on:
  * the /tutorial page (replay controls + written summary + data warning),
  * tutorial.css / tutorial.js being loaded on every page from base.html
    (required for the tour to survive page navigation),
  * a "Tutorial" entry in the navigation panel,
  * the part chooser on /tutorial and the section data behind it (every step belongs to a
    declared section, and each section is a contiguous run so its range is correct),
  * the module-creation form accepting a pass threshold (tour step 2).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend import create_app
from backend.data.store import data_store


def _client():
    return create_app().test_client()


def test_tutorial_page_offers_replay_and_summary():
    body = _client().get("/tutorial").data.decode("utf-8")

    assert "Start / Replay tutorial" in body
    assert "Show the welcome message again" in body
    assert "The workflow, step by step" in body
    assert "in memory only" in body  # data warning
    assert "never enter real student names" in body.lower()


def test_tutorial_assets_are_loaded_on_every_page():
    client = _client()
    for path in ("/", "/students", "/cohort", "/tutorial"):
        body = client.get(path).data.decode("utf-8")
        assert "css/tutorial.css" in body, path
        assert "js/tutorial.js" in body, path


def test_navigation_panel_links_to_the_tutorial():
    body = _client().get("/").data.decode("utf-8")

    assert 'href="/tutorial"' in body
    assert ">Tutorial</span>" in body.replace("\n", "").replace(" ", "") or "Tutorial" in body


def _tutorial_script() -> str:
    return Path("frontend/static/js/tutorial.js").read_text(encoding="utf-8")


def _step_records(script: str) -> list[dict]:
    """Parse the STEPS array line by line (route → action → section per step)."""
    records: list[dict] = []
    current: dict = {}
    for line in script.splitlines():
        stripped = line.strip()
        match = re.match(r'^route: "([^"]+)",$', stripped)
        if match:
            current = {"route": match.group(1)}
            continue
        match = re.match(r'^action: "([a-z]+)",$', stripped)
        if match and current:
            current["action"] = match.group(1)
            continue
        match = re.match(r'^section: "([a-z]+)",$', stripped)
        if match and current:
            current["section"] = match.group(1)
            records.append(current)
            current = {}
    return records


def test_steps_array_covers_the_documented_workflow():
    """The tour data must stay in step with the pages (guards renames/typos)."""
    script = _tutorial_script()
    records = _step_records(script)
    assert records, "no steps parsed out of tutorial.js"

    # Every page the tour visits must be a real route.
    for route in {record["route"] for record in records}:
        path = route.replace("*", "STU001")
        assert _client().get(path).status_code == 200, route

    # The storage keys the brief specifies must be present.
    assert "dss_tutorial_seen" in script
    assert "dss_tutorial_active" in script
    assert "sessionStorage" in script


def test_every_step_belongs_to_a_declared_section():
    """The section chooser derives its ranges from the steps — keep them honest."""
    script = _tutorial_script()
    records = _step_records(script)
    section_ids = re.findall(r'^\s*id: "([a-z]+)",$', script, re.M)

    assert section_ids, "no SECTIONS entries found"
    declared = set(section_ids)
    used = {record.get("section") for record in records}

    assert None not in used, "a step is missing its section"
    assert used == declared, f"steps use {used}, chooser declares {declared}"

    # A section must be a contiguous run of steps, otherwise its range is wrong.
    for section_id in declared:
        indices = [i for i, record in enumerate(records) if record["section"] == section_id]
        assert indices == list(range(indices[0], indices[-1] + 1)), section_id


def test_every_step_declares_how_it_advances():
    script = _tutorial_script()
    allowed = {"click", "type", "select", "submit", "next"}
    actions = [record.get("action") for record in _step_records(script)]

    assert all(action in allowed for action in actions), actions


def test_tutorial_page_has_a_section_chooser_host():
    body = _client().get("/tutorial").data.decode("utf-8")

    assert "data-tour-sections" in body
    assert "Or run just one part" in body


def test_create_module_accepts_a_pass_threshold():
    client = _client()
    try:
        resp = client.post(
            "/modules/create",
            data={"module_code": "THRESH1", "module_name": "Threshold test", "module_threshold": "65"},
        )
        assert resp.status_code == 302

        module = data_store.modules.get("THRESH1")
        assert module is not None
        assert module.config.pass_threshold == 65.0
        assert data_store.active_module is module

        # The new threshold is echoed back on the Modules page.
        assert "threshold 65.0%" in client.get("/modules").data.decode("utf-8")
    finally:
        data_store.delete_module("THRESH1")
        data_store.activate("CS101")


def test_create_module_rejects_an_out_of_range_threshold():
    client = _client()
    try:
        resp = client.post(
            "/modules/create",
            data={"module_code": "THRESH2", "module_name": "Bad", "module_threshold": "150"},
        )
        assert resp.status_code == 302
        assert "THRESH2" not in data_store.modules
    finally:
        data_store.activate("CS101")


def test_create_module_without_a_threshold_uses_the_default():
    client = _client()
    try:
        client.post("/modules/create", data={"module_code": "THRESH3", "module_name": "Default"})
        module = data_store.modules.get("THRESH3")
        assert module is not None
        assert module.config.pass_threshold == 50.0  # config.py default
    finally:
        data_store.delete_module("THRESH3")
        data_store.activate("CS101")
