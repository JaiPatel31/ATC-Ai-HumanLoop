import re

NUM_WORDS = {
    "ZERO": "0", "ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4",
    "FIVE": "5", "SIX": "6", "SEVEN": "7", "EIGHT": "8", "NINE": "9", "NINER": "9"
}

def words_to_number(words):
    """Converts ['THREE','ONE','FIVE'] -> 315"""
    digits = [NUM_WORDS.get(w, "") for w in words if w in NUM_WORDS]
    return int("".join(digits)) if digits else None


def parse_atc(text: str):
    text = text.upper().replace("-", " ")
    tokens = text.split()

    # --- Extract callsign prefix and digits ---
    callsign = None
    for i, token in enumerate(tokens):
        if re.match(r"^[A-Z]{2,3}$", token):
            num_block = []
            for w in tokens[i+1:i+5]:
                if w in NUM_WORDS:
                    num_block.append(w)
                else:
                    break
            if num_block:
                callsign = f"{token}{words_to_number(num_block):03d}"
            else:
                callsign = token
            break

    # --- Extract heading ---
    heading = None
    if "HEADING" in tokens:
        idx = tokens.index("HEADING") + 1
        heading = words_to_number(tokens[idx:idx+3])

    # --- Extract flight level ---
    flight_level = None
    if "FLIGHT" in tokens and "LEVEL" in tokens:
        idx = tokens.index("LEVEL") + 1
        flight_level = words_to_number(tokens[idx:idx+3])

    # --- Command type ---
    command = None
    if "DESCEND" in tokens:
        command = "descend"
    elif "CLIMB" in tokens:
        command = "climb"
    elif "TURN" in tokens or "HEADING" in tokens:
        command = "turn"
    elif "MAINTAIN" in tokens:
        command = "maintain"

    # --- Determine likely speaker ---
    # Heuristic: if the phrase *includes the callsign first* and a verb like 'DESCEND'/'CLIMB'/'TURN',
    # it's likely the controller issuing the command.
    # If it *starts directly with the verb*, it's likely the pilot reporting/requesting.
    speaker = None
    first_token = tokens[0] if tokens else ""
    if first_token in ("DESCEND", "CLIMB", "MAINTAIN", "TURN"):
        speaker = "pilot"
    elif callsign and first_token.startswith(callsign[:3]):
        speaker = "controller"
    else:
        speaker = "unknown"

    return {
        "callsign": callsign,
        "heading": heading,
        "flight_level": flight_level,
        "command": command,
        "speaker": speaker
    }
