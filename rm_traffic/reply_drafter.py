"""
LLM Reply Drafter — generates booking-oriented replies using LLM.

Drafts replies, does NOT auto-send. Human approval required for first contact.
Safe template auto-reply only for repeat/opt-in clients.

Uses the existing llm_client.py multi-provider fallback:
  transformers.js (local, free) → ollama → groq → openrouter

Falls back to fixed templates if LLM is unavailable.

Reply structure (always):
  - availability
  - location / incall-outcall boundary
  - rate clarity
  - session length
  - professional tone
  - one next-step question
  - no spammy pressure
  - no weird sexual escalation
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from .intent_engine import classify, IntentResult
from .llm_client import generate_with_fallback

log = logging.getLogger("reply_drafter")

# Reply classes
REPLY_BOOKING_NOW = "booking_now_reply"
REPLY_PRICE_QUESTION = "price_question_reply"
REPLY_LOCATION_QUESTION = "location_question_reply"
REPLY_REPEAT_CLIENT = "repeat_client_reply"
REPLY_INQUIRY = "inquiry_reply"
REPLY_FOLLOW_UP = "follow_up_reply"
REPLY_CLOSE_LOOP = "close_loop_reply"
REPLY_AVAILABILITY_QUESTION = "availability_reply"
REPLY_HIGH_VALUE_REPEAT = "high_value_repeat_reply"
REPLY_NONE = "none"

# Risk levels
RISK_SAFE = "safe"
RISK_REVIEW = "review"
RISK_BLOCKED = "blocked"


@dataclass
class DraftReply:
    username: str = ""
    intent_class: str = ""
    confidence: float = 0.0
    booking_probability: float = 0.0
    reply_text: str = ""
    reply_class: str = ""
    risk_level: str = RISK_SAFE
    needs_human_approval: bool = True
    reason: str = ""
    suggested_time_slots: List[str] = None
    error: str = ""

    def __post_init__(self):
        if self.suggested_time_slots is None:
            self.suggested_time_slots = []


def _build_prompt(message: str, intent: IntentResult, context: Dict) -> str:
    """Build LLM prompt for reply generation."""
    username = context.get("username", "")
    is_premium = context.get("is_premium", False)
    is_repeat = intent.classification in ("repeat_client", "high_value_repeat")
    rate = context.get("rate", "$200")
    phone = context.get("phone", "")
    location = context.get("location", "Manhattan incall")

    intent_desc = {
        "booking_now": "Client is asking to book now — wants time/availability today",
        "price_question": "Client is asking about rates",
        "availability_question": "Client is asking when you're available",
        "location_question": "Client is asking about location/incall/outcall",
        "repeat_client": "Returning client — has booked before",
        "high_value_repeat": "High-value returning client with booking intent",
        "ghosted_lead": "Lead that went silent and came back",
        "unknown": "General inquiry — intent unclear",
    }.get(intent.classification, "General inquiry")

    prompt = f"""You are a professional massage therapist replying to a client message on RentMasseur.

Client message: "{message[:500]}"
Client username: {username}
Client intent: {intent.classification} (confidence: {intent.confidence:.2f})
Intent description: {intent_desc}
Booking probability: {intent.booking_probability:.2f}
Is repeat client: {is_repeat}
Is premium member: {is_premium}

Your business:
- Deep tissue & sports recovery massage
- {location}
- Rate: {rate} for 60 min, $280 for 90 min, $360 for 120 min
- Contact: text {phone} to book

Rules:
- Professional tone, no sexual language, no innuendo
- Include: availability, location, rate, session length
- End with ONE next-step question
- Keep under 80 words
- Do not pressure or push
- If repeat client, acknowledge familiarity
- If price question, state rates clearly
- If booking intent, offer 2-3 specific time slots

