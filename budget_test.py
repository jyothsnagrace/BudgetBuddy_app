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

print("=" * 60)
print("BUDGET PERSISTENCE TEST")
print("=" * 60)

# Step 1: LOGIN
print("\n[STEP 1] LOGIN with username: test_user")
login_status, login_body = request('POST', '/api/auth/login', {'username': username})
print("LOGIN_STATUS=" + str(login_status))
print("LOGIN_BODY=" + login_body)

try:
    login_json = json.loads(login_body)
    token = login_json.get('token')
    user_id = login_json.get('user_id')
    print("TOKEN=" + str(token))
    print("USER_ID=" + str(user_id))
except Exception as e:
    print("ERROR parsing login response: " + str(e))
    token = None
    user_id = None

if not token:
    print("FAILED: No token received")
    exit(1)

headers = {'Authorization': 'Bearer ' + token}

# Step 2: SET BUDGET (using monthly_limit field)
print("\n[STEP 2] SET BUDGET of $3500.00 for 2026-04 with category=null")
budget_payload = {
    'monthly_limit': budget_amount,
    'month': budget_month,
    'category': None
}
print("Payload: " + json.dumps(budget_payload))
set_budget_status, set_budget_body = request('POST', '/api/budgets', budget_payload, headers)
print("SET_BUDGET_STATUS=" + str(set_budget_status))
print("SET_BUDGET_BODY=" + set_budget_body)

# Step 3: GET BUDGET
print("\n[STEP 3] GET BUDGET for month=2026-04")
get_budget_status, get_budget_body = request('GET', '/api/budgets?month=2026-04', None, headers)
print("GET_BUDGET_STATUS=" + str(get_budget_status))
print("GET_BUDGET_BODY=" + get_budget_body)

budget_found = False
try:
    budget_response = json.loads(get_budget_body)
    budget_list = budget_response.get('budgets', []) if isinstance(budget_response, dict) else (budget_response if isinstance(budget_response, list) else [])
    for budget in budget_list:
        if budget.get('month') == budget_month and budget.get('monthly_limit') == budget_amount:
            budget_found = True
            break
except Exception as e:
    print("ERROR parsing budget response: " + str(e))

print("BUDGET_FOUND_IN_DATABASE=" + str(budget_found))

# Step 4: CREATE EXPENSE
print("\n[STEP 4] CREATE EXPENSE of $50 in Food category on 2026-04-16")
expense_payload = {
    'amount': expense_amount,
    'category': expense_category,
    'description': expense_description,
    'date': expense_date
}
print("Payload: " + json.dumps(expense_payload))
create_expense_status, create_expense_body = request('POST', '/api/expenses', expense_payload, headers)
print("CREATE_EXPENSE_STATUS=" + str(create_expense_status))
print("CREATE_EXPENSE_BODY=" + create_expense_body)

expense_id = None
try:
    expense_json = json.loads(create_expense_body)
    expense_id = expense_json.get('id')
    print("EXPENSE_ID=" + str(expense_id))
except Exception as e:
    print("ERROR parsing expense response: " + str(e))

# Step 5: GET EXPENSES
print("\n[STEP 5] GET EXPENSES - Verify expense appears")
get_expenses_status, get_expenses_body = request('GET', '/api/expenses', None, headers)
print("GET_EXPENSES_STATUS=" + str(get_expenses_status))
print("GET_EXPENSES_BODY=" + get_expenses_body)

expense_in_list = False
try:
    expenses_response = json.loads(get_expenses_body)
    expense_list = expenses_response.get('expenses', []) if isinstance(expenses_response, dict) else (expenses_response if isinstance(expenses_response, list) else [])
    for expense in expense_list:
        if isinstance(expense, dict) and expense.get('amount') == expense_amount and expense.get('category') == expense_category:
            expense_in_list = True
            break
except Exception as e:
    print("ERROR parsing expenses response: " + str(e))

print("EXPENSE_FOUND_IN_LIST=" + str(expense_in_list))

# Step 6: GET BUDGET AGAIN - Verify it still shows
print("\n[STEP 6] GET BUDGET AGAIN - Verify it persists after expense creation")
get_budget_again_status, get_budget_again_body = request('GET', '/api/budgets?month=2026-04', None, headers)
print("GET_BUDGET_AGAIN_STATUS=" + str(get_budget_again_status))
print("GET_BUDGET_AGAIN_BODY=" + get_budget_again_body)

budget_still_found = False
try:
    budget_response = json.loads(get_budget_again_body)
    budget_list = budget_response.get('budgets', []) if isinstance(budget_response, dict) else (budget_response if isinstance(budget_response, list) else [])
    for budget in budget_list:
        if budget.get('month') == budget_month and budget.get('monthly_limit') == budget_amount:
            budget_still_found = True
            break
except Exception as e:
    print("ERROR parsing budget response: " + str(e))

print("BUDGET_STILL_PERSISTED=" + str(budget_still_found))

# Final Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print("LOGIN_STATUS: " + str(login_status))
print("TOKEN_RECEIVED: " + str(token is not None))
print("SET_BUDGET_STATUS: " + str(set_budget_status))
print("GET_BUDGET_STATUS: " + str(get_budget_status))
print("BUDGET_PERSISTED: " + str(budget_found))
print("CREATE_EXPENSE_STATUS: " + str(create_expense_status))
print("GET_EXPENSES_STATUS: " + str(get_expenses_status))
print("EXPENSE_FOUND: " + str(expense_in_list))
print("BUDGET_PERSISTS_AFTER_EXPENSE: " + str(budget_still_found))
print("\nOVERALL_TEST_RESULT: " + ("PASS" if all([login_status == 200, set_budget_status == 200, budget_found, create_expense_status == 200, expense_in_list, budget_still_found]) else "FAIL"))
print("=" * 60)
