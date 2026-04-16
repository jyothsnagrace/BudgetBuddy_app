"""Multi-agent cafe conversation engine with Reddit + budget context."""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from typing import Any, Dict, List

# --- Optional LLM clients ---
try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

try:
    import anthropic as _anthropic_sdk
except Exception:
    _anthropic_sdk = None  # type: ignore

try:
    from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent
    AUTOGEN_AVAILABLE = True
except Exception:
    AssistantAgent = UserProxyAgent = GroupChat = GroupChatManager = None  # type: ignore
    AUTOGEN_AVAILABLE = False

try:
    from .cafe_tools import fetch_cafe_context, load_cafe_memory, save_cafe_memory
except ImportError:
    from cafe_tools import fetch_cafe_context, load_cafe_memory, save_cafe_memory

# --- CONFIG ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

config_list = []
if OPENAI_API_KEY:
    config_list.append(
        {"model": os.getenv("AUTOGEN_MODEL", "gpt-4o-mini"), "api_key": OPENAI_API_KEY}
    )

# ---------------------------------------------------------------------------
# Speaker metadata
# ---------------------------------------------------------------------------

SPEAKER_ROTATION = ["user_pet", "npc_pet_1", "npc_pet_2", "barista_planner"]

SPEAKER_NAME = {
    "user_pet": "Mochi",
    "npc_pet_1": "Penny",
    "npc_pet_2": "Capy",
    "barista_planner": "Esper",
}

SPEAKER_EMOJI = {
    "user_pet": "🐱",
    "npc_pet_1": "🐧",
    "npc_pet_2": "🦫",
    "barista_planner": "🐉",
}

SPEAKER_PERSONA = {
    "user_pet": (
        "Mochi the Cat: sweet, sensitive, easily anxious about money. "
        "React to the Reddit post or budget fact with genuine emotion and one small hope."
    ),
    "npc_pet_1": (
        "Penny the Penguin: warm, optimistic, and practical. "
        "Offer one cheerful, concrete money tip inspired by the topic."
    ),
    "npc_pet_2": (
        "Capy the Capybara: protective, intense, big-hearted. "
        "Give one firm, protective piece of budget advice related to the topic."
    ),
    "barista_planner": (
        "Esper the Dragon: sassy, moody, treasure-obsessed planner. "
        "React to the topic with dry wit, then either give a sharp observation "
        "or assign a QUEST if a concrete action is obvious."
    ),
}

# ---------------------------------------------------------------------------
# Termination helper (autogen)
# ---------------------------------------------------------------------------

def is_termination_msg(msg: Dict[str, Any]) -> bool:
    content = msg.get("content", "").lower()
    return "end_conversation" in content or "goodbye" in content

# ---------------------------------------------------------------------------
# Content cleaning — strips nested speaker-prefix chains
# ---------------------------------------------------------------------------

def _clean_content(content: str) -> str:
    """Return only the last meaningful sentence, stripping any speaker-prefix nesting."""
    parts = re.split(r"\b(Mochi|Penny|Capy|Esper):\s*", content)
    speaker_names = {"Mochi", "Penny", "Capy", "Esper"}
    for segment in reversed(parts):
        segment = segment.strip()
        if segment and segment not in speaker_names:
            return segment
    return content.strip()

# ---------------------------------------------------------------------------
# Context summariser — builds a 1-2 sentence briefing for agents
# ---------------------------------------------------------------------------

def _summarise_context(ctx: Dict[str, Any]) -> str:
    """Turn fetch_cafe_context output into a short briefing string for prompts."""
    budget = ctx.get("budget", {})
    posts = ctx.get("reddit_posts", [])
    subreddit = ctx.get("subreddit", "coffee")

    budget_line = (
        f"Budget status: {budget.get('status', 'unknown')} — {budget.get('summary', '')} "
        f"Savings change: {budget.get('savings_change', 0):+.1f}."
    )

    post_lines = []
    for p in posts[:2]:
        post_lines.append(f'r/{subreddit} post "{p["title"]}" ({p["score"]} upvotes)')

    reddit_line = "Top Reddit posts: " + "; ".join(post_lines) + "." if post_lines else ""
    return f"{budget_line} {reddit_line}".strip()

# ---------------------------------------------------------------------------
# Single-turn LLM generation
# ---------------------------------------------------------------------------

def _call_openai(system_prompt: str, user_prompt: str, model: str) -> str:
    if not OPENAI_API_KEY or OpenAI is None:
        return ""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=model,
            temperature=0.85,
            max_tokens=90,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (response.choices[0].message.content or "").strip()
    except Exception:
        return ""


def _call_anthropic(system_prompt: str, user_prompt: str) -> str:
    if not ANTHROPIC_API_KEY or _anthropic_sdk is None:
        return ""
    try:
        client = _anthropic_sdk.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=90,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return (message.content[0].text or "").strip()
    except Exception:
        return ""


