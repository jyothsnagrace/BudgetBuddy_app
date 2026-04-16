"""Tool orchestration and persistence utilities for the Pet Community Cafe feature."""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Budget data
# ---------------------------------------------------------------------------

def fetch_budget_data(user_id: str) -> str:
    """
    Mock tool that returns recent budget behavior as a JSON string.

    The output shape is stable so the planner agent can always reason over it,
    and deterministic per user_id so tests remain reproducible.
    """
    digest = sha256(user_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:2], 16) % 3

    scenarios = [
        {
            "status": "overspent",
            "summary": "Overspent on dining out this week.",
            "recent_spending": [
                {"category": "Dining", "amount": 74.5, "trend": "up"},
                {"category": "Coffee", "amount": 32.0, "trend": "up"},
                {"category": "Groceries", "amount": 48.2, "trend": "steady"},
            ],
            "savings_change": -18.4,
        },
        {
            "status": "balanced",
            "summary": "Stayed close to budget with one impulse purchase.",
            "recent_spending": [
                {"category": "Dining", "amount": 24.0, "trend": "steady"},
                {"category": "Transport", "amount": 19.1, "trend": "steady"},
                {"category": "Shopping", "amount": 41.0, "trend": "up"},
            ],
            "savings_change": 6.5,
        },
        {
            "status": "saved",
            "summary": "Successfully increased savings this week.",
            "recent_spending": [
                {"category": "Dining", "amount": 16.4, "trend": "down"},
                {"category": "Coffee", "amount": 8.0, "trend": "down"},
                {"category": "Groceries", "amount": 52.1, "trend": "steady"},
            ],
            "savings_change": 42.7,
        },
    ]

    payload: Dict[str, Any] = {
        "user_id": user_id,
        "generated_at": datetime.now(UTC).isoformat(),
        **scenarios[bucket],
    }
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# Reddit fetching
# ---------------------------------------------------------------------------

REDDIT_SUBREDDITS = ["coffee", "frugal", "personalfinance", "povertyfinance"]
REDDIT_FALLBACK_POSTS = [
    {
        "subreddit": "coffee",
        "title": "What's your go-to cheap home brew method?",
        "score": 1420,
        "url": "https://www.reddit.com/r/coffee/comments/example1",
        "num_comments": 312,
    },
    {
        "subreddit": "frugal",
        "title": "Making coffee at home saved me $200 this month",
        "score": 3800,
        "url": "https://www.reddit.com/r/frugal/comments/example2",
        "num_comments": 187,
    },
    {
        "subreddit": "personalfinance",
        "title": "Small daily habits that actually moved the needle on savings",
        "score": 5100,
        "url": "https://www.reddit.com/r/personalfinance/comments/example3",
        "num_comments": 429,
    },
]


def fetch_reddit_posts(
    subreddit: str = "coffee",
    limit: int = 3,
    timeout: int = 5,
) -> List[Dict[str, Any]]:
    """
    Fetch top posts from a subreddit using Reddit's public JSON API.

    Falls back to REDDIT_FALLBACK_POSTS on any network or parse error so the
    cafe always has something to discuss even without internet access.

    Args:
        subreddit: subreddit name without the r/ prefix.
        limit: number of posts to return (max 10).
        timeout: HTTP timeout in seconds.

    Returns:
        List of dicts with keys: subreddit, title, score, url, num_comments.
    """
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={min(limit, 10)}"
    headers = {"User-Agent": "cafe-agents/1.0 (budget cafe app)"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        posts = data.get("data", {}).get("children", [])
        results = []
        for post in posts[:limit]:
            p = post.get("data", {})
            results.append(
                {
                    "subreddit": subreddit,
                    "title": p.get("title", ""),
                    "score": p.get("score", 0),
                    "url": f"https://www.reddit.com{p.get('permalink', '')}",
                    "num_comments": p.get("num_comments", 0),
                }
            )
        return results if results else REDDIT_FALLBACK_POSTS[:limit]
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, OSError):
        return REDDIT_FALLBACK_POSTS[:limit]


def fetch_cafe_context(user_id: str, subreddit: str = "coffee") -> Dict[str, Any]:
    """
    Aggregate budget data + Reddit posts into a single context dict for agents.

    This is the single call cafe_agents should make at conversation start so
    every agent has grounded, varied topic material to react to.
    """
    budget = json.loads(fetch_budget_data(user_id))
    posts = fetch_reddit_posts(subreddit=subreddit, limit=3)

    return {
        "budget": budget,
        "reddit_posts": posts,
        "subreddit": subreddit,
        "fetched_at": datetime.now(UTC).isoformat(),
    }


# ---------------------------------------------------------------------------
# Memory persistence
# ---------------------------------------------------------------------------

def load_cafe_memory(file_path: str) -> List[Dict[str, Any]]:
    """
    Load prior chat history from local JSON storage.

    Returns an empty list if the file does not exist or is malformed.
    """
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        return []


def save_cafe_memory(chat_history: List[Dict[str, Any]], file_path: str) -> None:
    """Persist full cafe chat history to local JSON storage."""
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as handle:
        json.dump(chat_history, handle, ensure_ascii=False, indent=2)