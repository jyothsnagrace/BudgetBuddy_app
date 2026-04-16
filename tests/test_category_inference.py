"""
Test category inference for receipt parsing
"""

from receipt_parser import ReceiptParser

def test_category_inference():
    parser = ReceiptParser()
    
    test_cases = [
        # Food
        {"merchant": "Chipotle", "description": "Burrito bowl", "expected": "Food"},
        {"merchant": "Starbucks", "description": "Coffee", "expected": "Food"},
        {"merchant": "Walmart", "description": "Groceries", "expected": "Food"},
        {"merchant": "", "description": "Pizza dinner", "expected": "Food"},
        
        # Transportation
        {"merchant": "Shell", "description": "Gas station", "expected": "Transportation"},
        {"merchant": "Uber", "description": "Ride", "expected": "Transportation"},
        {"merchant": "", "description": "Parking fee", "expected": "Transportation"},
        
        # Entertainment
        {"merchant": "AMC", "description": "Movie tickets", "expected": "Entertainment"},
        {"merchant": "Netflix", "description": "Subscription", "expected": "Entertainment"},
        
        # Shopping
        {"merchant": "Target", "description": "Retail shopping", "expected": "Shopping"},
        {"merchant": "Amazon", "description": "Electronics", "expected": "Shopping"},
        
        # Bills
        {"merchant": "Comcast", "description": "Internet bill", "expected": "Bills"},
        {"merchant": "", "description": "Electric utility", "expected": "Bills"},
        
        # Healthcare
        {"merchant": "CVS", "description": "Pharmacy", "expected": "Healthcare"},
        {"merchant": "", "description": "Doctor visit", "expected": "Healthcare"},
        
        # Education
        {"merchant": "Amazon", "description": "Textbooks", "expected": "Education"},
        {"merchant": "", "description": "University tuition", "expected": "Education"},
        
        # Other (fallback)
        {"merchant": "Unknown Store", "description": "Misc items", "expected": "Other"},
        {"merchant": "", "description": "", "expected": "Other"},
    ]
    
    print("=" * 70)
    print("Testing Category Inference Logic")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        data = {
            "merchant": test["merchant"],
            "description": test["description"],
            "amount": 10.0
        }
        
        inferred = parser._infer_category(data)
        expected = test["expected"]
        status = "✅" if inferred == expected else "❌"
        
        print(f"\n{i}. Merchant: '{test['merchant']}' | Description: '{test['description']}'")
        print(f"   Expected: {expected} | Got: {inferred} {status}")
        
        if inferred == expected:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 70)

if __name__ == "__main__":
    test_category_inference()
