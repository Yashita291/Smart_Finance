"""
Financial insight generation.

Two layers:
1. generate_rule_insights() - deterministic statistics on the user's own data.
   Always runs, no external calls, no cost, no data leaves the server.
2. generate_llm_insight() - SWAPPABLE STUB. Wire your provider here. It receives
   an already-aggregated, anonymized summary (never raw transactions) so that the
   privacy surface is a single, reviewable function.

The view calls refresh_insights(), which runs the rule engine and optionally the
LLM layer if settings.LLM_INSIGHTS_ENABLED is True and a key is configured.
"""
from __future__ import annotations
from decimal import Decimal
from datetime import date
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from core.models import Expense, Income, AIInsight


def _month_bounds(d: date):
    start = d.replace(day=1)
    if start.month == 12:
        nxt = start.replace(year=start.year + 1, month=1)
    else:
        nxt = start.replace(month=start.month + 1)
    return start, nxt


def _category_totals(user, start, end):
    rows = (
        Expense.objects.filter(user=user, date__gte=start, date__lt=end)
        .values("category__name")
        .annotate(total=Sum("amount"))
    )
    return {r["category__name"]: r["total"] or Decimal("0") for r in rows}


def build_summary(user) -> dict:
    """Aggregated, anonymized snapshot. This is the ONLY thing the LLM ever sees."""
    today = timezone.now().date()
    cur_start, cur_end = _month_bounds(today)
    prev_end = cur_start
    prev_start = (cur_start.replace(day=1) - timezone.timedelta(days=1)).replace(day=1)

    cur = _category_totals(user, cur_start, cur_end)
    prev = _category_totals(user, prev_start, prev_end)

    income = Income.objects.filter(user=user, date__gte=cur_start, date__lt=cur_end).aggregate(
        t=Sum("amount"))["t"] or Decimal("0")
    spent = sum(cur.values(), Decimal("0"))

    return {
        "month": cur_start.strftime("%B %Y"),
        "income": income,
        "spent": spent,
        "savings": income - spent,
        "current_by_category": cur,
        "previous_by_category": prev,
    }


def generate_rule_insights(user) -> list[str]:
    s = build_summary(user)
    out: list[str] = []

    # Month-over-month category jumps
    for cat, amt in s["current_by_category"].items():
        prev = s["previous_by_category"].get(cat, Decimal("0"))
        if prev > 0 and amt > prev:
            pct = round(((amt - prev) / prev) * 100)
            if pct >= 20:
                out.append(f"{cat} expenses rose {pct}% vs last month (₹{amt:,.0f} from ₹{prev:,.0f}).")
        elif prev == 0 and amt > 0:
            out.append(f"New spending appeared in {cat}: ₹{amt:,.0f} this month.")

    # Savings rate
    if s["income"] > 0:
        rate = round((s["savings"] / s["income"]) * 100)
        if rate < 0:
            out.append(f"You spent more than you earned this month (deficit ₹{abs(s['savings']):,.0f}).")
        elif rate < 10:
            out.append(f"Savings rate is low at {rate}%. Aim for 20%+ where possible.")
        else:
            out.append(f"Savings rate this month: {rate}%.")

    # Largest category
    if s["current_by_category"]:
        top_cat, top_amt = max(s["current_by_category"].items(), key=lambda kv: kv[1])
        share = round((top_amt / s["spent"]) * 100) if s["spent"] else 0
        out.append(f"Largest category is {top_cat} at ₹{top_amt:,.0f} ({share}% of spending).")

    if not out:
        out.append("Not enough activity yet to generate insights. Add some transactions.")
    return out


def generate_llm_insight(summary: dict) -> str | None:
    """
    STUB. To enable: set LLM_INSIGHTS_ENABLED=True and implement the call below.
    `summary` is pre-aggregated - no raw transactions, no merchant names, no PII.

    Example (pseudocode - fill with your provider's SDK):

        client = YourProvider(api_key=settings.LLM_API_KEY)
        prompt = f"Given this monthly summary, give one actionable tip: {summary}"
        resp = client.complete(prompt)
        return resp.text

    Returning None means "no LLM insight this run" and the UI shows only rule insights.
    """
    if not getattr(settings, "LLM_INSIGHTS_ENABLED", False):
        return None
    if not getattr(settings, "LLM_API_KEY", ""):
        return None
    # TODO: implement provider call. Intentionally not wired to any vendor.
    return None


def refresh_insights(user) -> None:
    """Regenerate insights for a user. Clears old ones to avoid unbounded growth."""
    AIInsight.objects.filter(user=user).delete()
    for text in generate_rule_insights(user):
        AIInsight.objects.create(user=user, text=text, source=AIInsight.SOURCE_RULE)

    llm_text = generate_llm_insight(build_summary(user))
    if llm_text:
        AIInsight.objects.create(user=user, text=llm_text, source=AIInsight.SOURCE_LLM)
