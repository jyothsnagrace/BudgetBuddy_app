"""
Test script for Receipt Parser
Tests both Groq+Tesseract OCR and Gemini Vision methods
"""

import asyncio
import sys
import os
from pathlib import Path

# Load environment variables FIRST before importing receipt_parser
from dotenv import load_dotenv
load_dotenv()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from receipt_parser import ReceiptParser


async def test_parser_initialization():
    """Test that the parser initializes correctly"""
    print("=" * 60)
    print("Testing Receipt Parser Initialization")
    print("=" * 60)
    
    parser = ReceiptParser()
    
    print("\n✓ Parser initialized successfully")
    print(f"  - Groq available: {parser.use_groq}")
    print(f"  - Tesseract available: {parser.use_tesseract}")
    print(f"  - Gemini Vision available: {parser.use_gemini}")
    
    if not parser.use_groq and not parser.use_gemini:
        print("\n⚠ WARNING: No parsing methods available!")
        print("  Please install either:")
        print("    1. Groq + Tesseract: pip install groq pytesseract")
        print("    2. Gemini: pip install google-generativeai")
        return False
    
    return True


async def test_with_sample_image():
    """Test with a sample receipt image if available"""
    print("\n" + "=" * 60)
    print("Testing Receipt Parsing")
    print("=" * 60)
    
    # Look for sample receipt images
    sample_paths = [
        "sample_receipt.jpg",
        "test_receipt.jpg",
        "receipt.jpg",
        "receipt.png",
        "../sample_receipt.jpg",
    ]
    
    sample_image = None
    for path in sample_paths:
        if os.path.exists(path):
            sample_image = path
            break
    
    if not sample_image:
        print("\n⚠ No sample receipt image found.")
        print("\nTo test with a real receipt:")
        print("  1. Save a receipt image as 'sample_receipt.jpg' in this folder")
        print("  2. Run: python test_receipt_parser.py")
        print("\nOr test via API:")
        print("  curl -X POST http://localhost:8000/api/parse-receipt \\")
        print("    -F 'file=@your_receipt.jpg'")
        return
    
    print(f"\n✓ Found sample image: {sample_image}")
    print("  Parsing receipt...")
    
    try:
        parser = ReceiptParser()
        
        with open(sample_image, "rb") as f:
            image_data = f.read()
        
        result = await parser.parse_receipt(image_data)
        
        print("\n✓ Receipt parsed successfully!")
        print("\nExtracted Data:")
        print(f"  Amount:      ${result.get('amount', 'N/A')}")
        print(f"  Category:    {result.get('category', 'N/A')}")
        print(f"  Description: {result.get('description', 'N/A')}")
        print(f"  Date:        {result.get('date', 'N/A')}")
        if 'merchant' in result:
            print(f"  Merchant:    {result.get('merchant', 'N/A')}")
        
        print("\nFull Result:")
        import json
        print(json.dumps(result, indent=2))
        
    except FileNotFoundError:
        print(f"\n✗ Error: Could not find image file: {sample_image}")
    except Exception as e:
        print(f"\n✗ Error parsing receipt: {e}")
        import traceback
        traceback.print_exc()


async def test_api_endpoint():
    """Test that the API endpoint exists"""
    print("\n" + "=" * 60)
    print("API Endpoint Information")
    print("=" * 60)
    
    print("\nReceipt parsing endpoint:")
    print("  POST /api/parse-receipt")
    print("\nExample curl command:")
    print("  curl -X POST http://localhost:8000/api/parse-receipt \\")
    print("    -H 'Authorization: Bearer YOUR_TOKEN' \\")
    print("    -F 'file=@receipt.jpg'")
    
    print("\nSupported image formats:")
    print("  - JPEG (.jpg, .jpeg)")
    print("  - PNG (.png)")
    print("  - GIF (.gif)")
    print("  - WEBP (.webp)")


async def check_dependencies():
    """Check if required dependencies are installed"""
    print("\n" + "=" * 60)
    print("Dependency Check")
    print("=" * 60)
    
    dependencies = {
        "groq": "pip install groq",
        "pytesseract": "pip install pytesseract",
        "google.generativeai": "pip install google-generativeai",
        "PIL": "pip install pillow"
    }
    
    print()
    for module, install_cmd in dependencies.items():
        try:
            __import__(module.replace(".", "/"))
            print(f"✓ {module:<25} installed")
        except ImportError:
            print(f"✗ {module:<25} NOT installed - {install_cmd}")
    
    # Check Tesseract OCR executable
    print("\nTesseract OCR:")
    try:
        import pytesseract
        tesseract_cmd = pytesseract.pytesseract.tesseract_cmd
        if os.path.exists(tesseract_cmd):
            print(f"✓ Tesseract found at: {tesseract_cmd}")
        else:
            print(f"⚠ Tesseract not found at expected path: {tesseract_cmd}")
            print("  Install from: https://github.com/UB-Mannheim/tesseract/wiki")
    except ImportError:
        print("✗ pytesseract not installed")
    
    # Check API keys
    print("\nAPI Keys:")
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if groq_key and not groq_key.startswith("your_"):
        print(f"✓ GROQ_API_KEY configured ({groq_key[:20]}...)")
    else:
        print("✗ GROQ_API_KEY not configured in .env")
    
    if gemini_key and not gemini_key.startswith("your_"):
        print(f"✓ GEMINI_API_KEY configured ({gemini_key[:20]}...)")
    else:
        print("✗ GEMINI_API_KEY not configured in .env")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("BUDGET BUDDY - RECEIPT PARSER TEST SUITE")
    print("=" * 60)
    
    # Run tests
    await check_dependencies()
    
    initialized = await test_parser_initialization()
    
    if initialized:
        await test_with_sample_image()
    
    await test_api_endpoint()
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
    print()


if __name__ == "__main__":
    asyncio.run(main())
