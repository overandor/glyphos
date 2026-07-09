"""
Reward Engine — measures metric deltas after actions and computes reward.

reward = 5.0 * booking_intent_delta
       + 3.0 * contact_click_delta
       + 2.0 * email_delta
       + 1.0 * view_delta
       - 2.0 * error_penalty
       - 3.0 * compliance_risk
       - 1.0 * excessive_mutation_penalty

Also computes attribution: which action produced which metric movement.
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

log = logging.getLogger("reward_engine")

REWARD_DB = Path(__file__).parent / "overclock_bandit.db"


@dataclass
class MetricDelta:
    views_delta: int = 0
    contact_clicks_delta: int = 0
    emails_delta: int = 0
    booking_intent_delta: float = 0.0
    rank_delta: int = 0
    availability_changed: bool = False
    visibility_changed: bool = False


def compute_delta(state_before, state_after) -> MetricDelta:
    """Compute metric delta between two TrafficState snapshots."""
    return MetricDelta(
        views_delta=state_after.views - state_before.views,
        contact_clicks_delta=state_after.contact_clicks - state_before.contact_clicks,
        emails_delta=state_after.mailbox_count - state_before.mailbox_count,
        booking_intent_delta=round(
            state_after.mailbox_intent_score - state_before.mailbox_intent_score, 3
        ),
        rank_delta=state_after.search_rank - state_before.search_rank if state_after.search_rank and state_before.search_rank else 0,
        availability_changed=state_after.available_status != state_before.available_status,
        visibility_changed=state_after.profile_hidden != state_before.profile_hidden,
    )


def compute_reward(delta: MetricDelta, action: str, error: str = "") -> float:
    """
    Compute reward from metric delta.

    reward = 5.0 * booking_intent_delta
           + 3.0 * contact_click_delta
           + 2.0 * email_delta
           + 1.0 * view_delta
           - 2.0 * error_penalty
           - 3.0 * compliance_risk
           - 1.0 * excessive_mutation_penalty
    """
    reward = (
        5.0 * max(0, delta.booking_intent_delta)
        + 3.0 * max(0, delta.contact_clicks_delta)
        + 2.0 * max(0, delta.emails_delta)
        + 1.0 * max(0, delta.views_delta) * 0.01  # views are small numbers, scale down
    )

    # Penalty for negative deltas
    if delta.booking_intent_delta < 0:
        reward += 3.0 * delta.booking_intent_delta
    if delta.contact_clicks_delta < 0:
        reward += 2.0 * delta.contact_clicks_delta

    # Rank improvement is good (lower rank number = better)
    if delta.rank_delta < 0:
        reward += 1.0 * abs(delta.rank_delta) * 0.5

    # Error penalty
    if error:
        reward -= 2.0

    # Compliance risk (handled by bandit, but double-check)
    risky_actions = {"rate_position_test", "photo_order_test"}
    if action in risky_actions:
        reward -= 0.5

    # Excessive mutation penalty: if we mutated profile and nothing moved
    mutation_actions = {"headline_variant_test", "bio_variant_test", "photo_order_test", "rate_position_test"}
    if action in mutation_actions:
        if delta.contact_clicks_delta == 0 and delta.booking_intent_delta == 0:
            reward -= 1.0  # mutation with no effect = penalty

    # Availability fix reward
    if action == "refresh_availability" and delta.availability_changed:
        reward += 2.0  # fixing availability is always valuable

    # Visibility fix reward
    if action == "ensure_visible" and delta.visibility_changed:
        reward += 2.0

    return round(reward, 3)


def delta_to_dict(delta: MetricDelta) -> Dict:
    return {
        "views_delta": delta.views_delta,
        "contact_clicks_delta": delta.contact_clicks_delta,
        "emails_delta": delta.emails_delta,
        "booking_intent_delta": delta.booking_intent_delta,
        "rank_delta": delta.rank_delta,
        "availability_changed": delta.availability_changed,
        "visibility_changed": delta.visibility_changed,
    }
