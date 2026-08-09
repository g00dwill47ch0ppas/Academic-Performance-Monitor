import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.algorithms.nlp_weights import optimise_weights


def test_weights_sum_to_one():
    marks = np.array([[80, 60], [70, 50], [90, 40]])
    weights = optimise_weights(marks, target_average=65.0)
    assert np.isclose(weights.sum(), 1.0, atol=1e-4)


def test_result_moves_average_toward_target():
    marks = np.array([[80, 60], [70, 50], [90, 40]])
    initial = np.array([0.5, 0.5])
    initial_avg = (marks @ initial).mean()

    weights = optimise_weights(marks, target_average=70.0, initial_weights=initial)
    resulting_avg = (marks @ weights).mean()

    assert abs(resulting_avg - 70.0) <= abs(initial_avg - 70.0) + 1e-6
