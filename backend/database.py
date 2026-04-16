"""
Database Client for Supabase
Handles all database operations
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta

# Try to import Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("Warning: Supabase not available. Database functionality disabled.")
    Client = None


class DatabaseClient:
    """Supabase database client"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._connected = False
    
    async def connect(self):
        """Initialize Supabase client"""
        if not SUPABASE_AVAILABLE:
            print("[DB] Supabase library not available. Using mock mode.")
            self._connected = False
            return
            
        # Read environment variables at connection time (after load_dotenv)
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        
        print(f"[DB] Attempting Supabase connection...")
        print(f"[DB] SUPABASE_URL: {supabase_url[:20]}..." if supabase_url else "[DB] SUPABASE_URL: X missing")
        print(f"[DB] SUPABASE_KEY: {'OK' if supabase_key else 'X missing'}")
        
        if not supabase_url or not supabase_key:
            print("[DB] WARNING: Supabase credentials not configured")
            print("[DB] Using mock mode for development")
            self._connected = False
            return
        
        try:
            print("[DB] Creating Supabase client...")
            self.client = create_client(supabase_url, supabase_key)
            self._connected = True
            print("[DB] OK Connected to Supabase successfully")
        except Exception as e:
            print(f"[DB] ERROR: Supabase connection failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self._connected = False
    
    async def disconnect(self):
        """Clean up connections"""
        self.client = None
        self._connected = False
    
    async def health_check(self) -> bool:
        """Check database connection"""
        return self._connected
    
    # ============================================
    # USER OPERATIONS
    # ============================================
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        if not self._connected:
            return None
        
        try:
            response = self.client.table('users').select('*').eq('username', username).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None
    
    async def create_user(self, username: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """Create new user"""
        if not self._connected:
            return {
                'id': 'mock-user-id',
                'username': username,
                'display_name': display_name or username
            }
        
        try:
            data = {
                'username': username,
                'display_name': display_name or username,
                'selected_pet': 'penguin',
                'friendship_level': 1
            }
            
            response = self.client.table('users').insert(data).execute()
            return response.data[0]
        except Exception as e:
            raise Exception(f"Failed to create user: {e}")
    
    async def update_user_activity(self, user_id: str):
        """Update last activity timestamp"""
        if not self._connected:
            return
        
        try:
            self.client.table('users').update({
                'last_activity': datetime.now().isoformat()
            }).eq('id', user_id).execute()
        except Exception as e:
            print(f"Error updating activity: {e}")
    
    async def update_friendship_level(self, user_id: str, level: int):
        """Update friendship level"""
        if not self._connected:
            return
        
        try:
            self.client.table('users').update({
                'friendship_level': level
            }).eq('id', user_id).execute()
        except Exception as e:
            print(f"Error updating friendship: {e}")
    
    async def update_user_pet(self, user_id: str, pet: str):
        """Update user's selected pet"""
        if not self._connected:
            return
        
        valid_pets = ['penguin', 'dragon', 'capybara', 'cat']
        if pet not in valid_pets:
            raise ValueError(f"Invalid pet. Must be one of {valid_pets}")
        
        try:
            self.client.table('users').update({
                'selected_pet': pet
            }).eq('id', user_id).execute()
        except Exception as e:
            raise Exception(f"Error updating pet: {e}")
    
    # ============================================
    # EXPENSE OPERATIONS
    # ============================================
    
    async def create_expense(self, user_id: str, expense_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new expense"""
        if not self._connected:
            return {
                'id': 'mock-expense-id',
                'user_id': user_id,
                **expense_data,
                'created_at': datetime.now().isoformat()
            }
        
        try:
            data = {
                'user_id': user_id,
                'amount': float(expense_data['amount']),
                'category': expense_data['category'],
                'description': expense_data.get('description', ''),
                'expense_date': expense_data['date'],
                'metadata': expense_data.get('metadata', {})
            }
            
            response = self.client.table('expenses').insert(data).execute()
            return response.data[0]
        except Exception as e:
            raise Exception(f"Failed to create expense: {e}")
    
    async def get_expenses(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get user's expenses with filters"""
        if not self._connected:
            return []
        
        try:
            query = self.client.table('expenses').select('*').eq('user_id', user_id)
            
            if start_date:
                query = query.gte('expense_date', start_date)
            
            if end_date:
                query = query.lte('expense_date', end_date)
            
            if category:
                query = query.eq('category', category)
            
            query = query.order('created_at', desc=True).limit(limit)
            
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Error fetching expenses: {e}")
            return []
    
    async def delete_expense(self, user_id: str, expense_id: str):
        """Delete an expense"""
        if not self._connected:
            return
        
        try:
            self.client.table('expenses').delete().eq('id', expense_id).eq('user_id', user_id).execute()
        except Exception as e:
            raise Exception(f"Failed to delete expense: {e}")
    
    async def get_category_totals(self, user_id: str, month: Optional[str] = None) -> Dict[str, float]:
        """Get spending totals by category"""
        if not self._connected:
            return {}
        
        try:
            query = self.client.table('expenses').select('category, amount').eq('user_id', user_id)
            
            if month:
                # Filter by month (YYYY-MM)
                start_date = f"{month}-01"
                end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=31)).strftime('%Y-%m-%d')
                query = query.gte('expense_date', start_date).lt('expense_date', end_date)
            
            response = query.execute()
            
            # Sum by category
            totals = {}
            for expense in response.data:
                category = expense['category']
                amount = float(expense['amount'])
                totals[category] = totals.get(category, 0) + amount
            
            return totals
        except Exception as e:
            print(f"Error fetching category totals: {e}")
            return {}
    
    # ============================================
    # BUDGET OPERATIONS
    # ============================================
    
    async def create_budget(self, user_id: str, budget_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update budget"""
        if not self._connected:
            return {
                'id': 'mock-budget-id',
                'user_id': user_id,
                **budget_data
            }
        
        try:
            month = budget_data.get('month', datetime.now().strftime('%Y-%m'))
            month_date = f"{month}-01"
            
            data = {
                'user_id': user_id,
                'monthly_limit': float(budget_data['monthly_limit']),
                'category': budget_data.get('category'),
                'month': month_date
            }
            
            # Upsert (insert or update)
            response = self.client.table('budgets').upsert(data).execute()
            return response.data[0]
        except Exception as e:
            raise Exception(f"Failed to create budget: {e}")
    
    async def get_budgets(self, user_id: str, month: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user's budgets"""
        if not self._connected:
            return []
        
        try:
            query = self.client.table('budgets').select('*').eq('user_id', user_id)
            
            if month:
                month_date = f"{month}-01"
                query = query.eq('month', month_date)
            
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Error fetching budgets: {e}")
            return []
    
    async def get_budget_comparison(self, user_id: str, month: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
        """Get budget vs actual comparison"""
        if not self._connected:
            return {}
        
        try:
            # Use the budget_comparison view
            query = self.client.table('budget_comparison').select('*').eq('user_id', user_id)
            
            if month:
                month_date = f"{month}-01"
                query = query.eq('month', month_date)
            
            if category:
                query = query.eq('category', category)
            
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Error fetching budget comparison: {e}")
            return {}
    
    # ============================================
    # CALENDAR OPERATIONS
    # ============================================
    
    async def get_calendar_entries(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get calendar entries"""
        if not self._connected:
            return []
        
        try:
            query = self.client.table('calendar_entries').select('*').eq('user_id', user_id)
            
            if start_date:
                query = query.gte('display_date', start_date)
            
            if end_date:
                query = query.lte('display_date', end_date)
            
            query = query.order('display_date', desc=False)
            
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Error fetching calendar entries: {e}")
            return []
    
    # ============================================
    # CHAT HISTORY
    # ============================================
    
    async def save_chat_message(self, user_id: str, message: str, sender: str):
        """Save chat message"""
        if not self._connected:
            return
        
        try:
            data = {
                'user_id': user_id,
                'message': message,
                'sender': sender
            }
            
            self.client.table('chat_history').insert(data).execute()
        except Exception as e:
            print(f"Error saving chat: {e}")
    
    async def get_chat_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent chat history"""
        if not self._connected:
            return []
        
        try:
            response = self.client.table('chat_history').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            print(f"Error fetching chat history: {e}")
            return []
    
    # ============================================
    # ANALYTICS & CONTEXT
    # ============================================
    
    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user context for LLM"""
        if not self._connected:
            return {
                'user_id': user_id,
                'budget': 2000,
                'total_spent': 0,
                'selected_pet': 'penguin',
                'friendship_level': 1
            }
        
        try:
            # Get user info
            user = await self.get_user_by_id(user_id)
            
            # Get current month expenses
            current_month = datetime.now().strftime('%Y-%m')
            expenses = await self.get_expenses(user_id, start_date=f"{current_month}-01")
            
            # Get budgets
            budgets = await self.get_budgets(user_id, month=current_month)
            
            # Calculate totals
            total_spent = sum(float(e['amount']) for e in expenses)
            category_totals = {}
            for e in expenses:
                cat = e['category']
                category_totals[cat] = category_totals.get(cat, 0) + float(e['amount'])
            
            # Get total budget
            total_budget = next(
                (float(b['monthly_limit']) for b in budgets if b['category'] is None),
                2000
            )
            
            return {
                'user_id': user_id,
                'username': user.get('username', ''),
                'selected_pet': user.get('selected_pet', 'penguin'),
                'friendship_level': user.get('friendship_level', 1),
                'budget': total_budget,
                'total_spent': total_spent,
                'remaining': total_budget - total_spent,
                'category_totals': category_totals,
                'recent_expenses': expenses[:10],
                'expense_count': len(expenses)
            }
        except Exception as e:
            print(f"Error getting user context: {e}")
            return {'user_id': user_id}
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        if not self._connected:
            return None
        
        try:
            response = self.client.table('users').select('*').eq('id', user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test():
        db = DatabaseClient()
        await db.connect()
        
        # Test user context
        context = await db.get_user_context('test-user-id')
        print("User context:", context)
    
    asyncio.run(test())
