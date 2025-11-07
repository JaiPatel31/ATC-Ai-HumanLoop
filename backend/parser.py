import re
from typing import Iterable, Optional

NUM_WORDS = {
    "ZERO": "0",
    "ONE": "1",
    "TWO": "2",
    "THREE": "3",
    "FOUR": "4",
    "FIVE": "5",
    "SIX": "6",
    "SEVEN": "7",
    "EIGHT": "8",
    "NINE": "9",
    "NINER": "9",
    "TEN": "10",
    "ELEVEN": "11",
    "TWELVE": "12",
    "THIRTEEN": "13",
    "FOURTEEN": "14",
    "FIFTEEN": "15",
    "SIXTEEN": "16",
    "SEVENTEEN": "17",
    "EIGHTEEN": "18",
    "NINETEEN": "19",
    "TWENTY": "20",
    "THIRTY": "30",
    "FORTY": "40",
    "FIFTY": "50",
    "SIXTY": "60",
    "SEVENTY": "70",
    "EIGHTY": "80",
    "NINETY": "90",
}

DESCEND_KEYWORDS = {
    "DESCEND",
    "DESCENDING",
    "DESCENT",
    "DOWN",
}

CLIMB_KEYWORDS = {
    "CLIMB",
    "CLIMBING",
    "ASCEND",
    "ASCENDING",
    "UP",
}

MAINTAIN_KEYWORDS = {
    "MAINTAIN",
    "MAINTAINING",
    "HOLD",
    "HOLDING",
    "KEEP",
    "KEEPING",
}

TURN_KEYWORDS = {
    "TURN",
    "TURNING",
    "VECTOR",
}

PILOT_MARKERS = {
    "REQUEST",
    "REQUESTING",
    "ROGER",
    "WILCO",
    "CHECKING",
    "REPORTING",
    "LEAVING",
    "CLIMBING",
    "DESCENDING",
    "MAINTAINING",
    "PASSING",
    "READY",
    "DEPARTING",
    "ESTABLISHED",
}

NON_CALLSIGN_PREFIXES = {
    "FL",
    "FLIGHT",
    "LEVEL",
    "HEADING",
    "HDG",
    "MAINTAIN",
    "MAINTAINING",
    "DESCEND",
    "DESCENDING",
    "CLIMB",
    "CLIMBING",
    "TURN",
    "TURNING",
    "REQUEST",
    "REQUESTING",
    "CENTER",
    "TOWER",
    "GROUND",
    "APPROACH",
    "DEPARTURE",
    "CONTACT",
    "WITH",
    "PASSING",
    "LEAVING",
    "REPORTING",
}

NON_CALLSIGN_PREFIXES |= set(NUM_WORDS.keys())


def _tokenize(text: str) -> list[str]:
    cleaned = text.upper().replace("-", " ")
    cleaned = re.sub(r"[^A-Z0-9\s]", " ", cleaned)
    tokens = [t for t in cleaned.split() if t]
    return tokens


def _digits_from_tokens(words: Iterable[str], *, min_digits: int = 1) -> Optional[int]:
    digits: list[str] = []
    for word in words:
        if word in NUM_WORDS:
            digits.append(NUM_WORDS[word])
        elif word.isdigit():
            digits.append(word)
        else:
            match = re.fullmatch(r"(FL)?(\d+)[A-Z]?", word)
            if match:
                digits.append(match.group(2))
            else:
                break
    if not digits:
        return None
    number = "".join(digits)
    if len(number) < min_digits:
        return None
    return int(number)


def _extract_callsign(tokens: list[str]) -> Optional[str]:
    for token in tokens:
        match = re.fullmatch(r"[A-Z]{1,10}\d{1,4}[A-Z]{0,2}", token)
        if match:
            prefix_match = re.match(r"^[A-Z]+", token)
            prefix = prefix_match.group(0) if prefix_match else ""
            if prefix in NON_CALLSIGN_PREFIXES:
                continue
            return token

    best_candidate: Optional[str] = None
    best_prefix_len = 0
    for idx, token in enumerate(tokens):
        if token in NON_CALLSIGN_PREFIXES:
            continue
        if not re.fullmatch(r"[A-Z]{2,9}", token):
            continue

        number_tokens = (t for t in tokens[idx + 1 : idx + 6] if t not in {"FLIGHT", "LEVEL"})
        number = _digits_from_tokens(number_tokens, min_digits=1)
        if number is None:
            continue

        candidate = f"{token}{number}"
        prefix_len = len(token)
        if prefix_len > best_prefix_len:
            best_candidate = candidate
            best_prefix_len = prefix_len

    # Attempt to combine adjacent tokens such as "AIR CANADA" before the number.
    for idx in range(len(tokens) - 1):
        first = tokens[idx]
        if first in NON_CALLSIGN_PREFIXES or not re.fullmatch(r"[A-Z]{2,9}", first):
            continue
        combined = first
        for next_idx in range(idx + 1, min(idx + 3, len(tokens))):
            second = tokens[next_idx]
            if second in NON_CALLSIGN_PREFIXES or not re.fullmatch(r"[A-Z]{2,9}", second):
                break
            combined += second
            number_tokens = (
                t for t in tokens[next_idx + 1 : next_idx + 6] if t not in {"FLIGHT", "LEVEL"}
            )
            number = _digits_from_tokens(number_tokens, min_digits=1)
            if number is not None and len(combined) > best_prefix_len:
                best_candidate = f"{combined}{number}"
                best_prefix_len = len(combined)

    return best_candidate


