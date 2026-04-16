"""
Quick test of receipt parser with specific receipt image
"""

import asyncio
import sys
import os
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from receipt_parser import ReceiptParser


async def test_specific_receipt():
    """Test with specific receipt image"""
    receipt_path = r"C:\Users\jyoth\Downloads\Project_0210\BudgetBuddy\tests\fixtures\receipts\sample_receipt_2.png"
    
    print("=" * 60)
    print("TESTING RECEIPT PARSER")
    print("=" * 60)
    print(f"\nReceipt: {receipt_path}")
    
    # Check if file exists
    if not os.path.exists(receipt_path):
        print(f"\n✗ Error: Receipt file not found!")
        print(f"  Path: {receipt_path}")
        return
    
    print(f"✓ Receipt file found ({os.path.getsize(receipt_path)} bytes)")
    
    try:
        print("\nInitializing parser...")
        parser = ReceiptParser()
        
        print(f"  - Groq available: {parser.use_groq}")
        print(f"  - Tesseract available: {parser.use_tesseract}")
        print(f"  - Gemini Vision available: {parser.use_gemini}")
        
        print("\nParsing receipt... (this may take a few seconds)")
        
        with open(receipt_path, "rb") as f:
            image_data = f.read()
        
        result = await parser.parse_receipt(image_data)
        
        print("\n" + "=" * 60)
        print("✓ RECEIPT PARSED SUCCESSFULLY!")
        print("=" * 60)
        
        print("\nExtracted Data:")
        print(f"  Amount:      ${result.get('amount', 'N/A')}")
        print(f"  Category:    {result.get('category', 'N/A')}")
        print(f"  Description: {result.get('description', 'N/A')}")
        print(f"  Date:        {result.get('date', 'N/A')}")
        if 'merchant' in result:
            print(f"  Merchant:    {result.get('merchant', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("Full JSON Result:")
        print("=" * 60)
        import json
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ ERROR PARSING RECEIPT")
        print("=" * 60)
        print(f"\nError: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_specific_receipt())
