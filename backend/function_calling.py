"""
Function Calling System with JSON Schema Validation
Structured LLM-to-Function execution
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from jsonschema import validate, ValidationError

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError as e:
    genai = None
    GEMINI_AVAILABLE = False
    print(f"Warning: Gemini import failed in function calling: {e}")

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_AVAILABLE and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


class FunctionCallingSystem:
    """
    Handles structured function calling from LLM
    Validates against JSON schemas before execution
    """
    
    # Function definitions with JSON schemas
    FUNCTIONS = {
        "add_expense": {
            "name": "add_expense",
            "description": "Add a new expense to the user's budget",
            "parameters": {
                "type": "object",
                "required": ["amount", "category", "date"],
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Expense amount in dollars",
                        "minimum": 0
                    },
                    "category": {
                        "type": "string",
                        "enum": ["Food", "Transportation", "Entertainment", "Shopping", "Bills", "Healthcare", "Education", "Other"],
                        "description": "Expense category"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the expense",
                        "maxLength": 200
                    },
                    "date": {
                        "type": "string",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                        "description": "Date in YYYY-MM-DD format"
                    }
                }
            }
        },
        "set_budget": {
            "name": "set_budget",
            "description": "Set monthly budget limit for a category or overall",
            "parameters": {
                "type": "object",
                "required": ["amount"],
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Budget amount in dollars",
                        "minimum": 0
                    },
                    "category": {
                        "type": "string",
                        "enum": ["Food", "Transportation", "Entertainment", "Shopping", "Bills", "Healthcare", "Education", "Other"],
                        "description": "Category to set budget for (optional, leave empty for total budget)"
                    },
                    "month": {
                        "type": "string",
                        "pattern": "^\\d{4}-\\d{2}$",
                        "description": "Month in YYYY-MM format (defaults to current month)"
                    }
                }
            }
        },
        "query_expenses": {
            "name": "query_expenses",
            "description": "Query and retrieve user's expenses with filters",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["Food", "Transportation", "Entertainment", "Shopping", "Bills", "Healthcare", "Education", "Other"],
                        "description": "Filter by category"
                    },
                    "start_date": {
                        "type": "string",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                        "description": "Start date (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                        "description": "End date (YYYY-MM-DD)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 50
                    }
                }
            }
        },
        "get_budget_status": {
            "name": "get_budget_status",
            "description": "Get current budget status and remaining amount",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["Food", "Transportation", "Entertainment", "Shopping", "Bills", "Healthcare", "Education", "Other"],
                        "description": "Get status for specific category (optional)"
                    }
                }
            }
        }
    }
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash') if GEMINI_AVAILABLE and GEMINI_API_KEY else None
        # Import database client (avoid circular import)
        from database import DatabaseClient
        self.db = DatabaseClient()
    
    def get_function_definitions(self) -> List[Dict]:
        """Get all function definitions for LLM"""
        return list(self.FUNCTIONS.values())
    
    async def execute(self, user_message: str, user_id: str) -> Dict[str, Any]:
        """
        Parse user message, identify function call, validate, and execute
        """
        # Stage 1: Identify and extract function call
        function_call = await self._identify_function_call(user_message)
        
        if not function_call:
            return {
                "error": "No valid function call identified",
                "message": "I couldn't understand what action to take. Try being more specific."
            }
        
        function_name = function_call.get('function')
        arguments = function_call.get('arguments', {})
        
        # Stage 2: Validate against schema
        try:
            self._validate_function_call(function_name, arguments)
        except ValidationError as e:
            return {
                "error": "Invalid function arguments",
                "message": f"Validation failed: {e.message}"
            }
        
        # Stage 3: Execute function
        try:
            result = await self._execute_function(function_name, arguments, user_id)
            return {
                "success": True,
                "function": function_name,
                "arguments": arguments,
                "result": result
            }
        except Exception as e:
            return {
                "error": "Execution failed",
                "message": str(e)
            }
    
    async def _identify_function_call(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Use LLM to identify which function to call and extract arguments
        """
        # Build function list for prompt
        function_list = []
        for func in self.FUNCTIONS.values():
            function_list.append(f"- {func['name']}: {func['description']}")
        
        functions_text = "\n".join(function_list)
        
        prompt = f"""You are a function calling assistant. Analyze the user's message and determine which function to call.

Available functions:
{functions_text}

User message: "{message}"

If the user wants to add an expense, use "add_expense".
If the user wants to set a budget, use "set_budget".
If the user wants to query expenses, use "query_expenses".
If the user wants to check budget status, use "get_budget_status".

Return ONLY a JSON object with:
{{
  "function": "<function_name>",
  "arguments": {{
    "arg1": "value1",
    "arg2": "value2"
  }}
}}

Function schemas:

add_expense:
- amount (required): number
- category (required): one of [Food, Transportation, Entertainment, Shopping, Bills, Healthcare, Education, Other]
- description (optional): string
- date (required): YYYY-MM-DD format (use today if not specified: {date.today().isoformat()})

set_budget:
- amount (required): number
- category (optional): category name or null for total budget
- month (optional): YYYY-MM format (current month if not specified)

query_expenses:
- category (optional): category to filter by
- start_date (optional): YYYY-MM-DD
- end_date (optional): YYYY-MM-DD
- limit (optional): number of results

get_budget_status:
- category (optional): specific category to check

Return ONLY valid JSON, no other text."""

        if not self.model:
            return None
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.2,
                    'max_output_tokens': 512,
                }
            )
            
            # Extract and parse JSON
            json_text = self._extract_json(response.text)
            function_call = json.loads(json_text)
            
            return function_call
            
        except Exception as e:
            print(f"Function identification failed: {e}")
            return None
    
    def _validate_function_call(self, function_name: str, arguments: Dict[str, Any]):
        """Validate function call against schema"""
        if function_name not in self.FUNCTIONS:
            raise ValidationError(f"Unknown function: {function_name}")
        
        schema = self.FUNCTIONS[function_name]['parameters']
        validate(instance=arguments, schema=schema)
    
    async def _execute_function(
        self, 
        function_name: str, 
        arguments: Dict[str, Any],
        user_id: str
    ) -> Any:
        """Execute the validated function"""
        if function_name == "add_expense":
            return await self._add_expense(user_id, arguments)
        
        elif function_name == "set_budget":
            return await self._set_budget(user_id, arguments)
        
        elif function_name == "query_expenses":
            return await self._query_expenses(user_id, arguments)
        
        elif function_name == "get_budget_status":
            return await self._get_budget_status(user_id, arguments)
        
        else:
            raise ValueError(f"Function not implemented: {function_name}")
    
    async def _add_expense(self, user_id: str, args: Dict) -> Dict:
        """Execute add_expense function"""
        expense_data = {
            'amount': float(args['amount']),
            'category': args['category'],
            'description': args.get('description', ''),
            'date': args['date']
        }
        
        result = await self.db.create_expense(user_id, expense_data)
        
        return {
            "message": f"✅ Added {args['category']} expense: ${args['amount']:.2f}",
            "expense_id": result['id'],
            "details": expense_data
        }
    
    async def _set_budget(self, user_id: str, args: Dict) -> Dict:
        """Execute set_budget function"""
        budget_data = {
            'monthly_limit': float(args['amount']),
            'category': args.get('category'),
            'month': args.get('month', datetime.now().strftime('%Y-%m'))
        }
        
        result = await self.db.create_budget(user_id, budget_data)
        
        category_text = budget_data['category'] if budget_data['category'] else "total"
        
        return {
            "message": f"✅ Set {category_text} budget to ${args['amount']:.2f}",
            "budget_id": result['id'],
            "details": budget_data
        }
    
    async def _query_expenses(self, user_id: str, args: Dict) -> Dict:
        """Execute query_expenses function"""
        expenses = await self.db.get_expenses(
            user_id,
            category=args.get('category'),
            start_date=args.get('start_date'),
            end_date=args.get('end_date'),
            limit=args.get('limit', 50)
        )
        
        total = sum(e['amount'] for e in expenses)
        
        return {
            "message": f"Found {len(expenses)} expenses",
            "expenses": expenses,
            "total": total,
            "count": len(expenses)
        }
    
    async def _get_budget_status(self, user_id: str, args: Dict) -> Dict:
        """Execute get_budget_status function"""
        category = args.get('category')
        
        budget_data = await self.db.get_budget_comparison(
            user_id,
            category=category
        )
        
        return {
            "message": "📊 Budget status retrieved",
            "status": budget_data
        }
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response"""
        import re
        
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Find JSON object
        json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return text.strip()


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test():
        system = FunctionCallingSystem()
        
        # Test function calling
        result = await system.execute(
            "Add a $25 expense for dinner at Italian restaurant",
            user_id="test-user-123"
        )
        
        print("Result:", json.dumps(result, indent=2))
    
    asyncio.run(test())
