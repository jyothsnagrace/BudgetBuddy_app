import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv('.env')
key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=key)

print('Available models:')
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f'  - {m.name}')

# Test with gemini-2.5-flash
try:
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content('Say OK')
    print(f'\n✓ gemini-2.5-flash works: {response.text}')
except Exception as e:
    print(f'\n✗ gemini-2.5-flash failed: {e}')
