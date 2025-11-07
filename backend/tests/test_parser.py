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

    def test_parser_detects_traffic_alert_conflict(self):
        transcript = (
            "Center, DEMO202 flight level three four zero heading two seven zero, "
            "TCAS traffic alert on DEMO101."
        )
        parsed = parse_atc(transcript)

        self.assertEqual(parsed.get("callsign"), "DEMO202")
        self.assertEqual(parsed.get("event"), "traffic_alert")
        self.assertEqual(parsed.get("traffic_callsign"), "DEMO101")
        self.assertEqual(parsed.get("heading"), 270)


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
            (
                {
                    "callsign": "DEMO202",
                    "flight_level": 340,
                    "heading": 270,
                    "speaker": "pilot",
                    "event": "traffic_alert",
                    "traffic_callsign": "DEMO101",
                },
                (
                    "DEMO202, roger. Traffic alert on DEMO101 acknowledged. "
                    "Turn left heading 240 immediately. Descend to flight level 320 for separation. "
                    "We'll ensure DEMO101 maintains clearance. Report clear of conflict."
                ),
            ),
        ]

        for parsed, expected in scenarios:
            with self.subTest(parsed=parsed):
                self.assertEqual(_build_controller_response(parsed), expected)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