def _mock_single_turn(speaker: str, context_summary: str, turn_index: int) -> str:
    """
    Last-resort fallback. Uses context_summary so the topic varies
    rather than returning the same four lines forever.
    """
    topic = context_summary.split(".")[0] if context_summary else "your budget this week"
    if speaker == "user_pet":
        return f"I'm a little anxious about {topic}, but one small win today would help."
    if speaker == "npc_pet_1":
        return f"We can tackle {topic} together — one practical step makes all the difference."
    if speaker == "npc_pet_2":
        return f"On {topic}: guard essentials first, then cut one unnecessary spend right now."
    if turn_index % 5 == 0:
        return f"QUEST: Take one concrete action on {topic} before the day ends."
    return f"Eyes on the treasure: {topic} is exactly where discipline pays off."


def _generate_turn(
    speaker: str,
    previous_content: str,
    context_summary: str,
    turn_index: int,
) -> str:
    """Generate one speaker bubble, trying OpenAI → Anthropic → mock fallback."""
    speaker_name = SPEAKER_NAME[speaker]
    persona = SPEAKER_PERSONA[speaker]

    system_prompt = (
        "You are generating ONE chat bubble for a cosy multi-agent budgeting cafe. "
        f"Current speaker: {speaker_name}. {persona}\n"
        "Hard rules:\n"
        "- 1-2 sentences MAX.\n"
        "- Plain text only — no markdown, no bullet points.\n"
        "- Do NOT quote, paraphrase, or echo the previous message.\n"
        "- Do NOT prefix your reply with your own name.\n"
        "- Do NOT write dialogue for any other character.\n"
        "- Ground your reply in the context provided (Reddit post title or budget fact).\n"
        "- If you are Esper and a concrete action is clear, start with 'QUEST:' exactly once."
    )
    user_prompt = (
        f"Cafe context (use this as your topic):\n{context_summary}\n\n"
        f"Previous message:\n{_clean_content(previous_content)}\n\n"
        f"Write only {speaker_name}'s next message as plain text."
    )

    model = os.getenv("AUTOGEN_MODEL", "gpt-4o-mini")
    text = _call_openai(system_prompt, user_prompt, model) or _call_anthropic(system_prompt, user_prompt)

    if not text:
        return _mock_single_turn(speaker, context_summary, turn_index)

    # Take first line only, strip any accidental self-name prefix
    first_line = text.split("\n", 1)[0].strip()
    name_prefix = f"{speaker_name}:"
    if first_line.startswith(name_prefix):
        first_line = first_line[len(name_prefix):].strip()

    return first_line or _mock_single_turn(speaker, context_summary, turn_index)

# ---------------------------------------------------------------------------
# Autogen group chat (optional path)
# ---------------------------------------------------------------------------

def _can_use_autogen() -> bool:
    return AUTOGEN_AVAILABLE and bool(config_list)


def _build_autogen_agents():
    if not _can_use_autogen():
        return None

    def _agent(name, persona):
        return AssistantAgent(
            name=name,
            system_message=(
                f"{persona} "
                "Keep responses under 2 sentences. No questions. "
                "Never quote or repeat what previous speakers said."
            ),
            llm_config={"config_list": config_list},
        )

    penguin = _agent("npc_pet_1", SPEAKER_PERSONA["npc_pet_1"])
    capybara = _agent("npc_pet_2", SPEAKER_PERSONA["npc_pet_2"])
    dragon = _agent("barista_planner", SPEAKER_PERSONA["barista_planner"])
    user_proxy = UserProxyAgent(
        name="user",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0,
        code_execution_config=False,
    )
    return user_proxy, penguin, capybara, dragon


def run_cafe_conversation(prompt: str):
    agents = _build_autogen_agents()
    if not agents:
        return [{"name": "barista_planner", "content": "Cafe open. One topic at a time."}]

    user_proxy, penguin, capybara, dragon = agents
    groupchat = GroupChat(
        agents=[user_proxy, penguin, capybara, dragon],
        messages=[],
        max_round=4,
    )
    manager = GroupChatManager(groupchat=groupchat, llm_config={"config_list": config_list})
    user_proxy.initiate_chat(manager, message=prompt)
    return groupchat.messages


def format_messages(messages):
    formatted = []
    for i, msg in enumerate(messages):
        speaker = msg.get("name", "unknown")
        content = msg.get("content", "").strip()
        if not content or speaker == "user":
            continue
        formatted.append(
            {
                "id": f"{datetime.now(UTC).timestamp()}-{i}",
                "speaker": speaker,
                "content": content.replace("end_conversation", "").strip(),
                "timestamp": datetime.now(UTC).isoformat(),
                "meta": {"quest": "quest:" in content.lower()},
            }
        )
    return formatted

