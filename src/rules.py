"""Step 4 - Decide (rules, no LLM).

Maps signals + intent + frustration + amounts + flags to urgency, escalation, action and a
human-review flag using src/rules.yaml. Every rule that fires is recorded (the audit trail).
"""

import time
from functools import lru_cache

import yaml

from src import config
from src.schemas import (URGENCY_ORDER, ClassificationResult, Decision, ExtractionResult,
                         PreprocessResult, StepTrace, Urgency)


@lru_cache(maxsize=1)
def load_rules() -> dict:
    return yaml.safe_load(config.RULES_PATH.read_text(encoding="utf-8"))


def _matches(when: dict, ctx: dict) -> bool:
    for key, want in when.items():
        if key == "signals" and not set(want) & ctx["signals"]:
            return False
        if key == "intent" and not set(want) & ctx["intents"]:
            return False
        if key == "frustration" and ctx["frustration"] not in want:
            return False
        if key == "flags" and not set(want) & ctx["flags"]:
            return False
        if key == "min_amount" and ctx["max_amount"] < want:
            return False
        if key == "sarcastic" and ctx["sarcastic"] != want:
            return False
        if key == "max_confidence" and ctx["confidence"] >= want:
            return False
        if key == "has_deadline" and ctx["has_deadline"] != want:
            return False
    return True


def decide(pre: PreprocessResult, cls: ClassificationResult,
           ext: ExtractionResult) -> tuple[Decision, StepTrace]:
    start = time.perf_counter()
    rules = load_rules()
    ctx = {
        "signals": {s.type.value for s in ext.signals},
        "intents": {cls.primary_intent.value, *(i.value for i in cls.secondary_intents)},
        "frustration": cls.frustration.value,
        "flags": set(pre.flags),
        "max_amount": max((a.value for a in pre.identifiers.amounts), default=0.0),
        "sarcastic": cls.is_sarcastic,
        "confidence": cls.confidence,
        "has_deadline": ext.deadline is not None,
    }

    fired: list[str] = []
    urgency = Urgency(rules["urgency_base"])
    for r in rules["urgency_rules"]:
        if _matches(r["when"], ctx):
            fired.append(r["name"])
            if URGENCY_ORDER.index(Urgency(r["urgency"])) > URGENCY_ORDER.index(urgency):
                urgency = Urgency(r["urgency"])

    escalation = False
    for r in rules["escalation_rules"]:
        if _matches(r["when"], ctx):
            escalation = True
            fired.append(f"escalate: {r['name']}")

    reasons: list[str] = []
    for r in rules["review_rules"]:
        if _matches(r["when"], ctx):
            reasons.append(r["reason"])
            fired.append(f"review: {r['name']}")

    action = rules["actions"].get(cls.primary_intent.value, rules["default_action"])
    if escalation:
        action = rules["escalation_action"] + action

    decision = Decision(urgency=urgency, escalation=escalation, recommended_action=action,
                        needs_human_review=bool(reasons), fired_rules=fired, review_reasons=reasons)
    trace = StepTrace(name="4 Decide", kind="rules", latency_ms=int((time.perf_counter() - start) * 1000),
                      output=decision.model_dump(mode="json"))
    return decision, trace
