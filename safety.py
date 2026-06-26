import json

from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, VALID_TIERS

_client = Groq(api_key=GROQ_API_KEY)

FALLBACK_RESULT = {
    "tier": "caution",
    "reason": "Classifier response could not be parsed, so this was assigned to caution by default.",
}

SYSTEM_PROMPT = """You are a safety classifier for home repair questions. Classify the user's question into exactly one tier: "safe", "caution", or "refuse".

Tier definitions:
- safe: Routine maintenance or low-risk repair where a typical homeowner using basic tools is unlikely to cause anything worse than cosmetic damage or a broken fixture, and no permit or licensed professional is normally required.
- caution: A repair a careful homeowner may be able to perform, usually at an existing fixture or connection, but where mistakes involving water, electricity, tools, or installation quality can cause meaningful property damage or minor injury.
- refuse: Work that should not receive DIY instructions because it can cause fire, flooding, structural failure, serious injury, death, or normally requires a permit or licensed professional, including new electrical/plumbing/gas work and structural modifications.

Boundary rules:
- Replacing an existing electrical device, fixture, faucet, toilet part, thermostat, ceiling fan, or showerhead in the same location is usually caution.
- Adding a new outlet, switch, circuit, electrical run, plumbing line, gas line, or appliance connection is refuse.
- Electrical panel work, service entrance work, breakers, gas work, gas odors, main water shutoff replacement, water heater replacement, structural wall removal, foundation work, and structural roof repair are refuse.
- Removing a wall is refuse unless the user states that a structural engineer has confirmed it is non-load-bearing.
- Small-sounding changes are still refuse if they require new wiring, new pipe, gas work, panel work, or structural modification.
- If the question is ambiguous, choose the more protective tier that fits the likely work; do not classify as safe unless it is clearly low-risk.

Examples:
- "How do I replace an outlet that stopped working?" -> caution, because it is a same-location swap on an existing circuit.
- "How do I add a new outlet in my garage?" -> refuse, because it requires new wiring or circuit work and may involve the panel and permits.
- "Can I replace a light switch with a dimmer in the same box?" -> caution, because it is replacing an existing switch at the same location.
- "Can I move a light switch six inches?" -> refuse, because moving it requires new wiring even though the distance sounds small.
- "How do I replace my furnace gas valve?" -> refuse, because gas work can cause explosion, fire, or carbon monoxide poisoning.
- "How do I replace a showerhead?" -> caution, because it is a fixture replacement involving water but not new plumbing lines.

Return only a valid JSON object in this exact shape:
{"tier":"safe|caution|refuse","reason":"One sentence explaining why this tier was assigned."}

Do not include markdown, code fences, extra keys, or DIY instructions."""


def _parse_classifier_response(raw_text: str) -> dict:
    try:
        parsed = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return FALLBACK_RESULT.copy()

    if not isinstance(parsed, dict):
        return FALLBACK_RESULT.copy()

    tier = str(parsed.get("tier", "")).strip().lower()
    reason = str(parsed.get("reason", "")).strip()

    if tier not in VALID_TIERS or not reason:
        return FALLBACK_RESULT.copy()

    return {"tier": tier, "reason": reason}


def classify_safety_tier(question: str) -> dict:
    """
    Classify a home repair question into one of three safety tiers.

    TODO — Milestone 1:

    Before writing any code, complete specs/classifier-spec.md. The blank fields
    there are the decisions that drive this implementation — prompt design, tier
    definitions, output format, and edge case handling.

    Your implementation should:
      1. Build a prompt using your tier definitions that asks the LLM to classify
         the question and explain its reasoning
      2. Send a single chat completion request (no tools, no history)
      3. Parse the tier and reason out of the raw response text
      4. Validate the tier against VALID_TIERS; fall back to "caution" if the
         response can't be parsed or the tier isn't recognized
      5. Return {"tier": ..., "reason": ...}

    Returns a dict with:
      - "tier"   : str — one of "safe", "caution", "refuse"
      - "reason" : str — a brief explanation of why this tier was assigned

    The three tiers:
      - "safe"    : routine, low-risk repairs most homeowners can handle safely
      - "caution" : doable with care, but mistakes have real cost or mild risk
      - "refuse"  : high-risk repairs that require a licensed professional —
                    mistakes can cause fire, flooding, injury, or structural damage
    """
    user_prompt = f"""Classify this home repair question:

{question}"""

    try:
        completion = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
    except Exception:
        return FALLBACK_RESULT.copy()

    raw_text = completion.choices[0].message.content
    return _parse_classifier_response(raw_text)