# ---------------------------------------------------------------------------
# Primary API: one turn per click
# ---------------------------------------------------------------------------

def run_cafe_continue_turn(
    user_id: str,
    memory_path: str = "backend/rag_cache/cafe_memory.json",
    subreddit: str = "coffee",
) -> List[Dict[str, Any]]:
    """
    Return exactly one new turn. Fetches Reddit + budget context on first turn
    and caches it in memory so all subsequent turns stay grounded on the same topic.
    """
    history = load_cafe_memory(memory_path)

    # --- First turn: fetch context, open the cafe ---
    if not history:
        ctx = fetch_cafe_context(user_id, subreddit=subreddit)
        context_summary = _summarise_context(ctx)
        first = {
            "id": f"{datetime.now(UTC).timestamp()}-0",
            "speaker": "barista_planner",
            "content": (
                f"Cafe open. Today's topic: {context_summary.split('.')[0]}. "
                "Let's keep it focused — one insight at a time."
            ),
            "timestamp": datetime.now(UTC).isoformat(),
            "meta": {
                "tool": "fetch_cafe_context",
                "context_summary": context_summary,
                "reddit_posts": ctx.get("reddit_posts", []),
                "quest": False,
            },
        }
        save_cafe_memory([first], memory_path)
        return [first]

    # --- Retrieve cached context summary from the opening turn ---
    opening_meta = history[0].get("meta", {})
    context_summary = opening_meta.get("context_summary", "")

    # If context is missing (old memory file), refresh it
    if not context_summary:
        ctx = fetch_cafe_context(user_id, subreddit=subreddit)
        context_summary = _summarise_context(ctx)

    # --- Pick next speaker (avoid repeating last two speakers) ---
    last_two_speakers = [e.get("speaker") for e in history[-2:]]
    available = [s for s in SPEAKER_ROTATION if s not in last_two_speakers] or SPEAKER_ROTATION[:]
    next_speaker = available[len(history) % len(available)]

    previous = _clean_content(str(history[-1].get("content", "")))
    content = _generate_turn(next_speaker, previous, context_summary, len(history))

    message = {
        "id": f"{datetime.now(UTC).timestamp()}-{len(history)}",
        "speaker": next_speaker,
        "content": content,
        "timestamp": datetime.now(UTC).isoformat(),
        "meta": {"quest": "quest:" in content.lower(), "continued": True},
    }
    save_cafe_memory(history + [message], memory_path)
    return [message]

# ---------------------------------------------------------------------------
# Compatibility shim for tests
# ---------------------------------------------------------------------------

def run_cafe_group_chat(
    user_id: str,
    memory_path: str = "backend/rag_cache/cafe_memory.json",
    max_round: int = 6,
    subreddit: str = "coffee",
) -> List[Dict[str, Any]]:
    """Compatibility API used by tests and previous backend code paths."""
    ctx = fetch_cafe_context(user_id, subreddit=subreddit)
    context_summary = _summarise_context(ctx)
    posts = ctx.get("reddit_posts", [])
    post_title = posts[0]["title"] if posts else "budgeting tips"

    convo = [
        {
            "id": f"{datetime.now(UTC).timestamp()}-0",
            "speaker": "barista_planner",
            "content": f"Cafe briefing started. Today's thread: \"{post_title}\".",
            "timestamp": datetime.now(UTC).isoformat(),
            "meta": {"tool": "fetch_cafe_context", "context_summary": context_summary,
                     "reddit_posts": posts},
        },
        {
            "id": f"{datetime.now(UTC).timestamp()}-1",
            "speaker": "user_pet",
            "content": "I'm nervous, but I want us to make one safer money move today.",
            "timestamp": datetime.now(UTC).isoformat(),
            "meta": {},
        },
        {
            "id": f"{datetime.now(UTC).timestamp()}-2",
            "speaker": "npc_pet_1",
            "content": "We can do this — one calm, practical choice can shift the whole week.",
            "timestamp": datetime.now(UTC).isoformat(),
            "meta": {},
        },
        {
            "id": f"{datetime.now(UTC).timestamp()}-3",
            "speaker": "npc_pet_2",
            "content": "Protect essentials first, then cut one wasteful spend with confidence.",
            "timestamp": datetime.now(UTC).isoformat(),
            "meta": {},
        },
        {
            "id": f"{datetime.now(UTC).timestamp()}-4",
            "speaker": "barista_planner",
            "content": "QUEST: Move 30 gold to savings and skip one impulse buy today.",
            "timestamp": datetime.now(UTC).isoformat(),
            "meta": {"quest": True},
        },
    ]

    convo = convo[: max(4, max_round)]
    save_cafe_memory(load_cafe_memory(memory_path) + convo, memory_path)
    return convo