def _extract_heading(tokens: list[str]) -> Optional[int]:
    for idx, token in enumerate(tokens):
        if token == "HEADING":
            number = _digits_from_tokens(tokens[idx + 1 : idx + 4], min_digits=2)
            if number is not None:
                return number
        match = re.fullmatch(r"(HDG|HEADING)(\d{2,3})", token)
        if match:
            return int(match.group(2))

    for idx, token in enumerate(tokens):
        if token == "TURN":
            number = _digits_from_tokens(tokens[idx + 1 : idx + 4], min_digits=2)
            if number is not None:
                return number
    return None


def _extract_flight_levels(tokens: list[str]) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """Return (flight_level, initial_level, target_level)."""
    flight_level = None
    initial_level = None
    target_level = None

    for token in tokens:
        match = re.fullmatch(r"FL(\d{2,3})", token)
        if match:
            flight_level = int(match.group(1))
            break

    if flight_level is None:
        if "FLIGHT" in tokens and "LEVEL" in tokens:
            idx = tokens.index("LEVEL") + 1
            candidate = _digits_from_tokens(tokens[idx : idx + 4], min_digits=2)
            if candidate is not None:
                flight_level = candidate

    if flight_level is None and "LEVEL" in tokens:
        idx = tokens.index("LEVEL") + 1
        candidate = _digits_from_tokens(tokens[idx : idx + 4], min_digits=2)
        if candidate is not None:
            flight_level = candidate

    if "LEAVING" in tokens and "FOR" in tokens:
        leave_idx = tokens.index("LEAVING")
        initial_tokens = (
            t for t in tokens[leave_idx + 1 : leave_idx + 6] if t not in {"FLIGHT", "LEVEL"}
        )
        initial = _digits_from_tokens(initial_tokens, min_digits=2)
        for_idx = tokens.index("FOR", leave_idx)
        target_tokens = (
            t for t in tokens[for_idx + 1 : for_idx + 6] if t not in {"FLIGHT", "LEVEL"}
        )
        target = _digits_from_tokens(target_tokens, min_digits=2)
        if initial is not None:
            initial_level = initial
        if target is not None:
            target_level = target
            flight_level = target

    return flight_level, initial_level, target_level


def _detect_command(tokens: list[str], *, trend: Optional[str]) -> Optional[str]:
    token_set = set(tokens)

    if token_set & DESCEND_KEYWORDS:
        return "descend"
    if token_set & CLIMB_KEYWORDS:
        return "climb"
    if token_set & MAINTAIN_KEYWORDS:
        return "maintain"
    if {"REQUEST", "REQUESTING"} & token_set:
        if token_set & DESCEND_KEYWORDS:
            return "descend"
        if token_set & CLIMB_KEYWORDS:
            return "climb"
        if token_set & MAINTAIN_KEYWORDS:
            return "maintain"
    if token_set & TURN_KEYWORDS or "HEADING" in token_set:
        return "turn"
    return trend


def _detect_speaker(tokens: list[str], callsign: Optional[str], command: Optional[str]) -> str:
    if not tokens:
        return "unknown"

    first = tokens[0]
    pilot_starts = {
        "DESCEND",
        "CLIMB",
        "MAINTAIN",
        "TURN",
        "REQUEST",
        "REQUESTING",
        "CHECKING",
        "REPORTING",
        "LEAVING",
        "CLIMBING",
        "DESCENDING",
        "MAINTAINING",
        "PASSING",
        "READY",
    }

    if first in pilot_starts:
        return "pilot"

    tokens_set = set(tokens)
    if tokens_set & PILOT_MARKERS:
        return "pilot"
    if "WITH" in tokens_set and "YOU" in tokens_set:
        return "pilot"

    if callsign:
        prefix_match = re.match(r"^[A-Z]+", callsign)
        prefix = prefix_match.group(0) if prefix_match else ""
        if prefix and tokens[0].startswith(prefix):
            return "controller"

    if command in {"descend", "climb", "turn", "maintain"}:
        return "controller"
    return "unknown"


def parse_atc(text: str):
    tokens = _tokenize(text)

    callsign = _extract_callsign(tokens)
    heading = _extract_heading(tokens)
    flight_level, initial_level, target_level = _extract_flight_levels(tokens)

    trend = None
    if initial_level is not None and target_level is not None:
        if target_level < initial_level:
            trend = "descend"
        elif target_level > initial_level:
            trend = "climb"

    command = _detect_command(tokens, trend=trend)

    if command is None and trend is not None:
        command = trend

    speaker = _detect_speaker(tokens, callsign, command)

    return {
        "callsign": callsign,
        "heading": heading,
        "flight_level": flight_level,
        "command": command,
        "speaker": speaker,
    }
