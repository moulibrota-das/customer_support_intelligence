# Presentation Brief: Customer Support Intelligence

**For:** Claude Design (to build the slide deck)
**Audience:** Mentors / technical reviewers (AI + software engineering). They want to see that we understood the problem and chose a sound technique, not a product demo.
**Format:** 5 slides, 16:9. Target about 5 minutes of speaking (about 1 minute per slide).
**Tone:** Clear, confident, engineering-minded. Short phrases, no paragraphs on slides. Honest about status.

---

## Design direction

- Clean, modern, light theme; one accent colour for **LLM steps** (blue) and a second for **code/rules steps** (green or grey). Use this colour code consistently across slides, since the "LLM only where needed" idea is the core message.
- Heavy use of visuals: the pipeline flow (slide 3) is the hero visual. Icons per step are welcome.
- Max about 40 words per slide in the body. Details go in speaker notes.
- Existing diagrams to reuse or redraw in the deck's style: `docs/diagrams/data_flow.png`, `docs/diagrams/architecture.png` (SVG and Mermaid sources are in the same folder).
- Do **not** invent metrics. The project has no evaluation results yet. The only real measurement is one smoke run (see slide 5).

---

## Slide 1: Problem Statement

**Title:** One message. Many problems. Hours of agent time.

**On-slide copy:**
- A company gets hundreds of support messages a day.
- A single message can mix: a problem + product details + several questions + urgency + frustration + refund or escalation demands.
- Agents spend their time reading, triaging, and drafting replies instead of solving.

**Goal (highlight box):** Turn one raw message into a structured triage result: **Intent · Urgency · Key Info · Recommended Action · Escalation · Draft Reply · Evidence**

**Visual idea:** A messy customer email on the left (angry, multi-topic, e.g. *"My order #45821 never arrived, I've emailed twice, I want a refund or I'm calling my lawyer. Email me at …"*) with arrows to the 7 structured output fields on the right.

**Speaker notes:** Emphasise that the system *recommends* and a human agent decides. We do not auto-send replies or auto-approve refunds.

---

## Slide 2: What "Good" Means (Our Understanding)

**Title:** Four principles that shaped every design choice

| Principle | Short copy |
|---|---|
| 🚨 Never miss an escalation | Legal threats, safety issues, angry repeat customers. A missed escalation is worse than an extra one. |
| 🚫 Never invent facts | No made-up order numbers, refund amounts, timelines or policies in the reply. |
| 🔍 Every decision is explainable | Each output carries the quote, signal or rule that produced it. |
| 🤷 Say "I'm not sure" | Vague, spam, sarcastic, non-English or manipulative messages go to a human instead of being guessed. |

**Bottom line (one sentence):** *Accuracy of intent matters, but trust matters more.*

**Speaker notes:** These are our interpretation of the problem; the brief only asks for triage and a draft. We chose to optimise for safety (recall on escalation, no hallucination) over raw fluency. This is why the architecture is not "one big prompt".

---

## Slide 3: Solution Approach: a Chain of Small Steps

**Title:** Not one giant prompt: 8 small steps, LLM only where language understanding is needed

**Hero visual (pipeline, left to right or top to bottom). Colour-code LLM vs Code vs Rules:**

| # | Step | Type | One-line job |
|---|---|---|---|
| 0 | Preprocess | Code | Clean text, skip garbage, **mask PII**, regex out order IDs / amounts / dates, flag prompt injection |
| 1 | Classify | **LLM** | Intents, sentiment, frustration, language, confidence |
| 2 | Extract | **LLM** | Product, issue, questions, requested outcome, risk signals, each with a verbatim quote |
| 3 | Verify | Code | Schema check, retry once, confirm every quote really exists in the message |
| 4 | Decide | Rules (YAML) | Urgency, escalation, action, human-review flag |
| 5 | Draft reply | **LLM** | Polite reply using only verified facts + written policies |
| 6 | Check draft | Code | No new IDs/amounts/dates; every question answered |
| 7 | Assemble | Code | Final output + reasoning/evidence |

