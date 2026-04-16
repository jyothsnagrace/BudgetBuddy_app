#!/usr/bin/env python3
"""
Parse receipt using Groq+Tesseract and save to database
Bypasses the API endpoint issue by using direct parser + API save
"""

import asyncio
import requests
import sys
from pathlib import Path
from receipt_parser import ReceiptParser

# Configuration
RECEIPT_PATH = r"C:\Users\jyoth\Downloads\Project_0210\BudgetBuddy\tests\fixtures\receipts\sample_receipt_2.png"
API_BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"


async def main():
    print("=" * 60)
    print("RECEIPT PARSER & DATABASE SAVER")
    print("=" * 60)
    
    # Check if receipt exists
    receipt_path = Path(RECEIPT_PATH)
    if not receipt_path.exists():
        print(f"❌ Receipt not found: {RECEIPT_PATH}")
        print("\nPlease update RECEIPT_PATH in this script with your receipt image path.")
        sys.exit(1)
    
    print(f"\n📄 Receipt: {receipt_path.name}")
    print(f"   Size: {receipt_path.stat().st_size:,} bytes")
    
    # Step 1: Parse receipt using standalone parser (WORKS!)
    print("\n" + "=" * 60)
    print("STEP 1: Parse Receipt with Groq + Tesseract")
    print("=" * 60)
    
    parser = ReceiptParser()
    
    with open(receipt_path, "rb") as f:
        image_data = f.read()
    
    try:
        parsed_data = await parser.parse_receipt(image_data)
        print("\n✅ Receipt parsed successfully!")
        print(f"\n   Amount:      ${parsed_data['amount']:.2f}")
        print(f"   Category:    {parsed_data['category']}")
        print(f"   Description: {parsed_data['description']}")
        print(f"   Date:        {parsed_data['date']}")
        if 'merchant' in parsed_data:
            print(f"   Merchant:    {parsed_data['merchant']}")
    except Exception as e:
        print(f"\n❌ Failed to parse receipt: {e}")
        sys.exit(1)
    
    # Step 2: Login to get token
    print("\n" + "=" * 60)
    print("STEP 2: Login to API")
    print("=" * 60)
    
    try:
        login_response = requests.post(
            f"{API_BASE_URL}/api/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=10
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            sys.exit(1)
        
        token = login_response.json()["token"]
        user_id = login_response.json()["user_id"]
        print(f"✅ Login successful")
        print(f"   User ID: {user_id}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        print("\n   Is the backend server running?")
        print("   Start it with: python backend\\main.py")
        sys.exit(1)
    
    # Step 3: Save to database
    print("\n" + "=" * 60)
    print("STEP 3: Save Expense to Database")
    print("=" * 60)
    
    expense_data = {
        "amount": parsed_data["amount"],
        "category": parsed_data["category"],
        "description": parsed_data["description"],
        "date": parsed_data["date"]
    }
    
    try:
        save_response = requests.post(
            f"{API_BASE_URL}/api/expenses",
            json=expense_data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if save_response.status_code == 200:
            saved_expense = save_response.json()["expense"]
            print("\n✅ Expense saved to database!")
            print(f"\n   Expense ID:  {saved_expense['id']}")
            print(f"   Amount:      ${saved_expense['amount']:.2f}")
            print(f"   Category:    {saved_expense['category']}")
            print(f"   Description: {saved_expense['description']}")
            print(f"   Date:        {saved_expense['date']}")
            print(f"   User ID:     {saved_expense['user_id']}")
        else:
            print(f"❌ Failed to save expense: {save_response.status_code}")
            print(f"   Response: {save_response.json()}")
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        sys.exit(1)
    
    # Success!
    print("\n" + "=" * 60)
    print("✅ SUCCESS! Receipt parsed and saved to database")
    print("=" * 60)
    print(f"\nYour expense of ${parsed_data['amount']:.2f} has been added to your budget.")


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(main())
