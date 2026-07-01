"""Tests du rapport PDF ML."""

import unittest

import pandas as pd
from pypdf import PdfReader

from src.ml.reports import build_prediction_pdf


class PredictionReportTests(unittest.TestCase):
    def test_builds_single_page_pdf(self):
        prediction = pd.Series(
            {
                "launch_name": "Test Mission",
                "prediction": "Réussite probable",
                "risk_score": 0.08,
                "risk_lower": 0.03,
                "risk_upper": 0.14,
            }
        )
        rocket = {"label": "Test Rocket", "attempts": 20, "failures": 1, "success_rate": 0.94}
        agency = {"label": "Test Agency", "attempts": 40, "failures": 2, "success_rate": 0.95}
        drivers = pd.DataFrame(
            [
                {"factor": "Expérience de la fusée", "direction": "Réduit le risque"},
                {"factor": "Orbite visée", "direction": "Augmente le risque"},
            ]
        )

        pdf = build_prediction_pdf(prediction, rocket, agency, drivers, "test-v1")

        self.assertTrue(pdf.startswith(b"%PDF"))
        reader = PdfReader(__import__("io").BytesIO(pdf))
        self.assertEqual(len(reader.pages), 1)
        self.assertIn("ARTEMIS SPACE ANALYTICS", reader.pages[0].extract_text())

    def test_wraps_long_reliability_labels(self):
        prediction = pd.Series(
            {
                "launch_name": "Long Agency Mission",
                "prediction": "Réussite probable",
                "risk_score": 0.04,
                "risk_lower": 0.01,
                "risk_upper": 0.09,
            }
        )
        rocket = {"label": "Long March 4C", "attempts": 60, "failures": 2, "success_rate": 0.957}
        agency = {
            "label": "China Aerospace Science and Technology Corporation",
            "attempts": 596,
            "failures": 14,
            "success_rate": 0.975,
        }
        drivers = pd.DataFrame(
            [{"factor": "Expérience de l'agence", "direction": "Réduit le risque"}]
        )

        pdf = build_prediction_pdf(prediction, rocket, agency, drivers, "test-v1")

        reader = PdfReader(__import__("io").BytesIO(pdf))
        text = " ".join(reader.pages[0].extract_text().split())
        self.assertIn("China Aerospace Science and Technology Corporation", text)
        self.assertEqual(len(reader.pages), 1)


if __name__ == "__main__":
    unittest.main()
