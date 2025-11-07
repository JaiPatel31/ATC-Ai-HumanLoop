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
AIRLINE_PREFIXES = {
    "DELTA": "Delta Air Lines",
    "AMERICAN": "American Airlines",
    "UNITED": "United Airlines",
    "SOUTHWEST": "Southwest Airlines",
    "LUFTHANSA": "Lufthansa",
    "RYANAIR": "Ryanair",
    "EASY": "easyJet",
    "EASYJET": "easyJet",
    "BRITISH": "British Airways",
    "SPEEDBIRD": "British Airways",
    "AIRFRANS": "Air France",
    "AIRFRANCE": "Air France",
    "KLM": "KLM Royal Dutch Airlines",
    "AIRCANADA": "Air Canada",
    "TURKISH": "Turkish Airlines",
    "AUSTRIAN": "Austrian Airlines",
    "SWISS": "Swiss International Air Lines",
    "AEROFLOT": "Aeroflot",
    "EMIRATES": "Emirates",
    "QATAR": "Qatar Airways",
    "QATARI": "Qatar Airways",
    "FINNAIR": "Finnair",
    "CSA": "Czech Airlines",
    "LOT": "LOT Polish Airlines",
    "AIRBERLIN": "Air Berlin",
    "AIRINDIA": "Air India",
    "ETHIOPIAN": "Ethiopian Airlines",
    "OMANAIR": "Oman Air",
    "SINGAPORE": "Singapore Airlines",
    "CATHAY": "Cathay Pacific",
    "JETBLUE": "JetBlue Airways",
    "UPS": "UPS Airlines",
    "FEDEX": "FedEx Express",
    "ALASKA": "Alaska Airlines",
    "SPIRIT": "Spirit Airlines",
    "VUELING": "Vueling Airlines",
    "AIRCARGO": "Air Cargo",
    "NORSHUTTLE": "Norwegian Air Shuttle",
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


# New airport operation keywords
TAXI_KEYWORDS = {"TAXI", "TAXIWAY", "TAXIING", "TAXI TO", "TAXY"}
TAKEOFF_KEYWORDS = {"TAKEOFF", "DEPART", "DEPARTURE", "LINEUP", "LINE", "CLEARED FOR TAKEOFF"}
LANDING_KEYWORDS = {"LAND", "LANDING", "TOUCH", "CLEARED TO LAND", "FINAL", "RUNWAY"}
HOLD_KEYWORDS = {"HOLD", "HOLDING", "HOLD SHORT", "LINE UP AND WAIT", "WAIT"}

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

def _extract_airline(callsign: Optional[str]) -> Optional[str]:
    """Infer airline name from the callsign prefix, if recognizable."""
    if not callsign:
        return None

    for prefix, name in AIRLINE_PREFIXES.items():
        if callsign.startswith(prefix):
            return name
    return None


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

    # Airborne operations
    if token_set & DESCEND_KEYWORDS:
        return "descend"
    if token_set & CLIMB_KEYWORDS:
        return "climb"
    if token_set & MAINTAIN_KEYWORDS:
        return "maintain"
    if token_set & TURN_KEYWORDS or "HEADING" in token_set:
        return "turn"

    # Ground operations
    if token_set & TAXI_KEYWORDS:
        return "taxi"
    if token_set & TAKEOFF_KEYWORDS:
        return "takeoff"
    if token_set & LANDING_KEYWORDS:
        return "land"
    if token_set & HOLD_KEYWORDS:
        return "hold"

    # Requests with embedded intent
    if {"REQUEST", "REQUESTING"} & token_set:
        if token_set & DESCEND_KEYWORDS:
            return "descend"
        if token_set & CLIMB_KEYWORDS:
            return "climb"
        if token_set & MAINTAIN_KEYWORDS:
            return "maintain"
        if token_set & TAXI_KEYWORDS:
            return "taxi"
        if token_set & TAKEOFF_KEYWORDS:
            return "takeoff"
        if token_set & LANDING_KEYWORDS:
            return "land"
        if token_set & HOLD_KEYWORDS:
            return "hold"

    return trend

def _extract_runway_and_taxiway(tokens: list[str]) -> tuple[Optional[str], Optional[str]]:
    runway = None
    taxiway = None

    # Runway numbers — e.g. "RUNWAY TWO FIVE" or "RUNWAY 25"
    for i, t in enumerate(tokens):
        if t == "RUNWAY" and i + 1 < len(tokens):
            num = _digits_from_tokens(tokens[i + 1 : i + 4])
            if num is not None:
                runway = f"{num:02d}"  # format as 02
                break

    # Taxiways — single letters or short alphanumeric names, e.g. "TAXIWAY ALPHA", "VIA A"
    for i, t in enumerate(tokens):
        if t in {"TAXIWAY", "VIA"} and i + 1 < len(tokens):
            nxt = tokens[i + 1]
            if re.fullmatch(r"[A-Z]{1,3}", nxt):
                taxiway = nxt
                break

    return runway, taxiway


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

    if command in {"descend", "climb", "turn", "maintain", "taxi", "takeoff", "land", "hold"}:
        return "controller"
    return "unknown"


def _additional_callsign(tokens: list[str], primary: Optional[str]) -> Optional[str]:
    """Return the first callsign candidate that isn't the primary."""

    if not tokens:
        return None

    def _is_callsign_candidate(token: str) -> bool:
        if token in NON_CALLSIGN_PREFIXES:
            return False
        return bool(re.fullmatch(r"[A-Z]{1,10}\d{1,4}[A-Z]{0,2}", token))

    for token in tokens:
        if not _is_callsign_candidate(token):
            continue
        if primary and token == primary:
            continue
        return token

    return None



def parse_atc(text: str):
    tokens = _tokenize(text)

    # --- Core extractions ---
    callsign = _extract_callsign(tokens)
    airline = _extract_airline(callsign)
    heading = _extract_heading(tokens)
    flight_level, initial_level, target_level = _extract_flight_levels(tokens)

    # ✈️ NEW: runway and taxiway support
    runway, taxiway = _extract_runway_and_taxiway(tokens)

    # --- Detect vertical trend (for climb/descend inference) ---
    trend = None
    if initial_level is not None and target_level is not None:
        if target_level < initial_level:
            trend = "descend"
        elif target_level > initial_level:
            trend = "climb"

    # --- Detect command (now includes taxi/land/takeoff/hold) ---
    command = _detect_command(tokens, trend=trend)
    if command is None and trend is not None:
        command = trend

    # --- Identify likely speaker ---
    speaker = _detect_speaker(tokens, callsign, command)

    # --- Secondary callsign (for traffic alerts or handoffs) ---
    traffic_callsign = _additional_callsign(tokens, callsign)

    # --- Detect special events ---
    event = None
    token_set = set(tokens)
    if (
        ("TCAS" in token_set and "ALERT" in token_set)
        or ("TCAS" in token_set and "TRAFFIC" in token_set)
        or ("TRAFFIC" in token_set and "ALERT" in token_set)
        or "CONFLICT" in token_set
    ):
        event = "traffic_alert"
    elif "RUNWAY" in token_set and "INCURSION" in token_set:
        event = "runway_incursion"
    elif "BIRD" in token_set and "STRIKE" in token_set:
        event = "bird_strike"
    elif "ABORT" in token_set or "REJECTED" in token_set:
        event = "takeoff_abort"

    # --- Return structured result ---
    return {
        "callsign": callsign,
        "airline": airline,  # ✈️ new field
        "heading": heading,
        "flight_level": flight_level,
        "command": command,
        "speaker": speaker,
        "event": event,
        "traffic_callsign": traffic_callsign,
        "runway": runway,
        "taxiway": taxiway,
    }


