"""Utility helpers to measure parser accuracy against curated ATC transcripts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, MutableMapping

from parser import parse_atc


@dataclass(frozen=True)
class Sample:
    """Container for an evaluated transmission."""

    transcript: str
    expected: Mapping[str, object]
    notes: str | None = None


SAMPLE_TRANSMISSIONS: list[Sample] = [
    Sample(
        transcript="Delta two one zero request climb flight level three three zero heading one eight zero",
        expected={
            "callsign": "DELTA210",
            "command": "climb",
            "flight_level": 330,
            "heading": 180,
            "speaker": "pilot",
        },
        notes="Typical pilot request mixing phonetic numbers and heading information.",
    ),
    Sample(
        transcript="Speedbird four zero five descend and maintain flight level two four zero",
        expected={
            "callsign": "SPEEDBIRD405",
            "command": "descend",
            "flight_level": 240,
            "speaker": "controller",
        },
        notes="Controller instruction with combined descend + maintain phraseology.",
    ),
    Sample(
        transcript="November seven one tango maintain present heading and flight level three zero zero",
        expected={
            "callsign": "NOVEMBER71",
            "command": "maintain",
            "flight_level": 300,
            "speaker": "controller",
        },
        notes="General aviation tail number that omits an explicit numeric suffix.",
    ),
    Sample(
        transcript="Atlas six one five leaving flight level three three zero for two seven zero",
        expected={
            "callsign": "ATLAS615",
            "command": "descend",
            "flight_level": 270,
            "speaker": "pilot",
        },
        notes="Pilot readback announcing a continuous descent with start/target levels.",
    ),
    Sample(
        transcript="Air Canada eight ninety turn right heading zero niner zero",
        expected={
            "callsign": "AIRCANADA890",
            "command": "turn",
            "heading": 90,
            "speaker": "controller",
        },
        notes="Controller turn instruction using ICAO 'niner' pronunciation.",
    ),
    Sample(
        transcript="United 441 maintain two five zero knots, request higher when able",
        expected={
            "callsign": "UNITED441",
            "command": "maintain",
            "speaker": "pilot",
        },
        notes="Speed assignment with implied maintain command and no new flight level.",
    ),
]


def evaluate(samples: Iterable[Sample] = SAMPLE_TRANSMISSIONS) -> dict[str, object]:
    """Return aggregate accuracy metrics for the parser fields."""

    totals: MutableMapping[str, int] = {"overall": 0}
    correct: MutableMapping[str, int] = {"overall": 0}
    mistakes: list[dict[str, object]] = []

    for sample in samples:
        parsed = parse_atc(sample.transcript)
        for field, expected_value in sample.expected.items():
            totals[field] = totals.get(field, 0) + 1
            totals["overall"] += 1

            observed = parsed.get(field)
            if observed == expected_value:
                correct[field] = correct.get(field, 0) + 1
                correct["overall"] += 1
            else:
                mistakes.append(
                    {
                        "transcript": sample.transcript,
                        "field": field,
                        "expected": expected_value,
                        "observed": observed,
                        "notes": sample.notes,
                    }
                )

    metrics: dict[str, object] = {"totals": dict(totals), "correct": dict(correct)}
    accuracy: MutableMapping[str, float] = {}
    for field, total in totals.items():
        if total:
            accuracy[field] = round(correct.get(field, 0) / total, 3)
    metrics["accuracy"] = dict(accuracy)
    metrics["mistakes"] = mistakes
    return metrics


def _format_accuracy_report(metrics: Mapping[str, object]) -> str:
    totals = metrics["totals"]
    correct = metrics["correct"]
    accuracy = metrics["accuracy"]

    lines = ["Field        Correct / Total    Accuracy"]
    lines.append("----------------------------------------")
    for field in sorted(k for k in totals.keys() if k != "overall"):
        lines.append(
            f"{field:<12} {correct.get(field, 0):>3} / {totals[field]:<3}      {accuracy.get(field, 0):>6.1%}"
        )
    lines.append("----------------------------------------")
    lines.append(
        f"{'overall':<12} {correct.get('overall', 0):>3} / {totals['overall']:<3}      {accuracy.get('overall', 0):>6.1%}"
    )
    return "\n".join(lines)


def generate_report(samples: Iterable[Sample] = SAMPLE_TRANSMISSIONS) -> str:
    """Generate a plain-text scorecard of parser accuracy."""

    metrics = evaluate(samples)
    report = ["ATC parser evaluation", "=======================", "", _format_accuracy_report(metrics)]

    mistakes = metrics["mistakes"]
    if mistakes:
        report.append("")
        report.append("Misclassifications:")
        for mistake in mistakes:
            report.append(
                "- {field} → expected {expected!r} but observed {observed!r} for '{transcript}'".format(
                    **mistake
                )
            )
            if mistake.get("notes"):
                report.append(f"    note: {mistake['notes']}")
    else:
        report.append("")
        report.append("No misclassifications detected.")

    return "\n".join(report)


if __name__ == "__main__":
    print(generate_report())
