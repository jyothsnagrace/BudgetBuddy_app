"""
Test the parse-expense endpoint with authentication
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_parse_expense():
    """Test text parsing endpoint"""
    
    # Step 1: Login to get token
    print("=" * 60)
    print("Step 1: Login")
    print("=" * 60)
    
    login_response = requests.post(
        f"{API_URL}/api/auth/login",
        json={"username": "test"}  # Use your actual username
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(login_response.text)
        return
    
    login_data = login_response.json()
    token = login_data["token"]
    print(f"✓ Login successful")
    print(f"  Token: {token[:20]}...")
    
    # Step 2: Test parse-expense endpoint
    print("\n" + "=" * 60)
    print("Step 2: Parse Expense Text")
    print("=" * 60)
    
    test_text = "I spent 45 dollars on pizza"
    print(f"Input: '{test_text}'")
    
    parse_response = requests.post(
        f"{API_URL}/api/parse-expense",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={"text": test_text}
    )
    
    print(f"\nResponse Status: {parse_response.status_code}")
    
    if parse_response.status_code == 200:
        data = parse_response.json()
        print("✓ Parse successful!")
        print("\nParsed Data:")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Parse failed")
        print(f"Error: {parse_response.text}")
    
    # Step 3: Test parse-receipt endpoint
    print("\n" + "=" * 60)
    print("Step 3: Parse Receipt Image")
    print("=" * 60)
    
    receipt_path = r"C:\Users\jyoth\Downloads\Project_0210\BudgetBuddy\tests\fixtures\receipts\sample_receipt_2.png"
    
    import os
    if not os.path.exists(receipt_path):
        print(f"⚠ Receipt file not found: {receipt_path}")
        return
    
    print(f"Receipt: {receipt_path}")
    
    with open(receipt_path, "rb") as f:
        files = {"file": ("receipt.png", f, "image/png")}
        
        receipt_response = requests.post(
            f"{API_URL}/api/parse-receipt",
            headers={
                "Authorization": f"Bearer {token}"
            },
            files=files
        )
    
    print(f"\nResponse Status: {receipt_response.status_code}")
    
    if receipt_response.status_code == 200:
        data = receipt_response.json()
        print("✓ Parse successful!")
        print("\nParsed Data:")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Parse failed")
        print(f"Error: {receipt_response.text}")


if __name__ == "__main__":
    test_parse_expense()
