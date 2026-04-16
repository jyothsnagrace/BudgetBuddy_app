"""
Test date parsing fixes
1. Dates without years should use current year
2. No date subtraction/timezone issues
"""

import asyncio
from datetime import date
from llm_pipeline import LLMPipeline

async def test_date_parsing():
    pipeline = LLMPipeline()
    
    test_cases = [
        "Spent $25 on groceries Jan 10",
        "Dinner on March 5 for $40",
        "Gas $40 yesterday",
        "Lunch today $15",
        "Coffee $5",  # No date specified
        "Movie tickets $30 on 2025-12-25",  # With year
    ]
    
    print("=" * 60)
    print("Testing Date Parsing Fixes")
    print("=" * 60)
    print(f"Current Year: {date.today().year}")
    print(f"Today's Date: {date.today().isoformat()}")
    print("=" * 60)
    
    for test_input in test_cases:
        print(f"\nInput: '{test_input}'")
        try:
            result = await pipeline.parse_expense(test_input)
            print(f"✅ Parsed Date: {result['date']}")
            print(f"   Amount: ${result['amount']}")
            print(f"   Category: {result['category']}")
            print(f"   Description: {result['description']}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_date_parsing())
