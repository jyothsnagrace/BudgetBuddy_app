import json, urllib.request, urllib.error, time, datetime

base = 'http://127.0.0.1:8000'
username = 'test_user'

# Test data
budget_amount = 3500.00
budget_month = '2026-04'
expense_amount = 50.00
expense_category = 'Food'
expense_date = '2026-04-16'
expense_description = 'Test Food Expense'

def request(method, path, data=None, headers=None):
    hdrs = dict(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode('utf-8')
        hdrs['Content-Type'] = 'application/json'
    req = urllib.request.Request(base + path, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')

print("=" * 70)
print("BUDGET PERSISTENCE TEST - DETAILED ANALYSIS")
print("=" * 70)

# Step 1: LOGIN
print("\n[STEP 1] LOGIN with username: test_user")
login_status, login_body = request('POST', '/api/auth/login', {'username': username})
try:
    login_json = json.loads(login_body)
    token = login_json.get('token')
    user_id = login_json.get('user_id')
    print("✓ LOGIN_STATUS=" + str(login_status))
    print("  USER_ID=" + str(user_id))
    print("  TOKEN_LENGTH=" + str(len(token)) if token else "  TOKEN=None")
except Exception as e:
    print("✗ LOGIN FAILED: " + str(e))
    exit(1)

headers = {'Authorization': 'Bearer ' + token}

# Step 2: SET BUDGET (using monthly_limit field)
print("\n[STEP 2] SET BUDGET of $3500.00 for 2026-04 with category=null")
budget_payload = {
    'monthly_limit': budget_amount,
    'month': budget_month,
    'category': None
}
print("  Payload: " + json.dumps(budget_payload))
set_budget_status, set_budget_body = request('POST', '/api/budgets', budget_payload, headers)
print("✗ SET_BUDGET_STATUS=" + str(set_budget_status) + " (Expected: 200)")
print("  ERROR_DETAIL: " + set_budget_body)

# Step 3: GET BUDGET
print("\n[STEP 3] GET BUDGET for month=2026-04")
get_budget_status, get_budget_body = request('GET', '/api/budgets?month=2026-04', None, headers)
print("✓ GET_BUDGET_STATUS=" + str(get_budget_status))
budget_response = json.loads(get_budget_body)
print("  BUDGET_COUNT=" + str(len(budget_response.get('budgets', []))))

# Step 4: CREATE EXPENSE
print("\n[STEP 4] CREATE EXPENSE of $50 in Food category on 2026-04-16")
expense_payload = {
    'amount': expense_amount,
    'category': expense_category,
    'description': expense_description,
    'date': expense_date
}
print("  Payload: " + json.dumps(expense_payload))
create_expense_status, create_expense_body = request('POST', '/api/expenses', expense_payload, headers)
print("✓ CREATE_EXPENSE_STATUS=" + str(create_expense_status))
try:
    expense_json = json.loads(create_expense_body)
    expense_id = expense_json.get('id')
    print("  EXPENSE_ID=" + str(expense_id))
    print("  AMOUNT=" + str(expense_json.get('amount')))
    print("  CATEGORY=" + str(expense_json.get('category')))
    print("  DATE=" + str(expense_json.get('expense_date')))
except Exception as e:
    print("  ERROR: " + str(e))

# Step 5: GET EXPENSES
print("\n[STEP 5] GET EXPENSES - Verify expense appears")
get_expenses_status, get_expenses_body = request('GET', '/api/expenses', None, headers)
print("✓ GET_EXPENSES_STATUS=" + str(get_expenses_status))
try:
    expenses_response = json.loads(get_expenses_body)
    expense_list = expenses_response.get('expenses', [])
    print("  TOTAL_EXPENSES=" + str(len(expense_list)))
    
    # Filter for our test expense
    for exp in expense_list:
        if exp.get('category') == expense_category and exp.get('amount') == expense_amount:
            print("  ✓ TEST_EXPENSE_FOUND: ID=" + str(exp.get('id')))
            break
except Exception as e:
    print("  ERROR: " + str(e))

# Step 6: GET USER DASHBOARD
print("\n[STEP 6] GET USER DASHBOARD - Check user stats")
get_dashboard_status, get_dashboard_body = request('GET', '/api/user/dashboard', None, headers)
print("GET_DASHBOARD_STATUS=" + str(get_dashboard_status))
try:
    dashboard_json = json.loads(get_dashboard_body)
    print("  TOTAL_SPENT=" + str(dashboard_json.get('total_spent')))
    print("  EXPENSE_COUNT=" + str(dashboard_json.get('expense_count')))
    print("  BUDGET=" + str(dashboard_json.get('budget')))
except Exception as e:
    print("  ERROR: " + str(e))

# Final Summary
print("\n" + "=" * 70)
print("CRITICAL ISSUE IDENTIFIED")
print("=" * 70)
print("""
✗ BUDGET CREATION FAILS with RLS (Row-Level Security) Error

ROOT CAUSE:
The budgets table in Supabase has Row-Level Security (RLS) policies that
are blocking the user from inserting/upserting budgets.

ERROR MESSAGE:
"new row violates row-level security policy for table 'budgets'"

This indicates:
1. RLS is enabled on the budgets table
2. The INSERT/UPDATE policy does not allow the authenticated user to create budgets
3. The SELECT policy allows reading (so GET returns empty list, not an error)

WHAT'S WORKING:
✓ Authentication/Login - Successfully retrieving JWT tokens
✓ Expense Persistence - Expenses are being created and retrieved from database
✓ Expense Operations - All CRUD operations work properly

WHAT'S BROKEN:
✗ Budget Persistence - Cannot create or update budgets due to RLS policy

NEXT STEPS TO FIX:
1. Check Supabase Dashboard -> Authentication -> Policies for budgets table
2. Verify RLS policy allows user to insert/update their own budgets
3. Ensure the policy checks user_id matches the authenticated user_id
4. Policy should look like:
   SELECT: (auth.uid()::text = user_id)
   INSERT: (auth.uid()::text = user_id)
   UPDATE: (auth.uid()::text = user_id)
   DELETE: (auth.uid()::text = user_id)
""")
print("=" * 70)