Show Steps 1 and 2 **in parallel** (they don't depend on each other). Show a "Safe fallback → needs human review" side path from Steps 0 and 6.

**Callout:** 3 LLM calls per message, 2 of them concurrent.

**Why this split (small caption under the diagram):** Exact answers (IDs, amounts, quote checks) → code. Meaning (intent, sarcasm, tone, writing) → LLM. Business decisions → auditable rules.

**Status chip:** Steps 0, 1, 2, 5 built · Steps 3, 4, 6, 7 in progress.

**Speaker notes:** The hard constraint was no single giant prompt. The split also makes every step independently testable and swappable.

---

## Slide 4: Techniques That Make It Trustworthy

**Title:** Techniques: how we get reliable output from an unreliable model

Use a 2x3 grid of cards: icon, bold name, one line.

1. **Structured output** — Pydantic models generate the JSON schema sent to Gemini; the format is enforced by the API, so prompts focus on meaning. Output is still validated, with one retry that shows the model its own validation error.
2. **PII masking before the LLM** — Cards (Luhn-validated), emails, phones become `[CARD_1]`, `[EMAIL_1]`; the LLM never sees them. The placeholder map stays in memory and restores email/phone in the draft. Card numbers are never restored.
3. **Evidence-grounded extraction** — Every extracted value must carry a verbatim quote; code verifies it is a substring of the message, so hallucinated evidence is caught exactly.
4. **LLM supplies signals, rules decide** — Escalation, urgency, and actions come from `rules.yaml`, so they are predictable, auditable and editable by non-engineers. This is also the main **prompt-injection defence**: no LLM output can directly trigger a refund or escalation.
5. **Hallucination guard on the draft** — The draft gets a code-built facts block plus mock company policies. Afterwards a regex check rejects any order ID, amount or date not in the input.
6. **Versioned prompts + measured iteration** — Prompts live in `prompts/<step>_<version>.md`. V1 is deliberately minimal as a baseline; every later change must fix an observed failure.

**Small footer chips:** Prompt-injection flag (flag, not block) · 5,000-char input cap · Fail fast on 429 quota errors · Errors returned, never raised → always a result

**Speaker notes:** If time is short, pick techniques 2, 3 and 4. The "rules decide, LLM only signals" design is the strongest answer to safety questions from mentors.

---

## Slide 5: Status, Early Evidence & Next Steps

**Title:** Where we are: Milestone 2 of 8

**Left: Progress tracker (visual stepper):**
- ✅ 1. Schemas + preprocessing (43 unit tests)
- ✅ 2. LLM client + Classify / Extract / Draft (V1 prompts) + CLI (12 tests)
- ⬜ 3. Rules engine (`rules.yaml`)
- ⬜ 4. Validation, retry, hallucination checks, fallback
- ⬜ 5. Labeled test set (≥25 cases) + evaluation runner
- ⬜ 6. Prompt iterations (V1 → V2 → final)
- ⬜ 7. Streamlit demo app (basic version already works)
- ⬜ 8. Final docs pass

**Right: Early evidence (single smoke run, label it clearly as "one example, not a benchmark"):**
- Correct intent (`delivery`; secondary `refund`, `complaint`), frustration high, verbatim evidence quotes
- Both customer questions and both risk signals (`repeat_contact`, `legal_threat`) found
- ~5.3 s end to end, ~1,345 tokens in / ~515 out (`gemini-3.5-flash`, thinking `low`)
- 55 offline unit tests pass

**Honest findings from V1 (shows rigour; present as "what evaluation will fix"):**
- Extract put an order ID in `product`; a quote didn't support its value
- Draft applied the return-refund policy to a never-delivered order
→ these motivate the verification step, rules engine and prompt V2

**Plan to measure:** intent accuracy, urgency accuracy, **escalation recall (priority)**, extraction accuracy, valid-JSON rate, hallucination rate, consistency (3 runs/case), latency and cost.

**Tech stack strip (bottom):** Python · Google Gemini (`google-genai`) · Pydantic v2 · YAML rules · Streamlit · pytest

**Speaker notes:** Be upfront that evaluation numbers do not exist yet and we will only report real runs. Known constraint: free-tier Gemini quota is about 20 requests/model/day (3 per message), so full evaluation needs a paid key or multi-day runs. This is an open decision to raise with mentors.

---

## Optional appendix (only if the deck allows)

- Data-flow diagram showing that only the three LLM steps send data to Google, and only masked text.
- Example output card for the sample message in slide 1.

## Team / footer

Team members: *<fill in>* · Repo: Customer Support Intelligence · Live URL: not deployed
