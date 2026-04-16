"""
Parse receipt and save to database
Uses: Groq LLM + Tesseract OCR + Database API
"""

import asyncio
import sys
import os
import requests
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from receipt_parser import ReceiptParser


async def parse_and_save_receipt():
    """Parse receipt and save to database"""
    receipt_path = r"C:\Users\jyoth\Downloads\Project_0210\BudgetBuddy\tests\fixtures\receipts\sample_receipt_2.png"
    
    print("=" * 60)
    print("PARSE RECEIPT & SAVE TO DATABASE")
    print("=" * 60)
    print(f"\n📄 Receipt: {Path(receipt_path).name}")
    
    # Check if file exists
    if not os.path.exists(receipt_path):
        print(f"\n✗ Error: Receipt file not found!")
        print(f"  Path: {receipt_path}")
        return
    
    print(f"   Size: {os.path.getsize(receipt_path):,} bytes")
    
    # STEP 1: Parse Receipt
    print("\n" + "=" * 60)
    print("STEP 1: Parse Receipt with Groq + Tesseract")
    print("=" * 60)
    
    try:
        parser = ReceiptParser()
        
        print(f"\nParser initialized:")
        print(f"  - Groq: {'✓' if parser.use_groq else '✗'}")
        print(f"  - Tesseract: {'✓' if parser.use_tesseract else '✗'}")
        print(f"  - Gemini Vision: {'✓' if parser.use_gemini else '✗'}")
        
        print("\nParsing receipt...")
        
        with open(receipt_path, "rb") as f:
            image_data = f.read()
        
        result = await parser.parse_receipt(image_data)
        
        print("\n✅ Receipt parsed successfully!")
        print(f"\n   Amount:      ${result.get('amount', 'N/A'):.2f}")
        print(f"   Category:    {result.get('category', 'N/A')}")
        print(f"   Description: {result.get('description', 'N/A')}")
        print(f"   Date:        {result.get('date', 'N/A')}")
        if 'merchant' in result:
            print(f"   Merchant:    {result.get('merchant', 'N/A')}")
        
    except Exception as e:
        print(f"\n✗ Failed to parse receipt: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # STEP 2: Login
    print("\n" + "=" * 60)
    print("STEP 2: Login to API")
    print("=" * 60)
    
    try:
        login_response = requests.post(
            "http://localhost:8000/api/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=10
        )
        
        if login_response.status_code != 200:
            print(f"\n✗ Login failed: {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return
        
        token = login_response.json()["token"]
        user_id = login_response.json()["user_id"]
        print(f"\n✅ Login successful")
        print(f"   User ID: {user_id}")
        
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Connection error: Could not connect to backend server")
        print(f"\n   Is the backend server running?")
        print(f"   Start it with: python backend\\main.py")
        return
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return
    
    # STEP 3: Save to Database
    print("\n" + "=" * 60)
    print("STEP 3: Save Expense to Database")
    print("=" * 60)
    
    expense_data = {
        "amount": result["amount"],
        "category": result["category"],
        "description": result["description"],
        "date": result["date"]
    }
    
    try:
        save_response = requests.post(
            "http://localhost:8000/api/expenses",
            json=expense_data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if save_response.status_code == 200:
            response_data = save_response.json()
            print(f"\n✅ Expense saved to database!")
            print(f"\n   Full response: {response_data}")
            
            if "expense" in response_data:
                saved_expense = response_data["expense"]
                print(f"\n   Expense ID:  {saved_expense['id']}")
                print(f"   Amount:      ${saved_expense['amount']:.2f}")
                print(f"   Category:    {saved_expense['category']}")
                print(f"   Description: {saved_expense['description']}")
                print(f"   Date:        {saved_expense['date']}")
                print(f"   User ID:     {saved_expense['user_id']}")
            else:
                print(f"\n   Data saved successfully!")
        else:
            print(f"\n✗ Failed to save expense: {save_response.status_code}")
            print(f"   Response: {save_response.json()}")
            return
            
    except Exception as e:
        print(f"\n✗ Error saving expense: {e}")
        return
    
    # Success!
    print("\n" + "=" * 60)
    print("✅ SUCCESS! Receipt parsed and saved to database")
    print("=" * 60)
    print(f"\nYour ${result['amount']:.2f} expense has been added to your budget!")


if __name__ == "__main__":
    asyncio.run(parse_and_save_receipt())
