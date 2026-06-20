"""Tests du classifieur réussite/échec."""

import unittest

import numpy as np
import pandas as pd

from src.ml import (
    explain_prediction,
    predict_outcomes,
    reliability_summary,
    train_outcome_classifier,
)


class OutcomeClassifierTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(42)
        rows = []
        for index, date in enumerate(pd.date_range("2000-01-01", periods=300, freq="20D")):
            risky = index % 5 == 0
            failed = risky and rng.random() < 0.85
            rows.append(
                {
                    "launch_id": str(index),
                    "launch_name": f"Mission {index}",
                    "launch_date": date,
                    "status": "Launch Failure" if failed else "Launch Successful",
                    "agency": "Agency Risk" if risky else "Agency Stable",
                    "country": "A" if risky else "B",
                    "rocket": "Prototype" if risky else "Mature",
                    "orbit": "LEO",
                    "mission_type": "Test" if risky else "Communications",
                    "agency_type": "Commercial",
                    "pad": "Pad 1" if risky else "Pad 2",
                    "latitude": 1.0,
                    "longitude": 2.0,
                    "agency_attempts": index + 1,
                    "pad_attempts": index + 1,
                    "location_attempts": index + 1,
                    "orbital_attempts": index + 1,
                }
            )
        self.launches = pd.DataFrame(rows)

    def test_trains_and_scores_launches(self):
        result = train_outcome_classifier(self.launches)
        predictions = predict_outcomes(result, self.launches.tail(2))

        self.assertEqual(len(predictions), 2)
        self.assertTrue(predictions["risk_score"].between(0, 1).all())
        self.assertTrue(predictions["risk_lower"].between(0, 1).all())
        self.assertTrue(predictions["risk_upper"].between(0, 1).all())
        self.assertIn("prediction", predictions.columns)
        self.assertEqual(result.confusion.shape, (2, 2))
        self.assertGreater(result.decision_threshold, 0)
        self.assertGreaterEqual(result.roc_auc, 0.5)

        reliability = reliability_summary(
            self.launches, predictions.iloc[-1], "rocket"
        )
        self.assertGreater(reliability["attempts"], 0)
        self.assertGreaterEqual(reliability["success_rate"], 0)

        drivers = explain_prediction(result, self.launches.tail(1))
        self.assertFalse(drivers.empty)
        self.assertIn("direction", drivers.columns)

    def test_rejects_missing_target(self):
        with self.assertRaisesRegex(ValueError, "status"):
            train_outcome_classifier(self.launches.drop(columns="status"))


if __name__ == "__main__":
    unittest.main()
