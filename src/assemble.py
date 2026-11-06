"""Step 7 - Assemble the final support result (code).

Turns the step outputs into the seven fields the support team sees. Verification and the
safe fallback (Steps 3 and 6) are added in Milestone 4.
"""

from typing import TYPE_CHECKING

from src.schemas import SupportResult

if TYPE_CHECKING:  # avoids importing the LLM client just to format a result
    from src.pipeline import PipelineResult


def assemble(r: "PipelineResult") -> SupportResult | None:
    cls, ext, dec, drf = r.classification, r.extraction, r.decision, r.draft
    if not (cls and ext and dec):
        return None
    ids = r.preprocess.identifiers

    info: dict[str, str | list[str]] = {}
    if ext.product:
        info["Product"] = ext.product.value
    if ext.issue_description:
        info["Issue"] = ext.issue_description.value
    if ids.order_ids:
        info["Order IDs"] = ids.order_ids
    if ids.amounts:
        info["Amounts"] = [a.raw for a in ids.amounts]
    if ids.dates:
        info["Dates"] = ids.dates
    if ext.questions:
        info["Customer questions"] = [q.value for q in ext.questions]
    if ext.requested_outcome:
        info["Requested outcome"] = ext.requested_outcome.value
    if ext.prior_contact:
        info["Prior contact"] = ext.prior_contact.value
    if ext.deadline:
        info["Deadline"] = ext.deadline.value
    info["Frustration"] = cls.frustration.value
    info["Language"] = cls.language

    evidence = [f"Classification: {cls.reasoning} (confidence {cls.confidence:.2f})"]
    evidence += [f'Intent evidence: "{q}"' for q in cls.intent_evidence]
    evidence += [f'Signal {s.type.value}: "{s.quote}"' for s in ext.signals]
    evidence += [f"Rule fired: {name}" for name in dec.fired_rules]
    evidence += [f"Preprocess flag: {f}" for f in r.preprocess.flags]
    evidence += [f"Needs human review: {why}" for why in dec.review_reasons]

    intent = cls.primary_intent.value
    if cls.secondary_intents:
        intent += " (also: " + ", ".join(i.value for i in cls.secondary_intents) + ")"
    return SupportResult(
        customer_intent=intent, urgency=dec.urgency, key_information=info,
        recommended_action=dec.recommended_action, escalation=dec.escalation,
        draft_response=drf.response if drf else "(draft unavailable)",
        reasoning_evidence=evidence, needs_human_review=dec.needs_human_review,
        review_reasons=dec.review_reasons,
    )
