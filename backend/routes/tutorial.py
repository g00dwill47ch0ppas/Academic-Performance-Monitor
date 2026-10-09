"""
Tutorial page — replay the guided tour and read the workflow in words.

The tour itself is client-side (``frontend/static/js/tutorial.js`` and
``frontend/static/css/tutorial.css``, loaded from ``base.html`` so it can follow
the user across pages). This blueprint only serves the page that hosts the
"Start / Replay tutorial" control and the written summary, so the tour is
reachable at any time without depending on the first-run popup.
"""

from flask import Blueprint, render_template

tutorial_bp = Blueprint("tutorial", __name__)


@tutorial_bp.route("/tutorial")
def tutorial():
    """Explain the workflow and offer the replay controls."""
    return render_template("tutorial.html")
