"""Regression tests for the domain-specific ATC parser."""
from __future__ import annotations

import pathlib
import sys
import unittest


# Ensure the backend directory is on the import path when running from repo root.
BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evaluation import SAMPLE_TRANSMISSIONS  # noqa: E402  pylint: disable=wrong-import-position
from main import _build_controller_response  # noqa: E402  pylint: disable=wrong-import-position
from parser import parse_atc  # noqa: E402  pylint: disable=wrong-import-position


class ParserRegressionTests(unittest.TestCase):
    def test_parser_handles_sample_transmissions(self):
        for sample in SAMPLE_TRANSMISSIONS:
            parsed = parse_atc(sample.transcript)
            for field, expected in sample.expected.items():
                with self.subTest(transcript=sample.transcript, field=field):
                    self.assertEqual(
                        parsed.get(field),
                        expected,
                        msg=f"field {field} mismatch for '{sample.transcript}'",
                    )


class ResponseBuilderTests(unittest.TestCase):
    def test_response_templates(self):
        scenarios = [
            (
                {"callsign": "DAL210", "command": "descend", "flight_level": 240, "speaker": "pilot"},
                "DAL210, roger. Descend to flight level 240 approved.",
            ),
            (
                {"callsign": "DAL210", "command": "climb", "flight_level": 330, "speaker": "controller"},
                "DAL210, wilco. Climbing to flight level 330.",
            ),
            (
                {"callsign": "SKY55", "command": "turn", "heading": 90, "speaker": "pilot"},
                "SKY55, roger. Turn heading 90 approved.",
            ),
            (
                {"callsign": "SKY55", "command": None, "speaker": "controller"},
                "SKY55, wilco.",
            ),
            (
                {"callsign": None, "command": None, "speaker": None},
                "Aircraft, say again — transmission unclear.",
            ),
        ]

        for parsed, expected in scenarios:
            with self.subTest(parsed=parsed):
                self.assertEqual(_build_controller_response(parsed), expected)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
