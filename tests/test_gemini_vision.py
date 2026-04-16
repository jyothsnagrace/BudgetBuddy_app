"""Test Gemini Vision API for receipt parsing"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import io
import base64

load_dotenv()

print("=" * 60)
print("🔍 Testing Gemini Vision API")
print("=" * 60)

# Check API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY not found in environment")
    exit(1)

print(f"✓ API Key: {api_key[:20]}...")

# Configure Gemini
genai.configure(api_key=api_key)

# List available models
print("\n📋 Available Gemini models:")
try:
    models = genai.list_models()
    vision_models = [m for m in models if 'gemini' in m.name and 'vision' in m.supported_generation_methods]
    
    if vision_models:
        print("  Vision-capable models:")
        for model in vision_models:
            print(f"    • {model.name}")
    else:
        print("  Checking all models...")
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                print(f"    • {model.name} - {model.supported_generation_methods}")
except Exception as e:
    print(f"  ⚠ Error listing models: {e}")

# Test vision with gemini-2.5-flash
print("\n🧪 Testing gemini-2.5-flash with image input...")
try:
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Test with a simple base64 image (1x1 white pixel PNG)
    # This is a minimal valid PNG
    test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    # Try to analyze it with inline data
    response = model.generate_content([
        {
            "mime_type": "image/png",
            "data": test_image_b64
        },
        "What do you see in this image?"
    ])
    
    print("✅ Vision API is working!")
    print(f"   Response: {response.text[:200]}...")
    
except Exception as e:
    print(f"❌ Vision test failed: {e}")
    print(f"   Error type: {type(e).__name__}")

print("\n" + "=" * 60)
