"""
Cost projection utilities for Milestone 14.
Provides a transparent monthly cost model across API usage, compute, and storage.
"""

from typing import Dict, Any


DEFAULT_PRICING = {
    "groq_fast_input_per_million": 0.05,
    "groq_fast_output_per_million": 0.08,
    "groq_accurate_input_per_million": 0.59,
    "groq_accurate_output_per_million": 0.79,
    "gemini_flash_input_per_million": 0.075,
    "gemini_flash_output_per_million": 0.30,
    "compute_base_monthly": 18.0,
    "compute_per_peak_rps": 1.25,
    "storage_per_gb_month": 0.023,
    "database_per_gb_month": 0.125,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def project_budgetbuddy_costs(config: Dict[str, Any]) -> Dict[str, Any]:
    """Compute monthly projected costs for BudgetBuddy under a workload profile."""
    days = int(config.get("days_per_month", 30))

    active_users = float(config.get("active_users", 1000))
    expenses_per_user_per_day = float(config.get("expenses_per_user_per_day", 1.4))
    chat_turns_per_user_per_day = float(config.get("chat_turns_per_user_per_day", 2.0))

    parse_cache_hit_rate = _clamp(float(config.get("parse_cache_hit_rate", 0.35)), 0.0, 0.98)
    chat_cache_hit_rate = _clamp(float(config.get("chat_cache_hit_rate", 0.45)), 0.0, 0.98)
    parse_fast_path_rate = _clamp(float(config.get("parse_fast_path_rate", 0.30)), 0.0, 0.95)
    accurate_route_rate = _clamp(float(config.get("accurate_route_rate", 0.20)), 0.0, 1.0)

    avg_parse_prompt_tokens = float(config.get("avg_parse_prompt_tokens", 220))
    avg_parse_completion_tokens = float(config.get("avg_parse_completion_tokens", 90))
    avg_chat_prompt_tokens = float(config.get("avg_chat_prompt_tokens", 650))
    avg_chat_completion_tokens = float(config.get("avg_chat_completion_tokens", 220))

    peak_rps = float(config.get("peak_requests_per_second", 18))
    monthly_receipt_storage_gb = float(config.get("monthly_receipt_storage_gb", 8))
    monthly_rag_storage_gb = float(config.get("monthly_rag_storage_gb", 1))
    monthly_db_growth_gb = float(config.get("monthly_db_growth_gb", 2))

    parse_requests = active_users * expenses_per_user_per_day * days
    chat_requests = active_users * chat_turns_per_user_per_day * days

    parse_llm_requests = parse_requests * (1 - parse_cache_hit_rate) * (1 - parse_fast_path_rate)
    chat_llm_requests = chat_requests * (1 - chat_cache_hit_rate)

    llm_requests = parse_llm_requests + chat_llm_requests
    accurate_requests = llm_requests * accurate_route_rate
    fast_requests = llm_requests - accurate_requests

    total_prompt_tokens = (
        (parse_llm_requests * avg_parse_prompt_tokens)
        + (chat_llm_requests * avg_chat_prompt_tokens)
    )
    total_completion_tokens = (
        (parse_llm_requests * avg_parse_completion_tokens)
        + (chat_llm_requests * avg_chat_completion_tokens)
    )

    fast_prompt_tokens = total_prompt_tokens * (fast_requests / llm_requests) if llm_requests else 0.0
    fast_completion_tokens = total_completion_tokens * (fast_requests / llm_requests) if llm_requests else 0.0
    accurate_prompt_tokens = total_prompt_tokens - fast_prompt_tokens
    accurate_completion_tokens = total_completion_tokens - fast_completion_tokens

    pricing = DEFAULT_PRICING

    fast_cost = (
        (fast_prompt_tokens / 1_000_000.0) * pricing["groq_fast_input_per_million"]
        + (fast_completion_tokens / 1_000_000.0) * pricing["groq_fast_output_per_million"]
    )
    accurate_cost = (
        (accurate_prompt_tokens / 1_000_000.0) * pricing["groq_accurate_input_per_million"]
        + (accurate_completion_tokens / 1_000_000.0) * pricing["groq_accurate_output_per_million"]
    )

    compute_cost = pricing["compute_base_monthly"] + max(0.0, peak_rps - 10) * pricing["compute_per_peak_rps"]
    storage_cost = (monthly_receipt_storage_gb + monthly_rag_storage_gb) * pricing["storage_per_gb_month"]
    database_cost = monthly_db_growth_gb * pricing["database_per_gb_month"]

    api_cost = fast_cost + accurate_cost
    total_cost = api_cost + compute_cost + storage_cost + database_cost

    cost_per_user = total_cost / active_users if active_users else 0.0
    cost_per_1k_users = cost_per_user * 1000

    return {
        "inputs": {
            "days_per_month": days,
            "active_users": active_users,
            "expenses_per_user_per_day": expenses_per_user_per_day,
            "chat_turns_per_user_per_day": chat_turns_per_user_per_day,
            "parse_cache_hit_rate": parse_cache_hit_rate,
            "chat_cache_hit_rate": chat_cache_hit_rate,
            "parse_fast_path_rate": parse_fast_path_rate,
            "accurate_route_rate": accurate_route_rate,
            "avg_parse_prompt_tokens": avg_parse_prompt_tokens,
            "avg_parse_completion_tokens": avg_parse_completion_tokens,
            "avg_chat_prompt_tokens": avg_chat_prompt_tokens,
            "avg_chat_completion_tokens": avg_chat_completion_tokens,
            "peak_requests_per_second": peak_rps,
            "monthly_receipt_storage_gb": monthly_receipt_storage_gb,
            "monthly_rag_storage_gb": monthly_rag_storage_gb,
            "monthly_db_growth_gb": monthly_db_growth_gb,
        },
        "derived_workload": {
            "parse_requests_monthly": round(parse_requests, 2),
            "chat_requests_monthly": round(chat_requests, 2),
            "llm_requests_monthly": round(llm_requests, 2),
            "fast_model_requests_monthly": round(fast_requests, 2),
            "accurate_model_requests_monthly": round(accurate_requests, 2),
            "total_prompt_tokens_monthly": round(total_prompt_tokens, 2),
            "total_completion_tokens_monthly": round(total_completion_tokens, 2),
        },
        "cost_breakdown_usd": {
            "api_fast_model": round(fast_cost, 2),
            "api_accurate_model": round(accurate_cost, 2),
            "api_total": round(api_cost, 2),
            "compute": round(compute_cost, 2),
            "storage": round(storage_cost, 2),
            "database": round(database_cost, 2),
            "total_monthly": round(total_cost, 2),
        },
        "unit_economics": {
            "cost_per_user_monthly_usd": round(cost_per_user, 4),
            "cost_per_1k_users_monthly_usd": round(cost_per_1k_users, 2),
        },
        "pricing_assumptions": pricing,
    }
