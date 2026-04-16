#!/usr/bin/env python3
"""Test receipt upload and save to database"""

import requests
import os
from pathlib import Path

RECEIPT_PATH = r"C:\Users\jyoth\Downloads\Project_0210\BudgetBuddy\tests\fixtures\receipts\sample_receipt_2.png"

# Login first
print("Step 1: Login...")
login_response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"username": "admin", "password": "admin123"}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["token"]
user_id = login_response.json()["user_id"]
print(f"✓ Login successful (user_id: {user_id})")

# Parse receipt
print("\nStep 2: Parse receipt...")
with open(RECEIPT_PATH, "rb") as f:
    files = {"file": ("receipt.png", f, "image/png")}
    headers = {"Authorization": f"Bearer {token}"}
    
    parse_response = requests.post(
        "http://localhost:8000/api/parse-receipt",
        files=files,
        headers=headers
    )

print(f"Status: {parse_response.status_code}")
if parse_response.status_code == 200:
    parsed_data = parse_response.json()["parsed_data"]
    print(f"✓ Receipt parsed successfully!")
    print(f"  Amount: ${parsed_data['amount']}")
    print(f"  Category: {parsed_data['category']}")
    print(f"  Description: {parsed_data['description']}")
    print(f"  Date: {parsed_data['date']}")
    
    # Save to database
    print("\nStep 3: Save expense to database...")
    expense_data = {
        "amount": parsed_data["amount"],
        "category": parsed_data["category"],
        "description": parsed_data["description"],
        "date": parsed_data["date"]
    }
    
    save_response = requests.post(
        "http://localhost:8000/api/expenses",
        json=expense_data,
        headers=headers
    )
    
    print(f"Status: {save_response.status_code}")
    if save_response.status_code == 200:
        saved_expense = save_response.json()["expense"]
        print(f"✓ Expense saved to database!")
        print(f"  Expense ID: {saved_expense['id']}")
        print(f"  Amount: ${saved_expense['amount']}")
        print(f"  Category: {saved_expense['category']}")
        print(f"  Description: {saved_expense['description']}")
    else:
        print(f"❌ Failed to save expense")
        print(save_response.json())
else:
    print(f"❌ Parse failed")
    print(parse_response.json())
