"""Planner-executor-reviewer orchestration for multi-step BudgetBuddy tasks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional
from uuid import uuid4


ToolFn = Callable[[str, Dict[str, Any], "AgentSessionState"], Awaitable[Dict[str, Any]]]


CATEGORY_MAP = {
    "food": "Food",
    "dining": "Food",
    "grocery": "Food",
    "groceries": "Food",
    "transport": "Transportation",
    "transportation": "Transportation",
    "uber": "Transportation",
    "lyft": "Transportation",
    "entertainment": "Entertainment",
    "shopping": "Shopping",
    "bills": "Bills",
    "healthcare": "Healthcare",
    "education": "Education",
    "other": "Other",
}


PERSONALITY_TEMPLATES = {
    "penguin": {
        "name": "Penny",
        "lead": "Cool update",
        "tail": "Stay chill, we are making steady progress.",
    },
    "dragon": {
        "name": "Esper",
        "lead": "Treasury report",
        "tail": "Guard the hoard and keep each move intentional.",
    },
    "capybara": {
        "name": "Capy",
        "lead": "Calm check-in",
        "tail": "No rush, one smart step at a time.",
    },
    "cat": {
        "name": "Mochi",
        "lead": "Purr-sonal ledger note",
        "tail": "Sharp choices today, keep that energy.",
    },
}


@dataclass
class AgentPlanStep:
    id: str
    action: str
    payload: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)


@dataclass
class AgentSessionState:
    session_id: str
    user_id: str
    created_at: str
    updated_at: str
    turn_count: int = 0
    recent_tasks: List[str] = field(default_factory=list)
    last_plan: List[Dict[str, Any]] = field(default_factory=list)
    last_step_outputs: Dict[str, Any] = field(default_factory=dict)
    working_memory: Dict[str, Any] = field(default_factory=dict)


class InMemoryAgentStateStore:
    """Simple in-process session state for multi-turn agent tasks."""

    def __init__(self) -> None:
        self._sessions: Dict[str, AgentSessionState] = {}

    def get_or_create(self, user_id: str, session_id: Optional[str] = None) -> AgentSessionState:
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            session.updated_at = datetime.now(UTC).isoformat()
            return session

        new_session_id = session_id or str(uuid4())
        now = datetime.now(UTC).isoformat()
        session = AgentSessionState(
            session_id=new_session_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        self._sessions[new_session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[AgentSessionState]:
        return self._sessions.get(session_id)


class PlannerAgent:
    """Turns a free-form goal into ordered, dependency-aware tool steps."""

    def create_plan(
        self,
        *,
        task: str,
        context: Optional[Dict[str, Any]],
        state: AgentSessionState,
    ) -> List[AgentPlanStep]:
        text = (task or "").strip()
        lowered = text.lower()
        steps: List[AgentPlanStep] = []

        parsed_expense_step_id: Optional[str] = None
        normalized_category = self._extract_category(lowered)
        extracted_city = self._extract_city(task, context or {})

        if self._wants_budget_update(lowered):
            budget_payload: Dict[str, Any] = {
                "monthly_limit": self._extract_amount_after_budget(lowered),
            }
            if normalized_category:
                budget_payload["category"] = normalized_category
            month = (context or {}).get("month")
            if month:
                budget_payload["month"] = month
            steps.append(
                AgentPlanStep(
                    id="set_budget_1",
                    action="set_budget",
                    payload=budget_payload,
                )
            )

        if self._wants_expense_parse(lowered):
            parsed_expense_step_id = "parse_expense_1"
            steps.append(
                AgentPlanStep(
                    id=parsed_expense_step_id,
                    action="parse_expense_text",
                    payload={"text": text},
                )
            )
            steps.append(
                AgentPlanStep(
                    id="add_expense_1",
                    action="add_expense",
                    payload={
                        "expense_data": {
                            "$from": f"{parsed_expense_step_id}.parsed_data",
                        }
                    },
                    depends_on=[parsed_expense_step_id],
                )
            )

        if self._wants_expense_query(lowered):
            query_payload: Dict[str, Any] = {"limit": 100}
            if normalized_category:
                query_payload["category"] = normalized_category
            steps.append(
                AgentPlanStep(
                    id="query_expenses_1",
                    action="query_expenses",
                    payload=query_payload,
                )
            )

        if self._wants_budget_comparison(lowered):
            comparison_payload: Dict[str, Any] = {}
            if normalized_category:
                comparison_payload["category"] = normalized_category
            month = (context or {}).get("month")
            if month:
                comparison_payload["month"] = month
            steps.append(
                AgentPlanStep(
                    id="get_budget_comparison_1",
                    action="get_budget_comparison",
                    payload=comparison_payload,
                )
            )

        if self._wants_cost_of_living(lowered):
            steps.append(
                AgentPlanStep(
                    id="get_cost_of_living_1",
                    action="get_cost_of_living",
                    payload={"city": extracted_city or "Charlotte, NC"},
                )
            )

        if not steps:
            # Generic fallback action if no explicit finance operation was inferred.
            steps.append(
                AgentPlanStep(
                    id="function_call_1",
                    action="function_call",
                    payload={"message": text},
                )
            )

        steps.append(
            AgentPlanStep(
                id="synthesize_response_1",
                action="synthesize_response",
                payload={"task": task},
                depends_on=[step.id for step in steps],
            )
        )

        return steps

    def _extract_category(self, lowered: str) -> Optional[str]:
        for key, value in CATEGORY_MAP.items():
            if re.search(rf"\\b{re.escape(key)}\\b", lowered):
                return value
        return None

    def _extract_amount_after_budget(self, lowered: str) -> float:
        match = re.search(r"budget\s+(?:to|at|is)?\s*\$?\s*(\d+(?:\.\d{1,2})?)", lowered)
        if match:
            return float(match.group(1))

        fallback = re.search(r"\$\s*(\d+(?:\.\d{1,2})?)", lowered)
        if fallback:
            return float(fallback.group(1))
        return 0.0

    def _extract_city(self, task: str, context: Dict[str, Any]) -> Optional[str]:
        city = context.get("city")
        if isinstance(city, str) and city.strip():
            return city.strip()

        match = re.search(r"(?:in|for)\s+([A-Za-z\s]+(?:,\s*[A-Za-z]{2})?)", task)
        if not match:
            return None
        return match.group(1).strip()

    def _wants_budget_update(self, lowered: str) -> bool:
        has_budget = "budget" in lowered
        has_update_verb = any(token in lowered for token in ["set", "update", "change", "limit", "to "])
        return has_budget and has_update_verb

    def _wants_expense_parse(self, lowered: str) -> bool:
        return any(token in lowered for token in ["spent", "spend", "paid", "bought", "expense"])

    def _wants_expense_query(self, lowered: str) -> bool:
        return "show my expenses" in lowered or ("show" in lowered and "expenses" in lowered) or "query expenses" in lowered

    def _wants_budget_comparison(self, lowered: str) -> bool:
        return "remaining budget" in lowered or "budget comparison" in lowered or ("remaining" in lowered and "budget" in lowered)

    def _wants_cost_of_living(self, lowered: str) -> bool:
        return "cost of living" in lowered


class ExecutorAgent:
    """Executes tool plan steps in order and records a full trace."""

    def __init__(self, tool_registry: Dict[str, ToolFn]) -> None:
        self.tool_registry = tool_registry

    async def run_plan(
        self,
        *,
        user_id: str,
        plan: List[AgentPlanStep],
        state: AgentSessionState,
    ) -> Dict[str, Any]:
        step_outputs: Dict[str, Any] = {}
        execution_trace: List[Dict[str, Any]] = []

        for step in plan:
            started_at = datetime.now(UTC).isoformat()
            resolved_input = self._resolve_payload(step.payload, step_outputs)

            if step.action == "synthesize_response":
                execution_trace.append(
                    {
                        "step_id": step.id,
                        "action": step.action,
                        "status": "completed",
                        "input": resolved_input,
                        "output": {"status": "queued_for_reviewer"},
                        "error": None,
                        "started_at": started_at,
                        "finished_at": datetime.now(UTC).isoformat(),
                    }
                )
                step_outputs[step.id] = {"status": "queued_for_reviewer"}
                continue

            tool_fn = self.tool_registry.get(step.action)
            if tool_fn is None:
                error_message = f"No tool registered for action '{step.action}'"
                execution_trace.append(
                    {
                        "step_id": step.id,
                        "action": step.action,
                        "status": "failed",
                        "input": resolved_input,
                        "output": None,
                        "error": error_message,
                        "started_at": started_at,
                        "finished_at": datetime.now(UTC).isoformat(),
                    }
                )
                step_outputs[step.id] = {"error": error_message}
                continue

            try:
                output = await tool_fn(user_id, resolved_input, state)
                execution_trace.append(
                    {
                        "step_id": step.id,
                        "action": step.action,
                        "status": "completed",
                        "input": resolved_input,
                        "output": output,
                        "error": None,
                        "started_at": started_at,
                        "finished_at": datetime.now(UTC).isoformat(),
                    }
                )
                step_outputs[step.id] = output
            except Exception as exc:
                execution_trace.append(
                    {
                        "step_id": step.id,
                        "action": step.action,
                        "status": "failed",
                        "input": resolved_input,
                        "output": None,
                        "error": str(exc),
                        "started_at": started_at,
                        "finished_at": datetime.now(UTC).isoformat(),
                    }
                )
                step_outputs[step.id] = {"error": str(exc)}

        return {
            "step_outputs": step_outputs,
            "execution_trace": execution_trace,
        }

    def _resolve_payload(self, payload: Any, step_outputs: Dict[str, Any]) -> Any:
        if isinstance(payload, dict):
            if set(payload.keys()) == {"$from"}:
                return self._resolve_reference(payload["$from"], step_outputs)
            return {key: self._resolve_payload(value, step_outputs) for key, value in payload.items()}
        if isinstance(payload, list):
            return [self._resolve_payload(item, step_outputs) for item in payload]
        return payload

    def _resolve_reference(self, pointer: str, step_outputs: Dict[str, Any]) -> Any:
        parts = pointer.split(".")
        if not parts:
            return None

        data: Any = step_outputs.get(parts[0], {})
        for part in parts[1:]:
            if isinstance(data, dict):
                data = data.get(part)
            else:
                return None
        return data


class ReviewerAgent:
    """Evaluates execution trace and synthesizes the final response."""

    def review(
        self,
        *,
        task: str,
        plan: List[AgentPlanStep],
        execution_trace: List[Dict[str, Any]],
        step_outputs: Dict[str, Any],
        state: AgentSessionState,
    ) -> Dict[str, Any]:
        failures = [step for step in execution_trace if step.get("status") == "failed"]
        status = "completed" if not failures else "partial"

        completed_actions = [s for s in execution_trace if s.get("status") == "completed"]
        set_budget_count = self._count_actions(completed_actions, "set_budget")
        add_expense_count = self._count_actions(completed_actions, "add_expense")
        query_count = self._sum_count_field(completed_actions, "query_expenses")
        comparison_count = self._count_actions(completed_actions, "get_budget_comparison")
        col_count = self._count_actions(completed_actions, "get_cost_of_living")

        summary_bits: List[str] = []
        if set_budget_count:
            summary_bits.append(f"Updated {set_budget_count} budget target(s).")
        if add_expense_count:
            summary_bits.append(f"Added {add_expense_count} expense item(s).")
        if query_count:
            summary_bits.append(f"Retrieved {query_count} expense record(s).")
        if comparison_count:
            summary_bits.append("Computed budget-vs-spending comparison.")
        if col_count:
            summary_bits.append("Included city cost-of-living context.")
        if not summary_bits:
            summary_bits.append("Completed requested finance actions.")

        if failures:
            summary_bits.append(f"{len(failures)} step(s) need review.")

        summary_bits.append(f"Session turns in memory: {state.turn_count}.")

        companion = str(state.working_memory.get("companion") or "penguin").lower()
        persona = PERSONALITY_TEMPLATES.get(companion, PERSONALITY_TEMPLATES["penguin"])
        final_response = f"{persona['name']} - {persona['lead']}: {' '.join(summary_bits)} {persona['tail']}"

        return {
            "status": status,
            "final_response": final_response,
            "failures": failures,
            "plan": [
                {
                    "id": step.id,
                    "action": step.action,
                    "payload": step.payload,
                    "depends_on": step.depends_on,
                }
                for step in plan
            ],
            "execution_trace": execution_trace,
            "step_outputs": step_outputs,
            "task": task,
        }

    def _count_actions(self, steps: List[Dict[str, Any]], action: str) -> int:
        return sum(1 for step in steps if step.get("action") == action)

    def _sum_count_field(self, steps: List[Dict[str, Any]], action: str) -> int:
        total = 0
        for step in steps:
            if step.get("action") != action:
                continue
            output = step.get("output") or {}
            total += int(output.get("count") or 0)
        return total


class BudgetBuddyAgentOrchestrator:
    """Main entry point for planner-executor-reviewer orchestration."""

    def __init__(
        self,
        tool_registry: Dict[str, ToolFn],
        state_store: Optional[InMemoryAgentStateStore] = None,
    ) -> None:
        self.state_store = state_store or InMemoryAgentStateStore()
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent(tool_registry)
        self.reviewer = ReviewerAgent()

    async def run_task(
        self,
        *,
        user_id: str,
        task: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        state = self.state_store.get_or_create(user_id=user_id, session_id=session_id)
        context = context or {}

        if context.get("companion"):
            state.working_memory["companion"] = context["companion"]
        elif "companion" not in state.working_memory:
            state.working_memory["companion"] = "penguin"

        if context.get("city"):
            state.working_memory["city"] = context["city"]

        state.turn_count += 1
        state.recent_tasks.append(task)
        state.recent_tasks = state.recent_tasks[-10:]

        plan = self.planner.create_plan(task=task, context=context, state=state)
        execution_result = await self.executor.run_plan(user_id=user_id, plan=plan, state=state)

        review = self.reviewer.review(
            task=task,
            plan=plan,
            execution_trace=execution_result["execution_trace"],
            step_outputs=execution_result["step_outputs"],
            state=state,
        )

        state.last_plan = review["plan"]
        state.last_step_outputs = review["step_outputs"]
        state.updated_at = datetime.now(UTC).isoformat()

        return {
            "status": review["status"],
            "session_id": state.session_id,
            "final_response": review["final_response"],
            "plan": review["plan"],
            "execution_trace": review["execution_trace"],
            "memory": self.get_session_state(state.session_id),
        }

    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self.state_store.get_session(session_id)
        if session is None:
            return None

        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "turn_count": session.turn_count,
            "recent_tasks": list(session.recent_tasks),
            "last_plan": list(session.last_plan),
            "last_step_outputs": dict(session.last_step_outputs),
            "working_memory": dict(session.working_memory),
        }


def build_budgetbuddy_tool_registry(
    *,
    db: Any,
    llm_pipeline: Any,
    col_api: Any,
    function_system: Any,
) -> Dict[str, ToolFn]:
    """Create orchestrator tools by wrapping existing backend capabilities."""

    async def parse_expense_text(_user_id: str, payload: Dict[str, Any], _session: AgentSessionState) -> Dict[str, Any]:
        text = str(payload.get("text") or "").strip()
        parsed = await llm_pipeline.parse_expense(text)
        return {"status": "parsed", "parsed_data": parsed}

    async def add_expense(user_id: str, payload: Dict[str, Any], _session: AgentSessionState) -> Dict[str, Any]:
        expense_data = payload.get("expense_data")
        if not isinstance(expense_data, dict):
            raise ValueError("expense_data must be a dictionary")
        saved = await db.create_expense(user_id, expense_data)
        return {"status": "expense_added", "expense_id": saved.get("id"), "expense": saved}

    async def set_budget(user_id: str, payload: Dict[str, Any], _session: AgentSessionState) -> Dict[str, Any]:
        if float(payload.get("monthly_limit") or 0) <= 0:
            raise ValueError("monthly_limit must be greater than zero")
        saved = await db.create_budget(user_id, payload)
        return {"status": "budget_set", "budget": saved}

    async def query_expenses(user_id: str, payload: Dict[str, Any], _session: AgentSessionState) -> Dict[str, Any]:
        rows = await db.get_expenses(
            user_id,
            start_date=payload.get("start_date"),
            end_date=payload.get("end_date"),
            category=payload.get("category"),
            limit=int(payload.get("limit", 100)),
        )
        return {"status": "expenses_queried", "count": len(rows), "expenses": rows}

    async def get_budget_comparison(user_id: str, payload: Dict[str, Any], _session: AgentSessionState) -> Dict[str, Any]:
        data = await db.get_budget_comparison(
            user_id,
            month=payload.get("month"),
            category=payload.get("category"),
        )
        return {"status": "budget_compared", "comparison": data}

    async def get_cost_of_living(_user_id: str, payload: Dict[str, Any], _session: AgentSessionState) -> Dict[str, Any]:
        city = payload.get("city") or _session.working_memory.get("city") or "Charlotte, NC"
        data = await col_api.get_city_data(city)
        return {"status": "cost_of_living_fetched", "city": city, "data": data}

    async def function_call(user_id: str, payload: Dict[str, Any], _session: AgentSessionState) -> Dict[str, Any]:
        message = str(payload.get("message") or "").strip()
        data = await function_system.execute(message, user_id)
        return {"status": "function_executed", "result": data}

    return {
        "parse_expense_text": parse_expense_text,
        "add_expense": add_expense,
        "set_budget": set_budget,
        "query_expenses": query_expenses,
        "get_budget_comparison": get_budget_comparison,
        "get_cost_of_living": get_cost_of_living,
        "function_call": function_call,
    }
