from __future__ import annotations

import re
import unicodedata
from typing import Any

import numpy as np

from contracts.diagnosis import ExtractedEvent

from .constants import ACTION_SLUG, IMP_GROUP_SLUG, IMP_SUBTYPE_SLUG, MONEY_SLUG, PSY_SLUG


def deterministic_amount(text: str, fallback: Any = None) -> float:
    value_text = unicodedata.normalize("NFKC", str(text or "")).replace(",", "")
    total = 0.0
    for unit, multiplier in [("억", 100_000_000), ("천만", 10_000_000), ("백만", 1_000_000), ("만", 10_000), ("천원", 1_000), ("백원", 100), ("십원", 10)]:
        match = re.search(rf"(\d+(?:\.\d+)?)\s*{unit}", value_text)
        if match:
            total += float(match.group(1)) * multiplier
    if total:
        return total
    match = re.search(r"(\d+(?:\.\d+)?)\s*원", value_text)
    if match:
        return float(match.group(1))
    try:
        return float(fallback) if fallback is not None else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def _add_repeat(out: dict[str, float], prefix: str, count: int) -> None:
    repeat = max(count - 1, 0)
    out[f"{prefix}_present"] = int(count >= 1)
    out[f"{prefix}_repeat"] = repeat
    out[f"{prefix}_accel_tri"] = int(repeat * (repeat - 1) / 2)
    out[f"{prefix}_count_qc"] = count


def features_from_events(events: list[ExtractedEvent]) -> dict[str, float]:
    out: dict[str, float] = {}
    impersonations = [event for event in events if event.event_family == "IMPERSONATION"]
    groups = {event.impersonation_group for event in impersonations if event.impersonation_group}
    subtypes = {event.subtype for event in impersonations if event.subtype}
    out["imp_present"] = int(bool(impersonations))
    out["imp_event_count_raw_qc"] = len(impersonations)
    for raw, slug in IMP_GROUP_SLUG.items():
        out[f"imp_{slug}"] = int(raw in groups)
    for raw, slug in IMP_SUBTYPE_SLUG.items():
        out[f"imp_{slug}"] = int(raw in subtypes)
    out["imp_group_diversity_qc"] = len(groups)
    out["imp_subtype_diversity_qc"] = len(subtypes)

    psy = [event.subtype for event in events if event.event_family == "PSY_STRATEGY" and event.subtype]
    for raw, slug in PSY_SLUG.items():
        _add_repeat(out, f"strategy_{slug}", psy.count(raw))
    out["strategy_diversity"] = len(set(psy))
    out["strategy_event_count_qc"] = len(psy)

    actions = [event.subtype for event in events if event.event_family == "ACTION_REQUEST" and event.subtype]
    for raw, slug in ACTION_SLUG.items():
        _add_repeat(out, f"action_{slug}", actions.count(raw))
    out["action_diversity"] = len(set(actions))
    out["action_event_count_qc"] = len(actions)

    money = [event.subtype for event in events if event.event_family == "MONEY_MOVEMENT" and event.subtype]
    _add_repeat(out, "money_movement", len(money))
    for raw, slug in MONEY_SLUG.items():
        _add_repeat(out, f"money_{slug}", money.count(raw))
    out["money_action_diversity"] = len(set(money))
    out["money_event_count_qc"] = len(money)

    amounts = [event for event in events if event.event_family == "AMOUNT"]
    requested = [event for event in amounts if event.is_requested]
    requested_values = [deterministic_amount(event.evidence_text, event.amount_krw) for event in requested]
    mentioned_values = [deterministic_amount(event.evidence_text, event.amount_krw) for event in amounts]
    requested_values = [value for value in requested_values if not np.isnan(value) and value >= 0]
    mentioned_values = [value for value in mentioned_values if not np.isnan(value) and value >= 0]
    req_repeat = max(len(requested) - 1, 0)
    out.update({
        "amount_mentioned_present": int(bool(amounts)), "amount_event_count_qc": len(amounts),
        "amount_requested_present": int(bool(requested)), "amount_request_repeat": req_repeat,
        "amount_request_accel_tri": int(req_repeat * (req_repeat - 1) / 2), "amount_request_count_qc": len(requested),
        "requested_amount_max": max(requested_values, default=0.0), "requested_amount_sum": sum(requested_values),
        "requested_amount_log1p_max": float(np.log1p(max(requested_values, default=0.0))),
        "requested_amount_log1p_sum": float(np.log1p(sum(requested_values))),
        "mentioned_amount_max_qc": max(mentioned_values, default=0.0),
    })
    out["signal_family_count"] = sum([
        out["imp_present"], int(out["strategy_event_count_qc"] > 0), int(out["action_event_count_qc"] > 0),
        out["money_movement_present"], out["amount_requested_present"],
    ])
    out["ix_imp_authority"] = out["imp_present"] * out["strategy_authority_present"]
    out["ix_public_authority"] = out["imp_public"] * out["strategy_authority_present"]
    out["ix_financial_authority"] = out["imp_financial"] * out["strategy_authority_present"]
    out["ix_authority_urgency"] = out["strategy_authority_present"] * out["strategy_urgency_present"]
    out["ix_fear_urgency"] = out["strategy_fear_present"] * out["strategy_urgency_present"]
    out["ix_info_sensitive"] = out["strategy_info_extraction_present"] * out["action_sensitive_info_present"]
    out["ix_info_auth"] = out["strategy_info_extraction_present"] * out["action_auth_info_present"]
    out["ix_moneystrategy_movement"] = out["strategy_money_request_strategy_present"] * out["money_movement_present"]
    out["ix_fear_money"] = out["strategy_fear_present"] * out["money_movement_present"]
    out["ix_isolation_contact"] = out["strategy_isolation_present"] * out["action_contact_restriction_present"]
    return out
