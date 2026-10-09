/**
 * Cohort planning — live validation of the per-assessment weight ranges.
 *
 * Mirrors the hard rules enforced on the server in backend/routes/cohort.py:
 *   1. every minimum must be > 0  (no assessment may be weighted to zero)
 *   2. minimum <= maximum for the same assessment
 *   3. the ranges must be able to add up to 100%:
 *        sum(min) <= 100 <= sum(max)
 *
 * This is a convenience layer only — the server re-checks every rule and is the
 * final arbiter. It disables the Calculate button while the ranges are invalid
 * and explains exactly what is wrong and by how much.
 */
(function () {
    "use strict";

    var form = document.getElementById("cohortForm");
    if (!form) return;

    var calculate = document.getElementById("cohortCalculate");
    var sumMinEl = document.getElementById("sumMin");
    var sumMaxEl = document.getElementById("sumMax");
    var problemEl = document.getElementById("rangeProblem");
    var okEl = document.getElementById("rangeOk");

    var rows = Array.prototype.slice.call(form.querySelectorAll(".weight-range-row"));

    /** Format a percentage the way the server does: always one decimal place. */
    function pct(value) {
        return (Math.round(value * 10) / 10).toFixed(1);
    }

    function numberOf(input) {
        var raw = (input.value || "").trim();
        if (raw === "") return null;
        var value = Number(raw);
        return Number.isFinite(value) ? value : null;
    }

    /** Keep a number input and its paired slider in step, in both directions. */
    function linkPair(numberInput, rangeInput) {
        if (!numberInput || !rangeInput) return;
        rangeInput.addEventListener("input", function () {
            numberInput.value = rangeInput.value;
        });
        numberInput.addEventListener("input", function () {
            var value = numberOf(numberInput);
            if (value !== null) rangeInput.value = Math.min(100, Math.max(0, value));
        });
    }

    rows.forEach(function (row) {
        linkPair(row.querySelector('[data-role="min-number"]'),
                 row.querySelector('[data-role="min-range"]'));
        linkPair(row.querySelector('[data-role="max-number"]'),
                 row.querySelector('[data-role="max-range"]'));
    });

    /**
     * Check every rule and update the summary + submit button.
     * Returns true when the form is safe to submit.
     */
    function validate() {
        var totalMin = 0;
        var totalMax = 0;
        var problem = null;
        var firstBadInput = null;

        // Clear any previous error marker so it never sticks to a fixed field.
        Array.prototype.forEach.call(form.querySelectorAll('[aria-invalid]'), function (el) {
            el.removeAttribute("aria-invalid");
        });

        rows.forEach(function (row) {
            if (problem) return;
            var name = row.getAttribute("data-assessment") || "this assessment";
            var minNumber = row.querySelector('[data-role="min-number"]');
            var maxNumber = row.querySelector('[data-role="max-number"]');
            var min = minNumber ? numberOf(minNumber) : null;
            var max = maxNumber ? numberOf(maxNumber) : null;

            if (min === null || max === null) {
                problem = "Enter a minimum and a maximum weight for '" + name + "'.";
                firstBadInput = min === null ? minNumber : maxNumber;
                return;
            }
            if (min <= 0) {
                problem = "Minimum weight for '" + name + "' must be greater than 0% — " +
                          "every assessment has to carry weight, so no weight may be zero.";
                firstBadInput = minNumber;
                return;
            }
            if (max > 100) {
                problem = "Maximum weight for '" + name + "' cannot be more than 100% (it is " +
                          pct(max) + "%).";
                firstBadInput = maxNumber;
                return;
            }
            if (min > max) {
                problem = "Minimum weight for '" + name + "' (" + pct(min) + "%) is above its " +
                          "maximum (" + pct(max) + "%). Lower the minimum or raise the maximum.";
                firstBadInput = minNumber;
                return;
            }
            totalMin += min;
            totalMax += max;
        });

        if (!problem && totalMin > 100) {
            problem = "Infeasible ranges: the minimum weights add up to " + pct(totalMin) +
                      "%, which is " + pct(totalMin - 100) + "% more than 100%. " +
                      "Lower the minimums by at least " + pct(totalMin - 100) + "% in total.";
        }
        if (!problem && totalMax < 100) {
            problem = "Infeasible ranges: the maximum weights add up to " + pct(totalMax) +
                      "%, which is " + pct(100 - totalMax) + "% less than 100%. " +
                      "Raise the maximums by at least " + pct(100 - totalMax) + "% in total.";
        }

        if (sumMinEl) sumMinEl.textContent = pct(totalMin) + "%";
        if (sumMaxEl) sumMaxEl.textContent = pct(totalMax) + "%";

        if (problemEl) {
            problemEl.textContent = problem || "";
            problemEl.hidden = !problem;
        }
        if (okEl) okEl.hidden = !!problem;

        if (calculate) {
            calculate.disabled = !!problem;
            calculate.setAttribute("aria-disabled", String(!!problem));
            if (problem) {
                calculate.title = problem;
            } else {
                calculate.removeAttribute("title");
            }
        }
        if (firstBadInput) firstBadInput.setAttribute("aria-invalid", "true");
        return !problem;
    }

    // Re-check when the target changes too (it is part of the same submission).
    form.addEventListener("input", validate);
    validate();
})();
