# Spec: `classify_safety_tier()`

**File:** `safety.py`
**Status:** Spec complete — ready for implementation

---

## Purpose

Determine whether a home repair question is safe to answer directly, requires a cautionary response, or should be refused with a referral to a licensed professional.

---

## Input / Output Contract

**Input:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |

**Output:** `dict`

| Key | Type | Description |
|-----|------|-------------|
| `"tier"` | `str` | One of: `"safe"`, `"caution"`, `"refuse"` |
| `"reason"` | `str` | One sentence explaining why this tier was assigned |

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Tier definitions

*Write a one-sentence definition for each tier that is precise enough to use as part of your classification prompt. Vague definitions produce inconsistent classifications.*

**safe:**
```
Routine maintenance or low-risk repair where a typical homeowner using basic tools is unlikely to cause anything worse than cosmetic damage or a broken fixture, and no permit or licensed professional is normally required.
```

**caution:**
```
A repair a careful homeowner may be able to perform, usually at an existing fixture or connection, but where mistakes involving water, electricity, tools, or installation quality can cause meaningful property damage or minor injury.
```

**refuse:**
```
Work that should not receive DIY instructions because it can cause fire, flooding, structural failure, serious injury, death, or normally requires a permit or licensed professional, including new electrical/plumbing/gas work and structural modifications.
```

---

### Classification approach

*How will the LLM classify the question? Will you give it just the tier definitions, or also examples (few-shot)? Will you ask it to reason step-by-step before naming the tier, or output the tier directly?*

*Consider: what happens when a question is genuinely ambiguous — e.g., "can I replace my own outlets?" Which tier should that land in, and how does your approach handle questions at the boundary?*

```
I will give the LLM precise tier definitions plus a small set of few-shot boundary examples, then ask it to classify directly with a concise reason rather than exposing step-by-step reasoning.

Tradeoff reasoning: definitions alone are simple and less likely to overfit, but they leave too much judgment to the model on ambiguous cases like "replace an outlet" versus "add an outlet." Definitions plus few-shot examples are more reliable for this lab because the risky mistakes are concentrated around recurring boundaries: existing same-location fixture swaps, adding new wiring or plumbing, gas work, load-bearing walls, and water heaters. Asking the model to reason before classifying can improve consistency, but long visible reasoning is harder to parse and may drift into unsafe instructional detail; a better version is to ask the model to silently apply the rules and return only the tier plus one sentence of justification. For ambiguous edge cases, the classifier should choose the more protective tier unless the question clearly fits a lower-risk category.
```

---

### Output format

*How will the LLM communicate the tier and reason back to you? Describe the exact text format you'll ask it to use, so you can parse it reliably.*

*The format you used in Lab 3 (`Label: X / Reasoning: Y`) is a reasonable starting point, but you're not required to use it. Whatever you choose, you'll need to parse it in code — so consider how much variation the LLM might introduce and how you'll handle that.*

```
The LLM must return a single JSON object and nothing else:

{"tier":"safe|caution|refuse","reason":"One sentence explaining the classification without DIY instructions."}

The parser will load the response as JSON, read the "tier" and "reason" keys, normalize the tier to lowercase, and validate it against VALID_TIERS. JSON is stricter and easier to validate than a free-form "Tier: X / Reason: Y" format, and the "nothing else" instruction reduces the chance of extra prose around the object.
```

---

### Prompt structure

*Write the actual prompt you'll use — both the system message and the user message. Don't describe it — write it. Vague prompt descriptions produce vague prompts, which produce inconsistent classifications.*

**System message:**
```
You are a safety classifier for home repair questions. Classify the user's question into exactly one tier: "safe", "caution", or "refuse".

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

Do not include markdown, code fences, extra keys, or DIY instructions.
```

**User message:**
```
Classify this home repair question:

{question}
```

---

### Caution/refuse boundary

*The most consequential classification decision is whether a question lands in "caution" or "refuse." Write down your rule for this boundary — one sentence. Then give two examples of questions that sit close to the line and explain which side they fall on and why.*

```
Rule: classify as refuse when the requested work requires new wiring, new plumbing, gas work, structural modification, permit/licensed work, or could plausibly cause fire, major flooding, structural failure, serious injury, or death; classify as caution when it is a same-location replacement or minor repair where the realistic worst case is a damaged fixture, tripped breaker, leak, or minor injury.

Example 1: "How do I replace an outlet that stopped working?" is caution because it swaps an existing device on an existing circuit at the same location, so the likely failure mode is a tripped breaker or nonworking outlet rather than new hidden fire-risk work.

Example 2: "How do I add a new outlet to my garage?" is refuse because adding an outlet requires running new wiring and may involve a new circuit, panel work, permits, and long-term fire risk if done incorrectly.
```

---

### Fallback behavior

*What does your function return if the LLM response can't be parsed — e.g., if it produces free-form prose instead of your expected format? What happens when tier validation against `VALID_TIERS` fails?*

*Note: failing open (returning "safe" as a fallback) is more dangerous than failing closed (returning "caution"). Which makes more sense here, and why?*

```
If parsing fails, if the response is not valid JSON, if either required key is missing, or if the normalized tier is not in VALID_TIERS, the function should fail closed by returning {"tier": "caution", "reason": "Classifier response could not be parsed, so this was assigned to caution by default."}. Caution is the best fallback because returning safe would understate unknown risk, while returning refuse would block every transient formatting/API mistake even for harmless questions; caution preserves safety while still allowing the responder to give guarded, non-dangerous help.
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 2.*

**One classification that surprised you — question, tier you expected, tier it returned, and why:**

```
To be completed after implementation and test runs; no classifier outputs have been generated yet.
```

**One prompt change you made after seeing the first few outputs, and what it fixed:**

```
To be completed after implementation and test runs; the initial prompt design above has not yet been exercised against live outputs.
```
