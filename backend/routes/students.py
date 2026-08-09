from flask import Blueprint, abort, render_template, request

from backend.algorithms.lp_bounds import compute_pmark_bounds
from backend.algorithms.participation_plan import generate_participation_plan
from backend.data.store import data_store

students_bp = Blueprint("students", __name__)


@students_bp.route("/student/<student_code>")
def student_detail(student_code):
    if student_code not in data_store.student_codes():
        abort(404)

    student = data_store.get_student(student_code)
    min_pm, max_pm = compute_pmark_bounds(student.assessments)

    target_pct = int(request.args.get("target_pct", 10))
    scenarios = generate_participation_plan(
        student.assessments, student.p_mark_current, target_pct
    )

    return render_template(
        "student_detail.html",
        student=student,
        min_pmark=min_pm,
        max_pmark=max_pm,
        target_pct=target_pct,
        scenarios=scenarios,
        target_pmark=round(student.p_mark_current * (1 + target_pct / 100), 1),
        all_codes=data_store.student_codes(),
    )