Write the reply:"""

    return prompt


def _clean_llm_output(text: str) -> str:
    """Clean LLM output — remove quotes, markdown, extra whitespace."""
    if not text:
        return ""
    text = text.strip()
    # Remove surrounding quotes
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    # Remove markdown
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Remove any "Reply:" prefix
    text = re.sub(r'^(Reply|Response|Message):\s*', '', text, flags=re.IGNORECASE)
    # Normalize whitespace
    text = ' '.join(text.split())
    return text.strip()


def _template_fallback(intent: IntentResult, context: Dict) -> str:
    """Fixed template fallback when LLM is unavailable."""
    rate = context.get("rate", "$200")
    phone = context.get("phone", "")
    cls = intent.classification

    if cls == "booking_now":
        return (
            f"Yes — I'm available today. I have openings at 7:30 or 9 PM. "
            f"Manhattan incall, {rate} for 60 min. "
            f"Which time works for you? Text {phone} to confirm."
        )

    if cls == "price_question":
        return (
            f"Rate is {rate} for 60 min, $280 for 90 min, $360 for 120 min. "
            f"Manhattan incall. What duration and time work for you? "
            f"Text {phone} to book."
        )

    if cls == "availability_question":
        return (
            f"I'm available today and this week. "
            f"Manhattan incall, {rate} for 60 min. "
            f"What day and time work for you? Text {phone} to schedule."
        )

    if cls == "location_question":
        return (
            f"I'm based in Manhattan — private incall space. "
            f"Outcall available within Manhattan for additional travel fee. "
            f"Rate is {rate}. Text {phone} for faster booking."
        )

    if cls in ("repeat_client", "high_value_repeat"):
        return (
            f"Great to hear from you again! "
            f"I have openings today. Same location in Manhattan. "
            f"Text {phone} to confirm your time."
        )

    if cls == "ghosted_lead":
        return (
            f"Hi — following up. I'm available this week if you'd like to book. "
            f"Manhattan incall, {rate} for 60 min. "
            f"Text {phone} to schedule."
        )

    return (
        f"Hi! Thanks for your interest. "
        f"I offer deep tissue and sports recovery massage in Manhattan. "
        f"Rate is {rate} for 60 min. "
        f"What questions can I answer? Text {phone} for faster response."
    )


def _determine_reply_class(intent: IntentResult) -> str:
    """Map intent classification to reply class."""
    mapping = {
        "booking_now": REPLY_BOOKING_NOW,
        "price_question": REPLY_PRICE_QUESTION,
        "availability_question": REPLY_AVAILABILITY_QUESTION,
        "location_question": REPLY_LOCATION_QUESTION,
        "repeat_client": REPLY_REPEAT_CLIENT,
        "high_value_repeat": REPLY_HIGH_VALUE_REPEAT,
        "ghosted_lead": REPLY_FOLLOW_UP,
        "do_not_contact": REPLY_NONE,
        "spam": REPLY_NONE,
        "unknown": REPLY_INQUIRY,
    }
    return mapping.get(intent.classification, REPLY_INQUIRY)


def _determine_risk(intent: IntentResult, is_first_contact: bool = True) -> str:
    """Determine risk level for the reply."""
    if intent.classification in ("do_not_contact", "spam"):
        return RISK_BLOCKED
    if "unsafe" in (intent.risk_flags or []):
        return RISK_BLOCKED
    if "opt_out" in (intent.risk_flags or []):
        return RISK_BLOCKED
    if is_first_contact:
        return RISK_REVIEW
    return RISK_SAFE


def draft_reply(message: str, context: Dict = None) -> DraftReply:
    """
    Generate an LLM-powered draft reply for a client message.

    Args:
        message: The client's message text
        context: Dict with username, is_premium, rate, phone, location, is_first_contact

    Returns:
        DraftReply with reply_text, risk_level, needs_human_approval
    """
    if context is None:
        context = {}

    # Classify intent
    intent = classify(message, context.get("username", ""))

    # Build draft
    draft = DraftReply(
        username=context.get("username", ""),
        intent_class=intent.classification,
        confidence=intent.confidence,
        booking_probability=intent.booking_probability,
        reply_class=_determine_reply_class(intent),
        risk_level=_determine_risk(intent, context.get("is_first_contact", True)),
        reason=f"Intent: {intent.classification} (conf={intent.confidence:.2f})",
    )

    # Blocked — no reply
    if draft.risk_level == RISK_BLOCKED:
        draft.reply_text = ""
        draft.needs_human_approval = False
        draft.reason = f"BLOCKED: {intent.classification} with risk flags {intent.risk_flags}"
        return draft

    # Try LLM generation
    prompt = _build_prompt(message, intent, context)
    llm_response = generate_with_fallback(prompt, max_tokens=200)

    if llm_response:
        draft.reply_text = _clean_llm_output(llm_response)
        draft.reason += " | LLM-generated"
        log.info(f"  ◉ LLM reply for {draft.username}: {draft.reply_text[:80]}...")
    else:
        # Fallback to template
        draft.reply_text = _template_fallback(intent, context)
        draft.reason += " | template-fallback"
        log.info(f"  ◉ Template reply for {draft.username}: {draft.reply_text[:80]}...")

    # Approval gate
    is_repeat = intent.classification in ("repeat_client", "high_value_repeat")
    is_safe_template = draft.reason.endswith("template-fallback")

    if is_repeat and is_safe_template and not context.get("is_first_contact", True):
        # Repeat client + safe template + not first contact = can auto-send
        draft.needs_human_approval = False
    else:
        draft.needs_human_approval = True

    # Suggested time slots for booking intent
    if intent.classification in ("booking_now", "high_value_repeat"):
        draft.suggested_time_slots = ["7:30 PM", "9:00 PM", "Tomorrow 12:00 PM"]

    return draft


def draft_mailbox_replies(emails: List[Dict], context: Dict = None) -> List[DraftReply]:
    """
    Generate draft replies for all mailbox conversations.

    Args:
        emails: List of email dicts from api.get_mailbox()
        context: Base context (rate, phone, location)

    Returns:
        List of DraftReply objects
    """
    if context is None:
        context = {}

    drafts = []
    for email in emails:
        uc = email.get("userCard", {})
        msg = email.get("lastMessage", "")
        username = uc.get("username", "")

        email_context = {
            **context,
            "username": username,
            "is_premium": bool(uc.get("isPremium", 0)),
            "is_first_contact": not bool(email.get("lastMessage", "")),
        }

        draft = draft_reply(msg, email_context)
        drafts.append(draft)

    return drafts


def format_drafts_summary(drafts: List[DraftReply]) -> str:
    """Format drafts for display."""
    lines = [f"\n{'='*60}", f"  REPLY DRAFT QUEUE — {len(drafts)} drafts", f"{'='*60}\n"]

    for d in drafts:
        if d.risk_level == RISK_BLOCKED:
            lines.append(f"  🚫 {d.username} [{d.intent_class}] — BLOCKED")
            lines.append(f"     {d.reason}")
            continue

        approval = "🔒 approval" if d.needs_human_approval else "⚡ auto-ok"
        lines.append(f"  ◉ {d.username} [{d.intent_class}] conf={d.confidence:.2f} {approval}")
        lines.append(f"    Reply: \"{d.reply_text[:120]}\"")
        if d.suggested_time_slots:
            lines.append(f"    Slots: {', '.join(d.suggested_time_slots)}")
        lines.append("")

    return "\n".join(lines)
