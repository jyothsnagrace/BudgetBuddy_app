import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agent_architecture import BudgetBuddyAgentOrchestrator  # noqa: E402


class FakeDatabase:
    def __init__(self) -> None:
        self.expenses: List[Dict[str, Any]] = []
        self.budgets: List[Dict[str, Any]] = []

    async def create_expense(self, user_id: str, expense_data: Dict[str, Any]) -> Dict[str, Any]:
        item = {"id": f"exp-{len(self.expenses) + 1}", "user_id": user_id, **expense_data}
        self.expenses.append(item)
        return item

    async def create_budget(self, user_id: str, budget_data: Dict[str, Any]) -> Dict[str, Any]:
        item = {"id": f"bud-{len(self.budgets) + 1}", "user_id": user_id, **budget_data}
        self.budgets.append(item)
        return item

    async def get_expenses(
        self,
        user_id: str,
        start_date: str = None,
        end_date: str = None,
        category: str = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        rows = [expense for expense in self.expenses if expense["user_id"] == user_id]
        if category:
            rows = [expense for expense in rows if expense.get("category") == category]
        return rows[:limit]

    async def get_budget_comparison(self, user_id: str, month: str = None, category: str = None) -> Dict[str, Any]:
        rows = [expense for expense in self.expenses if expense["user_id"] == user_id]
        if category:
            rows = [expense for expense in rows if expense.get("category") == category]
        spent = sum(float(expense.get("amount", 0)) for expense in rows)

        budgets = [budget for budget in self.budgets if budget["user_id"] == user_id]
        if category:
            budgets = [budget for budget in budgets if budget.get("category") == category]
        limit = float(budgets[-1].get("monthly_limit", 0)) if budgets else 0.0

        return {"budget": limit, "spent": spent, "remaining": limit - spent}


class FakePipeline:
    async def parse_expense(self, text: str) -> Dict[str, Any]:
        amount = 0.0
        for token in text.replace("$", "").split():
            try:
                amount = float(token)
                break
            except ValueError:
                continue

        lowered = text.lower()
        category = "Other"
        if "lunch" in lowered or "food" in lowered:
            category = "Food"
        elif "uber" in lowered or "bus" in lowered:
            category = "Transportation"

        return {
            "amount": amount,
            "category": category,
            "description": text,
            "date": "2026-03-24",
        }


class FakeCostOfLiving:
    async def get_city_data(self, city: str) -> Dict[str, Any]:
        return {"city": city, "cost_index": 88.2}


class FakeFunctionSystem:
    async def execute(self, message: str, user_id: str) -> Dict[str, Any]:
        return {"ok": True, "message": message, "user_id": user_id}


def build_tools(db: Any, pipeline: Any, col: Any, func: Any):
    async def parse_expense_text(_user_id, payload, _session):
        parsed = await pipeline.parse_expense(payload["text"])
        return {"status": "parsed", "parsed_data": parsed}

    async def add_expense(user_id, payload, _session):
        saved = await db.create_expense(user_id, payload["expense_data"])
        return {"status": "expense_added", "expense_id": saved["id"], "expense": saved}

    async def set_budget(user_id, payload, _session):
        saved = await db.create_budget(user_id, payload)
        return {"status": "budget_set", "budget": saved}

    async def query_expenses(user_id, payload, _session):
        rows = await db.get_expenses(
            user_id,
            start_date=payload.get("start_date"),
            end_date=payload.get("end_date"),
            category=payload.get("category"),
            limit=int(payload.get("limit", 100)),
        )
        return {"status": "expenses_queried", "count": len(rows), "expenses": rows}

    async def get_budget_comparison(user_id, payload, _session):
        data = await db.get_budget_comparison(
            user_id,
            month=payload.get("month"),
            category=payload.get("category"),
        )
        return {"status": "budget_compared", "comparison": data}

    async def get_cost_of_living(_user_id, payload, _session):
        data = await col.get_city_data(payload["city"])
        return {"status": "cost_of_living_fetched", "city": payload["city"], "data": data}

    async def function_call(user_id, payload, _session):
        data = await func.execute(payload["message"], user_id)
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


class AgentArchitectureTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        db = FakeDatabase()
        pipeline = FakePipeline()
        col = FakeCostOfLiving()
        func = FakeFunctionSystem()
        self.orchestrator = BudgetBuddyAgentOrchestrator(build_tools(db, pipeline, col, func))

    async def test_budget_expense_remaining_flow(self):
        result = await self.orchestrator.run_task(
            user_id="user-123",
            task="Set my food budget to 300 and I spent 25 on lunch then show my food expenses and remaining budget",
            context={"companion": "penguin"},
        )

        self.assertEqual(result["status"], "completed")
        actions = [step["action"] for step in result["plan"]]
        self.assertIn("set_budget", actions)
        self.assertIn("parse_expense_text", actions)
        self.assertIn("add_expense", actions)
        self.assertIn("query_expenses", actions)
        self.assertIn("get_budget_comparison", actions)

    async def test_session_memory_continuity(self):
        first = await self.orchestrator.run_task(
            user_id="user-123",
            task="Set my food budget to 300 and I spent 25 on lunch then show my food expenses and remaining budget",
            context={"companion": "cat"},
        )
        session_id = first["session_id"]

        second = await self.orchestrator.run_task(
            user_id="user-123",
            task="show my expenses",
            session_id=session_id,
        )

        self.assertEqual(second["session_id"], session_id)
        self.assertGreaterEqual(second["memory"]["turn_count"], 2)
        self.assertIn("show my expenses", second["memory"]["recent_tasks"])

    async def test_cost_of_living_and_query_flow(self):
        result = await self.orchestrator.run_task(
            user_id="user-123",
            task="What is the cost of living in Seattle, WA and show my expenses",
            context={"companion": "dragon"},
        )

        actions = [step["action"] for step in result["plan"]]
        self.assertIn("get_cost_of_living", actions)
        self.assertIn("query_expenses", actions)


if __name__ == "__main__":
    unittest.main()
