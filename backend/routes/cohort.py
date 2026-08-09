import numpy as np
import pandas as pd
from flask import Blueprint, render_template, request

from backend.algorithms.nlp_weights import optimise_weights
from backend.data.store import data_store

cohort_bp = Blueprint("cohort", __name__)


@cohort_bp.route("/cohort", methods=["GET", "POST"])
def cohort_planning():
    df = data_store.df
    assessment_names = list(df["assessment_name"].unique())

    pivot = df.pivot_table(
        index="student_code", columns="assessment_name", values="mark", aggfunc="first"
    ).reindex(columns=assessment_names)
    mark_matrix = pivot.apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy()

    current_weights = (
        df.drop_duplicates("assessment_name")
        .set_index("assessment_name")["weight"]
        .reindex(assessment_names)
        .to_numpy()
    )

    target = data_store.config.target_class_average
    result_rows = None
    error = None

    if request.method == "POST":
        try:
            target = float(request.form["target_average"])
            data_store.config.target_class_average = target
        except (KeyError, ValueError):
            error = "Invalid target average."

        if error is None:
            try:
                optimal_weights = optimise_weights(mark_matrix, target, current_weights)
                result_rows = [
                    {
                        "assessment": name,
                        "current_weight": round(float(cw), 3),
                        "proposed_weight": round(float(ow), 3),
                    }
                    for name, cw, ow in zip(assessment_names, current_weights, optimal_weights)
                ]
            except ValueError as e:
                error = str(e)

    current_class_avg = round(float((mark_matrix @ current_weights).mean()), 1)

    return render_template(
        "cohort_planning.html",
        assessment_names=assessment_names,
        current_weights=current_weights,
        target=target,
        result_rows=result_rows,
        error=error,
        current_class_avg=current_class_avg,
    )
