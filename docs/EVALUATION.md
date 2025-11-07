# Evaluation playbook

This repository now bundles a compact quality harness so you can reason about the
ATC parser's behaviour and communicate results with stakeholders.

## Dataset

The curated samples in `backend/evaluation.py` cover controller directives and
pilot readbacks that frequently appear in en-route sectors:

| Transcript highlight | Purpose | Expected fields |
| --- | --- | --- |
| "request climb flight level three three zero heading one eight zero" | Mixed command + heading request | callsign, command, flight_level, heading, speaker |
| "descend and maintain flight level two four zero" | Compound descend/maintain phrasing | callsign, command, flight_level, speaker |
| "maintain present heading" | Maintaining instructions without new headings | callsign, command, flight_level, speaker |
| "leaving flight level three three zero for two seven zero" | Trend-based command inference | callsign, command, flight_level, speaker |
| "turn right heading zero niner zero" | Heading extraction with ICAO phonetics | callsign, command, heading, speaker |
| "maintain two five zero knots" | Speed assignment implying maintain command | callsign, command, speaker |

Feel free to append additional `Sample` instances if you uncover new edge cases.

## Running the scorecard

```bash
python backend/evaluation.py
```

The script prints a compact accuracy table (correct/total per field plus an
overall rate) and lists any misclassifications along with analyst notes so
regression triage is quick.

## Continuous verification

`python -m unittest discover backend/tests` exercises the same corpus to guard
against regressions in both the parser and the controller-response templates. These tests run quickly
and can be wired into CI to block merges that degrade accuracy.

## Operational monitoring

The FastAPI service now exposes `GET /health`, which surfaces:

* STT availability and the configured Hugging Face checkpoint
* TTS availability, loaded voices, and supported speaker profiles
* Snapshot parser accuracy (mirroring `evaluation.py`)

Dashboards or smoke tests can hit this endpoint to ensure the loop is ready
before controllers rely on it.
