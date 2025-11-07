import re

ICAO_ALPHABET = {
    "A":"Alpha","B":"Bravo","C":"Charlie","D":"Delta","E":"Echo","F":"Foxtrot",
    "G":"Golf","H":"Hotel","I":"India","J":"Juliett","K":"Kilo","L":"Lima",
    "M":"Mike","N":"November","O":"Oscar","P":"Papa","Q":"Quebec","R":"Romeo",
    "S":"Sierra","T":"Tango","U":"Uniform","V":"Victor","W":"Whiskey","X":"X-ray",
    "Y":"Yankee","Z":"Zulu",
    "0":"Zero","1":"One","2":"Two","3":"Three","4":"Four",
    "5":"Five","6":"Six","7":"Seven","8":"Eight","9":"Nine"
}
NUM_WORDS = {"ZERO","ONE","TWO","THREE","FOUR","FIVE","SIX","SEVEN","EIGHT","NINE","NINER"}

def expand_callsign(cs: str) -> str:
    return " ".join(ICAO_ALPHABET.get(ch, ch) for ch in cs.upper())

def replace_callsign_at_start(transcript: str, callsign: str | None) -> str:
    """
    If transcript starts with a callsign in word/numeric form, replace that segment
    with ICAO-phonetic expansion of `callsign`. Handles:
      'CSA ZERO TWO FIVE ...'  -> 'Charlie Sierra Alpha Zero Two Five ...'
      'CSA 025 ...'           -> 'Charlie Sierra Alpha Zero Two Five ...'
      'CSA025 ...'            -> 'Charlie Sierra Alpha Zero Two Five ...'
    """
    if not transcript or not callsign:
        return transcript

    t = transcript.strip()
    tokens = t.split()
    if not tokens:
        return transcript

    cs = callsign.upper()
    m = re.match(r"^([A-Z]{2,3})(\d{1,4})$", cs)
    if not m:
        return transcript
    prefix, digits = m.group(1), m.group(2)

    # Only proceed if the first token starts with the callsign prefix (e.g., 'CSA')
    if not tokens[0].upper().startswith(prefix):
        return transcript

    # Consume following tokens that represent the numeric part of the callsign
    i = 1
    consumed = 0
    while i < len(tokens):
        tk = tokens[i].upper()
        if tk.isdigit():
            consumed += 1
            i += 1
            continue
        if tk in NUM_WORDS:
            consumed += 1
            i += 1
            continue
        break

    # Also handle compact form 'CSA025' as the very first token
    if tokens[0].upper() == cs:
        consumed = 0  # all in first token

    phonetic = expand_callsign(cs)
    # replace first token + any consumed numeric-word tokens
    new_tokens = [phonetic] + tokens[1 + consumed:]
    return " ".join(new_tokens)

def expand_callsign_inline(text: str, callsign: str | None) -> str:
    """
    Replace the callsign inside a full sentence with ICAO phonetic words.
    e.g. "CSA025, wilco. Descending..." →
         "Charlie Sierra Alpha Zero Two Five, wilco. Descending..."
    """
    if not text or not callsign:
        return text
    return text.replace(callsign, expand_callsign(callsign))
